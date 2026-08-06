"""Load ICD-11 entities from the bundled CSV into MongoDB (icd11_database.icd11_entities).

Used as the offline fallback when the live WHO ICD-11 API isn't available
(no credentials, network issue, etc). See scripts/fetch_icd11_live.py for the
live version.

Usage:
    python scripts/import_icd_csv.py [path/to/icd11_mms.csv]
"""

import csv
import sys
from pathlib import Path

from pymongo import MongoClient, UpdateOne

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV = BACKEND_DIR / "csvs" / "ICD-11" / "icd11_mms.csv"

FIELDS = [
    "id", "code", "title", "definition", "parent",
    "browserUrl", "codingNote", "synonyms", "exclusions",
    "inclusions", "isLeaf",
]


def load_rows(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            if not raw_row.get("id"):
                continue
            row = {field: (raw_row.get(field) or "").strip() or None for field in FIELDS}
            row["id"] = raw_row["id"].strip()
            rows.append(row)
    return rows


def main(csv_path: Path | None = None) -> None:
    if csv_path is None:
        csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    print(f"Reading ICD-11 entities from {csv_path}")
    rows = load_rows(csv_path)
    print(f"Parsed {len(rows)} rows")

    client = MongoClient("mongodb://localhost:27017")
    collection = client["icd11_database"]["icd11_entities"]
    collection.create_index("id", unique=True)

    batch_size = 2000
    upserted = 0
    modified = 0

    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        operations = [UpdateOne({"id": row["id"]}, {"$set": row}, upsert=True) for row in batch]
        result = collection.bulk_write(operations, ordered=False)
        upserted += result.upserted_count
        modified += result.modified_count
        print(f"  ...{start + len(batch)}/{len(rows)} processed")

    print(
        f"Import complete: {upserted} inserted, {modified} updated "
        f"(total in collection: {collection.count_documents({})})"
    )
    client.close()


if __name__ == "__main__":
    main()
