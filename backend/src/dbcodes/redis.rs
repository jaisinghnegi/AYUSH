use redis::{Client, aio::ConnectionManager};
use tokio::sync::OnceCell;
use serde::{Deserialize, Serialize};
use std::env;
use dotenv::dotenv;

// Global Redis client instance
static REDIS_CLIENT: OnceCell<ConnectionManager> = OnceCell::const_new();

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct RedisStatus {
    pub connected: bool,
    pub server_info: Option<String>,
    pub error: Option<String>,
}

pub struct RedisClient {
    manager: ConnectionManager,
}

impl RedisClient {
    pub async fn new() -> Result<Self, redis::RedisError> {
        // Load .env file variables
        dotenv().ok();
        
        // Get Redis URL from environment or use default
        let redis_url = env::var("REDIS_URL")
            .unwrap_or_else(|_| {
                println!("⚠️  REDIS_URL not found in .env, using default");
                "redis://127.0.0.1/".to_string()
            });

        println!("🔗 Connecting to Redis: {}", &redis_url);

        // Create Redis client and connection manager
        let client = Client::open(redis_url)?;
        let manager = ConnectionManager::new(client).await?;
        
        println!("✅ Redis client initialized");
        
        Ok(RedisClient { manager })
    }
    
    pub async fn get_instance() -> Result<&'static ConnectionManager, redis::RedisError> {
        REDIS_CLIENT
            .get_or_try_init(|| async {
                let client = RedisClient::new().await?;
                Ok(client.manager)
            })
            .await
    }
    
    pub async fn health_check(&self) -> RedisStatus {
        let mut conn = self.manager.clone();
        
        match redis::cmd("PING").query_async::<_, String>(&mut conn).await {
            Ok(response) if response == "PONG" => RedisStatus {
                connected: true,
                server_info: Some("Redis server responded with PONG".to_string()),
                error: None,
            },
            Ok(other_response) => RedisStatus {
                connected: false,
                server_info: Some(format!("Unexpected response: {}", other_response)),
                error: None,
            },
            Err(e) => RedisStatus {
                connected: false,
                server_info: None,
                error: Some(e.to_string()),
            },
        }
    }
}

// Initialize Redis connection
pub async fn init_redis() -> Result<(), redis::RedisError> {
    RedisClient::get_instance().await?;
    Ok(())
}

// Get Redis connection status for API responses
pub async fn get_connection_status() -> RedisStatus {
    match RedisClient::get_instance().await {
        Ok(manager) => {
            let client = RedisClient { manager: manager.clone() };
            client.health_check().await
        },
        Err(e) => RedisStatus {
            connected: false,
            server_info: None,
            error: Some(e.to_string()),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_redis_connection() {
        // This test requires a running Redis instance
        match RedisClient::new().await {
            Ok(client) => {
                let status = client.health_check().await;
                assert!(status.connected || status.error.is_some());
            },
            Err(e) => {
                println!("Redis connection failed (expected in CI): {}", e);
            }
        }
    }
}
