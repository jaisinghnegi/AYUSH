from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import config
from app.codecs.icd import IcdCodec, IcdFilter
from app.codecs.namaste import Language, NamasteCodec, NamasteFilter
from app.codecs.semantic import SimilarityResult
from app.codecs.semantic import semantic_search_local as _semantic_search_local
from app.gemini.embedding import call_gemini_embedding_api

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SearchMethod(str, Enum):
    SEMANTIC = "semantic"
    REGEX = "regex"
    AUTO = "auto"

    @staticmethod
    def from_str(s: str) -> "SearchMethod":
        lowered = s.lower()
        if lowered in ("semantic", "vector", "embedding"):
            return SearchMethod.SEMANTIC
        if lowered in ("regex", "text", "keyword"):
            return SearchMethod.REGEX
        return SearchMethod.AUTO


def _format_namaste_results(results: list[SimilarityResult], include_similarity: bool) -> list[dict]:
    formatted = []
    for result in results:
        doc = result.document
        title = (
            doc.get("vyAdhi-viniScayaH")
            or doc.get("vyādhi-viniścayaḥ")
            or doc.get("व्याधि-विनिश्चयः")
            or ""
        )
        json_result: dict[str, Any] = {
            "id": str(doc.get("_id", "")),
            "code": doc.get("field_1", ""),
            "title": title,
            "definition": doc.get("AYU", ""),
            "source": "NAMASTE",
            "system": "Ayurveda",
            "code_system": "NAMASTE",
            "nam_code": doc.get("field_1", ""),
            "icd_code": None,
        }

        if include_similarity:
            json_result["similarity"] = result.similarity
            json_result["search_type"] = "semantic"
        else:
            json_result["search_type"] = "regex"

        formatted.append(json_result)
    return formatted


def _format_icd_results(results: list[SimilarityResult], include_similarity: bool) -> list[dict]:
    formatted = []
    for result in results:
        doc = result.document
        json_result: dict[str, Any] = {
            "id": doc.get("id", ""),
            "code": doc.get("code", ""),
            "title": doc.get("title", ""),
            "definition": doc.get("definition", ""),
            "parent": doc.get("parent", ""),
            "browserUrl": doc.get("browserUrl", ""),
            "synonyms": doc.get("synonyms", ""),
            "exclusions": doc.get("exclusions", ""),
            "inclusions": doc.get("inclusions", ""),
            "isLeaf": doc.get("isLeaf", ""),
            "source": "ICD-11",
            "system": "Biomedicine",
            "code_system": "ICD",
            "nam_code": None,
            "icd_code": doc.get("code", ""),
        }

        if include_similarity:
            json_result["similarity"] = result.similarity
            json_result["search_type"] = "semantic"
        else:
            json_result["search_type"] = "regex"

        formatted.append(json_result)
    return formatted


def _extract_code_system(label: str) -> Optional[str]:
    start = label.find("(")
    if start == -1:
        return None
    end = label.find(")")
    if end == -1 or end <= start:
        return None
    return label[start + 1:end]


def _parse_language(value: Optional[str]) -> Language:
    if value == "hindi":
        return Language.HINDI
    if value == "english":
        return Language.ENGLISH
    return Language.BOTH


async def _perform_regex_search(
    search_term: Optional[str],
    limit: Optional[int],
    language: Language,
) -> tuple[list[dict], int, int]:
    combined_results: list[dict] = []
    namaste_count = 0
    icd_count = 0

    namaste_codec = NamasteCodec()
    namaste_filter = NamasteFilter(code=None, language=language, search_term=search_term)

    try:
        codes = await namaste_codec.search_codes(namaste_filter, limit)
        namaste_count = len(codes)
        formatted = namaste_codec.format_response(codes, language)
        for result in formatted:
            result["source"] = "NAMASTE"
            result["system"] = "Ayurveda"
            result["search_type"] = "regex"

            code_system = None
            if result.get("term"):
                code_system = _extract_code_system(result["term"])
            elif result.get("display"):
                code_system = _extract_code_system(result["display"])

            result["code_system"] = code_system or "NAMASTE"
            combined_results.append(result)
    except Exception as e:
        print(f"NAMASTE search failed: {e}")

    icd_codec = IcdCodec()
    icd_filter = IcdFilter(discipline=None, search_term=search_term, parent_filter=None)

    try:
        codes = await icd_codec.search_codes(icd_filter, limit)
        icd_count = len(codes)
        icd_formatted = icd_codec.format_response(codes)
        for result in icd_formatted:
            code_value = result.get("code")
            result["nam_code"] = None
            result["icd_code"] = code_value
            result["source"] = "ICD-11"
            result["system"] = "Biomedicine"
            result["code_system"] = "ICD"
            result["search_type"] = "regex"
            combined_results.append(result)
    except Exception as e:
        print(f"ICD search failed: {e}")

    if limit is not None:
        combined_results = combined_results[:limit]

    return combined_results, namaste_count, icd_count


