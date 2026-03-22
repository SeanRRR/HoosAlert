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
