// src/gemini/embedding.rs

use actix_web::{HttpResponse, Result};
use mongodb::bson::{doc, Document};
use mongodb::options::UpdateOptions;
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::Arc;
use tokio::sync::Semaphore;
use futures::stream::{self, StreamExt};

use crate::codecs::icd::{IcdCodec, IcdCode};
use crate::codecs::namaste::{NamasteCodec, NamasteCode};

/// Call Gemini embedding API with the given api_key and input text, return embedding vector
pub async fn call_gemini_embedding_api(api_key: &str, input_text: &str) -> anyhow::Result<Vec<f32>> {
    let client = reqwest::Client::new();
    let url = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent";
    
    let request_body = serde_json::json!({
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{
                "text": input_text
            }]
        }
    });

    let resp = client
        .post(url)
        .header("x-goog-api-key", api_key)
        .json(&request_body)
        .send()
        .await?
        .error_for_status()?;

    let json_resp: serde_json::Value = resp.json().await?;

    let embedding_array = json_resp["embedding"]["values"]
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("Invalid embedding response from Gemini"))?;

    let embedding: Vec<f32> = embedding_array
        .iter()
        .map(|v| v.as_f64().unwrap_or(0.0) as f32)
        .collect();

    Ok(embedding)
}

/// Check if a document already has embeddings in MongoDB
async fn has_embeddings_icd(code_id: &str) -> anyhow::Result<bool> {
    let client = crate::dbcodes::mongo::MongoClient::get_instance().await?;
    let db = client.get_database_by_name("icd11_database");
    let collection = db.collection::<Document>("icd11_entities");

    let filter = doc! {
        "id": code_id,
        "embedding": { "$exists": true, "$ne": [] }
    };

    let count = collection.count_documents(filter, None).await?;
    Ok(count > 0)
}

/// Find NAMASTE document by matching against the NamasteCode data
async fn find_and_check_namaste_embedding(code: &NamasteCode) -> anyhow::Result<(bool, Option<Document>)> {
    let client = crate::dbcodes::mongo::MongoClient::get_instance().await?;
    let db = client.get_database_by_name("ayurveda_db");
    let collection = db.collection::<Document>("namc_codes");

    // Try to find by the ID field (field_1 appears to be the ID based on your structure)
    let filter = doc! { "field_1": code.namc_id };
    
    if let Ok(Some(document)) = collection.find_one(filter.clone(), None).await {
        // Found the document, now check if it has embeddings
        let has_embedding = document.get_array("embedding")
            .map(|arr| !arr.is_empty())
            .unwrap_or(false);
        
        println!("🔍 Found NAMASTE code {} using field_1 filter", code.namc_id);
        return Ok((has_embedding, Some(document)));
    }

    // If not found by field_1, try to match by Sanskrit/Devanagari terms
    // Look for documents that match any of the term fields
    let possible_filters = vec![
        doc! { "vyAdhi-viniScayaH": &code.namc_term },
        doc! { "vyādhi-viniścayaḥ": &code.namc_term },
        doc! { "व्याधि-विनिश्चयः": &code.namc_term },
    ];

    for filter in possible_filters {
        if let Ok(Some(document)) = collection.find_one(filter.clone(), None).await {
            let has_embedding = document.get_array("embedding")
                .map(|arr| !arr.is_empty())
                .unwrap_or(false);
            
            println!("🔍 Found NAMASTE code {} using term filter: {}", code.namc_id, filter);
            return Ok((has_embedding, Some(document)));
        }
    }

    // Document not found with any strategy
    Ok((false, None))
}

