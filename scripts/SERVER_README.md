# Election Dashboard Server

Local development server for the election dashboard with PDF upload support.

## Quick Start

```bash
# From project root
python scripts/server.py
```

Then open http://localhost:5000

## Features

### 1. Dashboard Serving
- Serves `viz/dashboard.html` at `/`
- Serves `viz/data.js` at `/data.js`

### 2. PDF Upload
- Upload PDFs via the web UI
- Endpoint: `POST /upload`
- Auto-processes PDFs through full pipeline:
  1. Saves to `data/uploads/` with timestamp
  2. Runs `import_pdf.py --full`
  3. Reloads database
  4. Regenerates visualization data
  5. Returns extraction statistics

### 3. Status Endpoint
- `GET /status` returns current database stats
- Shows counties, total races, candidates, election dates

## Upload Flow

1. User selects PDF file in browser
2. Click "Upload & Process"
3. Server saves to `data/uploads/{timestamp}_{filename}.pdf`
4. Runs full import pipeline (may take 2-5 minutes)
5. Returns stats: races, candidates, county
6. Dashboard auto-reloads with new data

## Error Handling

- Invalid file types rejected
- Processing timeout: 5 minutes
- Errors displayed in upload status area
- Failed uploads don't block server

## Directory Structure

```
ulster-elections/
├── scripts/
│   └── server.py          # Flask server
├── viz/
│   ├── dashboard.html     # UI with upload section
│   └── data.js           # Visualization data
└── data/
    └── uploads/          # Uploaded PDFs (created automatically)
```

## Development Notes

- Debug mode enabled (auto-reloads on code changes)
- Server binds to 0.0.0.0:5000 (accessible from network)
- Uses project venv (Flask must be installed)
- Upload size limited by Flask defaults (16MB)

## Testing

### Test server imports
```bash
source .venv/bin/activate
python -c "import scripts.server; print('OK')"
```

### Test upload endpoint manually
```bash
curl -X POST -F "file=@data/test.pdf" http://localhost:5000/upload
```

### Test status endpoint
```bash
curl http://localhost:5000/status
```
