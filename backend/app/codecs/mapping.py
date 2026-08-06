import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MAPPING_PATH = Path(__file__).resolve().parent.parent / "data" / "namaste_icd11_mapping.json"

NAMASTE_SYSTEM = "http://namaste-codes.org"
ICD11_TM2_SYSTEM = "http://id.who.int/icd/release/11/mms"


@dataclass
class MappingEntry:
    namaste_id: int
    namaste_code: str
    namaste_term: str
    namaste_display: str
    namaste_devanagari: str
    icd11_tm2_code: str
    icd11_tm2_title: str
    icd11_tm2_id: Optional[str]
    equivalence: str
    source: str
    verified_at: Optional[str] = None


class MappingTable:
    """Verified NAMASTE <-> ICD-11 TM2 crosswalk.

    Built from scripts/build_namaste_tm2_mapping.py, which extracts TM2 codes
    embedded directly in the Ministry of AYUSH NAMASTE codebook and verifies
    each one against the live WHO ICD-11 TM2 data before accepting it. Every
    entry here traces back to two independent real sources -- nothing here is
    guessed.
    """

    def __init__(
        self,
        entries: list[MappingEntry],
        version: str = "unknown",
        verified_at: Optional[str] = None,
    ):
        self.entries = entries
        self.version = version
        self.verified_at = verified_at
        self._by_namaste_id: dict[int, list[MappingEntry]] = {}
        self._by_namaste_code: dict[str, list[MappingEntry]] = {}
        self._by_tm2_code: dict[str, list[MappingEntry]] = {}

        for entry in entries:
            self._by_namaste_id.setdefault(entry.namaste_id, []).append(entry)
            self._by_namaste_code.setdefault(entry.namaste_code, []).append(entry)
            self._by_tm2_code.setdefault(entry.icd11_tm2_code, []).append(entry)

    def lookup_by_namaste(self, code: str) -> list[MappingEntry]:
        code = code.strip()
        if code.isdigit():
            hit = self._by_namaste_id.get(int(code))
            if hit:
                return hit
        return self._by_namaste_code.get(code, [])

    def lookup_by_icd11_tm2(self, code: str) -> list[MappingEntry]:
        return self._by_tm2_code.get(code.strip(), [])

    def __len__(self) -> int:
        return len(self.entries)


def _load() -> MappingTable:
    if not MAPPING_PATH.exists():
        return MappingTable([])

    with open(MAPPING_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # Support both the current wrapped shape ({version, verified_at, entries})
    # and a bare list, so an older mapping file doesn't hard-fail the app.
    if isinstance(raw, dict):
        rows = raw.get("entries", [])
        version = raw.get("version", "unknown")
        verified_at = raw.get("verified_at")
    else:
        rows = raw
        version = "unknown"
        verified_at = None

    entries = [
        MappingEntry(
            namaste_id=row["namaste_id"],
            namaste_code=row["namaste_code"],
            namaste_term=row["namaste_term"],
            namaste_display=row["namaste_display"],
            namaste_devanagari=row.get("namaste_devanagari", ""),
            icd11_tm2_code=row["icd11_tm2_code"],
            icd11_tm2_title=row["icd11_tm2_title"],
            icd11_tm2_id=row.get("icd11_tm2_id"),
            equivalence=row.get("equivalence", "equivalent"),
            source=row.get("source", "namaste_codebook_embedded_code"),
            verified_at=row.get("verified_at", verified_at),
        )
        for row in rows
    ]
    return MappingTable(entries, version=version, verified_at=verified_at)


# Loaded once at import time -- the mapping file is static curated data, not
# something that changes per-request.
mapping_table = _load()
