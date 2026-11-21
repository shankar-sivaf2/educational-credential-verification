"""Shared input-validation patterns and helpers."""
import unicodedata

# Certificate IDs are used in URLs and QR codes: keep them to a safe alphabet.
CERT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9\-_/]{2,63}$"
STUDENT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9\-_/]{0,39}$"
SALT_PATTERN = r"^[0-9a-fA-F]{64}$"


def has_control_chars(value: str) -> bool:
    """True for control and invisible 'format' characters (newlines, zero-width, etc.)."""
    return any(unicodedata.category(ch).startswith("C") for ch in value)