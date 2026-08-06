from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.codecs.icd import IcdCodec, IcdDiscipline, IcdFilter

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_discipline(value: Optional[str]) -> Optional[IcdDiscipline]:
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "biomedicine":
        return IcdDiscipline.BIOMEDICINE
    if lowered == "tm2":
        return IcdDiscipline.TM2
    return None


@router.get("/search")
async def icd_search(
    search: Optional[str] = None,
    discipline: Optional[str] = None,
    parent: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    codec = IcdCodec()
    filter = IcdFilter(
        discipline=_parse_discipline(discipline),
        search_term=search,
        parent_filter=parent,
    )

    try:
        codes = await codec.search_codes(filter, limit)
        formatted = codec.format_response(codes)
        return JSONResponse(
            {
                "service": "ICD-11 Search",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "ICD-11 Search",
                "status": "error",
                "message": f"Search failed: {e}",
                "timestamp": _now(),
            },
        )


@router.get("/all")
async def icd_all(limit: Optional[int] = None) -> JSONResponse:
    codec = IcdCodec()
    try:
        codes = await codec.get_all_codes(limit)
        formatted = codec.format_response(codes)
        return JSONResponse(
            {
                "service": "ICD-11 All Codes",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "ICD-11 All Codes",
                "status": "error",
                "message": f"Failed: {e}",
                "timestamp": _now(),
            },
        )


@router.get("/biomedicine")
async def icd_biomedicine(limit: Optional[int] = None) -> JSONResponse:
    codec = IcdCodec()
    try:
        codes = await codec.get_biomedicine_codes(limit)
        formatted = codec.format_response(codes)
        return JSONResponse(
            {
                "service": "ICD-11 Biomedicine",
                "discipline": "BIOMEDICINE",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "ICD-11 Biomedicine",
                "status": "error",
                "message": f"Failed: {e}",
                "timestamp": _now(),
            },
        )


@router.get("/tm2")
async def icd_tm2(limit: Optional[int] = None) -> JSONResponse:
    codec = IcdCodec()
    try:
        codes = await codec.get_tm2_codes(limit)
        formatted = codec.format_response(codes)
        return JSONResponse(
            {
                "service": "ICD-11 Traditional Medicine",
                "discipline": "TM2",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "ICD-11 TM2",
                "status": "error",
                "message": f"Failed: {e}",
                "timestamp": _now(),
            },
        )
