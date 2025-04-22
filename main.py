#!/usr/bin/env python3
"""Main entry point for NFT-NFC operations."""

import logging
import argparse

from src.nfc.exceptions import TagLockedException, WriteError
from src.nfc.reader import NFCReader
from src.nft.data import NFTData
from src.nft.codec import encode_to_bytes, decode_from_bytes
from src.utils.logging import setup_logging
from src.utils.csv_handler import CSVHandler
import os
import csv


def handle_nfc_operation(args):
    """Handle NFC read/write operations."""
    reader = NFCReader()
    if not reader.connect():
        return

    try:
        if args.command == 'read':
            if args.uid:
                logging.info("Waiting for tag... Please touch an NFC tag to the reader then press enter or (q) to quit.")
                user_input = input()
                if user_input.lower() == 'q':
                    return
                data = reader.read_tag_uid()
                if data:
                    logging.info(f"UID: {data}")
            else:
                logging.info("Waiting for tag... Please touch an NFC tag to the reader then press enter or (q) to quit.")
                user_input = input()
                if user_input.lower() == 'q':
                    return
                tag_type = reader.get_tag_type()
                print(f"Tag Type: {tag_type}")
                if tag_type:
                    data = reader.read_data()
                    if data:
                        logging.info(f"Version: {data['version']}")
                        logging.info(f"NFT ID: {data['nft_id']}")
                        logging.info(f"Offer: {data['offer']}")

        elif args.command == 'write':
            logging.info("Waiting for tag... Please touch an NFC tag to the reader then press enter or (q) to quit.")
            user_input = input()
            if user_input.lower() == 'q':
                return
            tag_type = reader.get_tag_type()
            if tag_type:
                nft_data = {
                    'version': args.version,
                    'nft_id': args.nft_id,
                    'offer': args.offer
                }
                if reader.write_data(nft_data):
                    logging.info("Write successful")
                else:
                    logging.error("Write failed")

    except KeyboardInterrupt:
        logging.info("Operation stopped by user")
    finally:
        reader.close()


def handle_data_operation(args):
    """Handle data encode/decode operations without NFC."""
    try:
        if args.command == 'encode':
            nft_data = NFTData(
                version=args.version,
                nft_id=args.nft_id,
                offer=args.offer
            )
            encode_to_bytes(nft_data)

        elif args.command == 'decode':
            binary_data = bytes.fromhex(args.hex)
            decode_from_bytes(binary_data)

    except Exception as e:
        logging.error(f"Operation failed: {e}")


def validate_nft_data(data: dict, legacy: bool = False, strict: bool = True) -> bool:
    """Validate NFT data structure and contents."""
    try:
        nft_data = NFTData(
            version=data['version'],
            nft_id=data['nft_id'],
            offer=data['offer']
        )
        nft_data.validate_offer_length(strict=strict, legacy=legacy)
        return True
    except ValueError as e:
        logging.error(f"Invalid NFT data: {e}")
        return False


