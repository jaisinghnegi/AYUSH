"""CLI entrypoint for the live WHO ICD-11 sync.

The actual implementation lives in app/sync/icd11_sync.py, shared with the
POST /services/sync/icd11-live endpoint so there's a single source of truth
for the sync logic whether it's triggered manually or from the running app.

Requires a free WHO ICD-API registration: https://icd.who.int/icdapi
Generate a Client ID + Client Secret at https://icd.who.int/icdapi/Account/AccessKey
and put them in backend/.env as:

    WHO_ICD_CLIENT_ID=...
    WHO_ICD_CLIENT_SECRET=...

If credentials are missing or the live fetch fails, this automatically falls
back to the bundled icd11_mms.csv snapshot.

Usage:
    python scripts/fetch_icd11_live.py [--release 2025-01] [--concurrency 8]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sync.icd11_sync import run_sync  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", default="2025-01")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    result = asyncio.run(run_sync(release=args.release, concurrency=args.concurrency))

    print(f"\nDone. Source: {result['source']}")
    if "error" in result:
        print(f"Note: {result['error']}")
    print(f"Total entities in collection: {result.get('total')}")


if __name__ == "__main__":
    main()
