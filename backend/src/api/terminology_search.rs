use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use crate::codecs::namaste::{NamasteCodec, NamasteFilter, Language};
use crate::codecs::icd::{IcdCodec, IcdFilter};
use mongodb::{bson::{doc, Document}, Collection};
use futures::stream::TryStreamExt;
use crate::dbcodes::mongo::MongoClient;
use crate::gemini::embedding::call_gemini_embedding_api;

#[derive(Serialize, Deserialize)]
pub struct ApiResponse {
    pub service: String,
    pub status: String,
    pub message: String,
    pub timestamp: String,
}

#[derive(Debug, Clone)]
struct SimilarityResult {
    document: Document,
    similarity: f32,
}

#[derive(Debug, Clone)]
enum SearchMethod {
    Semantic,
    Regex,
    Auto, // Default: try semantic first, fallback to regex
}

impl SearchMethod {
    fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "semantic" | "vector" | "embedding" => SearchMethod::Semantic,
            "regex" | "text" | "keyword" => SearchMethod::Regex,
            "auto" | "hybrid" | _ => SearchMethod::Auto,
        }
    }
}

// Calculate cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        return 0.0;
    }
    
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        0.0
    } else {
        dot_product / (norm_a * norm_b)
    }
}

// Perform semantic search using application-level cosine similarity
async fn semantic_search_local(
    query_embedding: &[f32],
    limit: usize,
    threshold: f32,
    collection_name: &str,
    database_name: &str,
) -> anyhow::Result<Vec<SimilarityResult>> {
    let client = MongoClient::get_instance().await?;
    let db = client.get_database_by_name(database_name);
    let collection: Collection<Document> = db.collection(collection_name);

    // Find all documents with embeddings
    let filter = doc! {"embedding": {"$exists": true, "$ne": []}};
    let mut cursor = collection.find(filter, None).await?;
    let mut candidates = Vec::new();

    println!("🔍 Searching in collection: {}.{}", database_name, collection_name);

    // Calculate similarity for each document
    while let Some(doc) = cursor.try_next().await? {
        if let Ok(embedding_array) = doc.get_array("embedding") {
            let embedding_vec: Vec<f32> = embedding_array
                .iter()
                .filter_map(|v| v.as_f64().map(|f| f as f32))
                .collect();

            if !embedding_vec.is_empty() && embedding_vec.len() == query_embedding.len() {
                let similarity = cosine_similarity(query_embedding, &embedding_vec);
                if similarity >= threshold {
                    candidates.push(SimilarityResult {
                        document: doc,
                        similarity,
                    });
                }
            }
        }
    }

    println!("🎯 Found {} candidates above threshold {}", candidates.len(), threshold);

    // Sort by similarity (descending)
    candidates.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));
    candidates.truncate(limit);
    Ok(candidates)
}

// Format NAMASTE results
fn format_namaste_results(results: Vec<SimilarityResult>, include_similarity: bool) -> Vec<serde_json::Value> {
    results.into_iter().map(|result| {
        let doc = &result.document;
        let mut json_result = serde_json::json!({
            "id": doc.get_object_id("_id").map(|oid| oid.to_hex()).unwrap_or_default(),
            "code": doc.get_str("field_1").unwrap_or_default(),
            "title": doc.get_str("vyAdhi-viniScayaH").unwrap_or(
                doc.get_str("vyādhi-viniścayaḥ").unwrap_or(
                    doc.get_str("व्याधि-विनिश्चयः").unwrap_or_default()
                )
            ),
            "definition": doc.get_str("AYU").unwrap_or_default(),
            "source": "NAMASTE",
            "system": "Ayurveda",
            "code_system": "NAMASTE",
            "nam_code": doc.get_str("field_1").unwrap_or_default(),
            "icd_code": serde_json::Value::Null
        });
        
        if include_similarity {
            json_result.as_object_mut().unwrap().insert(
                "similarity".to_string(), 
                serde_json::Value::Number(serde_json::Number::from_f64(result.similarity as f64).unwrap_or(serde_json::Number::from(0)))
            );
            json_result.as_object_mut().unwrap().insert("search_type".to_string(), serde_json::Value::String("semantic".to_string()));
        } else {
            json_result.as_object_mut().unwrap().insert("search_type".to_string(), serde_json::Value::String("regex".to_string()));
        }
        
        json_result
    }).collect()
}

