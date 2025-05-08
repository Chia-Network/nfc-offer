"""NDEF message handling for NFT data."""

import ndef
from typing import Dict, Optional
import logging
from .constants import (
    NDEF_MIME_TYPE,
    NDEF_CONFIG
)
from .exceptions import TagLockedException
import time


class NFDEFHandler:
    """Handle NDEF message formatting and parsing."""

    def __init__(self, reader):
        self.reader = reader

    def is_locked(self, tag_type: str) -> bool:
        """Check if tag is locked based on lock bits."""
        try:
            config = NDEF_CONFIG[tag_type]
            if 'lock_page' not in config:
                return False

            # Read static lock bits first (common to all tags)
            static_lock = self.reader.read_page(2)
            if static_lock:
                logging.debug(f"Static lock bits: {static_lock.hex()}")
                # Check only the lock bits (bytes 2 and 3)
                if static_lock[2] & 0xFF or static_lock[3] & 0xFF:
                    logging.info(f"Tag is locked (static lock bits: {static_lock.hex()})")
                    return True

            # For tags with dynamic lock bits
            if tag_type != 'ULTRALIGHT':
                lock_page = config['lock_page']
                lock_data = self.reader.read_page(lock_page)
                if lock_data:
                    logging.debug(f"Lock bits at page {lock_page:02x}: {lock_data.hex()}")

                    # Check dynamic lock bits based on tag type
                    if tag_type == 'NTAG213':
                        return bool(lock_data[0] & 0xFF)
                    elif tag_type in ('NTAG215', 'NTAG21x_2A'):
                        return bool(lock_data[0] & 0xFF or lock_data[1] & 0xFF)
                    elif tag_type == 'NTAG216':
                        return bool(lock_data[0] & 0xFF or lock_data[1] & 0xFF or lock_data[2] & 0xFF)

            # If no lock bits are set, try a test write
            test_page = config['data_start']
            test_data = self.reader.read_page(test_page)  # Read current data
            if test_data:
                # Try writing same data back
                if not self.reader.write_page(test_page, test_data):
                    logging.info("Tag appears to be write protected")
                    return True

            logging.debug("Tag is writable")
            return False

        except Exception as e:
            logging.debug(f"Lock check error: {e}")
            return False

    def clear_tag(self, tag_type: str) -> bool:
        """Clear all user memory of the tag."""
        try:
            # Check if tag is locked
            if self.is_locked(tag_type):
                raise TagLockedException("Tag is locked (dynamic lock bits set)")

            config = NDEF_CONFIG[tag_type]
            start_page = config['data_start']
            end_page = config['data_area'][1]

            # Clear all user memory pages
            clear_bytes = bytes([0x00] * 4)
            for page in range(start_page, end_page + 1):
                if not self.reader.write_page(page, clear_bytes):
                    logging.error(f"Failed to clear page {page:02x}")
                    return False
                time.sleep(0.002)  # Sleep to ensure write is complete

            logging.debug(f"Clearing tag memory (pages {start_page:02x}-{end_page:02x})")
            return True

        except TagLockedException as e:
            raise
        except Exception as e:
            logging.error(f"Failed to clear tag: {e}")
            return False

    def format_tag(self) -> bool:
        """Format tag for NDEF use."""
        try:
            tag_type = self.reader.get_tag_type()
            if not tag_type or tag_type not in NDEF_CONFIG:
                logging.error("Unsupported tag type for NDEF")
                return False

            config = NDEF_CONFIG[tag_type]
            cc_bytes = config['cc_bytes']

            # Clear tag memory but continue regardless
            self.clear_tag(tag_type)
            time.sleep(0.1)

            # Write Capability Container with retries
            max_retries = 3
            for attempt in range(max_retries):
                if self.reader.write_page(config['cc_page'], cc_bytes):
                    break
                if attempt == max_retries - 1:
                    logging.error("Failed to write capability container")
                    return False
                time.sleep(0.2)

            # Verify CC but accept different sizes
            response = self.reader.read_page(config['cc_page'])
            if not response:
                logging.error("Failed to read capability container")
                return False

            if response != cc_bytes:
                # Accept if only memory size differs and tag reports larger size
                if (response[0] == cc_bytes[0] and
                        response[1] == cc_bytes[1] and
                        response[3] == cc_bytes[3] and
                        response[2] > cc_bytes[2]):
                    return True
                else:
                    # Try one more time with reported size
                    adjusted_cc = bytes([cc_bytes[0], cc_bytes[1], response[2], cc_bytes[3]])
                    if not self.reader.write_page(config['cc_page'], adjusted_cc):
                        return False

            return True

        except Exception as e:
            logging.error(f"Failed to format tag: {e}")
            return False

    def write_ndef_message(self, nft_data: Dict[str, str]) -> bool:
        """Write NFT data as NDEF message."""
        try:
            tag_type = self.reader.get_tag_type()
            if not tag_type or tag_type not in NDEF_CONFIG:
                return False

            config = NDEF_CONFIG[tag_type]

            # Create the data string
            data = f"{nft_data['version']}{nft_data['nft_id']}{nft_data['offer']}"

            # Create language code + data payload
            payload = bytes([0x02, 0x65, 0x6E]) + data.encode('utf-8')  # 0x02 + "en" + data

            # Create NDEF record
            ndef_record = bytes([
                0xD1,  # NDEF header (MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01)
                0x01,  # Type length (1 byte for "T")
                len(payload),  # Payload length
                ord('T')  # Type ("T" for text record)
            ]) + payload

            # Add TLV wrapper
            tlv_data = bytes([
                0x03,  # NDEF Message TLV tag
                len(ndef_record),  # TLV length
                *ndef_record,  # NDEF message
                0xFE  # TLV terminator
            ])

            if len(tlv_data) > config['max_size']:
                logging.error(f"NDEF message too large for tag, max size {config['max_size']} got {len(tlv_data)}")
                return False

            # Write data
            current_page = config['data_start']
            for i in range(0, len(tlv_data), 4):
                chunk = tlv_data[i:i + 4].ljust(4, b'\x00')
                if not self.reader.write_page(current_page, chunk):
                    logging.error(f"Failed to write NDEF data at page {current_page:02x}")
                    return False
                current_page += 1
                time.sleep(0.002)  # Sleep to ensure write is complete

            logging.info("NDEF message written successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to write NDEF message: {e}")
            return False

    def read_ndef_message(self) -> Optional[Dict[str, str]]:
        """Read and parse NDEF message from tag."""
        try:
            tag_type = self.reader.get_tag_type()
            if not tag_type:
                logging.debug("Could not determine tag type")
                return None

            config = NDEF_CONFIG[tag_type]

            # Read first data page
            data = self.reader.read_page(config['data_start'])
            if not data:
                logging.debug("Could not read initial data page")
                return None

            logging.debug(f"Initial data page: {data.hex()}")

            # Check for NDEF TLV tag
            if data[0] != 0x03:
                logging.debug(f"Invalid NDEF TLV tag: {data[0]}")
                return None

            # Get message length
            msg_length = data[1]
            logging.debug(f"NDEF message length: {msg_length}")

            # Read full message
            message = bytearray()
            pages_needed = (msg_length + 2 + 3) // 4  # Include TLV header and round up

            for page in range(config['data_start'], config['data_start'] + pages_needed):
                page_data = self.reader.read_page(page)
                if not page_data:
                    logging.debug(f"Failed to read page {page}")
                    return None
                message.extend(page_data)

            logging.debug(f"Full message data: {message.hex()}")

            # Extract NDEF message (skip TLV header)
            ndef_message = message[2:msg_length + 2]
            logging.debug(f"NDEF message data: {ndef_message.hex()}")

            # Skip TLV header (2 bytes) and NDEF header (4 bytes)
            # Then skip language code (3 bytes: 0x02 + "en")
            payload_start = 9  # 2 (TLV) + 4 (NDEF) + 3 (lang)
            payload = message[payload_start:msg_length + 2]  # +2 for TLV header

            # Convert to text and parse
            text = payload.decode('utf-8')
            logging.debug(f"Decoded payload: {text}")

            # Parse the components
            version = text[:5]  # DT001
            nft_id = text[5:67]  # 64 characters
            offer = text[67:]  # remainder

            return {
                'version': version,
                'nft_id': nft_id,
                'offer': offer
            }

        except Exception as e:
            logging.error(f"Error reading NDEF message: {e}")
            logging.debug(f"Exception type: {type(e)}")
            return None

    def lock_tag(self, tag_type: str = None) -> bool:
        """Lock the tag to prevent further writes."""
        if not tag_type:
            tag_type = self.reader.get_tag_type()
            if not tag_type:
                return False

        try:
            config = NDEF_CONFIG[tag_type]

            # Set static lock bits first (common to all tags)
            static_lock = bytes([0x00, 0x00, 0xFF, 0xFF])
            for _ in range(3):  # Try up to 3 times
                if self.reader.write_page(2, static_lock):
                    break
                time.sleep(0.1)
            else:
                logging.error("Failed to set static lock bits")
                return False

            # Set dynamic lock bits for tags that support them
            if tag_type != 'ULTRALIGHT':
                lock_page = config['lock_page']
                lock_bytes = config['lock_bytes']

                for _ in range(3):  # Try up to 3 times
                    if self.reader.write_page(lock_page, lock_bytes):
                        break
                    time.sleep(0.1)
                else:
                    logging.error(f"Failed to set dynamic lock bits for {tag_type}")
                    return False

            # Verify the lock was successful
            time.sleep(0.1)  # Give the tag time to process
            if not self.is_locked(tag_type):
                logging.error("Lock verification failed")
                return False

            logging.info(f"Successfully locked {tag_type} tag")
            return True

        except Exception as e:
            logging.error(f"Failed to lock tag: {e}")
            return False
