from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.codecs.namaste import Language, NamasteCodec, NamasteFilter

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_language(value: Optional[str]) -> Language:
    if value == "hindi":
        return Language.HINDI
    if value == "english":
        return Language.ENGLISH
    return Language.BOTH


@router.get("/search")
async def namaste_search(
    search: Optional[str] = None,
    code: Optional[str] = None,
    language: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    codec = NamasteCodec()
    lang = _parse_language(language)
    filter = NamasteFilter(code=code, language=lang, search_term=search)

    try:
        codes = await codec.search_codes(filter, limit)
        formatted = codec.format_response(codes, lang)
        return JSONResponse(
            {
                "service": "NAMASTE Code Search",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "NAMASTE Code Search",
                "status": "error",
                "message": f"Search failed: {e}",
                "timestamp": _now(),
            },
        )


@router.get("/all")
async def namaste_all(
    language: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    codec = NamasteCodec()
    lang = _parse_language(language)

    try:
        codes = await codec.get_all_codes(limit)
        formatted = codec.format_response(codes, lang)
        return JSONResponse(
            {
                "service": "NAMASTE All Codes",
                "total": len(formatted),
                "results": formatted,
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "service": "NAMASTE All Codes",
                "status": "error",
                "message": f"Failed: {e}",
                "timestamp": _now(),
            },
        )
