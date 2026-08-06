import requests
import csv
import time
import json

# Base URL for local ICD-API
BASE_URL = "http://localhost"

# Headers for API requests
HEADERS = {
    "Accept": "application/json",
    "API-Version": "v2",
    "Accept-Language": "en"
}

def localize_uri(uri):
    """Convert WHO cloud URIs to local URIs"""
    if uri.startswith("http://id.who.int") or uri.startswith("https://id.who.int"):
        return uri.replace("http://id.who.int", BASE_URL).replace("https://id.who.int", BASE_URL)
    return uri

def make_request(url, max_retries=3):
    """Make API request with retry logic and URI localization"""
    url = localize_uri(url)
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HTTP {response.status_code}: {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}): {e}")
            time.sleep(1)
    return None

def extract_entity_info(data, parent_id=""):
    """Extract relevant information from entity data"""
    entity = {
        "id": data.get("@id", ""),
        "code": data.get("code", ""),
        "title": "",
        "definition": "",
        "parent": parent_id,
        "browserUrl": data.get("browserUrl", ""),
        "codingNote": "",
        "synonyms": "",
        "exclusions": "",
        "inclusions": "",
        "isLeaf": str(len(data.get("child", [])) == 0)
    }
    
    # Extract title safely
    title = data.get("title", {})
    if isinstance(title, dict):
        entity["title"] = title.get("@value", "")
    elif isinstance(title, str):
        entity["title"] = title
    
    # Extract definition safely
    definition = data.get("definition", {})
    if isinstance(definition, dict):
        entity["definition"] = definition.get("@value", "")
    elif isinstance(definition, str):
        entity["definition"] = definition
    
    # Extract coding note
    coding_note = data.get("codingNote", {})
    if isinstance(coding_note, dict):
        entity["codingNote"] = coding_note.get("@value", "")
    
    # Extract synonyms
    synonyms = data.get("synonym", [])
    if synonyms:
        synonym_labels = []
        for synonym in synonyms:
            if isinstance(synonym, dict) and "label" in synonym:
                label = synonym["label"]
                if isinstance(label, dict):
                    synonym_labels.append(label.get("@value", ""))
                elif isinstance(label, str):
                    synonym_labels.append(label)
        entity["synonyms"] = "; ".join(synonym_labels)
    
    return entity

def fetch_entity_recursive(entity_uri, parent_id="", depth=0, max_depth=50):
    """Recursively fetch entity and its children with depth limit"""
    if depth > max_depth:
        print(f"Max depth reached for {entity_uri}")
        return []
    
    print(f"{'  ' * depth}Fetching: {entity_uri}")
    data = make_request(entity_uri)
    
    if not data:
        return []
    
    entities = []
    entity = extract_entity_info(data, parent_id)
    entities.append(entity)
    
    # Process children
    children = data.get("child", [])
    for child_uri in children:
        entities.extend(fetch_entity_recursive(child_uri, entity["id"], depth + 1, max_depth))
    
    return entities

def scrape_foundation_entities():
    """Scrape foundation entities"""
    print("Scraping Foundation entities...")
    foundation_url = f"{BASE_URL}/icd/entity"
    root_data = make_request(foundation_url)
    
    if not root_data:
        print("Failed to fetch foundation root")
        return []
    
    child_entities = root_data.get("child", [])
    all_entities = []
    
    for i, child_uri in enumerate(child_entities):
        print(f"Processing top-level entity {i+1}/{len(child_entities)}")
        entities = fetch_entity_recursive(child_uri)
        all_entities.extend(entities)
        print(f"Collected {len(entities)} entities from this branch")
    
    return all_entities

def scrape_mms_entities():
    """Scrape MMS linearization entities"""
    print("Scraping MMS linearization entities...")
    mms_url = f"{BASE_URL}/icd/release/11/2025-01/mms"
    root_data = make_request(mms_url)
    
    if not root_data:
        print("Failed to fetch MMS root")
        return []
    
    child_entities = root_data.get("child", [])
    all_entities = []
    
    for i, child_uri in enumerate(child_entities):
        print(f"Processing MMS chapter {i+1}/{len(child_entities)}")
        entities = fetch_entity_recursive(child_uri)
        all_entities.extend(entities)
        print(f"Collected {len(entities)} entities from this chapter")
    
    return all_entities

def save_to_csv(entities, filename):
    """Save entities to CSV file"""
    if not entities:
        print("No entities to save")
        return
    
    fieldnames = [
        "id", "code", "title", "definition", "parent", 
        "browserUrl", "codingNote", "synonyms", "exclusions", 
        "inclusions", "isLeaf"
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entities)
    
    print(f"Saved {len(entities)} entities to {filename}")

def main():
    """Main function - modify this to choose what to scrape"""
    print("Starting ICD-11 data scraping...")
    
    # Change this line to choose what to scrape:
    # "foundation" - Foundation entities
    # "mms" - MMS linearization 
    # "both" - Both foundation and MMS
    scrape_type = "mms"  # Change this as needed
    
    all_entities = []
    
    if scrape_type in ["foundation", "both"]:
        print("=== SCRAPING FOUNDATION ===")
        foundation_entities = scrape_foundation_entities()
        if foundation_entities:
            save_to_csv(foundation_entities, "icd11_foundation.csv")
            all_entities.extend(foundation_entities)
    
    if scrape_type in ["mms", "both"]:
        print("=== SCRAPING MMS ===")
        mms_entities = scrape_mms_entities()
        if mms_entities:
            save_to_csv(mms_entities, "icd11_mms.csv")
            all_entities.extend(mms_entities)
    
    if scrape_type == "both" and all_entities:
        save_to_csv(all_entities, "icd11_complete.csv")
    
    print(f"Scraping completed! Total entities: {len(all_entities)}")

if __name__ == "__main__":
    main()
