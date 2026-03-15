"""
tool_demander_dev.py — Enregistre une demande de developpement pour un outil manquant.

Cet outil est appele par l'agent quand il detecte qu'une analyse technique
necessite un outil qui n'existe pas encore (thermique, surface, structure, etc.).
Les demandes sont stockees dans data/dev_requests.json.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import portalocker

DEV_REQUESTS_FILE = Path("/app/data/dev_requests.json")


def _charger_demandes() -> list[dict]:
    if DEV_REQUESTS_FILE.exists():
        try:
            with open(DEV_REQUESTS_FILE, "r", encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                data = json.load(f)
                portalocker.unlock(f)
                return data
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _sauvegarder_demandes(demandes: list[dict]) -> None:
    DEV_REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DEV_REQUESTS_FILE, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(demandes, f, ensure_ascii=False, indent=2)
        portalocker.unlock(f)


def tool_demander_dev(outil_manquant: str, description_fonctionnelle: str) -> dict:
    """
    Enregistre une demande de developpement pour un outil manquant.
    Ecrit dans data/dev_requests.json (cree si inexistant).
    Retourne un message de confirmation a afficher a l'utilisateur.
    """
    demandes = _charger_demandes()

    nouvelle_demande = {
        "outil_manquant": outil_manquant,
        "description_fonctionnelle": description_fonctionnelle,
        "date_demande": datetime.now().isoformat(),
        "statut": "en_attente",
    }

    demandes.append(nouvelle_demande)
    _sauvegarder_demandes(demandes)

    return {
        "output": (
            f"Demande de developpement enregistree pour l'outil '{outil_manquant}'.\n"
            f"Description : {description_fonctionnelle}\n"
            f"Statut : en attente de developpement.\n"
            f"Total demandes en cours : {len([d for d in demandes if d['statut'] == 'en_attente'])}"
        )
    }
