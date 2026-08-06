"""Load NAMASTE codes from the bundled CSV into MongoDB (ayurveda_db.namc_codes).

Used as the offline fallback when no live NAMASTE data source is available.

Usage:
    python scripts/import_namaste_csv.py [path/to/NAMC_FINAL.csv]
"""

import csv
import sys
from pathlib import Path

from pymongo import MongoClient, UpdateOne

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from app import config  # noqa: E402

DEFAULT_CSV = BACKEND_DIR / "csvs" / "NAMASTE" / "NAMC_FINAL.csv"

INT_FIELDS = {"field_1", "field_1_1"}


def load_rows(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                value = (value or "").strip()
                if key in INT_FIELDS:
                    try:
                        row[key] = int(value) if value else 0
                    except ValueError:
                        row[key] = 0
                else:
                    row[key] = value or None
            rows.append(row)
    return rows


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"❌ CSV not found: {csv_path}")
        sys.exit(1)

    print(f"📄 Reading NAMASTE codes from {csv_path}")
    rows = load_rows(csv_path)
    print(f"✅ Parsed {len(rows)} rows")

    client = MongoClient(config.MONGODB_URI)
    collection = client["ayurveda_db"]["namc_codes"]

    operations = [
        UpdateOne({"field_1": row["field_1"]}, {"$set": row}, upsert=True) for row in rows
    ]

    if not operations:
        print("⚠️  No rows to import")
        return

    result = collection.bulk_write(operations, ordered=False)
    print(
        f"🎉 Import complete: {result.upserted_count} inserted, "
        f"{result.modified_count} updated (total in collection: {collection.count_documents({})})"
    )
    client.close()


if __name__ == "__main__":
    main()
