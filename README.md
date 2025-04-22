# NFT-NFC Writer

Tool for writing NFT data to NFC tags and managing tag operations.

## Features

- Write NFT data to NFC tags (NTAG213/215/216 and NTAG21x Type 2A)
- Batch processing from CSV files
- Optional permanent tag locking
- Tag scanning and UID collection
- Detailed tag information display

## Requirements

- Python 3.8+
- ACR122U NFC Reader
- NTAG213/215/216 or NTAG21x Type 2A compatible NFC tags
- Required Python packages (see requirements.txt)

## Installation

1. Install required packages:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
.\venv\Scripts\activate  # Windows
pip install -e .
```

2. Connect ACR122U NFC reader

## Usage

Note - this process expects you have a csv file with your NFT ids and offer short codes in the format shown in /examples/nft_data.csv and shown below.

CSV format for nft_data.csv:
```csv
nft_id,offer
nft1vyet0xdu0cady88hd7mm0xaauql8547hjlk8gt2ujcn5zvm8ly7s7krg4j,b5bfc1c6b79852c1e417234ba78b8716b97451e399585641e2b694b8b1e4123c
```

### Scan NFC Tags to Generate NFC Data File
In this process you will scan all NFC tags to be used, the UIDs will be recorded and combined with the nft_data.csv file to generate the nfc_data.csv file.
This results in a nfc_scan_output.csv file created in the root of the project and to be used in the batch command.
```bash
python main.py scan --nft-data-file/-d <nft_data_file> [--output/-o <output>] [--version/-v <version>]
```

To use the example data run:
```bash
python main.py scan -d ./examples/nfc_data.csv
```

### Batch Writing of NFC Tags
This process will write the assigned tag data to the NFC tags. 
Note this is a separate step for added security.
```bash
python main.py batch --full-nfc-data-file/-f <full_nfc_data_file> [--legacy-offer] [--allow-any-length] [--force]
```

To use the example data run (must complete the scan process first):
```bash
python main.py batch -f ./output/nfc_scan_output.csv
```

CSV format for nfc_data.csv:
```csv
uid,version,nft_id,offer
04CD7215BD2A81,DT001,nft1vyet0xdu0cady88hd7mm0xaauql8547hjlk8gt2ujcn5zvm8ly7s7krg4j,b5bfc1c6b79852c1e417234ba78b8716b97451e399585641e2b694b8b1e4123c
```

### Single Tag Operations
Write to a single tag (note single tag write does not support locking at this time):
```bash
python main.py write --nft-id/-n <id> --offer/-o <code> [--version/-v <ver>]
```

Read a tag:
```bash
python main.py read [--uid]
```

### Tag Information
Display detailed tag info:
```bash
python main.py info
```

## Tag Locking

Tags can be permanently locked during writing to prevent future modifications using dynamic lock bits. This is optional for batch operations and requires explicit confirmation.

**Warning**: Locked tags cannot be unlocked or rewritten. Test locking on sample tags first.

## Operation Logs

All operations are logged to `output/operations.log` with timestamps and detailed information, including:
- Write operations and results
- Lock status and verification
- Error conditions and handling
- Operation summaries

## Error Handling

- Tag not found/removed: Retry prompt
- Write failures: Retry/skip options
- Locked tags: Skip/quit options
- Invalid data: Clear error messages

## Notes

- Keep tags on reader until operation completes
- Verify tag type compatibility (NTAG213/215/216 or NTAG21x Type 2A)
- Back up data before batch operations
- Test locking on sample tags first (locking prevents future writing of the tags)

## Project Structure
```
nfc-offer/
├── src/
│   ├── nfc/          # NFC operations
│   ├── nft/          # NFT data handling
│   └── utils/        # Utilities (logging)
├── examples/         # Example scripts
├── output/           # Output directory for NFT/NFC data and logs
├── main.py           # CLI interface
└── README.md
```

## Troubleshooting

### MacOS Issues
If you encounter USB/NFC reader issues:
1. Ensure libusb is installed: `brew install libusb`
2. Check reader connection: `python main.py read --uid`
3. Try running with sudo if permission issues occur

### Common Errors
- "No NFC readers found": Check USB connection and driver installation
- "Failed to write data": Ensure tag is properly positioned and supported
- "Tag is locked": Tag has been permanently locked and cannot be written
- "Invalid NFT data format": Check input data format matches specification

## NDEF Support
The tool uses NDEF formatting for compatibility with NFC tools and readers:

- Standard NFC Forum Type 2 format
- Compatible with NFC tools and readers
- Custom MIME type: application/x-nft-data
- Automatic format detection when reading

### Supported Tag Types
The tool supports the following NFC tag types (note only the NTAG 213 has been extensively tested):
- NTAG213 (144 bytes)
- NTAG215 (504 bytes)
- NTAG216 (888 bytes)
- NTAG21x Type 2A (1016 bytes)

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

