"""Tests d'intégration pour app.api (endpoints FastAPI)."""
from fastapi.testclient import TestClient

from app.api import app, received_metrics

client = TestClient(app)


def setup_function():
    """Réinitialise l'état en mémoire avant chaque test.

    L'API stocke received_metrics dans une simple liste globale ; comme
    les tests partagent le même process, il faut la vider entre chaque
    test pour éviter les effets de bord (tests indépendants).
    """
    received_metrics.clear()


def test_health_endpoint_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_metrics_empty_by_default():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "metrics": []}


def test_post_metrics_stores_and_returns_summary():
    payload = {
        "agent": "test-agent",
        "event_type": "system_metrics",
        "data": {"cpu": {"percent": 1.0}},
    }

    response = client.post("/metrics", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["total_received"] == 1


def test_post_metrics_rejects_invalid_payload():
    response = client.post("/metrics", json={"event_type": "x"})
    assert response.status_code == 422


def test_latest_metrics_returns_404_when_empty():
    response = client.get("/metrics/latest")
    assert response.status_code == 404


def test_latest_metrics_returns_most_recent_entry():
    first = {"agent": "agent-1", "event_type": "system_metrics", "data": {}}
    second = {"agent": "agent-2", "event_type": "system_metrics", "data": {}}

    client.post("/metrics", json=first)
    client.post("/metrics", json=second)

    response = client.get("/metrics/latest")

    assert response.status_code == 200
    assert response.json()["agent"] == "agent-2"