/// Extract text content from MongoDB NAMASTE document for embedding
fn extract_namaste_text_from_document(document: &Document, fallback_term: &str) -> String {
    let mut text_parts = Vec::new();

    // Try to extract text from various fields in the document
    if let Ok(sanskrit) = document.get_str("vyAdhi-viniScayaH") {
        if !sanskrit.is_empty() {
            text_parts.push(sanskrit.to_string());
        }
    }

    if let Ok(sanskrit_iast) = document.get_str("vyādhi-viniścayaḥ") {
        if !sanskrit_iast.is_empty() {
            text_parts.push(sanskrit_iast.to_string());
        }
    }

    if let Ok(devanagari) = document.get_str("व्याधि-विनिश्चयः") {
        if !devanagari.is_empty() {
            text_parts.push(devanagari.to_string());
        }
    }

    // Add the AYU field if it exists
    if let Ok(ayu) = document.get_str("AYU") {
        if !ayu.is_empty() {
            text_parts.push(ayu.to_string());
        }
    }

    // If no text found in document, use the fallback term from NamasteCode
    if text_parts.is_empty() {
        text_parts.push(fallback_term.to_string());
    }

    text_parts.join(" ")
}

/// Process a single ICD code for embeddings
async fn process_icd_code(
    code: IcdCode,
    api_key: String,
    semaphore: Arc<Semaphore>,
) -> anyhow::Result<ProcessResult> {
    let _permit = semaphore.acquire().await.unwrap();

    match has_embeddings_icd(&code.id).await {
        Ok(has_embedding) => {
            if has_embedding {
                return Ok(ProcessResult::AlreadyExists);
            }
        },
        Err(e) => {
            println!("⚠️  Failed to check embedding status for ICD code {}: {}", code.id, e);
        }
    }

    let combined_text = format!(
        "{} {} {}",
        code.title,
        code.definition.clone().unwrap_or_default(),
        code.code
    );

    if combined_text.trim().is_empty() {
        return Ok(ProcessResult::Skipped);
    }

    match call_gemini_embedding_api(&api_key, &combined_text).await {
        Ok(embedding) => {
            let client = crate::dbcodes::mongo::MongoClient::get_instance().await?;
            let db = client.get_database_by_name("icd11_database");
            let collection = db.collection::<Document>("icd11_entities");

            let filter = doc! { "id": &code.id };
            let update = doc! { "$set": { "embedding": &embedding } };
            let options = UpdateOptions::builder().upsert(false).build();

            match collection.update_one(filter, update, options).await {
                Ok(update_result) => {
                    if update_result.modified_count > 0 {
                        println!("✅ Processed ICD code: {} (embedding size: {})", code.id, embedding.len());
                        Ok(ProcessResult::Success)
                    } else {
                        Ok(ProcessResult::AlreadyExists)
                    }
                },
                Err(e) => {
                    println!("❌ Failed to update ICD code {} in MongoDB: {}", code.id, e);
                    Ok(ProcessResult::Failed)
                }
            }
        },
        Err(e) => {
            println!("❌ Failed to generate embedding for ICD code {}: {}", code.id, e);
            Ok(ProcessResult::Failed)
        }
    }
}

