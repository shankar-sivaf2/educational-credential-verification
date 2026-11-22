# Database schema (SQLite via SQLAlchemy)

File: `storage/database/credentials.db`. Tables are created at start-up.

## certificates
| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| certificate_id | varchar(64) | unique, indexed |
| student_id | varchar(40) | indexed |
| student_name, institution_name, degree, department | varchar | certificate details |
| graduation_year | integer | |
| salt | varchar(64) | needed to rebuild the student's file |
| commitment | varchar(66) | 0x + SHA-256 hex |
| chain_key | varchar(66) | lookup key on the contract |
| access_code_hash | varchar(64) | HMAC of the student access code; the code itself is never stored |
| status | varchar(16) | PENDING, REGISTERED, REVOKED, FAILED; indexed |
| tx_hash, revoke_tx_hash | varchar(66) | transaction hashes |
| issuer_address | varchar(42) | account that registered it |
| failure_reason | varchar(255) | set when FAILED |
| created_at, registered_at, revoked_at | datetime (UTC) | |

Status flow: PENDING → REGISTERED → REVOKED, or PENDING → FAILED (can be retried).

## admin_users
`id`, `username` (unique), `password_hash` (bcrypt), `created_at`. The first admin is created
from `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`.

## audit_logs
`id`, `event_type` (ISSUE, REVOKE, VERIFY, STATUS_LOOKUP, STUDENT_ACCESS, LOGIN), `outcome`,
`actor`, `certificate_id` (nullable, indexed), `detail`, `created_at` (indexed).
No names, grades or access codes are ever written to this table.

## Not in the database
Verification results are not stored, and verification never reads these tables.
The blockchain is the source of truth for validity.