# Viva questions and answers

## Concept
**1. What problem does the project solve?**
Certificate fraud and slow manual verification. Employers get a quick, checkable answer
without phoning the institution, and a forged or altered certificate is detected.

**2. Why a blockchain instead of a normal database?**
A database is controlled by one party who can edit both a record and its hash. A blockchain
record cannot be quietly changed by the institution's administrator, and anyone can read it.
Our benchmark includes an "insider edit" test that shows exactly this difference.

**3. What is stored on the blockchain?**
Only a 32-byte salted commitment, the issuer's address, a timestamp and a revoked flag. No
names, grades or IDs.

**4. Why not store the whole certificate on-chain?**
Privacy (a public ledger cannot be erased) and cost (storage is expensive).

**5. What does "valid" actually prove?**
That the data is unchanged since an authorised issuer registered it and it was not revoked.
It does not prove the qualification was earned. The result screen says so.

## Cryptography
**6. What is a commitment?**
A value that binds you to some data without revealing it. Here, SHA-256 over the salted,
canonical certificate data.

**7. Why add a salt?**
Student data is low-entropy, so an unsalted hash could be guessed. The 256-bit random salt
makes guessing infeasible.

**8. What is canonicalisation and why do you need it?**
A fixed way to turn the data into bytes. Without it the same certificate could hash
differently because of spacing, key order or Unicode form.

**9. What is domain separation?**
Different fixed prefixes for different hashes, so a hash made for one purpose cannot be used
as another.

**10. Why SHA-256 and not Keccak?**
SHA-256 is the standard, available in Python's standard library, and the verifier recomputes
the hash off-chain, so the chain does not need to compute it. Keccak would also work.

## Smart contract
**11. How is access controlled?**
OpenZeppelin AccessControl. Only accounts with ISSUER_ROLE register; admins or the original
issuer revoke.

**12. What happens if an issuer's key is stolen?**
The admin removes its ISSUER_ROLE. Verification then returns INVALID_ISSUER for certificates
it registered. Records issued before the theft by that key are also flagged, which is a
deliberate conservative choice; the institution would reissue them.

**13. Can a registered certificate be changed?**
No. It can only be revoked. Registering the same key again reverts.

**14. How did you keep gas low?**
Two packed storage slots, custom errors and a small number of fields.

## Backend and security
**15. How does verification work?**
The backend rebuilds the canonical bytes from the uploaded file, computes the commitment and
key, reads the chain, and compares. It also checks the issuer role and revoked flag. It never
reads the database.

**16. What if the blockchain is down?**
The result is SERVICE_UNAVAILABLE, never "invalid", so an outage is not mistaken for fraud.

**17. What if the transaction fails during issuing?**
The certificate was saved as PENDING and is marked FAILED. It is never shown as registered.
Retrying reconciles: if the chain already has it, no second transaction is sent.

**18. How are passwords and student codes protected?**
Admin passwords use bcrypt. Student access codes are stored as an HMAC hash and shown once.
Both have a limit of five failures in five minutes.

**19. What privacy protections exist?**
No personal data on-chain, no personal data in the audit log, QR codes carry only an ID, and
uploaded files are checked in memory and not stored.

## Evaluation and limits
**20. How did you evaluate it?**
Automated tests for crypto, API, chain integration and verification; contract tests; and a
benchmark of latency, tamper detection and an insider-attack comparison. The numbers are in
`docs/benchmark-results.md`.

**21. Is the latency result realistic for a public network?**
No. It was measured on a local test chain with instant mining. Issuing on a public network
would wait for block confirmation. Verification only reads, so it would remain fast.

**22. What are the limitations?**
Local chain only, one demo issuer, in-memory rate limits, no formal contract audit, and a
valid result does not prove the qualification was earned.

**23. What would you do next?**
Deploy to a public test network, support several institutions with an onboarding process,
move keys to a managed key store, add a persistent rate limiter, and get an independent audit.

**24. Why did you not use Merkle trees or digital signatures?**
Each certificate has its own record, so a Merkle tree adds complexity without benefit.
Authenticity comes from the issuer's transaction, which the chain already signs.