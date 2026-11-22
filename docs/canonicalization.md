# Canonicalisation and hashing

Source: `backend/app/crypto/canonical.py` and `hashing.py`. Schema version: `ecv-cert/1`.

## Why it is needed
A hash changes completely if one byte changes. Issuing and verifying must therefore turn the
same certificate into exactly the same bytes, whatever spacing, key order or Unicode form the
input used.

## Rules
1. Fixed fields, no optional ones: `schema`, `certificate_id`, `student_name`, `student_id`,
   `institution_name`, `degree`, `department`, `graduation_year`, `salt`.
2. Text fields are Unicode NFC normalised, trimmed, and runs of whitespace become one space.
   Case is preserved (names are case-sensitive on a certificate).
3. `graduation_year` must be a JSON integer. Booleans and strings are rejected.
4. `salt` is 32 random bytes written as 64 lowercase hex characters.
5. The JSON object is written with sorted keys, no spaces and ASCII escapes, then UTF-8 encoded.
6. Empty fields and control or invisible characters are rejected before hashing.

## Hash construction
```
commitment = SHA-256( "ECV/credential-commitment/v1" || 0x00 || canonical_bytes )
cert key   = SHA-256( "ECV/certificate-key/v1"        || 0x00 || normalised certificate_id )
```
The two different prefixes (domain separation) mean a value computed for one purpose can never
be mistaken for the other.

## Why a salt
Names, IDs and years have little entropy. Without a salt, anyone could hash guesses and compare
them with the public on-chain value. With a random 256-bit salt that never leaves the
certificate file, guessing is infeasible.

## Known-answer test
Salt `abab...ab` (64 hex characters) with the sample certificate used in `test_crypto.py`:
- commitment `0x5eab671ee34e8fc38765cbcd0d843cf95975d361de447566478efa523d802748`
- key `0x5f37672420a8fa84a6d8750df6c2ffcde661aa244da686d4c41fc8917424839b`

These are fixed in the tests so an accidental change to the rules is caught immediately.

## Changing the rules
Any change to the rules is a new schema version (`ecv-cert/2`) with a new prefix. Existing
certificates keep verifying under `ecv-cert/1`.