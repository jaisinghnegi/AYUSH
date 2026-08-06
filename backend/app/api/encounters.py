"""Encounter persistence -- closes the "encounter upload" gap described on
the /docs page. A doctor builds a set of dual-coded diagnoses (in the
frontend Composer) and this is where that gets saved as a real patient
record tied to their account, with each diagnosis's NAMASTE<->ICD-11 TM2
pairing snapshotted against the verified mapping table at save time.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.auth.dependencies import get_current_user_email
from app.codecs.mapping import mapping_table
from app.db import encounters, users

router = APIRouter(prefix="/encounters")


class PatientInput(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class DiagnosisInput(BaseModel):
    namasteCode: Optional[str] = None
    icd11Code: Optional[str] = None
    # Only used as a fallback display if the code isn't found in our
    # verified mapping table (e.g. a manually-entered/unmapped pairing).
    namasteDisplay: Optional[str] = None
    icd11Display: Optional[str] = None


class EncounterCreateRequest(BaseModel):
    patient: PatientInput
    diagnoses: list[DiagnosisInput]


def _enrich_diagnosis(d: DiagnosisInput) -> dict:
    """Snapshot each diagnosis's dual-coding against the verified mapping
    table. mappingVerified=True only when the pairing actually comes from
    our verified NAMASTE<->TM2 crosswalk, not from freeform client input."""
    if d.namasteCode:
        matches = mapping_table.lookup_by_namaste(d.namasteCode)
        if matches:
            entry = matches[0]
            return {
                "namasteCode": entry.namaste_code,
                "namasteDisplay": entry.namaste_display or entry.namaste_term,
                "icd11Code": entry.icd11_tm2_code,
                "icd11Display": entry.icd11_tm2_title,
                "mappingVerified": True,
            }

    if d.icd11Code:
        matches = mapping_table.lookup_by_icd11_tm2(d.icd11Code)
        if matches:
            entry = matches[0]
            return {
                "namasteCode": entry.namaste_code,
                "namasteDisplay": entry.namaste_display or entry.namaste_term,
                "icd11Code": entry.icd11_tm2_code,
                "icd11Display": entry.icd11_tm2_title,
                "mappingVerified": True,
            }

    # No verified mapping found either direction -- store exactly what the
    # client sent, clearly flagged as unverified.
    return {
        "namasteCode": d.namasteCode,
        "namasteDisplay": d.namasteDisplay,
        "icd11Code": d.icd11Code,
        "icd11Display": d.icd11Display,
        "mappingVerified": False,
    }


@router.post("")
async def create_encounter(
    body: EncounterCreateRequest, email: str = Depends(get_current_user_email)
) -> JSONResponse:
    user = await users.get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=401, content={"error": "User not found"})

    diagnoses = [_enrich_diagnosis(d) for d in body.diagnoses]
    patient = body.patient.model_dump()

    encounter = await encounters.create_encounter(user.id, patient, diagnoses)
    return JSONResponse(status_code=201, content=encounter.to_response())


@router.get("")
async def list_encounters(email: str = Depends(get_current_user_email)) -> JSONResponse:
    user = await users.get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=401, content={"error": "User not found"})

    results = await encounters.list_encounters_by_user(user.id)
    return JSONResponse({"total": len(results), "encounters": [e.to_response() for e in results]})


@router.get("/{encounter_id}")
async def get_encounter(encounter_id: str, email: str = Depends(get_current_user_email)) -> JSONResponse:
    user = await users.get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=401, content={"error": "User not found"})

    encounter = await encounters.get_encounter(encounter_id, user.id)
    if not encounter:
        return JSONResponse(status_code=404, content={"error": "Encounter not found"})

    return JSONResponse(encounter.to_response())
