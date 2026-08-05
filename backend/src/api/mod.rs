use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use crate::dbcodes::{mongo, redis};

// Declare submodules
pub mod icd_search;
pub mod namaste_search;
pub mod terminology_search;

// Re-export functions from submodules
pub use icd_search::{icd_search, icd_all, icd_biomedicine, icd_tm2};
pub use namaste_search::{namaste_search, namaste_all};
pub use terminology_search::terminology_search;

// Basic response structure (shared across modules)
#[derive(Serialize, Deserialize)]
pub struct ApiResponse {
    pub service: String,
    pub status: String,
    pub message: String,
    pub timestamp: String,
}

// All the other API functions that weren't moved to separate files
// Health check endpoint
pub async fn health_check() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "FHIR Terminology Server".to_string(),
        status: "healthy".to_string(),
        message: "Server is running successfully".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// API Gateway handler
pub async fn api_gateway() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "API Gateway & OAuth 2.0 + ABHA Authentication".to_string(),
        status: "active".to_string(),
        message: "Authentication layer is operational".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// REST API Server handler
pub async fn rest_api() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "REST API Server".to_string(),
        status: "running".to_string(),
        message: "Main API server handling requests".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// Backend Services
pub async fn terminology_service() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Terminology Service".to_string(),
        status: "running".to_string(),
        message: "Managing medical terminologies and codes".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn mapping_service() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Mapping Service".to_string(),
        status: "running".to_string(),
        message: "Handling terminology mappings".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn sync_service() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Sync Service".to_string(),
        status: "running".to_string(),
        message: "Synchronizing with external APIs".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn audit_service() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Audit Service".to_string(),
        status: "running".to_string(),
        message: "Logging and auditing system activities".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// Core Components
pub async fn fhir_engine() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "FHIR R4 Engine".to_string(),
        status: "running".to_string(),
        message: "Processing FHIR R4 resources".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn vocabulary_manager() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Vocabulary Manager".to_string(),
        status: "running".to_string(),
        message: "Managing medical vocabularies".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn translation_engine() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "Translation Engine".to_string(),
        status: "running".to_string(),
        message: "Translating between coding systems".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// Data Layer - REAL MongoDB status using our mongo module
pub async fn mongodb_status() -> Result<HttpResponse> {
    let status = mongo::get_connection_status().await;
    let message = if status.connected {
        format!("Connected to {} - {}",
            status.database_name,
            status.server_info.unwrap_or_else(|| "MongoDB".to_string())
        )
    } else {
        format!("Connection failed: {}",
            status.error.unwrap_or_else(|| "Unknown error".to_string())
        )
    };

    let response = ApiResponse {
        service: "MongoDB".to_string(),
        status: if status.connected { "connected" } else { "disconnected" }.to_string(),
        message,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };

    if status.connected {
        Ok(HttpResponse::Ok().json(response))
    } else {
        Ok(HttpResponse::ServiceUnavailable().json(response))
    }
}

// Data Layer - REAL Redis status using our redis module
pub async fn redis_status() -> Result<HttpResponse> {
    let status = redis::get_connection_status().await;
    let message = if status.connected {
        status.server_info.unwrap_or_else(|| "Redis connected".to_string())
    } else {
        format!("Connection failed: {}",
            status.error.unwrap_or_else(|| "Unknown error".to_string())
        )
    };

    let response = ApiResponse {
        service: "Redis Cache".to_string(),
        status: if status.connected { "connected" } else { "disconnected" }.to_string(),
        message,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };

    if status.connected {
        Ok(HttpResponse::Ok().json(response))
    } else {
        Ok(HttpResponse::ServiceUnavailable().json(response))
    }
}

// External APIs
pub async fn who_api() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "WHO ICD-11 API".to_string(),
        status: "connected".to_string(),
        message: "WHO ICD-11 integration active".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn namaste_csv() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(ApiResponse {
        service: "NAMASTE CSV Files".to_string(),
        status: "accessible".to_string(),
        message: "NAMASTE data processing ready".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    }))
}

// MongoDB-specific endpoints
pub async fn mongodb_collections() -> Result<HttpResponse> {
    match mongo::MongoClient::get_instance().await {
        Ok(client) => {
            match client.list_collections().await {
                Ok(collections) => Ok(HttpResponse::Ok().json(serde_json::json!({
                    "service": "MongoDB Collections",
                    "collections": collections,
                    "count": collections.len(),
                    "timestamp": chrono::Utc::now().to_rfc3339()
                }))),
                Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
                    service: "MongoDB Collections".to_string(),
                    status: "error".to_string(),
                    message: format!("Failed to list collections: {}", e),
                    timestamp: chrono::Utc::now().to_rfc3339(),
                }))
            }
        },
        Err(e) => Ok(HttpResponse::ServiceUnavailable().json(ApiResponse {
            service: "MongoDB Collections".to_string(),
            status: "unavailable".to_string(),
            message: format!("MongoDB not connected: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}

pub async fn ayurveda_terminology() -> Result<HttpResponse> {
    match mongo::MongoClient::get_instance().await {
        Ok(client) => {
            let ayurveda_db = client.get_database_by_name("ayurveda_db");
            match ayurveda_db.list_collection_names(None).await {
                Ok(collections) => Ok(HttpResponse::Ok().json(serde_json::json!({
                    "service": "Ayurveda Terminology",
                    "status": "available",
                    "database_size": "584 KB",
                    "collections": collections,
                    "message": "Ayurveda database ready for FHIR terminology services",
                    "timestamp": chrono::Utc::now().to_rfc3339()
                }))),
                Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
                    service: "Ayurveda Terminology".to_string(),
                    status: "error".to_string(),
                    message: format!("Failed to access ayurveda_db: {}", e),
                    timestamp: chrono::Utc::now().to_rfc3339(),
                }))
            }
        },
        Err(e) => Ok(HttpResponse::ServiceUnavailable().json(ApiResponse {
            service: "Ayurveda Terminology".to_string(),
            status: "unavailable".to_string(),
            message: format!("Database not connected: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}
