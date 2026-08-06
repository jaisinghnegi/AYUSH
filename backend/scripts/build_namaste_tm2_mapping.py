"""Build a verified NAMASTE -> ICD-11 TM2 mapping table.

The NAMASTE codebook (published by the Ministry of AYUSH) embeds a WHO ICD-11
TM2 code directly inside its own `AYU` code field for a large share of entries,
e.g. "SP51(EC-3)" for jvaraH (fever) -- SP51 is WHO's real
"Fever disorder (TM2)" code. This script extracts every such embedded code and
verifies it against the actual icd11_entities collection (populated from the
live WHO API / CSV fallback) before accepting it -- so every mapping in the
output is checkable against two independent, real, government-published
sources: the NAMASTE CSV and the WHO ICD-11 API.

Entries where no embedded TM2 code exists, or the extracted code doesn't
resolve to a real TM2 entity, are left out (no guessing/fabrication).

Usage:
    python scripts/build_namaste_tm2_mapping.py
Writes: app/data/namaste_icd11_mapping.json
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

MAPPING_VERSION = "1.0.0"

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from app import config  # noqa: E402

OUTPUT_PATH = BACKEND_DIR / "app" / "data" / "namaste_icd11_mapping.json"

# WHO's TM2 chapter uses code prefixes SK through ST (SA-SJ is the separate
# TM1/East-Asian-pattern chapter -- excluded on purpose).
TM2_CODE_RE = re.compile(r"\bS[K-T][0-9A-Z]{1,3}\b")


def main() -> None:
    verified_at = datetime.now(timezone.utc).isoformat()
    client = MongoClient(config.MONGODB_URI)
    namaste = client["ayurveda_db"]["namc_codes"]
    icd = client["icd11_database"]["icd11_entities"]

    # Build a lookup of real, verified TM2 codes -> title from the actual
    # imported ICD-11 data (this is the source of truth for "does this code
    # really exist").
    tm2_lookup: dict[str, dict] = {}
    for doc in icd.find({"title": {"$regex": r"\(TM2\)"}, "code": {"$ne": None}}):
        tm2_lookup[doc["code"]] = {"code": doc["code"], "title": doc["title"], "id": doc.get("id")}

    print(f"Loaded {len(tm2_lookup)} verified TM2 codes from icd11_entities")

    mappings = []
    skipped_no_code = 0
    skipped_unverified = 0

    for row in namaste.find({}):
        ayu = row.get("AYU") or ""
        candidates = TM2_CODE_RE.findall(ayu)
        if not candidates:
            skipped_no_code += 1
            continue

        verified = None
        for candidate in candidates:
            if candidate in tm2_lookup:
                verified = tm2_lookup[candidate]
                break

        if not verified:
            skipped_unverified += 1
            continue

        term = row.get("vyAdhi-viniScayaH") or ""
        display = row.get("vyādhi-viniścayaḥ") or term
        devanagari = row.get("व्याधि-विनिश्चयः") or ""

        mappings.append(
            {
                "namaste_id": row.get("field_1"),
                "namaste_code": ayu,
                "namaste_term": term,
                "namaste_display": display,
                "namaste_devanagari": devanagari,
                "icd11_tm2_code": verified["code"],
                "icd11_tm2_title": verified["title"],
                "icd11_tm2_id": verified["id"],
                "equivalence": "equivalent",
                "source": "namaste_codebook_embedded_code",
                "verified_at": verified_at,
            }
        )

    print(f"Built {len(mappings)} verified mappings")
    print(f"  skipped (no embedded TM2-shaped code): {skipped_no_code}")
    print(f"  skipped (embedded code not found in live TM2 data): {skipped_unverified}")

    output = {
        "version": MAPPING_VERSION,
        "verified_at": verified_at,
        "entry_count": len(mappings),
        "entries": mappings,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT_PATH} (version {MAPPING_VERSION}, verified_at {verified_at})")


if __name__ == "__main__":
    main()
