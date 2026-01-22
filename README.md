# Brian's Boards 2025

A quick election data visualization tool for analyzing competitive races in Hudson Valley NY counties.

Built for fun to explore local election results and identify:
- **Flip opportunities** - R-held seats Dems could win
- **Retention risks** - D-held seats at risk

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

*Spun up quickly for fun. Not affiliated with any political organization.*
