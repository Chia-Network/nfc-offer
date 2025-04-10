"""CSV processing for batch NFC operations."""

import csv
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import os


@dataclass
class CSVRecord:
    """Single record from CSV file."""
    uid: str
    version: str
    nft_id: str
    offer: str
    status: str = "pending"  # pending, success, failed, skipped
    message: str = ""


class CSVHandler:
    """Handle CSV processing."""
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)

    def read_records(self) -> List[Dict[str, str]]:
        """Read records from CSV file."""
        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                if not records:
                    logging.error("No records found in CSV file")
                return records
                
        except FileNotFoundError:
            logging.error(f"CSV file not found: {self.csv_path}")
            return []
        except Exception as e:
            logging.error(f"Failed to read CSV file: {e}")
            return []

    def write_record(self, record: Dict[str, str]) -> bool:
        """Write a single record to CSV file."""
        try:
            file_exists = self.csv_path.exists()
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['uid', 'version', 'nft_id', 'offer'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow(record)
            return True
        except Exception as e:
            logging.error(f"Failed to write record: {e}")
            return False

    def get_record_for_uid(self, uid: str) -> Optional[CSVRecord]:
        """Get record matching NFC UID."""
        return self.records.get(uid)

    def update_record_status(self, uid: str, status: str, message: str = "") -> None:
        """Update record status."""
        if uid in self.records:
            self.records[uid].status = status
            self.records[uid].message = message
            # No progress saving needed

    def get_summary(self) -> dict:
        """Get processing summary."""
        summary = {
            'total': len(self.records),
            'pending': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for record in self.records.values():
            summary[record.status] += 1
            
        return summary

    def write_records(self, records: List[Dict[str, str]]) -> bool:
        """Write multiple records to CSV file.
        
        Args:
            records: List of dictionaries containing record data
            
        Returns:
            bool: True if all writes successful
        """
        try:
            # Check if file exists to determine if header needed
            file_exists = os.path.exists(self.csv_path)
            
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['uid', 'version', 'nft_id', 'offer'])
                
                if not file_exists:
                    writer.writeheader()
                    
                writer.writerows(records)
            return True
            
        except Exception as e:
            logging.error(f"Failed to write records: {e}")
            return False
