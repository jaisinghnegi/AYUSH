# Health check
curl "http://127.0.0.1:8080/health"

# API Gateway status
curl "http://127.0.0.1:8080/gateway"

# REST API status
curl "http://127.0.0.1:8080/api"

# MongoDB status
curl "http://127.0.0.1:8080/data/mongodb"

# List MongoDB collections
curl "http://127.0.0.1:8080/data/mongodb/collections"

# Redis status
curl "http://127.0.0.1:8080/data/redis"


# WHO ICD-11 API status
curl "http://127.0.0.1:8080/external/who-icd11"

# NAMASTE CSV status
curl "http://127.0.0.1:8080/external/namaste-csv"


# Search NAMASTE codes
curl "http://127.0.0.1:8080/namaste/search?search=vata&limit=5"

# Search with language filter (Hindi)
curl "http://127.0.0.1:8080/namaste/search?search=dosha&limit=3&language=hindi"

# Search with language filter (English)
curl "http://127.0.0.1:8080/namaste/search?search=dosha&limit=3&language=english"

# Search with both languages
curl "http://127.0.0.1:8080/namaste/search?search=pitta&limit=3&language=both"

# Search by code
curl "http://127.0.0.1:8080/namaste/search?code=AAE&limit=5"

# Get all NAMASTE codes (limited)
curl "http://127.0.0.1:8080/namaste/all?limit=10"

# Get all codes in Hindi
curl "http://127.0.0.1:8080/namaste/all?limit=5&language=hindi"


# Get all ICD codes (limited)
curl "http://127.0.0.1:8080/icd/all?limit=5"

# Search ICD codes
curl "http://127.0.0.1:8080/icd/search?search=cholera&limit=3"
curl "http://127.0.0.1:8080/icd/search?search=bacterial&limit=5"
curl "http://127.0.0.1:8080/icd/search?search=infectious&limit=5"
curl "http://127.0.0.1:8080/icd/search?search=fever&limit=7"

# Search by specific code
curl "http://127.0.0.1:8080/icd/search?search=1A00&limit=3"

# Get Biomedicine codes only
curl "http://127.0.0.1:8080/icd/biomedicine?limit=10"

# Get Traditional Medicine codes (may be empty if no TM2 data)
curl "http://127.0.0.1:8080/icd/tm2?limit=10"

# Search with discipline filter
curl "http://127.0.0.1:8080/icd/search?discipline=biomedicine&search=intestinal&limit=5"

# Search by parent code (hierarchical)
curl "http://127.0.0.1:8080/icd/search?parent=http://id.who.int/icd/release/11/2025-01/mms/135352227&limit=5"

# Test with different limits
curl "http://127.0.0.1:8080/icd/all?limit=1"
curl "http://127.0.0.1:8080/namaste/all?limit=20"

# Test with no parameters
curl "http://127.0.0.1:8080/icd/search"
curl "http://127.0.0.1:8080/namaste/search"

# Test error handling (invalid limit)
curl "http://127.0.0.1:8080/icd/all?limit=abc"

# Test case-insensitive search
curl "http://127.0.0.1:8080/icd/search?search=CHOLERA&limit=3"
curl "http://127.0.0.1:8080/icd/search?search=Bacterial&limit=3"
