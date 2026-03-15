"""
Tests pour pdf_export.py -- generation de rapports PDF.

Verifie les fonctions de nettoyage, d'encodage, et la generation PDF complete.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pdf_export import _nettoyer_contenu, _safe_text, generer_pdf_rapport


# ── Tests _nettoyer_contenu ──────────────────────────────

def test_nettoyer_mermaid_remplace():
    content = "Voici un schema:\n```mermaid\ngraph TD\nA-->B\n```\nSuite."
    result = _nettoyer_contenu(content)
    assert "mermaid" not in result
    assert "[Schema Mermaid" in result
    assert "Suite." in result


def test_nettoyer_bloc_code_garde_contenu():
    content = "Exemple:\n```python\nprint('hello')\n```"
    result = _nettoyer_contenu(content)
    assert "```" not in result
    assert "print('hello')" in result


def test_nettoyer_gras_supprime_etoiles():
    content = "Le texte est **important** ici"
    result = _nettoyer_contenu(content)
    assert "**" not in result
    assert "important" in result


def test_nettoyer_italique_supprime_etoiles():
    content = "Un mot *en italique* dans la phrase"
    result = _nettoyer_contenu(content)
    assert result == "Un mot en italique dans la phrase"


def test_nettoyer_titres_supprime_dieses():
    content = "## Titre niveau 2\nContenu apres."
    result = _nettoyer_contenu(content)
    assert "##" not in result
    assert "Titre niveau 2" in result


def test_nettoyer_chart_remplace():
    content = "CHART: bar_chart data"
    result = _nettoyer_contenu(content)
    assert "[Graphique" in result


def test_nettoyer_map_url_remplace():
    content = "MAP_URL: https://cadastre.example.com/map"
    result = _nettoyer_contenu(content)
    assert "[Carte cadastrale" in result


def test_nettoyer_texte_simple_inchange():
    content = "Texte simple sans formatage."
    result = _nettoyer_contenu(content)
    assert result == "Texte simple sans formatage."


# ── Tests _safe_text ─────────────────────────────────────

def test_safe_text_ascii():
    assert _safe_text("Hello World") == "Hello World"


def test_safe_text_accents_francais():
    result = _safe_text("edifice a etage superieur")
    assert "e" in result


def test_safe_text_emoji_remplace():
    result = _safe_text("Bonjour \U0001f600 monde")
    # L'emoji doit etre remplace (pas d'exception)
    assert "Bonjour" in result
    assert "monde" in result


def test_safe_text_caracteres_latin1_conserves():
    text = "cafe, naive, resume"
    result = _safe_text(text)
    assert result == text


# ── Tests generer_pdf_rapport ────────────────────────────

def test_generer_pdf_retourne_bytes():
    messages = [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bienvenue sur BOOMERANG."},
    ]
    result = generer_pdf_rapport("test_projet", messages)
    assert isinstance(result, (bytes, bytearray))
    assert len(result) > 100


def test_generer_pdf_commence_par_pdf_header():
    messages = [{"role": "user", "content": "Test"}]
    result = generer_pdf_rapport("projet_123", messages)
    assert result[:5] == b"%PDF-"


def test_generer_pdf_messages_vides():
    result = generer_pdf_rapport("projet_vide", [])
    assert isinstance(result, (bytes, bytearray))
    assert result[:5] == b"%PDF-"


def test_generer_pdf_message_sans_contenu_ignore():
    messages = [
        {"role": "user", "content": ""},
        {"role": "assistant", "content": "Reponse utile"},
    ]
    result = generer_pdf_rapport("projet_x", messages)
    assert isinstance(result, (bytes, bytearray))


def test_generer_pdf_avec_horodatage():
    messages = [
        {
            "role": "user",
            "content": "Question test",
            "created_at": datetime(2025, 6, 15, 10, 30),
        },
        {
            "role": "assistant",
            "content": "Reponse test",
            "created_at": "2025-06-15 10:31",
        },
    ]
    result = generer_pdf_rapport("projet_ts", messages)
    assert isinstance(result, (bytes, bytearray))
    assert len(result) > 100


def test_generer_pdf_contenu_markdown_nettoye():
    messages = [
        {"role": "assistant", "content": "## Titre\n**Gras** et *italique*\n```python\ncode\n```"},
    ]
    result = generer_pdf_rapport("projet_md", messages)
    assert isinstance(result, (bytes, bytearray))
