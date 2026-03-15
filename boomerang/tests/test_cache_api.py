"""
Tests pour le cache API (db_manager.py).

Verifie que get_cache/set_cache/purge_cache fonctionnent correctement
avec la table CacheAPI.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Rediriger la DB vers un fichier temporaire
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from db_manager import (
    init_db,
    get_cache,
    set_cache,
    purge_cache,
    stats_cache,
    _make_cache_key,
)


def setup_module():
    init_db()


def test_make_cache_key_deterministe():
    k1 = _make_cache_key("recherche_urbanisme", "75056")
    k2 = _make_cache_key("recherche_urbanisme", "75056")
    assert k1 == k2
    assert len(k1) == 64


def test_make_cache_key_different_tools():
    k1 = _make_cache_key("recherche_urbanisme", "75056")
    k2 = _make_cache_key("recherche_risques_parcelle", "75056")
    assert k1 != k2


def test_set_et_get_cache():
    set_cache("test_tool", "commune_123", "Resultat PLU zone UA", ttl_jours=7)
    result = get_cache("test_tool", "commune_123")
    assert result == "Resultat PLU zone UA"


def test_get_cache_absent():
    result = get_cache("test_tool", "commune_inexistante")
    assert result is None


def test_set_cache_update():
    set_cache("test_tool", "commune_update", "Version 1", ttl_jours=7)
    set_cache("test_tool", "commune_update", "Version 2", ttl_jours=7)
    result = get_cache("test_tool", "commune_update")
    assert result == "Version 2"


def test_cache_expire():
    # Creer une entree avec TTL=0 (expiree immediatement)
    set_cache("test_tool", "commune_expiree", "Ancien resultat", ttl_jours=0)
    result = get_cache("test_tool", "commune_expiree")
    # TTL=0 signifie expires_at = maintenant, donc devrait etre None
    # (la comparaison est > now, pas >=)
    assert result is None


def test_purge_cache_expirees():
    set_cache("test_purge", "a", "data", ttl_jours=0)
    set_cache("test_purge", "b", "data", ttl_jours=0)
    set_cache("test_purge", "c", "data", ttl_jours=30)
    count = purge_cache()  # Purge les expirees
    assert count >= 2


def test_purge_cache_par_outil():
    set_cache("outil_a", "x", "data", ttl_jours=30)
    set_cache("outil_b", "y", "data", ttl_jours=30)
    count = purge_cache("outil_a")  # Purge tout pour outil_a
    assert count >= 1
    # outil_b devrait encore etre la
    result = get_cache("outil_b", "y")
    assert result == "data"


def test_stats_cache():
    # Reinitialiser
    purge_cache("stats_test")
    set_cache("stats_test", "s1", "data", ttl_jours=30)
    set_cache("stats_test", "s2", "data", ttl_jours=30)
    stats = stats_cache()
    assert stats["actifs"] >= 2
    assert isinstance(stats["total"], int)
    assert isinstance(stats["expires"], int)


def teardown_module():
    os.unlink(_tmp.name)
