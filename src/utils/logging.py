"""Logging configuration."""

import logging
import sys
from pathlib import Path


class StripNewlinesFilter(logging.Filter):
    """Filter to remove leading/trailing newlines from log messages."""
    def filter(self, record):
        record.msg = record.msg.strip()
        return True


class ImmediateHandler(logging.StreamHandler):
    """Handler that flushes immediately."""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging():
    """Configure logging for both console and file output."""
    # Create logs directory if it doesn't exist
    log_dir = Path('output')
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.root.setLevel(logging.DEBUG)
    
    # Console handler - INFO level, minimal format
    console_handler = ImmediateHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler - DEBUG level, detailed format
    file_handler = ImmediateHandler(open('output/operations.log', 'a', encoding='utf-8'))
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(StripNewlinesFilter())
    
    # Clear any existing handlers
    logging.root.handlers = []
    
    # Add handlers
    logging.root.addHandler(console_handler)
    logging.root.addHandler(file_handler)

    # Add session separator to log file
    logging.info("="*80)
    logging.info("Starting new NFC operation session")
