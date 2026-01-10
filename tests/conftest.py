"""
MetaPM Test Configuration
Pytest fixtures and setup
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_task():
    """Sample task data for testing"""
    return {
        "title": "Test task for unit testing",
        "description": "This is a test task",
        "priority": 2,
        "projects": ["META"],
        "categories": ["TEST"]
    }


@pytest.fixture
def sample_quick_capture():
    """Sample quick capture request"""
    return {
        "title": "Quick capture test",
        "project": "META",
        "category": "IDEA"
    }