/// Process a single NAMASTE code for embeddings
async fn process_namaste_code(
    code: NamasteCode,
    api_key: String,
    semaphore: Arc<Semaphore>,
) -> anyhow::Result<ProcessResult> {
    let _permit = semaphore.acquire().await.unwrap();

    // Find the document and check if it has embeddings
    match find_and_check_namaste_embedding(&code).await {
        Ok((has_embedding, Some(document))) => {
            if has_embedding {
                return Ok(ProcessResult::AlreadyExists);
            }

            // Document found but no embedding, extract text and proceed
            let combined_text = extract_namaste_text_from_document(&document, &code.namc_term);

            if combined_text.trim().is_empty() {
                return Ok(ProcessResult::Skipped);
            }

            match call_gemini_embedding_api(&api_key, &combined_text).await {
                Ok(embedding) => {
                    let client = crate::dbcodes::mongo::MongoClient::get_instance().await?;
                    let db = client.get_database_by_name("ayurveda_db");
                    let collection = db.collection::<Document>("namc_codes");

                    // Use the _id from the found document for the update
                    let filter = doc! { "_id": document.get("_id").unwrap() };
                    let update = doc! { "$set": { "embedding": &embedding } };
                    let options = UpdateOptions::builder().upsert(false).build();

                    match collection.update_one(filter, update, options).await {
                        Ok(update_result) => {
                            if update_result.modified_count > 0 {
                                println!("✅ Processed NAMASTE code: {} - {} (embedding size: {})", 
                                       code.namc_id, combined_text.chars().take(50).collect::<String>(), embedding.len());
                                Ok(ProcessResult::Success)
                            } else {
                                Ok(ProcessResult::AlreadyExists)
                            }
                        },
                        Err(e) => {
                            println!("❌ Failed to update NAMASTE code {} in MongoDB: {}", code.namc_id, e);
                            Ok(ProcessResult::Failed)
                        }
                    }
                },
                Err(e) => {
                    println!("❌ Failed to generate embedding for NAMASTE code {}: {}", code.namc_id, e);
                    Ok(ProcessResult::Failed)
                }
            }
        },
        Ok((_, None)) => {
            println!("❌ NAMASTE code {} - '{}' not found in database", code.namc_id, code.namc_term);
            Ok(ProcessResult::Failed)
        },
        Err(e) => {
            println!("❌ Error checking NAMASTE code {}: {}", code.namc_id, e);
            Ok(ProcessResult::Failed)
        }
    }
}

#[derive(Debug)]
enum ProcessResult {
    Success,
    Failed,
    Skipped,
    AlreadyExists,
}

