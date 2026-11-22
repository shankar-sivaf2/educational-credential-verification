# Smart contract: CertificateRegistry

File: `blockchain/contracts/CertificateRegistry.sol`. Solidity 0.8.24, OpenZeppelin v5
`AccessControl`, optimizer 200 runs.

## Roles
- `DEFAULT_ADMIN_ROLE`: manages issuers and may revoke any certificate.
- `ISSUER_ROLE`: may register certificates. The deployer receives both roles.

## Storage
One record per certificate key, in two storage slots:
- slot 1: `bytes32 commitment`
- slot 2: `address issuer` (20 bytes) + `uint40 issuedAt` (5 bytes) + `bool revoked` (1 byte)

Packing keeps the cost of registering low. No personal data is stored.

## Functions
| Function | Who | Effect |
|---|---|---|
| `registerCertificate(bytes32 certKey, bytes32 commitment)` | issuer | Stores the record; emits `CertificateRegistered` |
| `revokeCertificate(bytes32 certKey)` | admin, or the original issuer if it still holds ISSUER_ROLE | Sets `revoked`; emits `CertificateRevoked` |
| `getCertificate(bytes32 certKey)` | anyone (view) | Returns `exists, commitment, issuer, issuedAt, revoked` |
| `isAuthorizedIssuer(address)` | anyone (view) | True if the account holds ISSUER_ROLE |

## Custom errors
`ZeroAdmin`, `ZeroCommitment`, `AlreadyRegistered`, `NotRegistered`, `AlreadyRevoked`,
`NotAllowedToRevoke`. Custom errors cost less gas than revert strings.

## Design notes
- A certificate cannot be overwritten. Registering the same key twice reverts.
- Revocation is permanent in this version (no un-revoke).
- The contract is not upgradeable. A mistake in it would require a new deployment.
- Removing an issuer's role makes verification report `INVALID_ISSUER` for its certificates.
  This is how a compromised issuer key is handled.

## Gas
Measured values come from `npm run gas` and are saved in `docs/gas-results.json`.
Gas measurements were collected using `npm run gas` on a local Hardhat in-process network.

| Operation | Measurement | Gas |
|---|---|---:|
| Contract deployment | Total | 553,986 |
| Certificate registration | Minimum (20 samples) | 71,586 |
| Certificate registration | Maximum (20 samples) | 71,610 |
| Certificate registration | Mean (20 samples) | 71,602 |
| Certificate revocation | Minimum (20 samples) | 35,885 |
| Certificate revocation | Maximum (20 samples) | 35,909 |
| Certificate revocation | Mean (20 samples) | 35,904 |

On-chain storage per certificate: **64 bytes**.

Environment: Hardhat 2.29.1, Solidity 0.8.24, optimizer runs 200, Node.js 22.20.0, Windows x64.

Detailed measurements are available in `docs/gas-results.json`.

## Limits
The contract has not been formally audited and has only been run on a local Hardhat chain.