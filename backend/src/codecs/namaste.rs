use serde::{Deserialize, Serialize};
use mongodb::bson::{doc};
use futures::stream::TryStreamExt;

use crate::dbcodes::mongo;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NamasteCode {
    #[serde(rename = "field_1")]
    pub sr_no: i32,
    #[serde(rename = "field_1_1")]
    pub namc_id: i32,
    #[serde(rename = "AYU")]
    pub namc_code: String,
    #[serde(rename = "vyAdhi-viniScayaH")]
    pub namc_term: String,
    #[serde(rename = "vyādhi-viniścayaḥ")]
    pub namc_term_diacritical: String,
    #[serde(rename = "व्याधि-विनिश्चयः")]
    pub namc_term_devanagari: String,
    #[serde(rename = "Unnamed: 6")]
    pub short_definition: Option<String>,
    #[serde(rename = "Unnamed: 7")]
    pub long_definition: Option<String>,
    #[serde(rename = "Unnamed: 8")]
    pub ontology_branches: Option<String>,
}

// Add a helper method to parse codes
impl NamasteCode {
    pub fn parse_codes(&self) -> (String, Option<String>) {
        // Parse the namc_code field to separate NAMASTE and ICD codes
        if self.namc_code.contains('(') && self.namc_code.contains(')') {
            // Format: "AAA-1 (SR-11)" or "SR11 (AAA-1)"
            let parts: Vec<&str> = self.namc_code.split('(').collect();
            if parts.len() == 2 {
                let nam_code = parts[0].trim().to_string();
                let icd_code = parts[1].replace(')', "").trim().to_string();
                return (nam_code, Some(icd_code));
            }
        } else if self.namc_code.contains(" - ") {
            // Format: "AAA-1 - SR-11"
            let parts: Vec<&str> = self.namc_code.split(" - ").collect();
            if parts.len() == 2 {
                let nam_code = parts[0].trim().to_string();
                let icd_code = parts[1].trim().to_string();
                return (nam_code, Some(icd_code));
            }
        }
        
        // Default: only NAMASTE code, no ICD mapping
        (self.namc_code.clone(), None)
    }
}


#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct NamasteFilter {
    pub code: Option<String>,
    pub language: Language,
    pub search_term: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Language {
    English,
    Hindi,
    Both,
}

pub struct NamasteCodec;

impl NamasteCodec {
    pub fn new() -> Self {
        Self
    }

    pub async fn search_codes(
    &self,
    filter: NamasteFilter,
    limit: Option<usize>,
) -> Result<Vec<NamasteCode>, Box<dyn std::error::Error>> {
    println!("🔍 Searching NAMASTE codes with filter: {:?}", filter);

    let client = mongo::MongoClient::get_instance().await?;
    let ayurveda_db = client.get_database_by_name("ayurveda_db");
    let collection = ayurveda_db.collection::<NamasteCode>("namc_codes");

    let mut query = doc! {};

    // Use regex search for better partial matching instead of text search
    if let Some(search_term) = &filter.search_term {
        query.insert("$or", vec![
            doc! { "vyAdhi-viniScayaH": { "$regex": search_term, "$options": "i" } },
            doc! { "vyādhi-viniścayaḥ": { "$regex": search_term, "$options": "i" } },
            doc! { "व्याधि-विनिश्चयः": { "$regex": search_term, "$options": "i" } },
            doc! { "AYU": { "$regex": search_term, "$options": "i" } }
        ]);
    }

    if let Some(code) = &filter.code {
        query.insert("AYU", mongodb::bson::Regex {
            pattern: code.clone(),
            options: "i".to_string(),
        });
    }

    println!("📊 MongoDB NAMASTE query: {:?}", query);

    let mut find_options = mongodb::options::FindOptions::default();
    if let Some(limit) = limit {
        find_options.limit = Some(limit as i64);
    }

    let mut cursor = collection.find(query, find_options).await?;
    let mut results = Vec::new();

    while let Some(doc) = cursor.try_next().await? {
        results.push(doc);
    }

    println!("✅ Found {} NAMASTE codes", results.len());
    Ok(results)
}


    pub async fn get_all_codes(&self, limit: Option<usize>) -> Result<Vec<NamasteCode>, Box<dyn std::error::Error>> {
        let filter = NamasteFilter {
            code: None,
            language: Language::Both,
            search_term: None,
        };
        self.search_codes(filter, limit).await
    }

    pub fn format_response(&self, codes: Vec<NamasteCode>, language: Language) -> Vec<serde_json::Value> {
    codes.into_iter().map(|code| {
        let display_name = match language {
            Language::Hindi => code.namc_term_devanagari.clone(),
            Language::English => code.namc_term_diacritical.clone(),
            Language::Both => format!("{} / {}", code.namc_term_diacritical, code.namc_term_devanagari),
        };

        // Parse the codes
        let (nam_code, icd_code) = code.parse_codes();

        serde_json::json!({
            "sr_no": code.sr_no,
            "namc_id": code.namc_id,
            "nam_code": nam_code,        // ✅ Separated NAMASTE code
            "icd_code": icd_code,        // ✅ Separated ICD code or null
            "term": code.namc_term,
            "display": display_name,
            "short_definition": code.short_definition,
            "long_definition": code.long_definition,
            "ontology_branches": code.ontology_branches
        })
    }).collect()
}
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NamasteDiscipline {
    Ayurveda,
    // Add others as needed based on your data
}
