# Brian's Boards 2025

Election data visualization tool for Hudson Valley counties.

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Stack

- **Frontend:** React + TypeScript + Vite + Ant Design
- **Backend:** FastAPI + PostgreSQL (Supabase)
- **Data:** PDF extraction with pdfplumber

## Data Pipeline

1. Upload PDF via UI or `python scripts/import_pdf.py <path> --full`
2. Extracts races, candidates, party lines
3. Loads into PostgreSQL database
4. Generates vulnerability analysis

## Key Files

- `frontend/src/components/Dashboard.tsx` - Main UI
- `backend/app/routers/upload.py` - PDF upload endpoint
- `backend/app/services/database.py` - Data queries
- `scripts/extractors/` - PDF parsing logic
