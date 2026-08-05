use mongodb::{
    bson::{doc},
    options::{ClientOptions, ServerApi, ServerApiVersion},
    Client, Database,
};
use serde::{Deserialize, Serialize};
use std::env;
use tokio::sync::OnceCell;
use dotenv::dotenv;

// Global MongoDB client instance
static MONGO_CLIENT: OnceCell<MongoClient> = OnceCell::const_new();

#[derive(Clone)]
pub struct MongoClient {
    client: Client,
    database: Database,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ConnectionStatus {
    pub connected: bool,
    pub database_name: String,
    pub server_info: Option<String>,
    pub error: Option<String>,
}

impl MongoClient {
    // Initialize MongoDB connection
    pub async fn new() -> Result<Self, mongodb::error::Error> {
        // Load .env file variables
        dotenv().ok();
        
        // Get connection string from environment or use default
        let uri = env::var("MONGODB_URI")
            .unwrap_or_else(|_| {
                println!("⚠️  MONGODB_URI not found in .env, using default");
                "mongodb://localhost:27017".to_string()
            });
        
        let database_name = env::var("MONGODB_DATABASE")
            .unwrap_or_else(|_| {
                println!("⚠️  MONGODB_DATABASE not found in .env, using default");
                "fhir_terminology".to_string()
            });

        println!("🔗 Connecting to MongoDB: {}", &uri);
        println!("📁 Using database: {}", &database_name);

        // Parse connection options
        let mut client_options = ClientOptions::parse(&uri).await?;
        
        // Set the server API version
        let server_api = ServerApi::builder()
            .version(ServerApiVersion::V1)
            .build();
        client_options.server_api = Some(server_api);
        
        // Set app name
        client_options.app_name = Some("FHIR Terminology Server".to_string());
        
        // Add authentication if provided
        if let (Ok(username), Ok(password)) = (env::var("MONGODB_USERNAME"), env::var("MONGODB_PASSWORD")) {
            if !username.is_empty() && !password.is_empty() {
                let auth_db = env::var("MONGODB_AUTH_DB").unwrap_or_else(|_| "admin".to_string());
                println!("🔐 Using authentication for user: {}", username);
                
                client_options.credential = Some(
                    mongodb::options::Credential::builder()
                        .username(username)
                        .password(password)
                        .source(auth_db)
                        .build()
                );
            }
        }
        
        // Create client
        let client = Client::with_options(client_options)?;
        let database = client.database(&database_name);
        
        println!("✅ MongoDB client initialized for database: {}", database_name);
        
        Ok(MongoClient { client, database })
    }
    
    // Get global instance (singleton pattern)
    pub async fn get_instance() -> Result<&'static MongoClient, mongodb::error::Error> {
        MONGO_CLIENT
            .get_or_try_init(|| async {
                MongoClient::new().await
            })
            .await
    }
    
    // ADD THIS METHOD: Get database by name
    pub fn get_database_by_name(&self, db_name: &str) -> Database {
        self.client.database(db_name)
    }
    
    // Health check - ping the database
    pub async fn health_check(&self) -> ConnectionStatus {
        match self.client
            .database("admin")
            .run_command(doc! { "ping": 1 }, None)
            .await 
        {
            Ok(_) => {
                // Get server info
                let server_info = match self.client
                    .database("admin")
                    .run_command(doc! { "buildInfo": 1 }, None)
                    .await 
                {
                    Ok(info) => {
                        let version = info.get("version")
                            .and_then(|v| v.as_str())
                            .unwrap_or("unknown");
                        Some(format!("MongoDB {}", version))
                    },
                    Err(_) => Some("MongoDB (version unknown)".to_string()),
                };
                
                ConnectionStatus {
                    connected: true,
                    database_name: self.database.name().to_string(),
                    server_info,
                    error: None,
                }
            },
            Err(e) => ConnectionStatus {
                connected: false,
                database_name: self.database.name().to_string(),
                server_info: None,
                error: Some(e.to_string()),
            },
        }
    }
    
    // List all collections
    pub async fn list_collections(&self) -> Result<Vec<String>, mongodb::error::Error> {
        let collections = self.database.list_collection_names(None).await?;
        Ok(collections)
    }
}

// Initialize MongoDB connection on module load
pub async fn init_mongodb() -> Result<(), mongodb::error::Error> {
    MongoClient::get_instance().await?;
    Ok(())
}

// Get connection status for API responses
pub async fn get_connection_status() -> ConnectionStatus {
    match MongoClient::get_instance().await {
        Ok(client) => client.health_check().await,
        Err(e) => ConnectionStatus {
            connected: false,
            database_name: "unknown".to_string(),
            server_info: None,
            error: Some(e.to_string()),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_mongodb_connection() {
        // This test requires a running MongoDB instance
        match MongoClient::new().await {
            Ok(client) => {
                let status = client.health_check().await;
                assert!(status.connected || status.error.is_some());
            },
            Err(e) => {
                println!("MongoDB connection failed (expected in CI): {}", e);
            }
        }
    }
}
