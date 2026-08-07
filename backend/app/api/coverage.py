"""Coverage dashboard data: how much of the NAMASTE codebook actually has a
verified ICD-11 TM2 mapping, broken down honestly. This exists specifically
so the app never implies broader coverage than what's actually been
verified -- the ratio is the point, not a number to hide.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.codecs.mapping import mapping_table
from app.codecs.tm2_categories import category_for_code
from app.db import mongo

router = APIRouter()


@router.get("/coverage")
async def coverage() -> JSONResponse:
    client = await mongo.get_instance()
    namaste_db = client.get_database_by_name("ayurveda_db")
    icd_db = client.get_database_by_name("icd11_database")

    namaste_total = await namaste_db["namc_codes"].count_documents({})
    tm2_total_available = await icd_db["icd11_entities"].count_documents(
        {"title": {"$regex": r"\(TM2\)"}}
    )

    namaste_verified = len(mapping_table)
    namaste_unverified = max(namaste_total - namaste_verified, 0)
    verified_pct = round((namaste_verified / namaste_total) * 100, 2) if namaste_total else 0.0
    unverified_pct = round(100 - verified_pct, 2) if namaste_total else 0.0

    distinct_tm2_used = len({e.icd11_tm2_code for e in mapping_table.entries})
    tm2_vocab_coverage_pct = (
        round((distinct_tm2_used / tm2_total_available) * 100, 2) if tm2_total_available else 0.0
    )

    category_counts: dict[str, int] = {}
    for entry in mapping_table.entries:
        label = category_for_code(entry.icd11_tm2_code)
        category_counts[label] = category_counts.get(label, 0) + 1

    breakdown = [
        {"category": label, "count": count}
        for label, count in sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return JSONResponse(
        {
            "namaste": {
                "total": namaste_total,
                "verified": namaste_verified,
                "unverified": namaste_unverified,
                "verified_percentage": verified_pct,
                "unverified_percentage": unverified_pct,
            },
            "tm2": {
                "total_who_tm2_codes": tm2_total_available,
                "distinct_codes_used_in_verified_mappings": distinct_tm2_used,
                "vocabulary_coverage_percentage": tm2_vocab_coverage_pct,
            },
            "breakdown_by_category": breakdown,
            "mapping_version": mapping_table.version,
            "mapping_verified_at": mapping_table.verified_at,
            "discipline_note": (
                "All current NAMASTE data is sourced from India's Ayurveda codebook "
                "(Ministry of AYUSH). Siddha and Unani have their own separate NAMASTE "
                "codebooks, not yet integrated into this dataset."
            ),
            "unmapped_reason": (
                "Unmapped entries are NAMASTE codes whose own codebook entry does not "
                "embed a WHO ICD-11 TM2 crosswalk code -- we only report a mapping as "
                "verified when it is directly traceable to both the NAMASTE codebook and "
                "live WHO ICD-11 data; we do not guess at the remainder."
            ),
        }
    )
