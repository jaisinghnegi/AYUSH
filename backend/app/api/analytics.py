"""Real-time morbidity analytics, built entirely from actual encounter
records -- not a mockup. As doctors save encounters through the app, this
reflects real dual-coded diagnosis activity: most common conditions,
verified-vs-unverified split, and category distribution.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.codecs.tm2_categories import category_for_code
from app.db import mongo

router = APIRouter()


@router.get("/analytics")
async def analytics() -> JSONResponse:
    client = await mongo.get_instance()
    collection = client.database["encounters"]

    total_encounters = await collection.count_documents({})

    patient_keys = set()
    diagnosis_counts: dict[str, dict] = {}
    category_counts: dict[str, int] = {}
    verified_count = 0
    unverified_count = 0

    cursor = collection.find({})
    async for doc in cursor:
        patient = doc.get("patient") or {}
        key = patient.get("email") or patient.get("name")
        if key:
            patient_keys.add(key)

        for dx in doc.get("diagnoses", []):
            if dx.get("mappingVerified"):
                verified_count += 1
            else:
                unverified_count += 1

            icd_code = dx.get("icd11Code")
            display = dx.get("icd11Display") or dx.get("namasteDisplay") or "Unlabeled diagnosis"
            key = icd_code or dx.get("namasteCode") or display

            if key not in diagnosis_counts:
                diagnosis_counts[key] = {"code": icd_code, "display": display, "count": 0}
            diagnosis_counts[key]["count"] += 1

            if icd_code:
                category = category_for_code(icd_code)
                category_counts[category] = category_counts.get(category, 0) + 1

    most_common = sorted(diagnosis_counts.values(), key=lambda d: d["count"], reverse=True)[:10]
    category_breakdown = sorted(
        ({"category": k, "count": v} for k, v in category_counts.items()),
        key=lambda d: d["count"],
        reverse=True,
    )

    recent = []
    async for doc in collection.find({}).sort("createdAt", -1).limit(5):
        recent.append(
            {
                "id": str(doc["_id"]),
                "patient_name": (doc.get("patient") or {}).get("name", "Unknown"),
                "diagnosis_count": len(doc.get("diagnoses", [])),
                "created_at": doc["createdAt"].isoformat(),
            }
        )

    total_diagnoses = verified_count + unverified_count

    return JSONResponse(
        {
            "total_encounters": total_encounters,
            "total_unique_patients": len(patient_keys),
            "total_diagnoses_recorded": total_diagnoses,
            "verified_diagnoses": verified_count,
            "unverified_diagnoses": unverified_count,
            "most_common_diagnoses": most_common,
            "diagnoses_by_category": category_breakdown,
            "recent_encounters": recent,
            "note": (
                "This reflects real encounters saved through the app (Composer -> Generate FHIR "
                "Bundle, while logged in). It starts empty and grows with actual usage -- nothing "
                "here is seeded or simulated."
            ),
        }
    )
