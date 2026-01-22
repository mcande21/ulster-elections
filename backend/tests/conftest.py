import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.database import init_pool, close_pool


@pytest.fixture(scope="module")
def client():
    """Create test client for FastAPI app with database pool initialized."""
    # Initialize the database pool before tests
    init_pool()

    with TestClient(app) as client:
        yield client

    # Cleanup after tests
    close_pool()
