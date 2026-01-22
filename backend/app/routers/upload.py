"""PDF upload and processing endpoint."""

import os
import subprocess
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
import pdfplumber

from ..models.schemas import UploadResponse


router = APIRouter(prefix="/api", tags=["upload"])


UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "data" / "uploads"
IMPORT_SCRIPT = Path(__file__).parent.parent.parent.parent / "scripts" / "import_pdf.py"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
PDF_MAGIC = b'%PDF'


def validate_election_pdf(pdf_path: str) -> tuple[bool, str]:
    """Validate PDF appears to be election results."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return False, "PDF has no pages"

            # Check first 2 pages for election-related content
            text = ""
            for page in pdf.pages[:2]:
                text += (page.extract_text() or "").lower()

            # Must contain election indicators
            has_election = any(term in text for term in ['election', 'results', 'official'])
            has_votes = any(term in text for term in ['votes', 'candidate', 'ballot', 'total'])
            has_county = 'county' in text

            if not (has_election or has_county):
                return False, "PDF does not appear to be election results (missing 'election', 'results', or 'county')"
            if not has_votes:
                return False, "PDF does not appear to contain vote data (missing 'votes', 'candidate', or 'ballot')"

            return True, "Valid election PDF"
    except Exception as e:
        return False, f"Could not read PDF: {str(e)}"


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file.

    Saves the uploaded PDF to data/uploads/ and runs import_pdf.py --full
    to process it into the database.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Read file contents
    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    # Validate PDF magic bytes
    if not contents.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="Invalid PDF file format.")

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Use UUID filename to prevent path traversal attacks
    safe_filename = f"{uuid.uuid4()}.pdf"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with file_path.open("wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Validate PDF before processing
    is_valid, validation_msg = validate_election_pdf(str(file_path))
    if not is_valid:
        os.remove(str(file_path))  # Clean up invalid file
        raise HTTPException(status_code=400, detail=validation_msg)

    # Run import script
    try:
        result = subprocess.run(
            ["python3", str(IMPORT_SCRIPT), str(file_path), "--full"],
            cwd=str(IMPORT_SCRIPT.parent.parent),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            # Parse output for race count (simple extraction)
            races_processed = None
            for line in result.stdout.splitlines():
                if "races" in line.lower() and "processed" in line.lower():
                    # Attempt to extract number
                    try:
                        races_processed = int(''.join(filter(str.isdigit, line)))
                    except ValueError:
                        pass

            return UploadResponse(
                success=True,
                message="PDF processed successfully",
                racesProcessed=races_processed
            )
        else:
            return UploadResponse(
                success=False,
                message="PDF processing failed",
                errors=[result.stderr] if result.stderr else None
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Processing timeout - PDF too large or complex")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
