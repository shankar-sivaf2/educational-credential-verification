# Benchmark results

Measured 2026-11-22T12:03:21+00:00 on Windows-11-10.0.26300-SP0, Python 3.13.0, local Hardhat node (instant mining) (chain 31337).

## Latency (milliseconds)

| Operation | n | mean | median | p95 | min | max |
|---|---|---|---|---|---|---|
| Issue certificate (API + blockchain transaction) | 20 | 129.88 | 118.99 | 156.63 | 99.7 | 300.09 |
| Verify certificate (API + blockchain read) | 100 | 54.74 | 49.61 | 79.6 | 39.13 | 106.66 |
| Baseline: database hash check (in-process, no network) | 100 | 0.04 | 0.04 | 0.05 | 0.03 | 0.15 |

The baseline runs inside one process with no HTTP and no blockchain, so it is a floor, not a
like-for-like rival. The comparison that matters is security, below.

## Correctness

- Genuine certificates verified as valid: 100 of 100
- Forged certificates rejected (blockchain system): 140 of 140  (verdicts: {'COMMITMENT_MISMATCH': 120, 'UNKNOWN': 20})
- Forged certificates rejected (database baseline, outsider forgeries): 140 of 140

## Insider attack

Someone with database access changes a certificate's data and the stored hash together.
- Database baseline accepts the altered certificate: **True**
- Blockchain system verdict for the same altered certificate: **COMMITMENT_MISMATCH**

The chain record cannot be edited by the institution's database administrator, which is the
property the baseline lacks.

## Gas (from docs/gas-results.json)

```json
{
  "measuredAt": "2026-11-22T11:39:21.771Z",
  "environment": {
    "network": "hardhat in-process",
    "hardhat": "2.29.1",
    "solidity": "0.8.24",
    "optimizerRuns": 200,
    "node": "v22.20.0",
    "platform": "win32 x64"
  },
  "deployment": {
    "gas": 553986
  },
  "registerCertificate": {
    "samples": 20,
    "min": 71586,
    "max": 71610,
    "mean": 71602
  },
  "revokeCertificate": {
    "samples": 20,
    "min": 35885,
    "max": 35909,
    "mean": 35904
  },
  "onChainBytesPerCertificate": 64
}
```

## Limits

- Local test chain with instant mining. Public-network confirmation takes seconds to minutes.
- Single machine, single run. Repeat several times and report the spread.
- A valid result proves the data is unchanged since an authorised issuer registered it. It does
  not prove the qualification itself was earned.
