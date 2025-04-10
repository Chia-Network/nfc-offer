"""NFT-specific exceptions."""

class NFTError(Exception):
    """Base exception for NFT operations."""
    pass


class ValidationError(NFTError):
    """Invalid NFT data format."""
    pass


class EncodingError(NFTError):
    """Failed to encode NFT data."""
    pass


class DecodingError(NFTError):
    """Failed to decode NFT data."""
    pass
