# CodeVedas_SIH


Installing mongodb on linux
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | sudo gpg -o /etc/apt/trusted.gpg.d/mongodb-server-8.0.gpg --dearmor && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list && sudo apt update && sudo apt install mongodb-org -y
```

Installing redis with apt
```bash
sudo apt install redis-server -y
```


To Import ayurveda codes inside backend/csvs
```bash
mongoimport --db ayurveda_db --collection namc_codes --type csv --headerline --file "NAMC_FINAL.csv"
```

Docker image for ICDapi
```bash
docker run -p 80:80 -e acceptLicense=true -e saveAnalytics=true whoicd/icd-api
```

```bash
docker run -p 8000:80 -e acceptLicense=true -e saveAnalytics=true whoicd/icd-api 
```

Import ICD-11 into mongo scrapped csv in /csvs/ICD-11
```bash
mongoimport --db icd11_database --collection icd11_entities --type csv --headerline --file icd11_mms.csv
```

Post Import Index creation
```bash
mongosh icd11_database --eval "
db.icd11_entities.createIndex({'id': 1}, {unique: true});
db.icd11_entities.createIndex({'code': 1}, {sparse: true});
db.icd11_entities.createIndex({'parent': 1});
db.icd11_entities.createIndex({'title': 'text', 'definition': 'text', 'synonyms': 'text'});
db.icd11_entities.createIndex({'parent': 1, 'isLeaf': 1});
db.icd11_entities.createIndex({'code': 1, 'isLeaf': 1});
print('Indexes created successfully');
"
```

Command to start mongodb if its stopped in linux
```bash
sudo systemctl start mongod
```

hello madhav