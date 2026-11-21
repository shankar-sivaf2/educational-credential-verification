# Security

## Assets and threats
| Threat | Defence |
|---|---|
| Employer receives an altered certificate | Commitment recomputed and compared with the blockchain |
| Database administrator edits records | Verification never reads the database; the chain record cannot be edited by them |
| Guessing student data from the on-chain hash | 256-bit random salt per certificate |
| Cross-purpose hash reuse | Domain-separation prefixes in both hashes (`ECV/credential-commitment/v1`, `ECV/certificate-key/v1`) |
| Ambiguous encoding (two inputs, same hash) | Canonical JSON: NFC normalisation, whitespace collapse, sorted keys, fixed fields |
| Hidden or look-alike characters | Control and invisible characters rejected |
| Unauthorised issuing or revoking | JWT for admin routes; `ISSUER_ROLE` / admin role on the contract |
| Password guessing | bcrypt, 5 failed logins per 5 minutes, dummy hash to equalise timing |
| Guessing a student's access code | Code stored only as an HMAC hash, shown once, 5 failures per 5 minutes |
| Malicious uploads | JSON only, 64 KB cap, read in memory, never stored |
| Personal data in logs | Audit log records events and outcomes only |
| Blockchain outage reported as "fake" | Separate `SERVICE_UNAVAILABLE` verdict |
| Half-finished issuance | PENDING → REGISTERED only after chain confirmation; retry reconciles |

## Not protected (state these honestly)
- A valid result does not prove the qualification was earned. An authorised issuer could
  register a false certificate.
- The student file contains personal data and the salt. Whoever holds it can prove the content.
- The demo uses one private key in `.env` and Hardhat's public test key. Production would need
  a hardware or cloud key manager.
- Rate limits are in memory and per process.
- Not deployed on a public chain; no formal audit of the contract has been done.
- HTTPS and production secrets management are out of scope for the local demo.

## Before any real use
Change `JWT_SECRET` and the admin password, replace the demo key, serve over HTTPS, use a
persistent rate limiter, and have the contract independently audited.