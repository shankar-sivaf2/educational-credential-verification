"""Canonical serialization of a certificate.

Issuance and verification MUST use exactly this function, otherwise the same
certificate would produce different commitments. Rules (schema "ecv-cert/1"):

1. Exactly these fields are used, in a JSON object with sorted keys:
   schema, certificate_id, student_name, student_id, institution_name,
   degree, department, graduation_year, salt.
2. Text fields: Unicode NFC normalised, leading/trailing whitespace removed,
   runs of internal whitespace collapsed to one space. Case is preserved.
3. graduation_year is a JSON integer (booleans and strings are rejected).
4. salt is 32 random bytes as 64 lowercase hex characters.
5. No optional fields exist in v1: every field is required.
6. JSON is written compactly (no spaces), ASCII-escaped, then UTF-8 encoded.
"""
import json
import re
import unicodedata
from typing import Any, Mapping

SCHEMA_VERSION = "ecv-cert/1"

TEXT_FIELDS = (
    "certificate_id",
    "student_name",
    "student_id",
    "institution_name",
    "degree",
    "department",
)
FIELDS = TEXT_FIELDS + ("graduation_year",)

_SALT_RE = re.compile(r"^[0-9a-f]{64}$")


class CanonicalizationError(ValueError):
    """Input cannot be turned into a canonical certificate."""


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def canonical_payload(data: Mapping[str, Any], salt: str) -> dict:
    payload: dict[str, Any] = {"schema": SCHEMA_VERSION}
    for name in TEXT_FIELDS:
        value = data.get(name)
        if not isinstance(value, str):
            raise CanonicalizationError(f"Field '{name}' is required and must be text.")
        value = normalize_text(value)
        if not value:
            raise CanonicalizationError(f"Field '{name}' must not be empty.")
        payload[name] = value

    year = data.get("graduation_year")
    if isinstance(year, bool) or not isinstance(year, int):
        raise CanonicalizationError("Field 'graduation_year' must be an integer.")
    payload["graduation_year"] = year

    if not isinstance(salt, str) or not _SALT_RE.match(salt.lower()):
        raise CanonicalizationError("Salt must be 64 hexadecimal characters.")
    payload["salt"] = salt.lower()
    return payload


def canonical_bytes(data: Mapping[str, Any], salt: str) -> bytes:
    payload = canonical_payload(data, salt)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text.encode("utf-8")