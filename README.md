# Brian's Boards 2025

Election data analysis platform for Hudson Valley NY counties: county board-of-elections PDFs go in, a competitiveness dashboard comes out. Results are extracted with pdfplumber, normalized into SQLite, and served through FastAPI to a React dashboard that identifies:
- **Flip opportunities** - R-held seats Dems could win
- **Retention risks** - D-held seats at risk

Analysis notes (fusion-voting methodology, vulnerability scoring) live in [`docs/`](docs/).

## Features

- 📊 Interactive dashboard with filters
- 📁 PDF upload for new election data
- 🔍 Search across races, winners, runner-ups
- 📈 Competitiveness analysis (Thin/Lean/Likely/Safe)
- 🗳️ Multi-county support (Ulster, Dutchess, Columbia, Greene)

## Quick Start

```bash
# Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React, TypeScript, Vite, Ant Design, Recharts |
| Backend | FastAPI, SQLite, Pydantic |
| Data | pdfplumber for PDF extraction |

## Adding New Counties

1. Get the official election results PDF
2. Upload via the UI, or run:
   ```bash
   python scripts/import_pdf.py /path/to/results.pdf --full
   ```
3. Data auto-extracts and appears in dashboard

## License

MIT - Do whatever you want with it.

---

*Weekend build. Not affiliated with any political organization.*
