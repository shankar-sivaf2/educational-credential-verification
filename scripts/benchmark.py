"""Measure the system and write real results to docs/benchmark-results.{json,md}.

Usage (backend + Hardhat node running, contract deployed):
    python scripts/benchmark.py                 # 20 certificates, 5 verification rounds
    python scripts/benchmark.py --certs 50 --rounds 10

What is measured
  1. Issue latency        : POST /certificates (includes the blockchain transaction).
  2. Verify latency       : POST /verify through the full API (blockchain read + hash check).
  3. Tamper detection     : altered certificates must NOT verify as valid.
  4. Baseline             : a conventional "compare against a database" check, run in-process.
  5. Gas                  : read from docs/gas-results.json if `npm run gas` was run.

Limits you must state in your report: this runs on a local Hardhat chain (instant blocks), so
real public-network confirmation times will be much longer. Latencies are from this machine only.
"""
import argparse
import hashlib
import json
import platform
import random
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ecv_client import DEFAULT_BASE, call, login  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def stats(values_ms):
    v = sorted(values_ms)
    p95 = v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]
    return {
        "n": len(v),
        "mean_ms": round(statistics.mean(v), 2),
        "median_ms": round(statistics.median(v), 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(v[0], 2),
        "max_ms": round(v[-1], 2),
    }


def timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000


def mutations(pkg):
    """Each is one realistic forgery: a single field of a genuine certificate is altered."""
    def with_(key, value):
        forged = dict(pkg)
        forged[key] = value
        return forged
    return {
        "student_name": with_("student_name", pkg["student_name"] + " Jr"),
        "degree": with_("degree", "M.Tech"),
        "department": with_("department", "Mechanical Engineering"),
        "institution_name": with_("institution_name", "Other University"),
        "graduation_year": with_("graduation_year", pkg["graduation_year"] + 1),
        "student_id": with_("student_id", pkg["student_id"] + "9"),
        "certificate_id": with_("certificate_id", pkg["certificate_id"] + "-X"),
    }


def baseline_check(db_rows):
    """Conventional approach: hash the data and compare with the hash stored in a database."""
    def digest(pkg):
        data = {k: pkg[k] for k in sorted(pkg) if k not in ("salt", "schema")}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE certs (id TEXT PRIMARY KEY, digest TEXT)")
    db.executemany("INSERT INTO certs VALUES (?, ?)", [(p["certificate_id"], digest(p)) for p in db_rows])

    def check(pkg):
        row = db.execute("SELECT digest FROM certs WHERE id = ?", (pkg["certificate_id"],)).fetchone()
        return row is not None and row[0] == digest(pkg)

    return db, check, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--certs", type=int, default=20)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--username", default="admin")
    p.add_argument("--password", default="ChangeMe@123")
    args = p.parse_args()

    token = login(args.base, args.username, args.password)
    health = call(args.base, "GET", "/health")
    if health["status"] != "ok":
        raise SystemExit(f"System is not healthy: {health}")

    # 1. Issue
    run = random.randint(10000, 99999)
    packages, issue_ms = [], []
    print(f"Issuing {args.certs} certificates...")
    for i in range(args.certs):
        payload = {
            "certificate_id": f"BENCH-{run}-{i + 1:04d}",
            "student_id": f"BS{run}{i + 1:04d}",
            "student_name": f"Benchmark Student {i + 1}",
            "institution_name": "Demo Institute of Technology",
            "degree": "B.Tech",
            "department": "Computer Science and Engineering",
            "graduation_year": 2026,
        }
        res, ms = timed(lambda: call(args.base, "POST", "/certificates", payload, token))
        packages.append(res["package"])
        issue_ms.append(ms)

    # 2. Verify (genuine)
    print("Verifying genuine certificates...")
    verify_ms, valid_count, total = [], 0, 0
    for _ in range(args.rounds):
        for pkg in packages:
            res, ms = timed(lambda: call(args.base, "POST", "/verify", pkg))
            verify_ms.append(ms)
            total += 1
            valid_count += bool(res["valid"] and res["status"] == "AUTHENTIC_VALID")

    # 3. Tamper detection
    print("Testing forged certificates...")
    forged_total, forged_rejected, by_status = 0, 0, {}
    for pkg in packages:
        for _name, forged in mutations(pkg).items():
            res = call(args.base, "POST", "/verify", forged)
            forged_total += 1
            forged_rejected += (not res["valid"])
            by_status[res["status"]] = by_status.get(res["status"], 0) + 1

    # 4. Baseline (in-process, no network, no blockchain)
    db, check, digest = baseline_check(packages)
    base_ms = []
    for _ in range(args.rounds):
        for pkg in packages:
            _, ms = timed(lambda: check(pkg))
            base_ms.append(ms)
    base_forged_rejected = sum(1 for pkg in packages for f in mutations(pkg).values() if not check(f))
    # Insider attack on the baseline: someone with database access edits the data AND its stored hash.
    victim = dict(packages[0], degree="M.Tech")
    db.execute("UPDATE certs SET digest = ? WHERE id = ?", (digest(victim), victim["certificate_id"]))
    baseline_insider_accepted = check(victim)
    blockchain_insider = call(args.base, "POST", "/verify", victim)

    # 5. Gas
    gas = None
    gas_file = DOCS / "gas-results.json"
    if gas_file.exists():
        gas = json.loads(gas_file.read_text(encoding="utf-8"))

    results = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "network": "local Hardhat node (instant mining)",
            "chain_id": health["blockchain"]["chain_id"],
        },
        "parameters": {"certificates": args.certs, "verify_rounds": args.rounds},
        "issue_latency": stats(issue_ms),
        "verify_latency_api": stats(verify_ms),
        "verify_genuine": {"valid": valid_count, "total": total},
        "tamper_detection": {"rejected": forged_rejected, "total": forged_total, "statuses": by_status},
        "baseline_database_check": {
            "latency": stats(base_ms),
            "forged_rejected": base_forged_rejected,
            "forged_total": forged_total,
            "insider_edit_of_data_and_hash_accepted": baseline_insider_accepted,
            "blockchain_result_for_same_forgery": blockchain_insider["status"],
        },
        "gas": gas,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "benchmark-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (DOCS / "benchmark-results.md").write_text(render_md(results), encoding="utf-8")
    print(render_md(results))
    print(f"Saved to {DOCS / 'benchmark-results.md'} and benchmark-results.json")


