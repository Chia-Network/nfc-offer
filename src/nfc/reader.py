"""NFC reader interface and operations."""

import logging
from typing import Optional, Tuple, Dict
from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.Exceptions import NoCardException

from .constants import APDU_COMMANDS
from .exceptions import *
from .ndef_utils import NFDEFHandler


class NFCReader:
    """Interface with NFC reader and tags."""

    def __init__(self):
        self.reader = None
        self.connection = None
        self.ndef_handler = None

    def connect(self) -> bool:
        """Connect to NFC reader."""
        try:
            available_readers = readers()
            if not available_readers:
                raise ReaderNotFoundError("No NFC readers found")
            
            self.reader = available_readers[0]
            logging.info(f"Found reader: {self.reader}")
            
            self.connection = self.reader.createConnection()
            try:
                self.connection.connect()
                logging.info("Successfully connected to reader")
            except NoCardException:
                # This is expected when no card is present
                pass
            self.ndef_handler = NFDEFHandler(self)
            return True

        except Exception as e:
            if not isinstance(e, NoCardException):
                raise ReaderConnectionError(f"Failed to connect to reader: {str(e)}")
            return False

    def _transmit(self, command: list, description: str) -> Tuple[list, int, int]:
        """Helper method to transmit APDU commands and handle errors."""
        try:
            if not self.connection:
                raise ReaderConnectionError("Reader not connected")
            
            try:
                # Try to connect if not already connected
                self.connection.connect()
            except NoCardException:
                raise NFCError("No card detected")
                
            response, sw1, sw2 = self.connection.transmit(command)
            if sw1 != 0x90:
                logging.debug(f"{description} failed. Status: {hex(sw1)}{hex(sw2)}")
            return response, sw1, sw2
            
        except Exception as e:
            raise NFCError(f"Command transmission error: {str(e)}")

    def read_tag_uid(self) -> Optional[str]:
        """Read NFC tag UID."""
        response, sw1, sw2 = self._transmit(
            APDU_COMMANDS['GET_UID'],
            "Reading UID"
        )
        
        if sw1 == 0x90:
            return toHexString(response)
        return None

    def get_tag_type(self) -> Optional[str]:
        """Identify the type of tag."""
        uid = self.read_tag_uid()
        if not uid:
            return None

        # Read manufacturer data
        response = self.read_page(0)
        if not response or len(uid.split()) != 7:
            return None

        if response[0] == 0x04:  # NTAG21x family
            # Read version data to determine exact variant
            version_data = []
            for page in range(0, 3):
                data = self.read_page(page)
                if data:
                    version_data.extend(data)

            if len(version_data) >= 8:
                prod_type = version_data[6]
                if prod_type == 0x0F:
                    return 'NTAG213'
                elif prod_type == 0x11:
                    return 'NTAG215'
                elif prod_type == 0x13:
                    return 'NTAG216'
                elif prod_type == 0x2A:  # Your specific variant
                    return 'NTAG21x_2A'
                
            # If version info unavailable or unknown type, try to identify by memory size
            cc_data = self.read_page(3)
            if cc_data and cc_data[0] == 0xE1:
                memory_size = cc_data[2] * 8  # Size in bytes
                if memory_size == 1016:  # Your tag appears to have this size
                    return 'NTAG21x_2A'
                elif memory_size == 144:
                    return 'NTAG213'
                elif memory_size == 504:
                    return 'NTAG215'
                
        return 'ULTRALIGHT'  # Default to Ultralight if unknown

    def read_page(self, page: int) -> Optional[bytes]:
        """Read a single page from the tag."""
        for cmd_base in [APDU_COMMANDS['READ_PAGE'], APDU_COMMANDS['READ_PAGE_ALT']]:
            cmd = cmd_base + [page, 4]  # 4 bytes per page
            response, sw1, sw2 = self._transmit(cmd, f"Reading page {page}")
            if sw1 == 0x90:
                return bytes(response)
        return None

    def write_page(self, page: int, data: bytes) -> bool:
        """Write data to a single page."""
        for cmd_base in [APDU_COMMANDS['WRITE_PAGE'], APDU_COMMANDS['WRITE_PAGE_ALT']]:
            cmd = cmd_base + [page, len(data)] + list(data)
            _, sw1, _ = self._transmit(cmd, f"Writing page {page}")
            if sw1 == 0x90:
                return True
        return False

    def read_data(self) -> Optional[Dict[str, str]]:
        """Read NDEF formatted data from NFC tag."""
        try:
            if not self.ndef_handler:
                return None
                
            nft_data = self.ndef_handler.read_ndef_message()
            if nft_data:
                logging.info("Successfully read NDEF data")
                return nft_data
            return None

        except Exception as e:
            logging.error(f"Failed to read data: {e}")
            return None

    def write_data(self, nft_data: dict, lock: bool = False) -> bool:
        """Write NFT data to tag and optionally lock it."""
        try:
            tag_type = self.get_tag_type()
            if not tag_type:
                logging.error("Could not determine tag type")
                return False
            
            # Check if tag is already locked
            if self.ndef_handler.is_locked(tag_type):
                logging.error("Tag is already locked")
                return False
            
            # Format and write NDEF data
            if not self.ndef_handler.format_tag():
                logging.error("Failed to format tag")
                return False
            
            if not self.ndef_handler.write_ndef_message(nft_data):
                logging.error("Failed to write NDEF message")
                return False
            
            # Lock the tag if requested
            if lock:
                if not self.ndef_handler.lock_tag(tag_type):
                    logging.error("Failed to lock tag - data was written but tag remains rewritable")
                    return False
                logging.info("Tag successfully written and locked")
            else:
                logging.info("Tag successfully written (unlocked)")
            
            return True
        
        except Exception as e:
            logging.error(f"Write failed: {e}")
            return False

    def close(self):
        """Close the connection to the reader."""
        if self.connection:
            self.connection.disconnect()
            logging.info("Reader connection closed")

    def get_detailed_tag_info(self) -> Dict[str, str]:
        """Get detailed tag information including exact type and configuration."""
        try:
            uid = self.read_tag_uid()
            if not uid:
                logging.error("Failed to read UID")
                return {}

            # Read manufacturer data (page 0)
            mfg_data = self.read_page(0)
            if not mfg_data:
                logging.error("Failed to read manufacturer data")
                return {}

            # Read capability container (page 3)
            cc_data = self.read_page(3)
            if not cc_data:
                logging.error("Failed to read capability container")
                return {}

            # Read version data (pages 0x00-0x02)
            version_data = []
            for page in range(0, 3):
                data = self.read_page(page)
                if data:
                    version_data.extend(data)

            info = {
                'uid': uid,
                'manufacturer_data': mfg_data.hex(),
                'cc_bytes': cc_data.hex(),
                'version_data': bytes(version_data).hex()
            }

            # Identify exact tag type
            if mfg_data[0] == 0x04:  # NTAG21x family
                if len(version_data) >= 8:
                    prod_type = version_data[6]
                    if prod_type == 0x0F:
                        info['type'] = 'NTAG213'
                        info['memory_size'] = '144 bytes'
                    elif prod_type == 0x11:
                        info['type'] = 'NTAG215'
                        info['memory_size'] = '504 bytes'
                    elif prod_type == 0x13:
                        info['type'] = 'NTAG216'
                        info['memory_size'] = '888 bytes'
                    else:
                        info['type'] = f'Unknown NTAG21x (type: {hex(prod_type)})'
                else:
                    info['type'] = 'NTAG21x (version info unavailable)'
            else:
                info['type'] = 'Unknown'

            # Check for locked/protected areas
            static_lock_bytes = self.read_page(2)
            if static_lock_bytes:
                info['static_lock'] = static_lock_bytes.hex()

            # For NTAG21x, check dynamic lock bytes
            if 'NTAG' in info.get('type', ''):
                if info['type'] == 'NTAG213':
                    lock_page = 0x28
                elif info['type'] == 'NTAG215':
                    lock_page = 0x82
                elif info['type'] == 'NTAG216':
                    lock_page = 0xE2
                else:
                    lock_page = None

                if lock_page:
                    dynamic_lock_bytes = self.read_page(lock_page)
                    if dynamic_lock_bytes:
                        info['dynamic_lock'] = dynamic_lock_bytes.hex()

            return info

        except Exception as e:
            logging.error(f"Failed to get detailed tag info: {e}")
            return {}
