
# Basic health check
curl "http://127.0.0.1:8080/health"

# Test MongoDB connection
curl "http://127.0.0.1:8080/data/mongodb"

# Test NAMASTE search
curl "http://127.0.0.1:8080/namaste/search?search=vata&limit=3"

# Test ICD search  
curl "http://127.0.0.1:8080/icd/search?search=cholera&limit=3"

# Test collections list
curl "http://127.0.0.1:8080/data/mongodb/collections"