// Format ICD results
fn format_icd_results(results: Vec<SimilarityResult>, include_similarity: bool) -> Vec<serde_json::Value> {
    results.into_iter().map(|result| {
        let doc = &result.document;
        let mut json_result = serde_json::json!({
            "id": doc.get_str("id").unwrap_or_default(),
            "code": doc.get_str("code").unwrap_or_default(),
            "title": doc.get_str("title").unwrap_or_default(),
            "definition": doc.get_str("definition").unwrap_or_default(),
            "parent": doc.get_str("parent").unwrap_or_default(),
            "browserUrl": doc.get_str("browserUrl").unwrap_or_default(),
            "synonyms": doc.get_str("synonyms").unwrap_or_default(),
            "exclusions": doc.get_str("exclusions").unwrap_or_default(),
            "inclusions": doc.get_str("inclusions").unwrap_or_default(),
            "isLeaf": doc.get_str("isLeaf").unwrap_or_default(),
            "source": "ICD-11",
            "system": "Biomedicine",
            "code_system": "ICD",
            "nam_code": serde_json::Value::Null,
            "icd_code": doc.get_str("code").unwrap_or_default()
        });
        
        if include_similarity {
            json_result.as_object_mut().unwrap().insert(
                "similarity".to_string(), 
                serde_json::Value::Number(serde_json::Number::from_f64(result.similarity as f64).unwrap_or(serde_json::Number::from(0)))
            );
            json_result.as_object_mut().unwrap().insert("search_type".to_string(), serde_json::Value::String("semantic".to_string()));
        } else {
            json_result.as_object_mut().unwrap().insert("search_type".to_string(), serde_json::Value::String("regex".to_string()));
        }
        
        json_result
    }).collect()
}

// Helper function to extract code system from brackets
fn extract_code_system(label: &str) -> Option<String> {
    if let Some(start) = label.find('(') {
        if let Some(end) = label.find(')') {
            if end > start {
                return Some(label[start + 1..end].to_string());
            }
        }
    }
    None
}

// Perform regex-based search
async fn perform_regex_search(
    query: &web::Query<std::collections::HashMap<String, String>>
) -> Result<(Vec<serde_json::Value>, usize, usize)> {
    let search_term = query.get("search").cloned();
    let limit = query.get("limit").and_then(|l| l.parse().ok());
    let language = query.get("language")
        .map(|l| match l.as_str() {
            "hindi" => Language::Hindi,
            "english" => Language::English,
            _ => Language::Both,
        })
        .unwrap_or(Language::Both);

    let mut combined_results = Vec::new();
    let mut namaste_count = 0;
    let mut icd_count = 0;

    // Search NAMASTE codes
    let namaste_codec = NamasteCodec::new();
    let namaste_filter = NamasteFilter {
        code: None,
        language: language.clone(),
        search_term: search_term.clone(),
    };

    match namaste_codec.search_codes(namaste_filter, limit).await {
        Ok(codes) => {
            namaste_count = codes.len();
            let formatted = namaste_codec.format_response(codes, language.clone());
            for mut result in formatted {
                result.as_object_mut().unwrap().insert("source".to_string(), serde_json::Value::String("NAMASTE".to_string()));
                result.as_object_mut().unwrap().insert("system".to_string(), serde_json::Value::String("Ayurveda".to_string()));
                result.as_object_mut().unwrap().insert("search_type".to_string(), serde_json::Value::String("regex".to_string()));

                let code_system = if let Some(term) = result.get("term").and_then(|v| v.as_str()) {
                    extract_code_system(term)
                } else if let Some(display) = result.get("display").and_then(|v| v.as_str()) {
                    extract_code_system(display)
                } else {
                    None
                };

                if let Some(cs) = code_system {
                    result.as_object_mut().unwrap().insert("code_system".to_string(), serde_json::Value::String(cs));
                } else {
                    result.as_object_mut().unwrap().insert("code_system".to_string(), serde_json::Value::String("NAMASTE".to_string()));
                }

                combined_results.push(result);
            }
        },
        Err(e) => eprintln!("NAMASTE search failed: {}", e),
    }

    // Search ICD codes
    let icd_codec = IcdCodec::new();
    let icd_filter = IcdFilter {
        discipline: None,
        search_term: search_term.clone(),
        parent_filter: None,
    };

    match icd_codec.search_codes(icd_filter, limit).await {
        Ok(codes) => {
            icd_count = codes.len();
            let icd_formatted = icd_codec.format_response(codes);
            for mut result in icd_formatted {
                if let Some(map) = result.as_object_mut() {
                    let code_value = map.get("code")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());

                    map.insert("nam_code".to_string(), serde_json::Value::Null);
                    map.insert("icd_code".to_string(),
                              code_value.map(serde_json::Value::String)
                              .unwrap_or(serde_json::Value::Null));
                    map.insert("source".to_string(), serde_json::Value::String("ICD-11".to_string()));
                    map.insert("system".to_string(), serde_json::Value::String("Biomedicine".to_string()));
                    map.insert("code_system".to_string(), serde_json::Value::String("ICD".to_string()));
                    map.insert("search_type".to_string(), serde_json::Value::String("regex".to_string()));
                }
                combined_results.push(result);
            }
        },
        Err(e) => eprintln!("ICD search failed: {}", e),
    }

    // Apply global limit if specified
    if let Some(global_limit) = limit {
        combined_results.truncate(global_limit);
    }

    Ok((combined_results, namaste_count, icd_count))
}

