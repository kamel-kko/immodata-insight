"""
Tests pour graph_orchestrator.py — Fonctions utilitaires et noeuds.

Note : Les tests qui necessitent un LLM ou une connexion sont mockes.
Seules les fonctions utilitaires pures sont testees directement.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_orchestrator import (
    _modele_supporte_tools,
    _contient_adresse,
    _est_requete_vague,
    _deviner_type_projet,
    _reformuler_requete_experte,
    _detecter_besoin_forge,
    _parse_prompt_based_tool_call,
    TOOL_CAPABLE_MODELS,
)


# ── _modele_supporte_tools ──

def test_modele_llama3_supporte():
    assert _modele_supporte_tools("llama3.2:3b") is True


def test_modele_qwen_supporte():
    assert _modele_supporte_tools("qwen2.5:14b") is True


def test_modele_mistral_supporte():
    assert _modele_supporte_tools("mistral:7b") is True


def test_modele_inconnu_pas_supporte():
    assert _modele_supporte_tools("phi3:mini") is False


def test_modele_casse_insensible():
    assert _modele_supporte_tools("Llama3.1:8B") is True


# ── _contient_adresse ──

def test_adresse_avec_code_postal():
    assert _contient_adresse("12 rue de Rivoli 75001 Paris") is True


def test_adresse_avec_rue():
    assert _contient_adresse("9 rue des Pyrenees") is True


def test_adresse_coordonnees_gps():
    assert _contient_adresse("43.6047, 1.4442") is True


def test_adresse_nom_compose():
    assert _contient_adresse("Saint-Vincent-de-Tyrosse") is True


def test_pas_adresse():
    assert _contient_adresse("Bonjour") is False


# ── _est_requete_vague ──

def test_requete_courte_vague():
    assert _est_requete_vague("PLU Paris") is True


def test_requete_avec_adresse_pas_vague():
    assert _est_requete_vague("12 rue de Rivoli 75001") is False


def test_requete_longue_pas_vague():
    texte = "Je souhaite construire un ERP de type M avec une capacite de 500 personnes sur un terrain de 2000m2"
    assert _est_requete_vague(texte) is False


# ── _deviner_type_projet ──

def test_type_erp():
    assert "ERP" in _deviner_type_projet("construction restaurant 200 places")


def test_type_habitation():
    assert "Habitation" in _deviner_type_projet("construire une maison")


def test_type_renovation():
    assert "Renovation" in _deviner_type_projet("renovation d'un immeuble ancien")


def test_type_extension():
    assert "Extension" in _deviner_type_projet("agrandissement garage")


def test_type_defaut():
    result = _deviner_type_projet("projet quelconque")
    assert "Construction neuve" in result


# ── _reformuler_requete_experte ──

def test_reformulation_contient_plu():
    result = _reformuler_requete_experte("12 rue de Rivoli Paris ERP restaurant")
    assert "PLU" in result
    assert "ERP" in result
    assert "PMR" in result


# ── _detecter_besoin_forge ──

def test_forge_detecte():
    assert _detecter_besoin_forge("je n'ai pas d'outil pour cela") is not None


def test_forge_pas_detecte():
    assert _detecter_besoin_forge("Voici le resultat du PLU") is None


# ── _parse_prompt_based_tool_call ──

def test_parse_appel_outil_valide():
    content = """[APPEL_OUTIL]
outil: recherche_urbanisme
query: 12 rue de Rivoli Paris
[/APPEL_OUTIL]"""
    result = _parse_prompt_based_tool_call(content)
    assert result is not None
    assert result["outil"] == "recherche_urbanisme"
    assert "Rivoli" in result["query"]


def test_parse_pas_appel_outil():
    result = _parse_prompt_based_tool_call("Bonjour, comment puis-je vous aider ?")
    assert result is None
