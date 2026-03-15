"""
Tests pour tool_runner.py — Chargement des outils et classes ContainerTool / LocalTool.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tool_runner
from tool_runner import ContainerTool, LocalTool, QueryInput, NoticeInput, DevRequestInput, TOOL_REGISTRY


def test_tool_registry_has_expected_tools():
    expected = {"recherche_web", "notice_securite", "recherche_urbanisme", "recherche_legale", "recherche_risques_parcelle"}
    assert set(TOOL_REGISTRY.keys()) == expected


def test_container_tool_run_success():
    with patch("tool_runner.requests.post") as mock_post, \
         patch.object(tool_runner, "_CACHE_AVAILABLE", False):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"output": "Zone UA"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        tool = ContainerTool(
            name="test_tool",
            description="Outil de test",
            tool_url="http://fake:8001",
        )
        result = tool._run(query="12 rue de Rivoli Paris")
        assert result == "Zone UA"


def test_container_tool_run_http_error():
    with patch("tool_runner.requests.post", side_effect=Exception("Connection refused")), \
         patch.object(tool_runner, "_CACHE_AVAILABLE", False):
        tool = ContainerTool(
            name="test_tool",
            description="Outil de test",
            tool_url="http://fake:8001",
        )
        result = tool._run(query="test")
        assert "Erreur" in result


def test_container_tool_cache_hit():
    mock_get_cache = MagicMock(return_value="Resultat cache")
    tool_runner.get_cache = mock_get_cache
    try:
        with patch.object(tool_runner, "_CACHE_AVAILABLE", True), \
             patch.object(tool_runner, "_CACHE_ENABLED", True):
            tool = ContainerTool(
                name="recherche_urbanisme",
                description="Test cache",
                tool_url="http://fake:8003",
            )
            result = tool._run(query="12 rue de Rivoli Paris")
            assert result == "Resultat cache"
            mock_get_cache.assert_called_once_with("recherche_urbanisme", "12 rue de rivoli paris")
    finally:
        if hasattr(tool_runner, "get_cache"):
            delattr(tool_runner, "get_cache")


def test_container_tool_cache_miss_then_store():
    mock_get_cache = MagicMock(return_value=None)
    mock_set_cache = MagicMock()
    tool_runner.get_cache = mock_get_cache
    tool_runner.set_cache = mock_set_cache
    try:
        with patch("tool_runner.requests.post") as mock_post, \
             patch.object(tool_runner, "_CACHE_AVAILABLE", True), \
             patch.object(tool_runner, "_CACHE_ENABLED", True):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"output": "Zone UA fraiche"}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            tool = ContainerTool(
                name="recherche_urbanisme",
                description="Test cache miss",
                tool_url="http://fake:8003",
            )
            result = tool._run(query="Paris centre")
            assert result == "Zone UA fraiche"
            mock_get_cache.assert_called_once()
            mock_set_cache.assert_called_once()
    finally:
        if hasattr(tool_runner, "get_cache"):
            delattr(tool_runner, "get_cache")
        if hasattr(tool_runner, "set_cache"):
            delattr(tool_runner, "set_cache")


def test_container_tool_cache_disabled():
    with patch("tool_runner.requests.post") as mock_post, \
         patch.object(tool_runner, "_CACHE_AVAILABLE", True), \
         patch.object(tool_runner, "_CACHE_ENABLED", False):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"output": "Direct API"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        tool = ContainerTool(
            name="recherche_urbanisme",
            description="Test cache off",
            tool_url="http://fake:8003",
        )
        result = tool._run(query="Paris")
        assert result == "Direct API"


def test_local_tool_run_success():
    def fake_func(a="", b=""):
        return {"output": f"OK: {a} {b}"}

    tool = LocalTool(
        name="test_local",
        description="Outil local test",
        func=fake_func,
    )
    result = tool._run(a="hello", b="world")
    assert "OK: hello world" in result


def test_local_tool_run_exception():
    def broken_func(**kwargs):
        raise ValueError("boom")

    tool = LocalTool(
        name="broken_tool",
        description="Outil casse",
        func=broken_func,
    )
    result = tool._run(x="test")
    assert "Erreur" in result


def test_query_input_schema():
    q = QueryInput(query="12 rue de Rivoli Paris")
    assert q.query == "12 rue de Rivoli Paris"


def test_notice_input_schema():
    n = NoticeInput(type_erp="M", capacite=300)
    assert n.type_erp == "M"
    assert n.capacite == 300


def test_dev_request_input_schema():
    d = DevRequestInput(outil_manquant="calcul_thermique", description_fonctionnelle="Calculer RT2020")
    assert d.outil_manquant == "calcul_thermique"


@patch("tool_runner.requests.get")
def test_charger_outils_container_indisponible(mock_get):
    mock_get.side_effect = Exception("Connection refused")
    from tool_runner import charger_outils
    outils = charger_outils()
    # Meme si tous les containers sont down, les outils locaux peuvent etre charges
    # (selon disponibilite de boomerang_tools)
    assert isinstance(outils, list)