async def _run_semantic_search(
    query_embedding: list[float], limit: int, threshold: float
) -> tuple[list[dict], int, int]:
    all_results: list[dict] = []
    namaste_count = 0
    icd_count = 0

    try:
        results = await _semantic_search_local(
            query_embedding, limit, threshold, "namc_codes", "ayurveda_db"
        )
        namaste_count = len(results)
        if namaste_count > 0:
            print(f"✅ Found {namaste_count} NAMASTE semantic results")
        all_results.extend(_format_namaste_results(results, True))
    except Exception as e:
        print(f"❌ NAMASTE semantic search failed: {e}")

    try:
        results = await _semantic_search_local(
            query_embedding, limit, threshold, "icd11_entities", "icd11_database"
        )
        icd_count = len(results)
        if icd_count > 0:
            print(f"✅ Found {icd_count} ICD semantic results")
        all_results.extend(_format_icd_results(results, True))
    except Exception as e:
        print(f"❌ ICD semantic search failed: {e}")

    all_results.sort(key=lambda r: r.get("similarity", 0.0), reverse=True)
    all_results = all_results[:limit]

    return all_results, namaste_count, icd_count


@router.get("/search")
async def terminology_search(request: Request) -> JSONResponse:
    params = request.query_params
    search_term = (params.get("search") or "").strip()

    if not search_term:
        return JSONResponse(
            status_code=400,
            content={
                "service": "Terminology Search",
                "status": "error",
                "message": "Search term is required",
                "timestamp": _now(),
            },
        )

    limit_raw = params.get("limit")
    limit = int(limit_raw) if limit_raw and limit_raw.isdigit() else 10

    threshold_raw = params.get("threshold")
    try:
        threshold = float(threshold_raw) if threshold_raw else 0.7
    except ValueError:
        threshold = 0.7

    language = _parse_language(params.get("language"))

    method_raw = params.get("method") or params.get("search_type")
    search_method = SearchMethod.from_str(method_raw) if method_raw else SearchMethod.AUTO

    print(f"🔍 Search method requested: {search_method}")

    if search_method == SearchMethod.REGEX:
        print("📝 Performing regex search (forced)")
        results, namaste_count, icd_count = await _perform_regex_search(search_term, limit, language)

        return JSONResponse(
            {
                "service": "Regex Terminology Search",
                "search_term": search_term,
                "total_results": len(results),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": results,
                "search_type": "regex",
                "method_requested": "regex",
                "timestamp": _now(),
            }
        )

    if search_method == SearchMethod.SEMANTIC:
        api_key = config.GEMINI_KEY
        if not api_key:
            return JSONResponse(
                status_code=400,
                content={
                    "service": "Semantic Terminology Search",
                    "status": "error",
                    "message": "Semantic search requested but GEMINI_KEY not available",
                    "search_term": search_term,
                    "method_requested": "semantic",
                    "timestamp": _now(),
                },
            )

        try:
            query_embedding = await call_gemini_embedding_api(api_key, search_term)
            print(f"✅ Generated query embedding with {len(query_embedding)} dimensions")
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "service": "Semantic Terminology Search",
                    "status": "error",
                    "message": f"Failed to generate embedding: {e}",
                    "search_term": search_term,
                    "method_requested": "semantic",
                    "timestamp": _now(),
                },
            )

        print("🔍 Performing semantic search (forced)")
        all_results, namaste_count, icd_count = await _run_semantic_search(
            query_embedding, limit, threshold
        )

        return JSONResponse(
            {
                "service": "Semantic Terminology Search",
                "search_term": search_term,
                "total_results": len(all_results),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": all_results,
                "search_type": "semantic",
                "method_requested": "semantic",
                "threshold": threshold,
                "timestamp": _now(),
            }
        )

    # SearchMethod.AUTO: try semantic first, fallback to regex
    api_key = config.GEMINI_KEY
    if not api_key:
        print("❌ No GEMINI_KEY found, falling back to regex search")
        results, namaste_count, icd_count = await _perform_regex_search(search_term, limit, language)

        return JSONResponse(
            {
                "service": "Auto Terminology Search (Regex Fallback)",
                "search_term": search_term,
                "total_results": len(results),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": results,
                "search_type": "regex",
                "method_requested": "auto",
                "fallback_reason": "no_gemini_key",
                "timestamp": _now(),
            }
        )

    try:
        query_embedding = await call_gemini_embedding_api(api_key, search_term)
        print(f"✅ Generated query embedding with {len(query_embedding)} dimensions")
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}, falling back to regex search")
        results, namaste_count, icd_count = await _perform_regex_search(search_term, limit, language)

        return JSONResponse(
            {
                "service": "Auto Terminology Search (Regex Fallback)",
                "search_term": search_term,
                "total_results": len(results),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": results,
                "search_type": "regex",
                "method_requested": "auto",
                "fallback_reason": "embedding_generation_failed",
                "timestamp": _now(),
            }
        )

    print("🔍 Performing semantic search (auto mode)")
    all_results, namaste_count, icd_count = await _run_semantic_search(query_embedding, limit, threshold)

    if not all_results:
        print("❌ No semantic results found, falling back to regex search")
        results, namaste_count, icd_count = await _perform_regex_search(search_term, limit, language)

        return JSONResponse(
            {
                "service": "Auto Terminology Search (Regex Fallback)",
                "search_term": search_term,
                "total_results": len(results),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": results,
                "search_type": "regex",
                "method_requested": "auto",
                "fallback_reason": "no_semantic_results",
                "threshold": threshold,
                "timestamp": _now(),
            }
        )

    print(f"✅ Semantic search completed with {len(all_results)} total results")

    return JSONResponse(
        {
            "service": "Auto Semantic Terminology Search",
            "search_term": search_term,
            "total_results": len(all_results),
            "namaste_results": namaste_count,
            "icd_results": icd_count,
            "results": all_results,
            "search_type": "semantic",
            "method_requested": "auto",
            "threshold": threshold,
            "timestamp": _now(),
        }
    )
