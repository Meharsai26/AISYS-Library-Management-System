from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_live():
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready():
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_unknown_endpoint():
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
