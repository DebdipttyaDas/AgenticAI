"""Integration tests for FastAPI endpoints, demo loader, and React web dashboard."""

import pytest
from fastapi.testclient import TestClient
from hireflow.api.routes import app


@pytest.fixture
def client():
    return TestClient(app)


def test_serve_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "HireFlow AI" in response.text
    assert "React" in response.text


def test_load_demo_dataset(client):
    response = client.post("/api/v1/demo/load")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["candidates_loaded"] == 4


def test_get_pool_and_provenance(client):
    # Ensure pool is loaded
    client.post("/api/v1/demo/load")

    pool_resp = client.get("/api/v1/pool")
    assert pool_resp.status_code == 200
    pool_data = pool_resp.json()
    assert pool_data["total_candidates"] == 4
    assert len(pool_data["candidates"]) == 4

    # Test individual candidate HTML scorecard
    html_resp = client.get("/api/v1/candidates/cand_001/scorecard.html")
    assert html_resp.status_code == 200
    assert "Alex Chen" in html_resp.text

    # Test provenance endpoint
    prov_resp = client.get("/api/v1/candidates/cand_001/provenance")
    assert prov_resp.status_code == 200
    prov_data = prov_resp.json()
    assert prov_data["candidate_id"] == "cand_001"
    assert prov_data["total_records"] > 0


def test_query_and_raw_interview_eval(client):
    client.post("/api/v1/demo/load")

    # Test natural language query
    q_resp = client.post("/api/v1/query", json={"query": "Find Go architects", "top_k": 3})
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    assert len(q_data["matched_candidates"]) >= 1

    # Test raw interview notes evaluation
    notes_sample = """# Technical Interview Notes - Maya Patel
Interviewer: David Vance
## Section: Distributed Systems & Backend Architecture
- Candidate designed FastAPI microservice handling 85ms response times.
- Rating: Strong
## Section: Cloud & Container Orchestration
- Maya containerized Python apps with Docker and deployed to Kubernetes.
- Rating: Acceptable
"""
    audit_resp = client.post(
        "/api/v1/evaluate-interview-raw",
        json={"candidate_id": "cand_002", "notes_text": notes_sample},
    )
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["candidate_id"] == "cand_002"
    assert audit_data["coverage_ratio"] > 0
