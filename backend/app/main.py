from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import fhir, icd_search, namaste_search, routes, terminology_search
from app.db import mongo, redis_client
from app.gemini.embedding import generate_embeddings_handler


def _print_startup_banner() -> None:
    print("🚀 Starting FHIR Terminology Server...")


def _print_endpoint_banner() -> None:
    print(f"📊 Server running on http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"🏥 Health check: http://{config.SERVER_HOST}:{config.SERVER_PORT}/health")
    print()
    print("📋 Available API Endpoints:")

    print("   🔧 SYSTEM:")
    print("      GET  /health                     - Health check")
    print("      GET  /gateway                    - API Gateway & OAuth 2.0 status")
    print("      GET  /api                        - REST API server status")

    print("   🛠️  SERVICES:")
    print("      GET  /services/terminology       - Terminology service status")
    print("      GET  /services/mapping           - Mapping service status")
    print("      GET  /services/sync              - Sync service status")
    print("      GET  /services/audit             - Audit service status")

    print("   🧠 CORE:")
    print("      GET  /core/fhir                  - FHIR R4 engine status")
    print("      GET  /core/vocabulary             - Vocabulary manager status")
    print("      GET  /core/translation            - Translation engine status")

    print("   💾 DATA:")
    print("      GET  /data/mongodb               - MongoDB connection status")
    print("      GET  /data/mongodb/collections   - List MongoDB collections")
    print("      GET  /data/redis                 - Redis cache status")

    print("   🌐 EXTERNAL:")
    print("      GET  /external/who-icd11         - WHO ICD-11 API status")
    print("      GET  /external/namaste-csv       - NAMASTE CSV files status")

    print(" 📚 TERMINOLOGY:")
    print(" GET /terminology/search - Combined NAMASTE + ICD search")
    print("     ?search=term           - Search term (required)")
    print("     &method=auto|semantic|regex - Search method (default: auto)")
    print("     &limit=N               - Limit results")
    print("     &threshold=0.7         - Similarity threshold for semantic search")
    print("     &language=both|english|hindi - Language filter for NAMASTE")

    print("   🏥 NAMASTE (Ayurveda):")
    print("      GET  /namaste/search?search=term&limit=N&language=both|english|hindi")
    print("      GET  /namaste/all?limit=N&language=both|english|hindi")

    print("   🩺 ICD-11:")
    print("      GET  /icd/search?search=term&limit=N&discipline=biomedicine|tm2&parent=url")
    print("      GET  /icd/all?limit=N             - All ICD-11 codes")
    print("      GET  /icd/biomedicine?limit=N     - ICD-11 Biomedicine codes")
    print("      GET  /icd/tm2?limit=N             - ICD-11 Traditional Medicine codes")

    print()
    print("📝 Query Parameters:")
    print("   • search=<term>     - Search in titles, definitions, codes")
    print("   • limit=<number>    - Limit results (default: no limit)")
    print("   • language=<lang>   - Language filter for NAMASTE (both|english|hindi)")
    print("   • discipline=<type> - Discipline filter for ICD (biomedicine|tm2)")
    print("   • parent=<url>      - Filter by parent ICD code URL")
    print()
    print("🚀 Server ready for FHIR terminology requests!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _print_startup_banner()

    try:
        await mongo.init_mongodb()
        print("✅ MongoDB connection initialized")
    except Exception as e:
        print(f"⚠️  MongoDB connection failed: {e} (server will still start)")

    try:
        await redis_client.init_redis()
        print("✅ Redis connection initialized")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e} (server will still start)")

    _print_endpoint_banner()

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="FHIR Terminology Server", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Accept", "Content-Type"],
        max_age=3600,
    )

    app.include_router(routes.router)
    app.add_api_route(
        "/services/generate-embeddings", generate_embeddings_handler, methods=["GET"]
    )
    app.include_router(terminology_search.router, prefix="/terminology")
    app.include_router(icd_search.router, prefix="/icd")
    app.include_router(namaste_search.router, prefix="/namaste")
    app.include_router(fhir.router)

    return app


app = create_app()
