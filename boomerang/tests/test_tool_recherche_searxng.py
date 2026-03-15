"""
Tests pour tool_recherche_searxng — Recherche web via SearXNG.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "boomerang_tools", "tool_recherche_searxng"))

from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["requiert_internet"] is True


@patch("server.requests.get")
def test_run_with_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {"title": "PLU Paris", "url": "https://example.com", "content": "Contenu PLU"},
            {"title": "ERP Normes", "url": "https://example2.com", "content": "Contenu ERP"},
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    resp = client.post("/run", json={"input": {"query": "PLU Paris"}})
    assert resp.status_code == 200
    output = resp.json()["output"]
    assert "PLU Paris" in output


@patch("server.requests.get")
def test_run_no_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": []}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    resp = client.post("/run", json={"input": {"query": "query impossible"}})
    output = resp.json()["output"]
    assert "Aucun résultat" in output


@patch("server.requests.get", side_effect=Exception("Connection refused"))
def test_run_searxng_error(mock_get):
    resp = client.post("/run", json={"input": {"query": "test"}})
    output = resp.json()["output"]
    assert "Erreur" in output
