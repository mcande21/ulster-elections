#!/usr/bin/env python3
"""
Local dev server for election dashboard with file upload support.

Usage:
    python scripts/server.py

Then open http://localhost:5000

Features:
    - Serve dashboard.html and data.js
    - POST /upload - Accept PDF files, run import_pdf.py --full
    - GET /status - Return current database statistics
"""
from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os
import sys
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__, static_folder='../viz')

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"

# Ensure uploads directory exists
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/')
def index():
    """Serve the main dashboard HTML."""
    return send_from_directory(app.static_folder, 'dashboard.html')


@app.route('/data.js')
def data():
    """Serve the visualization data JS file."""
    return send_from_directory(app.static_folder, 'data.js')


@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle PDF upload and processing.

    Accepts:
        - file: PDF file (multipart/form-data)

    Returns:
        JSON with:
        - success: bool
        - message: str
        - stats: dict (races, candidates, county) if successful
        - error: str if failed
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files accepted'}), 400

    try:
        # Save uploaded file with timestamp to avoid collisions
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file.filename}"
        upload_path = UPLOADS_DIR / safe_filename

        file.save(str(upload_path))
        print(f"Saved upload to: {upload_path}")

        # Run import_pdf.py with --full flag
        print(f"Processing PDF with import_pdf.py...")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "import_pdf.py"), str(upload_path), "--full"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"ERROR: import_pdf.py failed:\n{error_msg}")
            return jsonify({
                'success': False,
                'error': f'PDF processing failed: {error_msg}'
            }), 500

        # Parse stdout for statistics
        output = result.stdout
        print(f"import_pdf.py output:\n{output}")

        # Extract stats from output
        stats = extract_stats_from_output(output)

        return jsonify({
            'success': True,
            'message': 'PDF processed successfully',
            'stats': stats,
            'filename': safe_filename
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Processing timeout (5 minutes exceeded)'
        }), 500
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/status')
def status():
    """
    Return current database statistics.

    Returns:
        JSON with:
        - counties: list of county names
        - total_races: int
        - total_candidates: int
        - election_dates: list of dates
    """
    try:
        # Read all JSON files from data/raw/
        raw_dir = DATA_DIR / "raw"
        if not raw_dir.exists():
            return jsonify({
                'counties': [],
                'total_races': 0,
                'total_candidates': 0,
                'election_dates': []
            })

        counties = set()
        total_races = 0
        total_candidates = 0
        dates = set()

        for json_file in raw_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    counties.add(data.get('county', 'Unknown'))
                    dates.add(data.get('election_date', 'Unknown'))
                    races = data.get('races', [])
                    total_races += len(races)
                    for race in races:
                        total_candidates += len(race.get('candidates', []))
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
                continue

        return jsonify({
            'counties': sorted(list(counties)),
            'total_races': total_races,
            'total_candidates': total_candidates,
            'election_dates': sorted(list(dates))
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to read status: {str(e)}'
        }), 500


def extract_stats_from_output(output: str) -> dict:
    """
    Extract statistics from import_pdf.py output.

    Looks for patterns like:
        "✓ Extracted 45 races with 123 candidates"
        "County: Ulster"
        "Date: 2025-11-04"
    """
    import re

    stats = {
        'races': 0,
        'candidates': 0,
        'county': 'Unknown',
        'date': 'Unknown'
    }

    # Extract race and candidate count
    race_match = re.search(r'Extracted (\d+) races with (\d+) candidates', output)
    if race_match:
        stats['races'] = int(race_match.group(1))
        stats['candidates'] = int(race_match.group(2))

    # Extract county
    county_match = re.search(r'County:\s*(\w+)', output)
    if county_match:
        stats['county'] = county_match.group(1)

    # Extract date
    date_match = re.search(r'Date:\s*([\d-]+)', output)
    if date_match:
        stats['date'] = date_match.group(1)

    return stats


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*60)
    print("Election Dashboard Server")
    print("="*60)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Uploads dir: {UPLOADS_DIR}")
    print(f"Server: http://localhost:{port}")
    print("="*60)
    print()

    app.run(debug=True, port=port, host='0.0.0.0')
