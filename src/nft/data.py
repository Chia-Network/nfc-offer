"""NFT data structure and validation."""

from dataclasses import dataclass
from .exceptions import ValidationError


@dataclass
class NFTData:
    """NFT data structure."""
    version: str
    nft_id: str
    offer: str
    
    DEFAULT_VERSION = "DT001"
    DEFAULT_OFFER_LENGTH = 64  # New default length
    LEGACY_OFFER_LENGTH = 5    # Original length
    MAX_OFFER_LENGTH = 64      # Hardcoded to the default length
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.version:
            self.version = self.DEFAULT_VERSION
            
        if not self.nft_id:
            raise ValueError("NFT ID is required")
            
        if not self.offer:
            raise ValueError("Offer code is required")
            
        # Validate lengths
        version_length = len(self.version)
        if version_length > 5:
            raise ValueError("Version string too long (max 5 characters)")

        nft_length = len(self.nft_id)
        if nft_length > 62:
            raise ValueError(f"NFT ID too long (max 62 characters expected, got {nft_length})")
            
        # Offer code validation is now handled separately
            
    def validate_offer_length(self, strict: bool = True, legacy: bool = False) -> bool:
        """
        Validate offer code length.
        
        Args:
            strict: If True, enforce exact length. If False, only check maximum.
            legacy: If True, use LEGACY_OFFER_LENGTH, else use DEFAULT_OFFER_LENGTH
        """
        offer_len = len(self.offer)
        target_len = self.LEGACY_OFFER_LENGTH if legacy else self.DEFAULT_OFFER_LENGTH
        
        if strict:
            if offer_len != target_len:
                raise ValueError(f"Offer code must be exactly {target_len} characters, got {offer_len}")
        elif offer_len > self.MAX_OFFER_LENGTH:
            raise ValueError(f"Offer code too long (max {self.MAX_OFFER_LENGTH} characters expected, got {offer_len})")
            
        return True

    def validate(self):
        """Validate NFT data format."""
        if len(self.version) != 5:
            raise ValidationError("Version must be 5 characters")
        if not self.nft_id.startswith("nft1"):
            raise ValidationError("NFT ID must start with 'nft1'")
        if not self.validate_offer_length():
            raise ValidationError("Offer code length is invalid")
