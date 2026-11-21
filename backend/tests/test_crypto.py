"""Module 2 tests: canonical serialization and SHA-256 commitments."""
import hashlib

import pytest

from app.crypto.canonical import (
    CanonicalizationError,
    SCHEMA_VERSION,
    canonical_bytes,
    normalize_text,
)
from app.crypto.hashing import (
    COMMITMENT_DOMAIN,
    certificate_key,
    commitments_equal,
    compute_commitment,
    generate_salt,
    hex_to_bytes32,
)

SALT = "ab" * 32

CERT = {
    "certificate_id": "CERT-2026-0001",
    "student_name": "Asha Raman",
    "student_id": "STU1001",
    "institution_name": "Demo Institute of Technology",
    "degree": "B.Tech",
    "department": "Computer Science and Engineering",
    "graduation_year": 2026,
}

# Known-answer vector: if this changes, issuance and verification are no longer compatible.
EXPECTED_COMMITMENT = "0x5eab671ee34e8fc38765cbcd0d843cf95975d361de447566478efa523d802748"
EXPECTED_KEY = "0x5f37672420a8fa84a6d8750df6c2ffcde661aa244da686d4c41fc8917424839b"


def test_known_answer_vector():
    assert compute_commitment(CERT, SALT) == EXPECTED_COMMITMENT
    assert certificate_key("CERT-2026-0001") == EXPECTED_KEY


def test_commitment_is_deterministic():
    assert compute_commitment(CERT, SALT) == compute_commitment(dict(CERT), SALT)


def test_field_order_does_not_matter():
    reordered = dict(reversed(list(CERT.items())))
    assert compute_commitment(reordered, SALT) == compute_commitment(CERT, SALT)


def test_extra_keys_are_ignored():
    with_extra = {**CERT, "schema": SCHEMA_VERSION, "salt": SALT, "note": "ignored"}
    assert compute_commitment(with_extra, SALT) == compute_commitment(CERT, SALT)


def test_whitespace_and_unicode_are_normalised():
    messy = {**CERT, "student_name": "  Asha   Raman \n"}
    assert compute_commitment(messy, SALT) == compute_commitment(CERT, SALT)
    # "é" as one character vs "e" + combining accent must hash the same (NFC)
    a = {**CERT, "student_name": "Jos\u00e9"}
    b = {**CERT, "student_name": "Jose\u0301"}
    assert compute_commitment(a, SALT) == compute_commitment(b, SALT)


def test_case_is_preserved():
    lower = {**CERT, "student_name": "asha raman"}
    assert compute_commitment(lower, SALT) != compute_commitment(CERT, SALT)


def test_any_field_change_changes_commitment():
    base = compute_commitment(CERT, SALT)
    changes = {
        "certificate_id": "CERT-2026-0002",
        "student_name": "Asha Raman K",
        "student_id": "STU1002",
        "institution_name": "Other Institute",
        "degree": "M.Tech",
        "department": "Mechanical Engineering",
        "graduation_year": 2027,
    }
    for field, new_value in changes.items():
        assert compute_commitment({**CERT, field: new_value}, SALT) != base, field


def test_different_salt_gives_different_commitment():
    assert compute_commitment(CERT, "cd" * 32) != compute_commitment(CERT, SALT)


def test_salt_is_case_insensitive_hex():
    assert compute_commitment(CERT, SALT.upper()) == compute_commitment(CERT, SALT)


def test_domain_separation():
    plain = "0x" + hashlib.sha256(canonical_bytes(CERT, SALT)).hexdigest()
    assert compute_commitment(CERT, SALT) != plain
    assert COMMITMENT_DOMAIN.endswith(b"\x00")


def test_certificate_key_differs_from_commitment_domain():
    assert certificate_key("CERT-2026-0001") != compute_commitment(CERT, SALT)


def test_canonical_bytes_are_compact_sorted_ascii():
    text = canonical_bytes(CERT, SALT).decode("ascii")
    assert text.startswith('{"certificate_id":"CERT-2026-0001","degree":')
    assert " " not in text.replace("Asha Raman", "").replace("Demo Institute of Technology", "").replace(
        "Computer Science and Engineering", ""
    )


def test_missing_field_is_rejected():
    broken = dict(CERT)
    del broken["degree"]
    with pytest.raises(CanonicalizationError):
        compute_commitment(broken, SALT)


def test_empty_text_is_rejected():
    with pytest.raises(CanonicalizationError):
        compute_commitment({**CERT, "department": "   "}, SALT)


def test_year_must_be_integer():
    for bad in ("2026", 2026.0, True, None):
        with pytest.raises(CanonicalizationError):
            compute_commitment({**CERT, "graduation_year": bad}, SALT)


def test_bad_salt_is_rejected():
    for bad in ("", "xyz", "ab" * 31, "zz" * 32, None):
        with pytest.raises(CanonicalizationError):
            compute_commitment(CERT, bad)


def test_generate_salt_format_and_uniqueness():
    salts = {generate_salt() for _ in range(50)}
    assert len(salts) == 50
    assert all(len(s) == 64 and int(s, 16) >= 0 for s in salts)


def test_certificate_key_is_stable_and_normalised():
    assert certificate_key("CERT-1") == certificate_key("  CERT-1 ")
    assert certificate_key("CERT-1") != certificate_key("CERT-2")
    assert len(hex_to_bytes32(certificate_key("CERT-1"))) == 32


def test_hex_to_bytes32_rejects_wrong_length():
    with pytest.raises(ValueError):
        hex_to_bytes32("0x1234")


def test_commitments_equal_ignores_case():
    assert commitments_equal("0xAB", "0xab")
    assert not commitments_equal("0xab", "0xac")


def test_normalize_text():
    assert normalize_text("  a \t b\n c ") == "a b c"