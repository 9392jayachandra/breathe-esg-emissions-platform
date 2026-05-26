# BreatheESG — Emissions Ingestion Platform

A Django REST + React app that ingests emissions data from SAP, utility portals, and corporate travel platforms, normalizes it, and surfaces a review dashboard for analyst sign-off before audit.

## Live Demo
- **Frontend:** [add after deploy]
- **Backend API:** [add after deploy]
- **Login:** No auth in prototype — enter any name as "analyst" in review actions

---

## Local Setup

### Backend (Django)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API runs at `http://localhost:8000`
Admin panel at `http://localhost:8000/admin`

### Frontend (React)

```bash
cd frontend
npm install
npm start
```

App runs at `http://localhost:3000`

---

## First Steps After Setup

1. Go to **Clients** tab → add a client (e.g. "Acme Corp", slug: "acme-corp")
2. Go to **Ingest Data** → select client → upload one of the sample CSVs from `backend/sample_data/`
3. Go to **Review** → inspect, approve, or reject records

---

## Sample Data

Located in `backend/sample_data/`:
- `sap_export.csv` — SAP flat-file with German headers, fuel data
- `utility_export.csv` — Utility portal CSV with multiple meters
- `travel_export.csv` — Concur-style travel export with flights, hotels, ground

---

## Deployment (Railway)

### Backend
1. Create a new Railway project
2. Connect GitHub repo, set root directory to `backend/`
3. Railway auto-detects Django + Procfile
4. Add environment variables:
   - `SECRET_KEY` = any long random string
   - `DEBUG` = False
   - `DATABASE_URL` = Railway provides this automatically with PostgreSQL plugin
5. Add PostgreSQL plugin in Railway dashboard

### Frontend
1. Create Vercel account, connect GitHub
2. Set root directory to `frontend/`
3. Add environment variable: `REACT_APP_API_URL` = your Railway backend URL + `/api`
4. Deploy

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/tenants/` | List / create clients |
| POST | `/api/upload/` | Upload a CSV file |
| GET | `/api/sources/` | List upload history |
| GET | `/api/records/` | List emission records (filterable) |
| GET/PATCH | `/api/records/<id>/` | Record detail / edit |
| POST | `/api/records/<id>/review/` | Approve / reject / flag |
| POST | `/api/records/bulk-review/` | Bulk approve/reject |
| GET | `/api/records/<id>/audit/` | Audit trail for a record |
| GET | `/api/dashboard/` | Summary stats |

---

## Documentation

- `docs/MODEL.md` — Data model and design decisions
- `docs/DECISIONS.md` — Every ambiguity resolved
- `docs/TRADEOFFS.md` — Three things deliberately not built
- `docs/SOURCES.md` — Research behind each data source format