def handle_batch_operation(args):
    """Handle batch processing from CSV file."""
    reader = NFCReader()
    if not reader.connect():
        return

    try:
        csv_handler = CSVHandler(args.full_nfc_data_file)
        records = csv_handler.read_records()

        if not records:
            logging.error("No records found in CSV file")
            return

        # Validate all records first
        for record in records:
            if not validate_nft_data(record,
                                     legacy=args.legacy_offer,
                                     strict=not args.allow_any_length):
                logging.error("Validation failed - check offer code lengths")
                return

        logging.info(f"Processing NFC Writes: {len(records)} to be written")

        # Track success/failure counts
        total = len(records)
        success_count = 0
        fail_count = 0

        # Ask about locking at start
        lock_choice = 'no'
        while True:
            choice = input("\nLock tags to prevent future writes? (yes / default = no): ").lower()
            if not choice or choice in ['yes', 'no']:
                if choice == 'yes':
                    lock_choice = choice
                break
            print("Please answer 'yes' or 'no'")

        if lock_choice == 'yes':
            confirm = input("\nWARNING: Locking cannot be undone! Type 'LOCK' to confirm: ")
            if confirm != 'LOCK':
                logging.info("Locking cancelled - proceeding with write-only mode")
                lock_choice = 'no'

        # Keep track of processed UIDs
        processed_uids = set()

        while len(processed_uids) < total:
            logging.info("\nPlace tag on reader and press Enter (or 'q' to quit)...")
            user_input = input()
            if user_input.lower() == 'q':
                break

            uid = reader.read_tag_uid()
            if not uid:
                continue

            # Normalize scanned UID
            scanned_uid = uid.strip().upper()

            # Find matching record
            matching_record = None
            for record in records:
                expected_uid = record['uid'].strip().upper()
                if scanned_uid == expected_uid:
                    matching_record = record
                    break

            if not matching_record:
                logging.error(f"No matching UID found in records: {scanned_uid}")
                continue

            if scanned_uid in processed_uids:
                logging.error(f"This tag has already been processed: {scanned_uid}")
                continue

            try:
                # Write data
                nft_data = {
                    'version': matching_record['version'],
                    'nft_id': matching_record['nft_id'],
                    'offer': matching_record['offer']
                }
                logging.info(f"\nWriting to tag {scanned_uid}:")
                for key, value in nft_data.items():
                    logging.info(f"    {key.title()}: {value}")

                if reader.write_data(nft_data, lock=lock_choice == 'yes'):
                    success_count += 1
                    processed_uids.add(scanned_uid)
                    logging.info(f"Success ({success_count}/{total}, {fail_count} failed)")
                else:
                    fail_count += 1
                    processed_uids.add(scanned_uid)
                    logging.error(f"Write failed ({success_count}/{total}, {fail_count} failed)")

            except TagLockedException:
                logging.error("Tag is locked - cannot write")
                while True:
                    action = input("(s)kip/(q)uit: ").lower()
                    if action in ['s', 'q']:
                        break
                if action == 'q':
                    break
                if action == 's':
                    fail_count += 1
                    processed_uids.add(scanned_uid)
                    logging.info(f"Skipped ({success_count}/{total}, {fail_count} failed)")

            except WriteError as e:
                logging.error(f"\nWrite failed: {str(e)}")
                while True:
                    action = input("Choose action (r)etry/(s)kip/(q)uit: ").lower()
                    if action in ['r', 's', 'q']:
                        break
                if action == 'q':
                    break
                if action == 's':
                    fail_count += 1
                    processed_uids.add(scanned_uid)
                    logging.info(f"Skipped ({success_count}/{total}, {fail_count} failed)")

        # Final summary
        logging.info(
            f"\nOperation complete: {success_count} successful, {fail_count} failed, {total - success_count - fail_count} remaining")

    except KeyboardInterrupt:
        logging.info("\nOperation stopped by user")
    finally:
        reader.close()


