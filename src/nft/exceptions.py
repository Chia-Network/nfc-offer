"""NFT-specific exceptions."""

class NFTError(Exception):
    """Base exception for NFT operations."""
    pass


class ValidationError(NFTError):
    """Invalid NFT data format."""
    pass
