use actix_web::{web, App, HttpServer, middleware::Logger, http};
use crate::dbcodes::{mongo, redis};
use crate::api;  // Import the api module
use actix_cors::Cors;
use crate::gemini::embedding::generate_embeddings_handler;


// Configure all routes
fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg
        // Health check
        .route("/health", web::get().to(api::health_check))
        // API Gateway
        .route("/gateway", web::get().to(api::api_gateway))
        // Main API
        .route("/api", web::get().to(api::rest_api))
        

        // Backend Services
        .service(
            web::scope("/services")
                .route("/terminology", web::get().to(api::terminology_service))
                .route("/mapping", web::get().to(api::mapping_service))
                .route("/sync", web::get().to(api::sync_service))
                .route("/audit", web::get().to(api::audit_service))
                .route("/generate-embeddings", web::get().to(generate_embeddings_handler)) // <-- new route added here

        )

        // Core Components
        .service(
            web::scope("/core")
                .route("/fhir", web::get().to(api::fhir_engine))
                .route("/vocabulary", web::get().to(api::vocabulary_manager))
                .route("/translation", web::get().to(api::translation_engine))
        )

        // Data Layer
        .service(
            web::scope("/data")
                .route("/mongodb", web::get().to(api::mongodb_status))
                .route("/mongodb/collections", web::get().to(api::mongodb_collections))
                .route("/redis", web::get().to(api::redis_status))
        )

        // External APIs
        .service(
            web::scope("/external")
                .route("/who-icd11", web::get().to(api::who_api))
                .route("/namaste-csv", web::get().to(api::namaste_csv))
        )

        // Terminology Services - FIX: Move the combined search here
        .service(
            web::scope("/terminology")
                .route("/ayurveda", web::get().to(api::ayurveda_terminology))
                .route("/search", web::get().to(api::terminology_search)) // CORRECT!
        )

        // ICD-11 search
        .service(
            web::scope("/icd")
                .route("/search", web::get().to(api::icd_search))
                .route("/all", web::get().to(api::icd_all))
                .route("/biomedicine", web::get().to(api::icd_biomedicine))
                .route("/tm2", web::get().to(api::icd_tm2))
        )
        
        .service(
            web::scope("/namaste")
                .route("/search", web::get().to(api::namaste_search))
                .route("/all", web::get().to(api::namaste_all))
        );
}


// Create the application
pub fn create_app() -> App<
    impl actix_web::dev::ServiceFactory<
        actix_web::dev::ServiceRequest,
        Response = actix_web::dev::ServiceResponse<impl actix_web::body::MessageBody>,
        Error = actix_web::Error,
        Config = (),
        InitError = (),
    >
> {
    let cors = Cors::default()
    .allowed_origin("http://localhost:5173")
    .allowed_methods(vec!["GET", "POST", "PUT", "DELETE"])
    .allowed_headers(vec![
        http::header::AUTHORIZATION,
        http::header::ACCEPT,
        http::header::CONTENT_TYPE,
    ])
    .supports_credentials()
    .max_age(3600);

    App::new()
        .wrap(cors)
        .configure(configure_routes)
        .wrap(Logger::default())
        .wrap(
            actix_web::middleware::DefaultHeaders::new()
                .add(("Content-Type", "application/json"))
        )
}

//Start server
pub async fn start_server() -> std::io::Result<()> {
    // Initialize logging
    env_logger::init();
    
    println!("🚀 Starting FHIR Terminology Server...");
    
    // Initialize MongoDB connection
    match mongo::init_mongodb().await {
        Ok(_) => println!("✅ MongoDB connection initialized"),
        Err(e) => println!("⚠️  MongoDB connection failed: {} (server will still start)", e),
    }
    
    // Initialize Redis connection
    match redis::init_redis().await {
        Ok(_) => println!("✅ Redis connection initialized"),
        Err(e) => println!("⚠️  Redis connection failed: {} (server will still start)", e),
    }
    
    println!("📊 Server running on http://127.0.0.1:8080");
    println!("🏥 Health check: http://127.0.0.1:8080/health");
    println!();
    println!("📋 Available API Endpoints:");


    
    // Core System Endpoints
    println!("   🔧 SYSTEM:");
    println!("      GET  /health                     - Health check");
    println!("      GET  /gateway                    - API Gateway & OAuth 2.0 status");
    println!("      GET  /api                        - REST API server status");
    
    // Backend Services
    println!("   🛠️  SERVICES:");
    println!("      GET  /services/terminology       - Terminology service status");
    println!("      GET  /services/mapping           - Mapping service status");
    println!("      GET  /services/sync              - Sync service status");
    println!("      GET  /services/audit             - Audit service status");
    
    // Core Components
    println!("   🧠 CORE:");
    println!("      GET  /core/fhir                  - FHIR R4 engine status");
    println!("      GET  /core/vocabulary            - Vocabulary manager status");
    println!("      GET  /core/translation           - Translation engine status");
    
    // Data Layer
    println!("   💾 DATA:");
    println!("      GET  /data/mongodb               - MongoDB connection status");
    println!("      GET  /data/mongodb/collections   - List MongoDB collections");
    println!("      GET  /data/redis                 - Redis cache status");
    
    // External APIs
    println!("   🌐 EXTERNAL:");
    println!("      GET  /external/who-icd11         - WHO ICD-11 API status");
    println!("      GET  /external/namaste-csv       - NAMASTE CSV files status");
    
    // TERMINOLOGY documentations
    println!(" 📚 TERMINOLOGY:");
    println!(" GET /terminology/search - Combined NAMASTE + ICD search");
    println!("     ?search=term           - Search term (required)");
    println!("     &method=auto|semantic|regex - Search method (default: auto)");
    println!("     &limit=N               - Limit results"); 
    println!("     &threshold=0.7         - Similarity threshold for semantic search");
    println!("     &language=both|english|hindi - Language filter for NAMASTE");


    // NAMASTE Ayurveda Codes
    println!("   🏥 NAMASTE (Ayurveda):");
    println!("      GET  /namaste/search?search=term&limit=N&language=both|english|hindi");
    println!("      GET  /namaste/all?limit=N&language=both|english|hindi");
    
    // ICD-11 Codes  
    println!("   🩺 ICD-11:");
    println!("      GET  /icd/search?search=term&limit=N&discipline=biomedicine|tm2&parent=url");
    println!("      GET  /icd/all?limit=N             - All ICD-11 codes");
    println!("      GET  /icd/biomedicine?limit=N     - ICD-11 Biomedicine codes");
    println!("      GET  /icd/tm2?limit=N             - ICD-11 Traditional Medicine codes");
    
    println!();
    println!("📝 Query Parameters:");
    println!("   • search=<term>     - Search in titles, definitions, codes");
    println!("   • limit=<number>    - Limit results (default: no limit)");
    println!("   • language=<lang>   - Language filter for NAMASTE (both|english|hindi)");
    println!("   • discipline=<type> - Discipline filter for ICD (biomedicine|tm2)");
    println!("   • parent=<url>      - Filter by parent ICD code URL");
    println!();
    println!("🚀 Server ready for FHIR terminology requests!");

    
    
    HttpServer::new(|| create_app())
        .bind("127.0.0.1:8080")?
        .run()
        .await
}

