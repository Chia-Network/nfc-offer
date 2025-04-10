"""NFC-related exceptions."""


class NFCError(Exception):
    """Base class for NFC exceptions."""
    pass


class ReaderNotFoundError(NFCError):
    """No NFC reader found."""
    pass


class ReaderConnectionError(NFCError):
    """Failed to connect to reader."""
    pass


class ReadError(NFCError):
    """Failed to read from NFC tag."""
    pass


class WriteError(NFCError):
    """Failed to write to tag."""
    pass


class TagNotFoundError(NFCError):
    """No NFC tag was detected."""
    pass


class UnsupportedTagError(NFCError):
    """Tag type is not supported."""
    pass


class TagLockedException(Exception):
    """Raised when attempting to write to a locked tag."""
    pass


class ValidationError(NFCError):
    """Invalid data format."""
    pass
