"""
Tests pour db_manager.py — Gestionnaire SQLite (SQLAlchemy).
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On redirige la DB vers un fichier temporaire pour les tests
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from db_manager import (
    init_db,
    sauvegarder_message,
    charger_historique,
    supprimer_historique,
    lister_projets,
    enregistrer_port,
    lister_ports,
    enregistrer_outil_forge,
    lister_outils_projet,
)


def setup_module():
    init_db()


def test_sauvegarder_et_charger_historique():
    sauvegarder_message("test_projet_1", "user", "Bonjour BOOMERANG")
    sauvegarder_message("test_projet_1", "assistant", "Bonjour ! Comment puis-je vous aider ?")

    historique = charger_historique("test_projet_1")
    assert len(historique) >= 2
    assert historique[0]["role"] == "user"
    assert historique[0]["content"] == "Bonjour BOOMERANG"
    assert historique[1]["role"] == "assistant"


def test_lister_projets():
    sauvegarder_message("test_projet_2", "user", "Test")
    projets = lister_projets()
    assert "test_projet_1" in projets
    assert "test_projet_2" in projets


def test_supprimer_historique():
    sauvegarder_message("test_suppr", "user", "A supprimer")
    count = supprimer_historique("test_suppr")
    assert count >= 1
    historique = charger_historique("test_suppr")
    assert len(historique) == 0


def test_enregistrer_et_lister_ports():
    enregistrer_port("outil_test", 8099)
    ports = lister_ports()
    assert ports["outil_test"] == 8099


def test_enregistrer_port_update():
    enregistrer_port("outil_test", 8100)
    ports = lister_ports()
    assert ports["outil_test"] == 8100


def test_enregistrer_outil_forge():
    enregistrer_outil_forge("test_projet_1", "tool_calcul", "besoin calcul thermique")
    outils = lister_outils_projet("test_projet_1")
    assert any(o["nom_fichier"] == "tool_calcul" for o in outils)


def test_charger_historique_limite():
    for i in range(60):
        sauvegarder_message("test_limite", "user", f"msg {i}")
    historique = charger_historique("test_limite", limite=10)
    assert len(historique) == 10


def teardown_module():
    os.unlink(_tmp.name)