/// Generate embeddings for all ICD and NAMASTE codes and update MongoDB documents
pub async fn generate_and_store_embeddings() -> anyhow::Result<()> {
    println!("🚀 Starting embedding generation process with 100 parallel requests...");
    
    let api_key = env::var("GEMINI_KEY")
        .map_err(|_| anyhow::anyhow!("GEMINI_KEY not found in environment variables"))?;
    
    println!("✅ Gemini API key loaded successfully");

    let icd_codec = IcdCodec::new();
    let namaste_codec = NamasteCodec::new();
    let semaphore = Arc::new(Semaphore::new(100));

    // Process ICD codes
    println!("📊 Fetching ICD codes from database...");
    let icd_codes: Vec<IcdCode> = match icd_codec.get_all_codes(None).await {
        Ok(codes) => {
            println!("✅ Successfully fetched {} ICD codes", codes.len());
            codes
        },
        Err(e) => {
            println!("❌ Failed to fetch ICD codes: {}", e);
            return Err(anyhow::anyhow!("Failed to fetch ICD codes: {}", e));
        },
    };

    println!("🔄 Processing ICD codes for embeddings (up to 100 parallel requests)...");
    let icd_results = stream::iter(icd_codes.into_iter().enumerate())
        .map(|(index, code)| {
            let api_key = api_key.clone();
            let semaphore = semaphore.clone();
            
            tokio::spawn(async move {
                if index % 100 == 0 {
                    println!("🔄 Processing ICD batch starting at index {}", index);
                }
                process_icd_code(code, api_key, semaphore).await
            })
        })
        .buffer_unordered(100)
        .collect::<Vec<_>>()
        .await;

    let mut processed_icd = 0;
    let mut skipped_icd = 0;
    let mut failed_icd = 0;
    let mut existing_icd = 0;

    for result in icd_results {
        match result {
            Ok(Ok(ProcessResult::Success)) => processed_icd += 1,
            Ok(Ok(ProcessResult::Skipped)) => skipped_icd += 1,
            Ok(Ok(ProcessResult::Failed)) => failed_icd += 1,
            Ok(Ok(ProcessResult::AlreadyExists)) => existing_icd += 1,
            Ok(Err(e)) => {
                println!("❌ Task error: {}", e);
                failed_icd += 1;
            },
            Err(e) => {
                println!("❌ Join error: {}", e);
                failed_icd += 1;
            }
        }
    }

    println!("📈 ICD Summary: {} processed, {} skipped, {} existing, {} failed", 
             processed_icd, skipped_icd, existing_icd, failed_icd);

    // Process NAMASTE codes
    println!("📊 Fetching NAMASTE codes from database...");
    let namaste_codes: Vec<NamasteCode> = match namaste_codec.get_all_codes(None).await {
        Ok(codes) => {
            println!("✅ Successfully fetched {} NAMASTE codes", codes.len());
            codes
        },
        Err(e) => {
            println!("❌ Failed to fetch NAMASTE codes: {}", e);
            return Err(anyhow::anyhow!("Failed to fetch NAMASTE codes: {}", e));
        },
    };

    println!("🔄 Processing NAMASTE codes for embeddings (up to 100 parallel requests)...");
    let namaste_results = stream::iter(namaste_codes.into_iter().enumerate())
        .map(|(index, code)| {
            let api_key = api_key.clone();
            let semaphore = semaphore.clone();
            
            tokio::spawn(async move {
                if index % 100 == 0 {
                    println!("🔄 Processing NAMASTE batch starting at index {}", index);
                }
                process_namaste_code(code, api_key, semaphore).await
            })
        })
        .buffer_unordered(100)
        .collect::<Vec<_>>()
        .await;

    let mut processed_namaste = 0;
    let mut skipped_namaste = 0;
    let mut failed_namaste = 0;
    let mut existing_namaste = 0;

    for result in namaste_results {
        match result {
            Ok(Ok(ProcessResult::Success)) => processed_namaste += 1,
            Ok(Ok(ProcessResult::Skipped)) => skipped_namaste += 1,
            Ok(Ok(ProcessResult::Failed)) => failed_namaste += 1,
            Ok(Ok(ProcessResult::AlreadyExists)) => existing_namaste += 1,
            Ok(Err(e)) => {
                println!("❌ Task error: {}", e);
                failed_namaste += 1;
            },
            Err(e) => {
                println!("❌ Join error: {}", e);
                failed_namaste += 1;
            }
        }
    }

    println!("📈 NAMASTE Summary: {} processed, {} skipped, {} existing, {} failed", 
             processed_namaste, skipped_namaste, existing_namaste, failed_namaste);

    let total_processed = processed_icd + processed_namaste;
    let total_existing = existing_icd + existing_namaste;
    let total_failed = failed_icd + failed_namaste;
    let total_codes = (processed_icd + skipped_icd + existing_icd + failed_icd) + 
                     (processed_namaste + skipped_namaste + existing_namaste + failed_namaste);

    println!("🎉 Parallel embedding generation completed!");
    println!("📊 Final Summary:");
    println!("   • Total codes: {}", total_codes);
    println!("   • Successfully processed: {}", total_processed);
    println!("   • Already had embeddings: {}", total_existing);
    println!("   • Failed: {}", total_failed);
    println!("   • Total coverage: {:.2}%", 
             ((total_processed + total_existing) as f64 / total_codes as f64) * 100.0);

    Ok(())
}

/// Actix-web handler to trigger embedding generation via API call
pub async fn generate_embeddings_handler() -> Result<HttpResponse> {
    println!("🌐 Parallel embedding generation endpoint called");
    
    match generate_and_store_embeddings().await {
        Ok(_) => {
            println!("✅ Parallel embedding generation completed successfully");
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "status": "success",
                "message": "Gemini embeddings generated and stored in MongoDB with 100 parallel requests",
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        },
        Err(err) => {
            println!("❌ Parallel embedding generation failed: {:?}", err);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "status": "error",
                "message": format!("Failed to generate embeddings: {}", err),
                "timestamp": chrono::Utc::now().to_rfc3339()
            })))
        }
    }
}
