# HoosAlert

uva-alert-system/
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── README.md
├── backend/
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json (or requirements.txt)
│   └── README.md
├── python-service/
│   ├── scrapers/
│   ├── models/
│   ├── data/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── shared/
│   ├── api-spec/
│   ├── schemas/
│   └── campus-data/
├── docs/
│   └── README.md
├── infrastructure/
│   └── docker-compose.yml
├── README.md


## Inspect MongoDB (Local)

From repo root (`C:\HoosAlert`), open a shell in the Mongo container:

```powershell
docker compose -f infrastructure/docker-compose.yml exec mongo mongosh
```

Then run:

```javascript
show dbs
use hoos_alert
show collections
db.incidents.countDocuments()
db.incidents.find().sort({ created_at: -1 }).limit(10).pretty()
```

If you are in a continuation prompt (`|`), press `Ctrl + C` once and rerun commands line-by-line.

## Inspect MongoDB (Without Docker)

Use this if you want to run MongoDB locally without containers.

### 1) Install MongoDB + mongosh

1. Install MongoDB Community Server.
2. Install MongoDB Shell (`mongosh`) if it is not included.
3. Start your local MongoDB service.

Quick check:

```powershell
mongosh --version
```

### 2) Point backend to local MongoDB

In `backend/.env`, set:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=hoos_alert
MONGO_INCIDENTS_COLLECTION=incidents
```

### 3) Open Mongo shell and inspect data

```powershell
mongosh
```

Then run:

```javascript
show dbs
use hoos_alert
show collections
db.incidents.countDocuments()
db.incidents.find().sort({ created_at: -1 }).limit(10).pretty()
```

### 4) Optional: seed mock incidents

Start backend, then call the seed endpoint (if enabled in your app flow), or submit reports from the frontend to create records.
