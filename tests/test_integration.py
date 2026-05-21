"""
NexusTrade — Integration Test Suite
Tests the full API flow end-to-end against a running server.

Usage:
    # Start the server first:
    uvicorn app.main:app --port 8000

    # Then run:
    python tests/test_integration.py
    # or: pytest tests/test_integration.py -v
"""

import os
import json
import time
import httpx
import pytest

BASE_URL = os.getenv("NEXUSTRADE_BASE_URL", "http://localhost:8000")
TEST_USER = "pytest-runner-001"


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        yield c


@pytest.fixture(scope="session")
def token(client):
    res = client.post("/v2/auth/token", json={"user_id": TEST_USER})
    assert res.status_code == 200, f"Auth failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert "version" in body
    print(f"\n✅ Health OK — version {body['version']}")


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_token_issued(client):
    res = client.post("/v2/auth/token", json={"user_id": "integration-test-user"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    print(f"\n✅ Token issued — expires_in={body['expires_in']}s")


def test_invalid_user_id_rejected(client):
    res = client.post("/v2/auth/token", json={"user_id": "bad user id!!"})
    assert res.status_code == 422
    print("\n✅ Invalid user_id correctly rejected")


def test_protected_endpoint_requires_token(client):
    res = client.get("/v2/history")
    assert res.status_code == 403
    print("\n✅ Protected endpoint correctly requires auth")


# ── Insights ──────────────────────────────────────────────────────────────────

def test_quick_insight(client, auth_headers):
    payload = {"sector": "pharmaceuticals", "region": "Southeast Asia", "depth": "quick"}
    res = client.post("/v2/insights", json=payload, headers=auth_headers)
    assert res.status_code == 200, f"Insight failed: {res.text}"
    body = res.json()
    assert body["sector"] == "pharmaceuticals"
    assert len(body["report_markdown"]) > 200
    assert "processing_ms" in body
    print(f"\n✅ Quick insight — {body['processing_ms']}ms, {len(body['report_markdown'])} chars")


def test_popular_sectors(client, auth_headers):
    res = client.get("/v2/insights/sectors")
    assert res.status_code == 200
    body = res.json()
    assert "sectors" in body
    assert len(body["sectors"]) > 0
    print(f"\n✅ Sectors endpoint — {len(body['sectors'])} sectors returned")


# ── Watchlist ─────────────────────────────────────────────────────────────────

def test_watchlist_add_and_get(client, auth_headers):
    # Add
    res = client.post(
        "/v2/watchlist",
        json={"sector": "Green Hydrogen", "region": "EU", "alert_enabled": False},
        headers=auth_headers,
    )
    assert res.status_code == 201
    entry = res.json()
    assert entry["sector"] == "Green Hydrogen"

    # Get
    res = client.get("/v2/watchlist", headers=auth_headers)
    assert res.status_code == 200
    watchlist = res.json()
    assert any(e["sector"] == "Green Hydrogen" for e in watchlist)
    print(f"\n✅ Watchlist — add/get passed ({len(watchlist)} entries)")


def test_watchlist_remove(client, auth_headers):
    res = client.delete("/v2/watchlist/Green Hydrogen", headers=auth_headers)
    assert res.status_code == 204
    print("\n✅ Watchlist — remove passed")


# ── History ───────────────────────────────────────────────────────────────────

def test_history_populated(client, auth_headers):
    res = client.get("/v2/history", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "records" in body
    assert "total_queries" in body
    print(f"\n✅ History — {body['total_queries']} records found")


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], check=False)
    raise SystemExit(result.returncode)
