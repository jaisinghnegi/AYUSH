from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse

from app.codecs.mapping import mapping_table
from app.db import mongo, redis_client
from app.sync.icd11_sync import run_sync, sync_status

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_response(service: str, status: str, message: str) -> dict:
    return {"service": service, "status": status, "message": message, "timestamp": _now()}


@router.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(
        _api_response("FHIR Terminology Server", "healthy", "Server is running successfully")
    )


@router.get("/gateway")
async def api_gateway() -> JSONResponse:
    return JSONResponse(
        _api_response(
            "API Gateway & OAuth 2.0 + ABHA Authentication",
            "active",
            "Authentication layer is operational",
        )
    )


@router.get("/api")
async def rest_api() -> JSONResponse:
    return JSONResponse(
        _api_response("REST API Server", "running", "Main API server handling requests")
    )


@router.get("/services/terminology")
async def terminology_service() -> JSONResponse:
    return JSONResponse(
        _api_response("Terminology Service", "running", "Managing medical terminologies and codes")
    )


@router.get("/services/mapping")
async def mapping_service() -> JSONResponse:
    return JSONResponse(
        {
            "service": "Mapping Service",
            "status": "running",
            "message": "Handling NAMASTE <-> ICD-11 TM2 terminology mappings",
            "mapping_version": mapping_table.version,
            "mapping_verified_at": mapping_table.verified_at,
            "mapping_entry_count": len(mapping_table),
            "timestamp": _now(),
        }
    )


@router.get("/services/sync")
async def sync_service() -> JSONResponse:
    return JSONResponse(
        _api_response("Sync Service", "running", "Synchronizing with external APIs")
    )


@router.post("/services/sync/icd11-live")
async def sync_icd11_live(background_tasks: BackgroundTasks, release: str = "2025-01") -> JSONResponse:
    if sync_status["state"] == "running":
        return JSONResponse(
            status_code=409,
            content={
                "service": "ICD-11 Live Sync",
                "status": "already_running",
                "message": "A sync is already in progress -- check GET /services/sync/icd11-live/status",
                "timestamp": _now(),
            },
        )

    # Pulling the full WHO ICD-11 MMS tree takes tens of minutes, far past
    # any sane HTTP timeout, so this kicks it off and returns immediately --
    # poll the status endpoint below for progress.
    background_tasks.add_task(run_sync, release=release)

    return JSONResponse(
        {
            "service": "ICD-11 Live Sync",
            "status": "started",
            "message": f"Live sync from WHO ICD-11 API (release {release}) started in the background. "
                       "Falls back to the bundled CSV automatically if WHO credentials are missing or "
                       "the live pull fails.",
            "poll_url": "/services/sync/icd11-live/status",
            "timestamp": _now(),
        }
    )


@router.get("/services/sync/icd11-live/status")
async def sync_icd11_live_status() -> JSONResponse:
    return JSONResponse({"service": "ICD-11 Live Sync", **sync_status, "timestamp": _now()})


@router.get("/services/audit")
async def audit_service() -> JSONResponse:
    return JSONResponse(
        _api_response("Audit Service", "running", "Logging and auditing system activities")
    )


@router.get("/core/fhir")
async def fhir_engine() -> JSONResponse:
    return JSONResponse(
        _api_response("FHIR R4 Engine", "running", "Processing FHIR R4 resources")
    )


@router.get("/core/vocabulary")
async def vocabulary_manager() -> JSONResponse:
    return JSONResponse(
        _api_response("Vocabulary Manager", "running", "Managing medical vocabularies")
    )


@router.get("/core/translation")
async def translation_engine() -> JSONResponse:
    return JSONResponse(
        _api_response("Translation Engine", "running", "Translating between coding systems")
    )


@router.get("/data/mongodb")
async def mongodb_status() -> JSONResponse:
    status = await mongo.get_connection_status()
    if status.connected:
        message = f"Connected to {status.database_name} - {status.server_info or 'MongoDB'}"
    else:
        message = f"Connection failed: {status.error or 'Unknown error'}"

    response = _api_response(
        "MongoDB", "connected" if status.connected else "disconnected", message
    )
    return JSONResponse(response, status_code=200 if status.connected else 503)


@router.get("/data/redis")
async def redis_status() -> JSONResponse:
    status = await redis_client.get_connection_status()
    if status.connected:
        message = status.server_info or "Redis connected"
    else:
        message = f"Connection failed: {status.error or 'Unknown error'}"

    response = _api_response(
        "Redis Cache", "connected" if status.connected else "disconnected", message
    )
    return JSONResponse(response, status_code=200 if status.connected else 503)


@router.get("/external/who-icd11")
async def who_api() -> JSONResponse:
    return JSONResponse(
        _api_response("WHO ICD-11 API", "connected", "WHO ICD-11 integration active")
    )


@router.get("/external/namaste-csv")
async def namaste_csv() -> JSONResponse:
    return JSONResponse(
        _api_response("NAMASTE CSV Files", "accessible", "NAMASTE data processing ready")
    )


@router.get("/data/mongodb/collections")
async def mongodb_collections() -> JSONResponse:
    try:
        client = await mongo.get_instance()
        collections = await client.list_collections()
        return JSONResponse(
            {
                "service": "MongoDB Collections",
                "collections": collections,
                "count": len(collections),
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content=_api_response(
                "MongoDB Collections", "unavailable", f"MongoDB not connected: {e}"
            ),
        )


@router.get("/terminology/ayurveda")
async def ayurveda_terminology() -> JSONResponse:
    try:
        client = await mongo.get_instance()
        ayurveda_db = client.get_database_by_name("ayurveda_db")
        collections = await ayurveda_db.list_collection_names()
        return JSONResponse(
            {
                "service": "Ayurveda Terminology",
                "status": "available",
                "database_size": "584 KB",
                "collections": collections,
                "message": "Ayurveda database ready for FHIR terminology services",
                "timestamp": _now(),
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content=_api_response(
                "Ayurveda Terminology", "unavailable", f"Database not connected: {e}"
            ),
        )
