"""
Tests pour guide_depot_pc.py -- Guide depot Permis de Construire.

Teste les fonctions pures (non-Streamlit) et les constantes.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from guide_depot_pc import (
    ETAPES,
    PIECES_PCMI,
    PIECES_SUPPLEMENTAIRES,
    _appeler_outil,
    _check_outil_dispo,
    _generer_resume_texte,
)


# ── Tests constantes ─────────────────────────────────────

def test_etapes_count():
    assert len(ETAPES) == 6


def test_etapes_ont_titre_et_icone():
    for etape in ETAPES:
        assert "titre" in etape
        assert "icone" in etape
        assert len(etape["titre"]) > 0


def test_pieces_pcmi_count():
    assert len(PIECES_PCMI) == 8


def test_pieces_pcmi_codes_uniques():
    codes = [code for code, _ in PIECES_PCMI]
    assert len(codes) == len(set(codes))


def test_pieces_pcmi_toutes_commencent_par_pcmi():
    for code, _ in PIECES_PCMI:
        assert code.startswith("PCMI")


def test_pieces_supplementaires_non_vide():
    assert len(PIECES_SUPPLEMENTAIRES) > 0


# ── Tests _appeler_outil ─────────────────────────────────

@patch("guide_depot_pc.requests.post")
def test_appeler_outil_succes(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"output": "Zone UA centre-ville"}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    result = _appeler_outil("http://fake:8003", "12 rue de Rivoli Paris")
    assert result == "Zone UA centre-ville"
    mock_post.assert_called_once()


@patch("guide_depot_pc.requests.post")
def test_appeler_outil_erreur_http(mock_post):
    mock_post.side_effect = Exception("Connection refused")

    result = _appeler_outil("http://fake:8003", "adresse test")
    assert "Erreur" in result


@patch("guide_depot_pc.requests.post")
def test_appeler_outil_pas_de_output(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    result = _appeler_outil("http://fake:8003", "test")
    assert result == "Pas de resultat."


# ── Tests _check_outil_dispo ─────────────────────────────

@patch("guide_depot_pc.requests.get")
def test_check_outil_dispo_ok(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    assert _check_outil_dispo("http://fake:8003") is True


@patch("guide_depot_pc.requests.get")
def test_check_outil_dispo_erreur(mock_get):
    mock_get.side_effect = Exception("Connection refused")

    assert _check_outil_dispo("http://fake:8003") is False


@patch("guide_depot_pc.requests.get")
def test_check_outil_dispo_500(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_get.return_value = mock_resp

    assert _check_outil_dispo("http://fake:8003") is False


# ── Tests _generer_resume_texte ──────────────────────────

def test_resume_texte_minimal():
    data = {"adresse": "12 rue de Rivoli, Paris"}
    result = _generer_resume_texte(data)
    assert "12 rue de Rivoli" in result
    assert "BOOMERANG" in result


def test_resume_texte_complet():
    data = {
        "adresse": "5 place de la Republique, Lyon",
        "commune": "Lyon 3e",
        "parcelle": "AB 456",
        "type_projet": "Extension",
        "surface_plancher": 120,
        "hauteur": 9.5,
        "architecte_obligatoire": False,
        "resultat_plu": "Zone UC - habitat collectif",
        "resultat_risques": "Pas de risque majeur identifie",
        "checklist": {
            "check_PCMI1": True,
            "check_PCMI2": True,
            "check_PCMI3": False,
        },
    }
    result = _generer_resume_texte(data)
    assert "5 place de la Republique" in result
    assert "Lyon 3e" in result
    assert "AB 456" in result
    assert "Extension" in result
    assert "120" in result
    assert "9.5" in result
    assert "Non obligatoire" in result
    assert "ZONAGE PLU" in result
    assert "Zone UC" in result
    assert "RISQUES" in result
    assert "CHECKLIST" in result
    assert "[X]" in result
    assert "[ ]" in result


def test_resume_texte_architecte_obligatoire():
    data = {"architecte_obligatoire": True}
    result = _generer_resume_texte(data)
    assert "Obligatoire" in result


def test_resume_texte_sans_plu_ni_risques():
    data = {"adresse": "test"}
    result = _generer_resume_texte(data)
    assert "ZONAGE PLU" not in result
    assert "RISQUES" not in result


def test_resume_texte_valeurs_par_defaut():
    data = {}
    result = _generer_resume_texte(data)
    assert "Non renseignee" in result
    assert "Non renseigne" in result