def handle_scan_uids(args):
    """Scan NFCs and record UIDs to CSV file."""
    output_file = args.output or "output/nfc_scan_output.csv"

    # Load NFT data template if provided
    nft_data_rows = []
    if args.nft_data_file:
        try:
            with open(args.nft_data_file, 'r') as f:
                reader = csv.DictReader(f)
                nft_data_rows = list(reader)
            total_nfts = len(nft_data_rows)
            logging.info(f"Loaded {total_nfts} NFT records from data file")
        except Exception as e:
            logging.error(f"Failed to load template file: {e}")
            return

    # Initialize or read existing CSV
    existing_uids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_uids.add(row['uid'])

        # Validate we haven't exceeded NFT data rows
        if nft_data_rows and len(existing_uids) >= len(nft_data_rows):
            logging.error(
                f"Already scanned {len(existing_uids)} UIDs - matches or exceeds available NFT records ({len(nft_data_rows)})")
            return

    # Initialize reader
    reader = NFCReader()
    if not reader.connect():
        logging.error("Failed to find NFC reader")
        return

    try:
        # Create/Open CSV file
        with open(output_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['uid', 'version', 'nft_id', 'offer'])
            # Write header if file is new
            if f.tell() == 0:
                writer.writeheader()

            count = len(existing_uids)
            nft_index = count  # Start from where we left off

            if nft_data_rows:
                remaining = len(nft_data_rows) - count
                logging.info(
                    f"\nStarting scan. {count} UIDs already in file, {remaining} NFT records remaining to assign.")
            else:
                logging.info(f"\nStarting scan. {count} UIDs already in file, {count} NFT records remaining to assign.")

            while True:
                if nft_data_rows:
                    if nft_index >= len(nft_data_rows):
                        logging.info("\nAll NFT records have been assigned!")
                        break
                    remaining = len(nft_data_rows) - nft_index
                    logging.info(f"\nNFT records remaining: {remaining}")

                logging.info("Place NFC tag on reader and press Enter to scan (or 'q' to quit)...")
                choice = input().lower()
                if choice == 'q':
                    if nft_data_rows and nft_index < len(nft_data_rows):
                        remaining = len(nft_data_rows) - nft_index
                        logging.warning(f"\nScan stopped with {remaining} NFT records still unassigned")
                    break

                # Read tag UID
                try:
                    uid = reader.read_tag_uid()
                    if not uid:
                        logging.error("Failed to read tag. Please try again.")
                        continue

                    tag_type = reader.get_tag_type()
                    if tag_type and reader.ndef_handler.is_locked(tag_type):
                        logging.warning(f"Tag {uid} is locked - skipping")
                        continue

                    if uid in existing_uids:
                        logging.warning(f"UID already scanned: {uid}")
                        continue

                    # Get NFT data from template or use empty values
                    nft_data = {
                        'uid': uid.strip(),
                        'version': (args.version or NFTData.DEFAULT_VERSION).strip(),
                        'nft_id': '',
                        'offer': ''
                    }

                    if nft_data_rows:
                        nft_data.update({
                            'nft_id': nft_data_rows[nft_index]['nft_id'].strip(),
                            'offer': nft_data_rows[nft_index]['offer'].strip()
                        })
                        nft_index += 1

                    # Write new row
                    writer.writerow(nft_data)
                    f.flush()  # Ensure immediate write to file

                    existing_uids.add(uid)
                    count += 1
                    logging.info(f"Successfully recorded UID: {uid}")
                    if nft_data_rows:
                        logging.info(f"Assigned NFT ID: {nft_data['nft_id']}")
                        logging.info(f"Assigned offer: {nft_data['offer']}")
                        logging.info(f"NFTs remaining: {len(nft_data_rows) - count}")
                    else:
                        logging.info(f"Total UIDs scanned: {count}")
                    logging.info("You can now remove the tag")

                except Exception as e:
                    logging.error(f"Error reading tag: {e}")

    except KeyboardInterrupt:
        if nft_data_rows and nft_index < len(nft_data_rows):
            remaining = len(nft_data_rows) - nft_index
            logging.warning(f"\nScan stopped with {remaining} NFT records still unassigned")
        logging.info("\nOperation stopped by user")
    finally:
        reader.close()

    if nft_data_rows:
        remaining = len(nft_data_rows) - count
        if remaining > 0:
            logging.warning(f"\nScan complete but {remaining} NFT records remain unassigned")
        else:
            logging.info("\nScan complete - all NFT records assigned!")
    else:
        logging.info(f"\nScan complete. Total UIDs in file: {len(existing_uids)}")


