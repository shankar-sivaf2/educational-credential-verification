"""Create synthetic demo certificates through the real API.

Usage (backend and Hardhat node running, contract deployed):
    python scripts/seed-demo-data.py                # 5 certificates
    python scripts/seed-demo-data.py --count 10

Writes each student's certificate file and access code to storage/certificates/demo/.
All data is synthetic. Never enter real student data into this demo system.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ecv_client import DEFAULT_BASE, ApiError, call, login  # noqa: E402

NAMES = ["Asha Raman", "Ravi Kumar", "Meena Iyer", "Arjun Nair", "Divya Menon",
         "Karthik Subramanian", "Priya Natarajan", "Sanjay Pillai", "Lakshmi Devi", "Vikram Rao"]
DEPARTMENTS = ["Computer Science and Engineering", "Information Technology",
               "Electronics and Communication Engineering", "Mechanical Engineering"]
OUT_DIR = Path(__file__).resolve().parent.parent / "storage" / "certificates" / "demo"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--username", default="admin")
    p.add_argument("--password", default="ChangeMe@123")
    args = p.parse_args()

    token = login(args.base, args.username, args.password)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run = random.randint(10000, 99999)  # keeps IDs unique when the script is run again
    summary = []

    for i in range(args.count):
        payload = {
            "certificate_id": f"DEMO-{run}-{i + 1:03d}",
            "student_id": f"DS{run}{i + 1:03d}",
            "student_name": NAMES[i % len(NAMES)],
            "institution_name": "Demo Institute of Technology",
            "degree": "B.Tech",
            "department": DEPARTMENTS[i % len(DEPARTMENTS)],
            "graduation_year": 2026,
        }
        try:
            res = call(args.base, "POST", "/certificates", payload, token)
        except ApiError as exc:
            print(f"  FAILED {payload['certificate_id']}: {exc}")
            continue
        cid = res["certificate"]["certificate_id"]
        (OUT_DIR / f"{cid}.json").write_text(json.dumps(res["package"], indent=2), encoding="utf-8")
        summary.append((cid, payload["student_id"], res["access_code"]))
        print(f"  issued {cid}  status={res['certificate']['status']}")

    lines = ["certificate_id,student_id,access_code"] + [",".join(r) for r in summary]
    (OUT_DIR / "demo-access-codes.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(summary)} certificate(s) issued. Files and access codes are in:\n  {OUT_DIR}")


if __name__ == "__main__":
    main()