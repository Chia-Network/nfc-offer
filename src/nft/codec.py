"""NFT data encoding and decoding functions."""

import logging
from ..utils.bech32m import decode_puzzle_hash, encode_puzzle_hash  # Use local bech32m implementation
from .data import NFTData
from .exceptions import EncodingError, DecodingError


def encode_to_bytes(nft_data: NFTData) -> bytes:
    """Encode NFT data to binary format."""
    try:
        # Encode version (5 bytes)
        version_bytes = nft_data.version.encode('utf-8')
        
        # Convert NFT ID to hash bytes (32 bytes)
        nft_hash = decode_puzzle_hash(nft_data.nft_id)
        if not nft_hash:
            raise EncodingError("Invalid NFT ID format")
            
        # Encode offer code (5 bytes)
        offer_bytes = nft_data.offer.encode('utf-8')
        
        # Combine all parts
        result = version_bytes + nft_hash + offer_bytes
        
        # Log encoding details with indentation
        logging.info("\nWriting to NFC:")
        logging.info("    Version: %s", nft_data.version)
        logging.info("    NFT ID:  %s", nft_data.nft_id)
        logging.info("    Offer:   %s", nft_data.offer)
        
        return result
        
    except Exception as e:
        raise EncodingError(f"Failed to encode NFT data: {str(e)}")


def decode_from_bytes(data: bytes) -> NFTData:
    """Decode binary format to NFT data."""
    try:
        if len(data) != 42:
            raise DecodingError("Invalid data length")
            
        # Split data into components
        version = data[:5].decode('utf-8')
        nft_hash = data[5:37]
        offer = data[37:].decode('utf-8')
        
        # Convert hash to NFT ID using bech32m
        nft_id = encode_puzzle_hash(nft_hash, "nft")
        if not nft_id:
            raise DecodingError("Failed to encode NFT ID")
        
        logging.info("\nDECODING:")
        logging.info("-" * 50)
        logging.info("Encoded Data:")
        logging.info(f"   Version Bytes:          {' '.join([f'{b:02X}' for b in data[:5]])}")
        logging.info(f"   NFT Hash Bytes:         {' '.join([f'{b:02X}' for b in nft_hash])}")
        logging.info(f"   Offer Short Code Bytes: {' '.join([f'{b:02X}' for b in data[37:]])}")
        logging.info("\nDecoded format:")
        logging.info(f"   Version:  {version}")
        logging.info(f"   NFT ID:   {nft_id}")
        logging.info(f"   NFT Hash: {nft_hash.hex()}")
        logging.info(f"   Offer:    {offer}")
        
        # Create and validate NFT data
        return NFTData(
            version=version,
            nft_id=nft_id,
            offer=offer
        )
        
    except Exception as e:
        raise DecodingError(f"Failed to decode NFT data: {str(e)}")
