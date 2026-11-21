# Module 8 - Testing and Evaluation Results

## Backend Tests
- Pytest: 87 passed, 1 skipped, 0 failed.
- Execution time: 72.21 seconds.

## Smart Contract Tests
- Hardhat: 16 passed, 0 failed.

## Demo Certificate Generation
- First run: 5 certificates registered.
- Second run: 10 certificates registered.
- Total: 15 certificates registered.

## Performance Benchmark
- Certificates issued: 20.
- Verification rounds: 5.
- Genuine certificates verified: 100/100.
- Forged certificates rejected: 140/140.

## Forgery Detection Results
- COMMITMENT_MISMATCH: 120.
- UNKNOWN: 20.
- Total rejected: 140.

## Latency Measurements
| Operation | Mean latency |
|---|---:|
| Certificate issuance | 125.14 ms |
| Certificate verification | 57.66 ms |
| Database baseline | 0.04 ms |

## Gas Measurements
| Operation | Gas |
|---|---:|
| Contract deployment | 553986 |
| Registration mean | 71602 |
| Revocation mean | 35904 |
| On-chain storage | 64 bytes per certificate |

## Insider Attack
- Database baseline accepted altered data and its modified hash.
- Blockchain verification returned COMMITMENT_MISMATCH.

## Limitations
- Testing used a local Hardhat network.
- Public blockchain confirmation times will differ.
- Performance results are from one development machine.
- Verification proves integrity against the registered commitment, not that the qualification was genuinely earned.

## Final Result
All recorded Module 8 automated tests, certificate generation, genuine verification, forgery rejection, and insider attack experiments completed successfully.
