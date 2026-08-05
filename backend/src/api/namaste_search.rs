use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use crate::codecs::namaste::{NamasteCodec, NamasteFilter, Language};

// Basic response structure
#[derive(Serialize, Deserialize)]
pub struct ApiResponse {
    pub service: String,
    pub status: String,
    pub message: String,
    pub timestamp: String,
}

// NAMASTE search endpoint
pub async fn namaste_search(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = NamasteCodec::new();
    let language = query.get("language")
        .map(|l| match l.as_str() {
            "hindi" => Language::Hindi,
            "english" => Language::English,
            _ => Language::Both,
        })
        .unwrap_or(Language::Both);

    let filter = NamasteFilter {
        code: query.get("code").cloned(),
        language: language.clone(),
        search_term: query.get("search").cloned(),
    };

    match codec.search_codes(filter, query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes, language);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "NAMASTE Code Search",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "NAMASTE Code Search".to_string(),
            status: "error".to_string(),
            message: format!("Search failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}

// Get all NAMASTE codes endpoint
pub async fn namaste_all(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let codec = NamasteCodec::new();
    let language = query.get("language")
        .map(|l| match l.as_str() {
            "hindi" => Language::Hindi,
            "english" => Language::English,
            _ => Language::Both,
        })
        .unwrap_or(Language::Both);

    match codec.get_all_codes(query.get("limit").and_then(|l| l.parse().ok())).await {
        Ok(codes) => {
            let formatted = codec.format_response(codes, language);
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "NAMASTE All Codes",
                "total": formatted.len(),
                "results": formatted,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse {
            service: "NAMASTE All Codes".to_string(),
            status: "error".to_string(),
            message: format!("Failed: {}", e),
            timestamp: chrono::Utc::now().to_rfc3339(),
        }))
    }
}
