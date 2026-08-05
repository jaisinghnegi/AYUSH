use serde::{Deserialize, Serialize};
use mongodb::bson::{doc, Bson};
use futures::stream::TryStreamExt;
use crate::dbcodes::mongo;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IcdCode {
    pub id: String,
    #[serde(deserialize_with = "deserialize_code")]
    pub code: String,  // Handle both integer and string codes
    pub title: String,
    pub definition: Option<String>,
    pub parent: Option<String>,
    #[serde(rename = "browserUrl")]
    pub browser_url: Option<String>,
    #[serde(rename = "codingNote")]
    pub coding_note: Option<String>,
    pub synonyms: Option<String>,
    pub exclusions: Option<String>,
    pub inclusions: Option<String>,
    #[serde(rename = "isLeaf")]
    pub is_leaf: Option<String>,
}

// Custom deserializer to handle mixed code types (integer/string/empty)
fn deserialize_code<'de, D>(deserializer: D) -> Result<String, D::Error>
where
    D: serde::Deserializer<'de>,
{
    match Bson::deserialize(deserializer)? {
        Bson::String(s) => Ok(s),
        Bson::Int32(i) => Ok(i.to_string()),
        Bson::Int64(i) => Ok(i.to_string()),
        Bson::Null => Ok(String::new()),
        _ => Ok(String::new()),
    }
}

// Rest of your code remains the same...
#[derive(Debug, Clone)]
pub struct IcdFilter {
    pub discipline: Option<IcdDiscipline>,
    pub search_term: Option<String>,
    pub parent_filter: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum IcdDiscipline {
    Biomedicine,
    TM2,
}

pub struct IcdCodec;

impl IcdCodec {
    pub fn new() -> Self {
        Self
    }

    pub async fn search_codes(
        &self,
        filter: IcdFilter,
        limit: Option<usize>,
    ) -> Result<Vec<IcdCode>, Box<dyn std::error::Error>> {
        println!("🔍 Searching ICD codes with filter: {:?}", filter);

        let client = mongo::MongoClient::get_instance().await?;
        let icd_db = client.get_database_by_name("icd11_database");
        let collection = icd_db.collection::<IcdCode>("icd11_entities");

        let mut query = doc! {};

        // Discipline filtering based on URL patterns
        if let Some(discipline) = &filter.discipline {
            match discipline {
                IcdDiscipline::Biomedicine => {
                    query.insert("id", doc! { "$regex": "/mms/", "$options": "i" });
                },
                IcdDiscipline::TM2 => {
                    query.insert("id", doc! { "$regex": "/tm/", "$options": "i" });
                }
            }
        }

        // Text search across multiple fields
        if let Some(search_term) = &filter.search_term {
            query.insert("$or", vec![
                doc! { "title": { "$regex": search_term, "$options": "i" } },
                doc! { "definition": { "$regex": search_term, "$options": "i" } },
                doc! { "code": { "$regex": search_term, "$options": "i" } },
            ]);
        }

        // Filter by parent code
        if let Some(parent) = &filter.parent_filter {
            query.insert("parent", parent);
        }

        println!("📊 MongoDB ICD query: {:?}", query);

        let mut find_options = mongodb::options::FindOptions::default();
        if let Some(limit) = limit {
            find_options.limit = Some(limit as i64);
        }

        let mut cursor = collection.find(query, find_options).await?;
        let mut results = Vec::new();

        while let Some(doc) = cursor.try_next().await? {
            results.push(doc);
        }

        println!("✅ Found {} ICD codes", results.len());
        Ok(results)
    }

    pub async fn get_biomedicine_codes(&self, limit: Option<usize>) -> Result<Vec<IcdCode>, Box<dyn std::error::Error>> {
        let filter = IcdFilter {
            discipline: Some(IcdDiscipline::Biomedicine),
            search_term: None,
            parent_filter: None,
        };
        self.search_codes(filter, limit).await
    }

    pub async fn get_tm2_codes(&self, limit: Option<usize>) -> Result<Vec<IcdCode>, Box<dyn std::error::Error>> {
        let filter = IcdFilter {
            discipline: Some(IcdDiscipline::TM2),
            search_term: None,
            parent_filter: None,
        };
        self.search_codes(filter, limit).await
    }

    pub async fn get_all_codes(&self, limit: Option<usize>) -> Result<Vec<IcdCode>, Box<dyn std::error::Error>> {
        let filter = IcdFilter {
            discipline: None,
            search_term: None,
            parent_filter: None,
        };
        self.search_codes(filter, limit).await
    }

    pub fn format_response(&self, codes: Vec<IcdCode>) -> Vec<serde_json::Value> {
        codes.into_iter().map(|code| {
            serde_json::json!({
                "id": code.id,
                "code": code.code,
                "title": code.title,
                "definition": code.definition,
                "parent": code.parent,
                "browserUrl": code.browser_url,
                "codingNote": code.coding_note,
                "synonyms": code.synonyms,
                "exclusions": code.exclusions,
                "inclusions": code.inclusions,
                "isLeaf": code.is_leaf
            })
        }).collect()
    }
}

impl std::fmt::Display for IcdDiscipline {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            IcdDiscipline::Biomedicine => write!(f, "BIOMEDICINE"),
            IcdDiscipline::TM2 => write!(f, "TM2"),
        }
    }
}
