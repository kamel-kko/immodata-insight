"""
plu_fetcher.py -- Geocodage, recherche PLU GPU, telechargement avec cache.

Pipeline : adresse -> BAN (geocodage) -> GPU (infos PLU) -> telechargement ZIP -> extraction PDFs
Toutes les APIs sont publiques et gratuites, zero cle d'API requise.
"""

import os
import re
import json
import time
import zipfile
import logging
import requests

logger = logging.getLogger(__name__)

BAN_URL = "https://api-adresse.data.gouv.fr/search/"
GPU_APICARTO_DOC = "https://apicarto.ign.fr/api/gpu/document"
GPU_APICARTO_ZONE = "https://apicarto.ign.fr/api/gpu/zone-urba"
GPU_DETAILS = "https://www.geoportail-urbanisme.gouv.fr/api/document/{doc_id}/details"
CACHE_DIR = os.environ.get("PLU_CACHE_DIR", "/app/data/plu_cache")
CACHE_TTL_JOURS = 30


# ── 1A — Geocodage via API BAN ──────────────────────────

def geocoder_adresse(adresse: str) -> dict:
    """Geocode une adresse via l'API BAN (Base Adresse Nationale).

    Retourne un dict avec : code_insee, commune, departement, longitude,
    latitude, adresse_normalisee, score_confiance.
    Leve ValueError si le score est trop bas (adresse ambigue).
    """
    resp = requests.get(BAN_URL, params={"q": adresse, "limit": 1}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        raise ValueError(f"Adresse introuvable : '{adresse}'")

    props = features[0]["properties"]
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    score = props.get("score", 0)

    if score < 0.5:
        raise ValueError(
            f"Adresse ambigue (score={score:.2f}). "
            "Precisez : numero, rue, commune, code postal."
        )

    code_insee = props.get("citycode", "")
    return {
        "code_insee": code_insee,
        "commune": props.get("city", ""),
        "departement": code_insee[:2] if code_insee else "",
        "longitude": coords[0],
        "latitude": coords[1],
        "adresse_normalisee": props.get("label", adresse),
        "score_confiance": round(score, 3),
    }


# ── 1B — Recherche PLU sur le GPU ───────────────────────

def rechercher_plu_gpu(code_insee: str) -> dict:
    """Interroge le Geoportail de l'Urbanisme pour trouver le PLU d'une commune.

    Retourne un dict avec : nom_commune, type_document, date_approbation,
    gpu_doc_id, archive_url, fichiers_pdf[], statut.
    """
    partition = f"DU_{code_insee}"

    # Etape 1 : chercher le document via APICarto
    try:
        resp = requests.get(
            GPU_APICARTO_DOC,
            params={"partition": partition},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"statut": "erreur_gpu", "message": str(e)}

    features = data.get("features", [])
    if not features:
        return {
            "statut": "commune_rnu",
            "message": (
                f"Commune {code_insee} : aucun document d'urbanisme sur le GPU. "
                "Cette commune est probablement soumise au RNU (Reglement National "
                "d'Urbanisme). Contacter la prefecture."
            ),
        }

    # Prendre le document le plus recent en production
    doc = None
    for f in features:
        props = f["properties"]
        if props.get("gpu_status") == "production":
            doc = props
            break
    if not doc:
        doc = features[0]["properties"]

    gpu_doc_id = doc.get("gpu_doc_id", "")

    # Etape 2 : obtenir les details (fichiers, archive URL)
    fichiers = []
    archive_url = ""
    titre = ""
    date_appro = ""

    if gpu_doc_id:
        try:
            resp2 = requests.get(
                GPU_DETAILS.format(doc_id=gpu_doc_id),
                timeout=15,
            )
            resp2.raise_for_status()
            details = resp2.json()
            fichiers = details.get("files", [])
            archive_url = details.get("archiveUrl", "")
            titre = details.get("title", "")
            date_appro = details.get("statusDate", "")
        except Exception as e:
            logger.warning(f"Impossible de recuperer les details GPU : {e}")

    return {
        "statut": "trouve",
        "nom_commune": doc.get("grid_title", ""),
        "type_document": doc.get("du_type", ""),
        "nom_document": doc.get("name", ""),
        "date_approbation": date_appro,
        "titre": titre,
        "gpu_doc_id": gpu_doc_id,
        "archive_url": archive_url,
        "fichiers_pdf": [f for f in fichiers if f.endswith(".pdf")],
    }


# ── 1C — Telechargement avec cache ──────────────────────

def _cache_valide(cache_dir: str) -> bool:
    """Verifie si le cache existe et n'a pas expire (30 jours)."""
    meta_path = os.path.join(cache_dir, "metadata.json")
    if not os.path.exists(meta_path):
        return False
    try:
        with open(meta_path, "r") as f:
            meta = json.load(f)
        ts = meta.get("timestamp", 0)
        age_jours = (time.time() - ts) / 86400
        return age_jours < CACHE_TTL_JOURS
    except Exception:
        return False


def _detecter_ocr(chemin_pdf: str) -> bool:
    """Detecte si un PDF necessite de l'OCR (moins de 100 chars sur page 1)."""
    try:
        import fitz
        doc = fitz.open(chemin_pdf)
        if doc.page_count == 0:
            return True
        text = doc[0].get_text()
        doc.close()
        return len(text.strip()) < 100
    except Exception:
        return False


def telecharger_plu(infos_plu: dict, code_insee: str) -> dict:
    """Telecharge les PDFs du PLU dans un cache local.

    Retourne un dict avec : code_insee, chemin_cache, fichiers[],
    depuis_cache, avertissement_ocr.
    """
    cache_dir = os.path.join(CACHE_DIR, code_insee)
    result = {
        "code_insee": code_insee,
        "chemin_cache": cache_dir,
        "fichiers": [],
        "depuis_cache": False,
        "avertissement_ocr": False,
    }

    # Verifier le cache
    if _cache_valide(cache_dir):
        meta_path = os.path.join(cache_dir, "metadata.json")
        with open(meta_path, "r") as f:
            meta = json.load(f)
        result["fichiers"] = meta.get("fichiers", [])
        result["depuis_cache"] = True
        return result

    # Creer le dossier de cache
    os.makedirs(cache_dir, exist_ok=True)

    archive_url = infos_plu.get("archive_url", "")
    if not archive_url:
        result["fichiers"] = []
        return result

    # Telecharger le ZIP
    zip_path = os.path.join(cache_dir, "plu.zip")
    try:
        resp = requests.get(archive_url, timeout=60, stream=True, allow_redirects=True)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        logger.error(f"Telechargement PLU echoue : {e}")
        return result

    # Extraire les PDFs du ZIP
    fichiers_info = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.lower().endswith(".pdf"):
                    zf.extract(name, cache_dir)
                    chemin = os.path.join(cache_dir, name)
                    taille_mo = round(os.path.getsize(chemin) / 1024 / 1024, 2)
                    needs_ocr = _detecter_ocr(chemin)

                    # Determiner le type de document
                    name_lower = name.lower()
                    if "reglement" in name_lower and "graphique" not in name_lower:
                        doc_type = "reglement"
                    elif "padd" in name_lower:
                        doc_type = "padd"
                    elif "rapport" in name_lower:
                        doc_type = "rapport"
                    elif "annexe" in name_lower or "ann_" in name_lower:
                        doc_type = "annexe"
                    elif "orientations" in name_lower or "oap" in name_lower:
                        doc_type = "oap"
                    else:
                        doc_type = "autre"

                    finfo = {
                        "nom": name,
                        "chemin": chemin,
                        "taille_mo": taille_mo,
                        "needs_ocr": needs_ocr,
                        "type": doc_type,
                    }

                    # Compter les pages
                    try:
                        import fitz
                        doc = fitz.open(chemin)
                        finfo["pages"] = doc.page_count
                        doc.close()
                    except Exception:
                        finfo["pages"] = 0

                    fichiers_info.append(finfo)

                    if needs_ocr:
                        result["avertissement_ocr"] = True

    except zipfile.BadZipFile:
        logger.error("Fichier ZIP invalide")
        return result
    finally:
        # Nettoyer le ZIP
        if os.path.exists(zip_path):
            os.remove(zip_path)

    result["fichiers"] = fichiers_info

    # Sauvegarder les metadonnees du cache
    meta = {
        "code_insee": code_insee,
        "timestamp": time.time(),
        "fichiers": fichiers_info,
    }
    with open(os.path.join(cache_dir, "metadata.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return result