def handle_info_command(args):
    """Display detailed tag information."""
    reader = NFCReader()
    if not reader.connect():
        return

    try:
        logging.info("\nPlace tag on reader and press Enter...")
        input()

        info = reader.get_detailed_tag_info()
        if info:
            logging.info("\nTag Information:")
            logging.info("-" * 40)
            for key, value in info.items():
                logging.info(f"{key.replace('_', ' ').title()}: {value}")
        else:
            logging.error("Failed to read tag information")

    except KeyboardInterrupt:
        logging.info("\nOperation stopped by user")
    finally:
        reader.close()


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(description='NFT-NFC Operations')
    subparsers = parser.add_subparsers(dest='command')

    # Common arguments for commands that use offer codes
    offer_args = argparse.ArgumentParser(add_help=False)
    offer_args.add_argument('--legacy-offer', action='store_true',
                            help='Use legacy 5-character offer codes')
    offer_args.add_argument('--allow-any-length', action='store_true',
                            help='Allow non-standard offer code lengths')

    # NFC Commands
    read_parser = subparsers.add_parser('read', help='Read NFC tag')
    read_parser.add_argument('--uid', action='store_true',
                             help='Only read tag UID')

    write_parser = subparsers.add_parser('write', parents=[offer_args], help='Write to NFC tag')
    write_parser.add_argument('--version', '-v', default=NFTData.DEFAULT_VERSION,
                              help=f'Version string (default: {NFTData.DEFAULT_VERSION})')
    write_parser.add_argument('--nft-id', '-n', required=True,
                              help='NFT ID or 32-byte hash')
    write_parser.add_argument('--offer', '-o', required=True,
                              help='Offer code (default 64 chars, use --legacy-offer for 5 chars)')

    # Batch Command
    batch_parser = subparsers.add_parser('batch', parents=[offer_args], help='Process NFCs from CSV file')
    batch_parser.add_argument('--full-nfc-data-file', '-f', required=True,
                              help='Path to CSV file containing full NFC data')
    batch_parser.add_argument('--force', action='store_true',
                              help='Force overwrite of protected tags')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan NFCs and record UIDs to CSV')
    scan_parser.add_argument('--output', '-o',
                             help='Output CSV file (default: nfc_scan_output.csv)')
    scan_parser.add_argument('--nft-data-file', '-d', required=True,
                             help='CSV file containing NFT IDs and offer codes')
    scan_parser.add_argument('--version', '-v',
                             help=f'Version string (default: {NFTData.DEFAULT_VERSION})')

    # Add info command
    subparsers.add_parser('info', help='Display detailed tag information')

    return parser


def validate_args(args):
    """Validate command line arguments."""
    if not args.command:
        return False, "No command specified"

    if args.command == 'write':
        if not args.nft_id:
            return False, "NFT ID is required"
        if not args.offer:
            return False, "Offer code is required"

    elif args.command == 'batch':
        if not args.full_nfc_data_file:
            return False, "NFT data file is required"
        if not os.path.exists(args.full_nfc_data_file):
            return False, f"NFT data file not found: {args.full_nfc_data_file}"

    elif args.command == 'scan':
        if not args.nft_data_file:
            return False, "NFT data file is required"
        if not os.path.exists(args.nft_data_file):
            return False, f"NFT data file not found: {args.nft_data_file}"

    return True, ""


def main():
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments before setting up logging
    valid, error = validate_args(args)
    if not valid:
        if error:
            print(f"Error: {error}")
        parser.print_help()
        return

    setup_logging()

    try:
        if args.command == 'scan':
            handle_scan_uids(args)
        elif args.command == 'batch':
            handle_batch_operation(args)
        elif args.command in ['read', 'write']:
            handle_nfc_operation(args)
        elif args.command == 'info':
            handle_info_command(args)
        else:
            handle_data_operation(args)

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
    except PermissionError as e:
        logging.error(f"Permission denied: {e}")
    except Exception as e:
        logging.error(f"Operation failed: {e}")


if __name__ == "__main__":
    main()