def row(label, s):
    return f"| {label} | {s['n']} | {s['mean_ms']} | {s['median_ms']} | {s['p95_ms']} | {s['min_ms']} | {s['max_ms']} |"


def render_md(r):
    b = r["baseline_database_check"]
    t = r["tamper_detection"]
    lines = [
        "# Benchmark results",
        "",
        f"Measured {r['measured_at']} on {r['environment']['os']}, Python {r['environment']['python']}, "
        f"{r['environment']['network']} (chain {r['environment']['chain_id']}).",
        "",
        "## Latency (milliseconds)",
        "",
        "| Operation | n | mean | median | p95 | min | max |",
        "|---|---|---|---|---|---|---|",
        row("Issue certificate (API + blockchain transaction)", r["issue_latency"]),
        row("Verify certificate (API + blockchain read)", r["verify_latency_api"]),
        row("Baseline: database hash check (in-process, no network)", b["latency"]),
        "",
        "The baseline runs inside one process with no HTTP and no blockchain, so it is a floor, not a",
        "like-for-like rival. The comparison that matters is security, below.",
        "",
        "## Correctness",
        "",
        f"- Genuine certificates verified as valid: {r['verify_genuine']['valid']} of {r['verify_genuine']['total']}",
        f"- Forged certificates rejected (blockchain system): {t['rejected']} of {t['total']}  (verdicts: {t['statuses']})",
        f"- Forged certificates rejected (database baseline, outsider forgeries): {b['forged_rejected']} of {b['forged_total']}",
        "",
        "## Insider attack",
        "",
        "Someone with database access changes a certificate's data and the stored hash together.",
        f"- Database baseline accepts the altered certificate: **{b['insider_edit_of_data_and_hash_accepted']}**",
        f"- Blockchain system verdict for the same altered certificate: **{b['blockchain_result_for_same_forgery']}**",
        "",
        "The chain record cannot be edited by the institution's database administrator, which is the",
        "property the baseline lacks.",
    ]
    if r["gas"]:
        lines += ["", "## Gas (from docs/gas-results.json)", "", "```json", json.dumps(r["gas"], indent=2), "```"]
    else:
        lines += ["", "Gas: run `npm run gas` in blockchain/ first, then run this script again to include it."]
    lines += [
        "",
        "## Limits",
        "",
        "- Local test chain with instant mining. Public-network confirmation takes seconds to minutes.",
        "- Single machine, single run. Repeat several times and report the spread.",
        "- A valid result proves the data is unchanged since an authorised issuer registered it. It does",
        "  not prove the qualification itself was earned.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()