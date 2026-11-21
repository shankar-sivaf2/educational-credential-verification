"""SHA-256 commitments with domain separation.

commitment = SHA-256( "ECV/credential-commitment/v1" || 0x00 || canonical_bytes )
cert key   = SHA-256( "ECV/certificate-key/v1"        || 0x00 || certificate_id )

Domain prefixes make sure a hash computed for one purpose can never be reused
as a hash for another purpose. The random per-certificate salt inside the
canonical bytes stops anyone from guessing the commitment from a student's
name and ID, so nothing sensitive can be recovered from the public chain.
"""
import hashlib
import hmac
import secrets
from typing import Any, Mapping

from app.crypto.canonical import canonical_bytes, normalize_text

COMMITMENT_DOMAIN = b"ECV/credential-commitment/v1\x00"
KEY_DOMAIN = b"ECV/certificate-key/v1\x00"


def generate_salt() -> str:
    return secrets.token_hex(32)


def compute_commitment(data: Mapping[str, Any], salt: str) -> str:
    digest = hashlib.sha256(COMMITMENT_DOMAIN + canonical_bytes(data, salt)).hexdigest()
    return "0x" + digest


def certificate_key(certificate_id: str) -> str:
    """Public on-chain lookup key for a certificate identifier."""
    normalized = normalize_text(certificate_id).encode("utf-8")
    return "0x" + hashlib.sha256(KEY_DOMAIN + normalized).hexdigest()


def commitments_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.lower().encode(), b.lower().encode())


def hex_to_bytes32(value: str) -> bytes:
    raw = bytes.fromhex(value[2:] if value.startswith("0x") else value)
    if len(raw) != 32:
        raise ValueError("Expected 32 bytes")
    return raw