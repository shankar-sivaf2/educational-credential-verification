# Architecture

## Components
```mermaid
flowchart LR
  A[Admin / Institution] -->|JWT| W[React web app]
  S[Student] --> W
  E[Employer] --> W
  W -->|HTTPS /api| B[FastAPI backend]
  B --> D[(SQLite)]
  B -->|Web3.py| C[(CertificateRegistry on Hardhat chain)]
```

| Component | Responsibility |
|---|---|
| React web app | Screens for issue, dashboard, audit, verify, student records, system status |
| FastAPI backend | Validation, hashing, authentication, issuing, verification, audit log |
| SQLite | Full certificate details, hashed student access codes, audit events |
| Smart contract | Immutable record of commitment, issuer and revoked flag per certificate |

## Design decisions
- **Hash on-chain, data off-chain.** Personal data is never written to a public ledger. The
  chain holds a salted SHA-256 commitment.
- **Salt.** Student names and IDs have low entropy, so an unsalted hash could be guessed. The
  256-bit random salt prevents that. The salt travels only inside the student's file.
- **Verification reads only the blockchain.** The database is never consulted, so a database
  edit cannot change a verdict.
- **Backend recomputes the hash.** The employer uploads the file; the server derives the
  commitment itself, so a client cannot supply its own hash.

## Class diagram
```mermaid
classDiagram
  class Certificate {
    certificate_id
    student_id
    student_name
    institution_name
    degree
    department
    graduation_year
    salt
    commitment
    chain_key
    status
    tx_hash
  }
  class AdminUser { username; password_hash }
  class AuditLog { event_type; outcome; actor; certificate_id; created_at }
  class ChainClient {
    <<interface>>
    register(key, commitment)
    revoke(key)
    get(key)
  }
  class Web3ChainClient
  class InMemoryChainClient
  ChainClient <|.. Web3ChainClient
  ChainClient <|.. InMemoryChainClient
```
`InMemoryChainClient` exists only so the automated tests run without a blockchain.

## Issuing sequence
```mermaid
sequenceDiagram
  participant Admin
  participant API as FastAPI
  participant DB as SQLite
  participant Chain as Smart contract
  Admin->>API: POST /certificates (JWT)
  API->>Chain: is the chain reachable? is this ID free?
  API->>DB: save row as PENDING
  API->>Chain: registerCertificate(key, commitment)
  Chain-->>API: transaction receipt
  API->>DB: mark REGISTERED (or FAILED, retryable)
  API-->>Admin: certificate, one-time access code, package, QR link
```
A certificate becomes REGISTERED only after the chain confirms it. If a previous attempt
registered on-chain but failed to update the database, the retry reconciles without sending
a second transaction.

## Verification sequence
```mermaid
sequenceDiagram
  participant Employer
  participant API as FastAPI
  participant Chain as Smart contract
  Employer->>API: POST /verify/upload (certificate file)
  API->>API: canonicalise + recompute commitment
  API->>Chain: getCertificate(key), isAuthorizedIssuer(issuer)
  Chain-->>API: commitment, issuer, revoked
  API-->>Employer: verdict + four checks
```

## Data flow (level 1)
```mermaid
flowchart TB
  A((Admin)) -- certificate details --> P1[1 Issue]
  P1 -- commitment --> C[(Blockchain)]
  P1 -- full record --> D[(Database)]
  P1 -- file + QR + code --> A
  E((Employer)) -- certificate file --> P2[2 Verify]
  P2 -- key --> C
  C -- commitment, issuer, revoked --> P2
  P2 -- verdict --> E
  S((Student)) -- ID + access code --> P3[3 Retrieve]
  D -- own records --> P3
  P3 -- certificate file --> S
```

## Verdicts
| Verdict | Meaning |
|---|---|
| AUTHENTIC_VALID | Registered, hash matches, issuer authorised, not revoked |
| REVOKED | Registered but revoked by the institution |
| UNKNOWN | No record for this certificate ID |
| COMMITMENT_MISMATCH | A record exists but the data does not match it (altered file) |
| INVALID_ISSUER | The registering account has lost its issuer role |
| SERVICE_UNAVAILABLE | The blockchain could not be reached. This is never reported as "invalid" |