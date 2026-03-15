"""
Tests pour tool_api_urbanisme — Interrogation GPU / BAN.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "boomerang_tools", "tool_api_urbanisme"))

from fastapi.testclient import TestClient
from server import app, _parser_coordonnees

import pytest

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["requiert_internet"] is True


def test_run_query_vide():
    resp = client.post("/run", json={"input": {"query": ""}})
    output = resp.json()["output"]
    assert "Erreur" in output


def test_parser_coordonnees_valides():
    lat, lon, label = _parser_coordonnees("43.6047, 1.4442")
    assert abs(lat - 43.6047) < 0.001
    assert abs(lon - 1.4442) < 0.001


def test_parser_coordonnees_hors_limites():
    with pytest.raises(ValueError, match="hors limites"):
        _parser_coordonnees("999.0, 999.0")


@patch("server.requests.get")
def test_run_avec_adresse_mock(mock_get):
    # Mock BAN geocoding
    ban_resp = MagicMock()
    ban_resp.json.return_value = {
        "features": [{
            "geometry": {"coordinates": [2.3522, 48.8566]},
            "properties": {"label": "Paris"}
        }]
    }
    ban_resp.raise_for_status = MagicMock()

    # Mock GPU API
    gpu_resp = MagicMock()
    gpu_resp.json.return_value = {
        "features": [{
            "properties": {
                "libelle": "UA",
                "typezone": "U",
                "libelong": "Zone urbaine",
                "destdomi": "Habitat",
                "nomfic": "PLU_Paris.pdf",
            }
        }]
    }
    gpu_resp.raise_for_status = MagicMock()

    mock_get.side_effect = [ban_resp, gpu_resp]

    resp = client.post("/run", json={"input": {"query": "12 rue de Rivoli Paris"}})
    assert resp.status_code == 200
    output = resp.json()["output"]
    assert "ZONAGE PLU" in output
