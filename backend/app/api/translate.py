from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.assistant.groq_client import GroqNotConfiguredError
from app.assistant.translate import translate_text
from app.db import translations
from app.db.translations import SUPPORTED_LANGUAGES

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    language: str  # one of SUPPORTED_LANGUAGES keys, e.g. "hi"
    # Identifies the record/field being translated so repeat views of the
    # same record hit the cache instead of calling Groq again.
    source: str
    record_id: str
    field: str


@router.post("/translate")
async def translate(body: TranslateRequest) -> JSONResponse:
    if body.language not in SUPPORTED_LANGUAGES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported language '{body.language}'. Supported: {list(SUPPORTED_LANGUAGES)}"
            },
        )

    if not body.text.strip():
        return JSONResponse({"translated_text": body.text, "cached": False})

    cache_key = translations.make_cache_key(body.source, body.record_id, body.field, body.language)

    cached = await translations.get_cached(cache_key)
    if cached is not None:
        return JSONResponse({"translated_text": cached, "cached": True})

    try:
        translated = await translate_text(body.text, SUPPORTED_LANGUAGES[body.language])
    except GroqNotConfiguredError:
        return JSONResponse(
            status_code=503,
            content={"error": "Translation isn't configured yet (missing GROQ_API_KEY)."},
        )
    except Exception as e:
        print(f"Translation failed: {e}")
        return JSONResponse(
            status_code=502, content={"error": "Translation is temporarily unavailable."}
        )

    await translations.store(cache_key, body.text, translated, body.language)
    return JSONResponse({"translated_text": translated, "cached": False})


@router.get("/translate/languages")
async def list_languages() -> JSONResponse:
    return JSONResponse({"languages": SUPPORTED_LANGUAGES})
