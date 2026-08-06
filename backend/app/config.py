import os

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "fhir_terminology")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")
MONGODB_AUTH_DB = os.getenv("MONGODB_AUTH_DB", "admin")

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1/")

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))

GEMINI_KEY = os.getenv("GEMINI_KEY", "")

WHO_ICD_CLIENT_ID = os.getenv("WHO_ICD_CLIENT_ID", "")
WHO_ICD_CLIENT_SECRET = os.getenv("WHO_ICD_CLIENT_SECRET", "")

CORS_ORIGINS = ["http://localhost:5173"]