// Main search function with explicit search method control
pub async fn terminology_search(
    query: web::Query<std::collections::HashMap<String, String>>
) -> Result<HttpResponse> {
    let search_term = match query.get("search") {
        Some(term) if !term.trim().is_empty() => term.clone(),
        _ => return Ok(HttpResponse::BadRequest().json(serde_json::json!({
            "service": "Terminology Search",
            "status": "error",
            "message": "Search term is required",
            "timestamp": chrono::Utc::now().to_rfc3339()
        })))
    };

    let limit = query.get("limit").and_then(|l| l.parse().ok()).unwrap_or(10);
    let threshold = query.get("threshold").and_then(|t| t.parse().ok()).unwrap_or(0.7);
    
    // NEW: Parse search method from query parameter
    let search_method = query.get("method")
        .or_else(|| query.get("search_type"))
        .map(|m| SearchMethod::from_str(m))
        .unwrap_or(SearchMethod::Auto);

    println!("🔍 Search method requested: {:?}", search_method);

    match search_method {
        SearchMethod::Regex => {
            // Force regex search
            println!("📝 Performing regex search (forced)");
            let (results, namaste_count, icd_count) = perform_regex_search(&query).await?;
            
            return Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "Regex Terminology Search",
                "search_term": search_term,
                "total_results": results.len(),
                "namaste_results": namaste_count,
                "icd_results": icd_count,
                "results": results,
                "search_type": "regex",
                "method_requested": "regex",
                "timestamp": chrono::Utc::now().to_rfc3339()
            })));
        },
        SearchMethod::Semantic => {
            // Force semantic search (fail if not possible)
            let api_key = match std::env::var("GEMINI_KEY") {
                Ok(key) if !key.is_empty() => key,
                _ => {
                    return Ok(HttpResponse::BadRequest().json(serde_json::json!({
                        "service": "Semantic Terminology Search",
                        "status": "error",
                        "message": "Semantic search requested but GEMINI_KEY not available",
                        "search_term": search_term,
                        "method_requested": "semantic",
                        "timestamp": chrono::Utc::now().to_rfc3339()
                    })));
                }
            };

            let query_embedding = match call_gemini_embedding_api(&api_key, &search_term).await {
                Ok(embedding) => {
                    println!("✅ Generated query embedding with {} dimensions", embedding.len());
                    embedding
                },
                Err(e) => {
                    return Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                        "service": "Semantic Terminology Search",
                        "status": "error",
                        "message": format!("Failed to generate embedding: {}", e),
                        "search_term": search_term,
                        "method_requested": "semantic",
                        "timestamp": chrono::Utc::now().to_rfc3339()
                    })));
                }
            };

            println!("🔍 Performing semantic search (forced)");
            
            let mut all_results = Vec::new();
            let mut semantic_namaste_count = 0;
            let mut semantic_icd_count = 0;

            // Semantic search on NAMASTE collection
            match semantic_search_local(&query_embedding, limit, threshold, "namc_codes", "ayurveda_db").await {
                Ok(results) => {
                    semantic_namaste_count = results.len();
                    if semantic_namaste_count > 0 {
                        println!("✅ Found {} NAMASTE semantic results", semantic_namaste_count);
                    }
                    let formatted_results = format_namaste_results(results, true);
                    all_results.extend(formatted_results);
                },
                Err(e) => println!("❌ NAMASTE semantic search failed: {}", e),
            }

            // Semantic search on ICD collection  
            match semantic_search_local(&query_embedding, limit, threshold, "icd11_entities", "icd11_database").await {
                Ok(results) => {
                    semantic_icd_count = results.len();
                    if semantic_icd_count > 0 {
                        println!("✅ Found {} ICD semantic results", semantic_icd_count);
                    }
                    let formatted_results = format_icd_results(results, true);
                    all_results.extend(formatted_results);
                },
                Err(e) => println!("❌ ICD semantic search failed: {}", e),
            }

            // Sort by similarity score (descending)
            all_results.sort_by(|a, b| {
                let score_a = a["similarity"].as_f64().unwrap_or(0.0);
                let score_b = b["similarity"].as_f64().unwrap_or(0.0);
                score_b.partial_cmp(&score_a).unwrap_or(std::cmp::Ordering::Equal)
            });

            // Apply global limit
            all_results.truncate(limit);

            return Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "Semantic Terminology Search",
                "search_term": search_term,
                "total_results": all_results.len(),
                "namaste_results": semantic_namaste_count,
                "icd_results": semantic_icd_count,
                "results": all_results,
                "search_type": "semantic",
                "method_requested": "semantic",
                "threshold": threshold,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })));
        },
        SearchMethod::Auto => {
            // Auto mode: try semantic first, fallback to regex
            let api_key = match std::env::var("GEMINI_KEY") {
                Ok(key) if !key.is_empty() => key,
                _ => {
                    println!("❌ No GEMINI_KEY found, falling back to regex search");
                    let (results, namaste_count, icd_count) = perform_regex_search(&query).await?;
                    
                    return Ok(HttpResponse::Ok().json(serde_json::json!({
                        "service": "Auto Terminology Search (Regex Fallback)",
                        "search_term": search_term,
                        "total_results": results.len(),
                        "namaste_results": namaste_count,
                        "icd_results": icd_count,
                        "results": results,
                        "search_type": "regex",
                        "method_requested": "auto",
                        "fallback_reason": "no_gemini_key",
                        "timestamp": chrono::Utc::now().to_rfc3339()
                    })));
                }
            };

            let query_embedding = match call_gemini_embedding_api(&api_key, &search_term).await {
                Ok(embedding) => {
                    println!("✅ Generated query embedding with {} dimensions", embedding.len());
                    embedding
                },
                Err(e) => {
                    println!("❌ Failed to generate embedding: {}, falling back to regex search", e);
                    let (results, namaste_count, icd_count) = perform_regex_search(&query).await?;
                    
                    return Ok(HttpResponse::Ok().json(serde_json::json!({
                        "service": "Auto Terminology Search (Regex Fallback)",
                        "search_term": search_term,
                        "total_results": results.len(),
                        "namaste_results": namaste_count,
                        "icd_results": icd_count,
                        "results": results,
                        "search_type": "regex",
                        "method_requested": "auto",
                        "fallback_reason": "embedding_generation_failed",
                        "timestamp": chrono::Utc::now().to_rfc3339()
                    })));
                }
            };

            println!("🔍 Performing semantic search (auto mode)");

            let mut all_results = Vec::new();
            let mut semantic_namaste_count = 0;
            let mut semantic_icd_count = 0;

            // Semantic search on NAMASTE collection
            match semantic_search_local(&query_embedding, limit, threshold, "namc_codes", "ayurveda_db").await {
                Ok(results) => {
                    semantic_namaste_count = results.len();
                    if semantic_namaste_count > 0 {
                        println!("✅ Found {} NAMASTE semantic results", semantic_namaste_count);
                    }
                    let formatted_results = format_namaste_results(results, true);
                    all_results.extend(formatted_results);
                },
                Err(e) => println!("❌ NAMASTE semantic search failed: {}", e),
            }

            // Semantic search on ICD collection  
            match semantic_search_local(&query_embedding, limit, threshold, "icd11_entities", "icd11_database").await {
                Ok(results) => {
                    semantic_icd_count = results.len();
                    if semantic_icd_count > 0 {
                        println!("✅ Found {} ICD semantic results", semantic_icd_count);
                    }
                    let formatted_results = format_icd_results(results, true);
                    all_results.extend(formatted_results);
                },
                Err(e) => println!("❌ ICD semantic search failed: {}", e),
            }

            // Sort by similarity score (descending)
            all_results.sort_by(|a, b| {
                let score_a = a["similarity"].as_f64().unwrap_or(0.0);
                let score_b = b["similarity"].as_f64().unwrap_or(0.0);
                score_b.partial_cmp(&score_a).unwrap_or(std::cmp::Ordering::Equal)
            });

            // Apply global limit
            all_results.truncate(limit);

            // If semantic search returned no results, fall back to regex search
            if all_results.is_empty() {
                println!("❌ No semantic results found, falling back to regex search");
                let (results, namaste_count, icd_count) = perform_regex_search(&query).await?;
                
                return Ok(HttpResponse::Ok().json(serde_json::json!({
                    "service": "Auto Terminology Search (Regex Fallback)",
                    "search_term": search_term,
                    "total_results": results.len(),
                    "namaste_results": namaste_count,
                    "icd_results": icd_count,
                    "results": results,
                    "search_type": "regex",
                    "method_requested": "auto",
                    "fallback_reason": "no_semantic_results",
                    "threshold": threshold,
                    "timestamp": chrono::Utc::now().to_rfc3339()
                })));
            }

            println!("✅ Semantic search completed with {} total results", all_results.len());

            return Ok(HttpResponse::Ok().json(serde_json::json!({
                "service": "Auto Semantic Terminology Search",
                "search_term": search_term,
                "total_results": all_results.len(),
                "namaste_results": semantic_namaste_count,
                "icd_results": semantic_icd_count,
                "results": all_results,
                "search_type": "semantic",
                "method_requested": "auto",
                "threshold": threshold,
                "timestamp": chrono::Utc::now().to_rfc3339()
            })));
        }
    }
}
