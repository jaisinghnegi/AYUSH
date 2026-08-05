use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use crate::codecs::icd::{IcdCodec, IcdFilter, IcdDiscipline};

// Basic response structure
#[derive(Serialize, Deserialize)]
pub struct ApiResponse {
    pub service: String,
    pub status: String,
    pub message: String,
    pub timestamp: String,
}

// ICD search endpoint
pub async fn icd_search(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = IcdCodec::new();
    let discipline = query.get("discipline")
        .and_then(|d| match d.to_lowercase().as_str() {
            "biomedicine" => Some(IcdDiscipline::Biomedicine),
            "tm2" => Some(IcdDiscipline::TM2),
            _ => None,
        });

    let filter = IcdFilter {
        discipline,
        search_term: query.get("search").cloned(),
        parent_filter: query.get("parent").cloned(),
    };

    match codec.search_codes(filter, query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "ICD-11 Search",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "ICD-11 Search".to_string(),
            status: "error".to_string(),
            message: format!("Search failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}

// ICD all codes endpoint
pub async fn icd_all(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = IcdCodec::new();
    match codec.get_all_codes(query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "ICD-11 All Codes",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "ICD-11 All Codes".to_string(),
            status: "error".to_string(),
            message: format!("Failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}

// Get biomedicine codes
pub async fn icd_biomedicine(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = IcdCodec::new();
    match codec.get_biomedicine_codes(query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "ICD-11 Biomedicine",
                "discipline": "BIOMEDICINE",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "ICD-11 Biomedicine".to_string(),
            status: "error".to_string(),
            message: format!("Failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}

// Get TM2 codes
pub async fn icd_tm2(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = IcdCodec::new();
    match codec.get_tm2_codes(query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "ICD-11 Traditional Medicine",
                "discipline": "TM2",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "ICD-11 TM2".to_string(),
            status: "error".to_string(),
            message: format!("Failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}
