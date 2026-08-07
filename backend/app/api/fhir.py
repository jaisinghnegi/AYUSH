"""FHIR-operation-shaped endpoints: ConceptMap/$translate, ValueSet/$expand,
CodeSystem/$lookup.

These wrap the same search/mapping logic used by the plain REST endpoints
(/namaste/search, /icd/search, /terminology/search) and the verified
NAMASTE<->TM2 mapping table, but expose it under the literal FHIR operation
names and Parameters/ValueSet response shapes described in the API docs page,
since that's the contract external FHIR-aware systems (and evaluators) will
actually look for.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from app import config
from app.auth.dependencies import get_optional_user_email
from app.codecs.icd import IcdCodec, IcdFilter
from app.codecs.mapping import ICD11_TM2_SYSTEM, NAMASTE_SYSTEM, mapping_table
from app.codecs.namaste import Language, NamasteCodec, NamasteFilter
from app.codecs.semantic import semantic_search_by_text
from app.db import audit, mongo, users

router = APIRouter()

# Canonical URL of the ConceptMap this $translate operation is backed by --
# matches the ConceptMap resource described on the /docs page. FHIR defines
# match.source as a uri referencing this, not a free-text provenance note.
CONCEPT_MAP_URL = "http://ayu-setu.org/ConceptMap/namaste-to-icd11"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_namaste_system(system: str) -> bool:
    return "namaste" in system.lower()


def _is_icd11_system(system: str) -> bool:
    lowered = system.lower()
    return "icd" in lowered or "who.int" in lowered


# ---------------------------------------------------------------------------
# ConceptMap/$translate
# ---------------------------------------------------------------------------

def _extract_translate_params(body: dict) -> tuple[Optional[str], Optional[str]]:
    """Pull {code, system} out of a FHIR Parameters resource body."""
    code = None
    system = None
    for param in body.get("parameter", []):
        name = param.get("name")
        if name == "code":
            code = param.get("valueCode") or param.get("valueString")
        elif name == "system":
            system = param.get("valueUri") or param.get("valueString")
    return code, system


def _translate_result(
    result: bool, message: str, matches: list[dict], candidates: Optional[list[dict]] = None
) -> dict:
    parameters: list[dict] = [
        {"name": "result", "valueBoolean": result},
        {"name": "message", "valueString": message},
    ]
    for match in matches:
        parameters.append({"name": "match", "part": match})
    # "candidate" is not a FHIR-defined part of $translate -- it's our own
    # addition for the case where there's no verified crosswalk entry, but
    # semantic search over real TM2 embeddings still found plausible
    # matches. Kept clearly distinct from "match" (verified) so a client
    # can never confuse an AI-ranked guess for a confirmed mapping.
    for candidate in candidates or []:
        parameters.append({"name": "candidate", "part": candidate})
    return {"resourceType": "Parameters", "parameter": parameters}


async def _get_namaste_query_text(code: str) -> Optional[str]:
    """Fetch a NAMASTE entry's own text (for embedding), by numeric id or
    raw AYU code -- same lookup semantics as mapping_table.lookup_by_namaste."""
    client = await mongo.get_instance()
    db = client.get_database_by_name("ayurveda_db")
    collection = db["namc_codes"]

    doc = None
    if code.isdigit():
        doc = await collection.find_one({"field_1": int(code)})
    if doc is None:
        doc = await collection.find_one({"AYU": code})
    if doc is None:
        return None

    parts = [
        doc.get("vyAdhi-viniScayaH"),
        doc.get("vyādhi-viniścayaḥ"),
        doc.get("व्याधि-विनिश्चयः"),
        doc.get("Unnamed: 7"),  # long_definition
    ]
    text = " ".join(p for p in parts if p)
    return text or None


async def _find_semantic_candidates(code: str, limit: int = 3, threshold: float = 0.55) -> list[dict]:
    """When there's no verified NAMASTE<->TM2 mapping, fall back to real
    embedding similarity over the (separately generated) TM2 embeddings --
    ranked, honestly labeled as unverified, never presented as a match."""
    if not config.GEMINI_KEY:
        return []

    query_text = await _get_namaste_query_text(code)
    if not query_text:
        return []

    try:
        results = await semantic_search_by_text(
            config.GEMINI_KEY, query_text, limit, threshold, "icd11_entities", "icd11_database"
        )
    except Exception as e:
        print(f"Semantic candidate search failed (non-fatal): {e}")
        return []

    candidates = []
    for r in results:
        doc = r.document
        candidates.append(
            [
                {
                    "name": "concept",
                    "valueCoding": {
                        "system": ICD11_TM2_SYSTEM,
                        "code": doc.get("code", ""),
                        "display": doc.get("title", ""),
                    },
                },
                {"name": "similarity", "valueDecimal": round(r.similarity, 3)},
            ]
        )
    return candidates


async def _resolve_user_id(email: Optional[str]) -> Optional[str]:
    """Best-effort: turn a JWT's email subject into the user's Mongo _id for
    audit attribution. Returns None if there's no token, or it doesn't match
    a real user -- callers must treat that as "unauthenticated", not error."""
    if not email:
        return None
    user = await users.get_user_by_email(email)
    return user.id if user else None


async def _do_translate(
    code: Optional[str], system: Optional[str], requester_email: Optional[str] = None
) -> JSONResponse:
    user_id = await _resolve_user_id(requester_email)

    if not code or not system:
        return JSONResponse(
            status_code=400,
            content=_translate_result(False, "Both 'code' and 'system' are required", []),
        )

    if _is_namaste_system(system):
        entries = mapping_table.lookup_by_namaste(code)
        target_system_label = "NAMASTE"
    elif _is_icd11_system(system):
        entries = mapping_table.lookup_by_icd11_tm2(code)
        target_system_label = "ICD-11 TM2"
    else:
        return JSONResponse(
            status_code=400,
            content=_translate_result(False, f"Unrecognized system: {system}", []),
        )

    if not entries:
        candidates = await _find_semantic_candidates(code) if _is_namaste_system(system) else []
        message = f"No verified mapping found for code '{code}' in {target_system_label}"
        if candidates:
            message += (
                f" -- showing {len(candidates)} semantically similar candidate(s) instead, "
                "ranked by real embedding similarity. These are unverified suggestions, not "
                "confirmed mappings."
            )
        await audit.log_lookup(
            "ConceptMap/$translate", system, code, found=False, user_id=user_id
        )
        return JSONResponse(_translate_result(False, message, [], candidates))

    matches = []
    for entry in entries:
        if _is_namaste_system(system):
            concept = {
                "system": ICD11_TM2_SYSTEM,
                "code": entry.icd11_tm2_code,
                "display": entry.icd11_tm2_title,
            }
        else:
            concept = {
                "system": NAMASTE_SYSTEM,
                "code": entry.namaste_code,
                "display": entry.namaste_display or entry.namaste_term,
            }

        matches.append(
            [
                {"name": "equivalence", "valueCode": entry.equivalence},
                {"name": "concept", "valueCoding": concept},
                # FHIR-defined part: canonical URL of the ConceptMap used.
                {"name": "source", "valueUri": CONCEPT_MAP_URL},
                # Custom (non-reserved) part: our own provenance note --
                # Parameters is an open resource, extra named parts are fine
                # as long as they don't collide with spec-defined names.
                {"name": "provenance", "valueString": entry.source},
            ]
        )

    first = entries[0]
    await audit.log_lookup(
        "ConceptMap/$translate",
        system,
        code,
        found=True,
        result_code=first.icd11_tm2_code if _is_namaste_system(system) else first.namaste_code,
        result_display=first.icd11_tm2_title if _is_namaste_system(system) else first.namaste_display,
        user_id=user_id,
    )

    return JSONResponse(_translate_result(True, "Concept translated", matches))


@router.post("/ConceptMap/$translate")
async def concept_map_translate(
    body: dict = Body(default={}), requester_email: Optional[str] = Depends(get_optional_user_email)
) -> JSONResponse:
    code, system = _extract_translate_params(body)
    return await _do_translate(code, system, requester_email)


@router.get("/ConceptMap/$translate")
async def concept_map_translate_get(
    code: Optional[str] = None,
    system: Optional[str] = None,
    requester_email: Optional[str] = Depends(get_optional_user_email),
) -> JSONResponse:
    return await _do_translate(code, system, requester_email)


# ---------------------------------------------------------------------------
# ValueSet/$expand
# ---------------------------------------------------------------------------

def _valueset_contains_from_namaste(results: list[dict]) -> list[dict]:
    return [
        {
            "system": NAMASTE_SYSTEM,
            "code": r.get("nam_code") or "",
            "display": r.get("display") or r.get("term") or "",
            "designation": [{"value": r.get("term") or ""}],
        }
        for r in results
    ]


def _valueset_contains_from_icd(results: list[dict]) -> list[dict]:
    return [
        {
            "system": ICD11_TM2_SYSTEM,
            "code": r.get("code") or "",
            "display": r.get("title") or "",
            "designation": [{"value": r.get("title") or ""}],
        }
        for r in results
    ]


@router.get("/ValueSet/$expand")
async def valueset_expand(url: str = "", filter: str = "", count: int = 20) -> JSONResponse:
    filter_term = filter.strip()
    if not filter_term:
        return JSONResponse(
            status_code=400,
            content={
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "diagnostics": "'filter' query parameter is required"}],
            },
        )

    contains: list[dict] = []

    if _is_namaste_system(url) or not url:
        codec = NamasteCodec()
        results = await codec.search_codes(
            NamasteFilter(code=None, language=Language.BOTH, search_term=filter_term), count
        )
        contains.extend(_valueset_contains_from_namaste(codec.format_response(results, Language.BOTH)))

    if _is_icd11_system(url) or not url:
        codec = IcdCodec()
        results = await codec.search_codes(IcdFilter(search_term=filter_term), count)
        contains.extend(_valueset_contains_from_icd(codec.format_response(results)))

    return JSONResponse(
        {
            "resourceType": "ValueSet",
            "expansion": {
                "identifier": f"expand-{filter_term}",
                "timestamp": _now(),
                "total": len(contains),
                "contains": contains[:count],
            },
        }
    )


# ---------------------------------------------------------------------------
# CodeSystem/$lookup
# ---------------------------------------------------------------------------

@router.get("/CodeSystem/$lookup")
async def codesystem_lookup(
    system: str = "",
    code: str = "",
    requester_email: Optional[str] = Depends(get_optional_user_email),
) -> JSONResponse:
    user_id = await _resolve_user_id(requester_email)

    if not system or not code:
        return JSONResponse(
            status_code=400,
            content={
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "diagnostics": "'system' and 'code' query parameters are required"}],
            },
        )

    if _is_namaste_system(system):
        client = await mongo.get_instance()
        db = client.get_database_by_name("ayurveda_db")
        collection = db["namc_codes"]

        # $lookup is an exact-code operation, not fuzzy search -- match the
        # AYU field literally (it can contain regex metacharacters like
        # parentheses, e.g. "SP51(EC-3)") or fall back to the numeric id.
        doc = await collection.find_one({"AYU": code})
        if doc is None and code.isdigit():
            doc = await collection.find_one({"field_1": int(code)})

        if doc is None:
            await audit.log_lookup("CodeSystem/$lookup", system, code, found=False, user_id=user_id)
            return JSONResponse(
                status_code=404,
                content={
                    "resourceType": "OperationOutcome",
                    "issue": [{"severity": "error", "diagnostics": f"Code '{code}' not found in {system}"}],
                },
            )

        display = doc.get("vyādhi-viniścayaḥ") or doc.get("vyAdhi-viniScayaH") or ""
        definition = doc.get("Unnamed: 6") or doc.get("Unnamed: 7") or ""
        await audit.log_lookup(
            "CodeSystem/$lookup", system, code, found=True, result_display=display, user_id=user_id
        )
        return JSONResponse(
            {
                "resourceType": "Parameters",
                "parameter": [
                    {"name": "name", "valueString": "NAMASTE"},
                    {"name": "display", "valueString": display},
                    {"name": "definition", "valueString": definition},
                    {"name": "code", "valueCode": doc.get("AYU", "")},
                ],
            }
        )

    if _is_icd11_system(system):
        client = await mongo.get_instance()
        db = client.get_database_by_name("icd11_database")
        collection = db["icd11_entities"]
        doc = await collection.find_one({"code": code})
        if not doc:
            await audit.log_lookup("CodeSystem/$lookup", system, code, found=False, user_id=user_id)
            return JSONResponse(
                status_code=404,
                content={
                    "resourceType": "OperationOutcome",
                    "issue": [{"severity": "error", "diagnostics": f"Code '{code}' not found in {system}"}],
                },
            )
        await audit.log_lookup(
            "CodeSystem/$lookup",
            system,
            code,
            found=True,
            result_display=doc.get("title", ""),
            user_id=user_id,
        )
        return JSONResponse(
            {
                "resourceType": "Parameters",
                "parameter": [
                    {"name": "name", "valueString": "ICD-11"},
                    {"name": "display", "valueString": doc.get("title", "")},
                    {"name": "definition", "valueString": doc.get("definition") or ""},
                    {"name": "code", "valueCode": doc.get("code", "")},
                ],
            }
        )

    return JSONResponse(
        status_code=400,
        content={
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "diagnostics": f"Unrecognized system: {system}"}],
        },
    )
