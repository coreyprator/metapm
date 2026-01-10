"""
MetaPM Tests - Health and Basic Endpoints
"""

import pytest


def test_root_endpoint(client):
    """Test root endpoint returns service info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MetaPM"
    assert data["status"] == "healthy"


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_docs_available(client):
    """Test OpenAPI docs are available"""
    response = client.get("/docs")
    assert response.status_code == 200


# Note: Full CRUD tests require database connection
# These will be integration tests run with actual DB

class TestTaskEndpoints:
    """Task endpoint tests (require DB)"""
    
    @pytest.mark.skip(reason="Requires database connection")
    def test_list_tasks(self, client):
        """Test listing tasks"""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
    
    @pytest.mark.skip(reason="Requires database connection")
    def test_create_task(self, client, sample_task):
        """Test creating a task"""
        response = client.post("/api/tasks", json=sample_task)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_task["title"]
        assert "taskId" in data


class TestCaptureEndpoint:
    """Quick capture endpoint tests"""
    
    @pytest.mark.skip(reason="Requires database connection")
    def test_quick_capture(self, client, sample_quick_capture):
        """Test quick capture creates task"""
        response = client.post("/api/capture", json=sample_quick_capture)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_quick_capture["title"]
        assert "taskId" in data


class TestProjectEndpoints:
    """Project endpoint tests"""
    
    @pytest.mark.skip(reason="Requires database connection")
    def test_list_projects(self, client):
        """Test listing projects"""
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data


class TestMethodologyEndpoints:
    """Methodology endpoint tests"""
    
    @pytest.mark.skip(reason="Requires database connection")
    def test_list_rules(self, client):
        """Test listing methodology rules"""
        response = client.get("/api/methodology/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
