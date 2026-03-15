"""
Tests pour tool_notice_securite — Generation de notices ERP.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "boomerang_tools", "tool_notice_securite"))

from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "tool" in data
    assert data["requiert_internet"] is False


def test_run_basic():
    resp = client.post("/run", json={"input": {"type_erp": "M", "capacite": 300}})
    assert resp.status_code == 200
    output = resp.json()["output"]
    assert "NOTICE DE SÉCURITÉ" in output
    assert "M" in output
    assert "300" in output


def test_run_categorie_1():
    resp = client.post("/run", json={"input": {"type_erp": "L", "capacite": 2000}})
    output = resp.json()["output"]
    assert "1ère catégorie" in output


def test_run_categorie_5():
    resp = client.post("/run", json={"input": {"type_erp": "N", "capacite": 50}})
    output = resp.json()["output"]
    assert "5ème catégorie" in output


def test_run_capacite_invalide():
    resp = client.post("/run", json={"input": {"type_erp": "M", "capacite": "abc"}})
    output = resp.json()["output"]
    assert "Erreur" in output


def test_run_capacite_hors_limites():
    resp = client.post("/run", json={"input": {"type_erp": "M", "capacite": 200000}})
    output = resp.json()["output"]
    assert "hors limites" in output


def test_run_type_erp_vide():
    resp = client.post("/run", json={"input": {"type_erp": "", "capacite": 100}})
    output = resp.json()["output"]
    assert "Erreur" in output
