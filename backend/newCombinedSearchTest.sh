# Basic search for fever (both NAMASTE & ICD systems)
curl "http://127.0.0.1:8080/terminology/search?search=fever&limit=10"

# Search for traditional medicine terms (should return NAMASTE results)
curl "http://127.0.0.1:8080/terminology/search?search=vata&limit=6"

# Search for bacterial infections (should return ICD codes)
curl "http://127.0.0.1:8080/terminology/search?search=bacterial&limit=8"

# Search with Hindi language preference for NAMASTE results
curl "http://127.0.0.1:8080/terminology/search?search=dosha&limit=5&language=hindi"

# Search for cholera (should return both systems)
curl "http://127.0.0.1:8080/terminology/search?search=cholera&limit=5"

# Search for pain without limit
curl "http://127.0.0.1:8080/terminology/search?search=pain"

# Search for specific ICD code
curl "http://127.0.0.1:8080/terminology/search?search=1A00&limit=3"

#Returns both 
curl "http://127.0.0.1:8080/terminology/search?search=VB&limit=5"


