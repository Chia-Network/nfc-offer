"""NFC-related constants and configuration."""
from typing import Dict, Any

# APDU Commands for NFC operations
APDU_COMMANDS = {
    'GET_UID': [0xFF, 0xCA, 0x00, 0x00, 0x00],
    'READ_PAGE': [0xFF, 0xB0, 0x00],  # Needs page number and length
    'READ_PAGE_ALT': [0xFF, 0x30, 0x00],  # Alternative read command
    'WRITE_PAGE': [0xFF, 0xD6, 0x00],  # Needs page number, length, and data
    'WRITE_PAGE_ALT': [0xFF, 0xA2, 0x00]  # Alternative write command
}

# Supported tag types
TAG_TYPES = {
    'NTAG213': 'NTAG213',
    'NTAG215': 'NTAG215',
    'NTAG216': 'NTAG216',
    'NTAG21x_2A': 'NTAG21x Type 2A',
    'ULTRALIGHT': 'MIFARE Ultralight'
}

# NDEF Type Names
NDEF_TNF_WELL_KNOWN = 0x01
NDEF_TNF_MIME_MEDIA = 0x02
NDEF_TYPE_TEXT = 'T'
NDEF_TYPE_URI = 'U'
NDEF_MIME_TYPE = 'application/x-nft-data'

# NDEF configuration
NDEF_CONFIG = {
    'NTAG213': {
        'data_start': 0x04,
        'data_area': (0x04, 0x27),
        'cc_page': 0x03,
        'cc_bytes': bytes([0xE1, 0x10, 0x12, 0x00]),
        'max_size': 144,
        'lock_page': 0x28,
        'lock_bytes': bytes([0xFF, 0xFF, 0x00, 0x00])
    },
    'NTAG215': {
        'data_start': 0x04,
        'data_area': (0x04, 0x81),
        'cc_page': 0x03,
        'cc_bytes': bytes([0xE1, 0x10, 0x3E, 0x00]),
        'max_size': 504,
        'lock_page': 0x82,
        'lock_bytes': bytes([0xFF, 0xFF, 0x00, 0x00])
    },
    'NTAG216': {
        'data_start': 0x04,
        'data_area': (0x04, 0xE1),
        'cc_page': 0x03,
        'cc_bytes': bytes([0xE1, 0x10, 0x6D, 0x00]),
        'max_size': 888,
        'lock_page': 0xE2,
        'lock_bytes': bytes([0xFF, 0xFF, 0xFF, 0x00])
    },
    'ULTRALIGHT': {
        'data_start': 0x04,
        'data_area': (0x04, 0x0F),
        'cc_page': 0x03,
        'cc_bytes': bytes([0xE1, 0x10, 0x06, 0x00]),
        'max_size': 48,
        'lock_page': 0x02,  # Static lock bytes
        'lock_bytes': bytes([0xFF, 0xFF, 0x00, 0x00])
    },
    'NTAG21x_2A': {
        'data_start': 0x04,
        'data_area': (0x04, 0x81),
        'cc_page': 0x03,
        'cc_bytes': bytes([0xE1, 0x11, 0x7F, 0x00]),
        'max_size': 1016,
        'lock_page': 0x82,
        'lock_bytes': bytes([0xFF, 0xFF, 0x00, 0x00])
    }
}
