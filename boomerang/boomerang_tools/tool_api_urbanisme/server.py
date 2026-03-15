# REQUIERT_INTERNET: oui — appelle les APIs publiques BAN et Géoportail de l'Urbanisme
import os
import sys
import re
import logging
import requests
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Importer le cache si disponible (en container, PYTHONPATH=/app)
try:
    from db_manager import get_cache, set_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

app = FastAPI()
TOOL_NAME = "recherche_geoportail_urbanisme"
TOOL_DESCRIPTION = (
    "Interroge l'API publique du Géoportail de l'Urbanisme (GPU) pour obtenir "
    "le zonage PLU d'une parcelle à partir de coordonnées GPS ou d'une adresse. "
    "Utiliser cet outil UNIQUEMENT pour les règles d'urbanisme LOCALES : "
    "zonage PLU (UA, UB, N, A...), COS, règles de hauteur spécifiques à une commune, "
    "emprise au sol, reculs, etc. "
    "NE PAS utiliser pour les lois nationales (Code de la construction, arrêtés ERP) "
    "ni pour les risques naturels (inondation, sismicité). "
    "Entrée : coordonnées 'lat,lon' (ex: '43.6047,1.4442') ou adresse textuelle "
    "(ex: '12 rue de Rivoli Paris'). "
    "Sortie : zone PLU, libellé, références réglementaires applicables."
)

BAN_URL = "https://api-adresse.data.gouv.fr/search/"
GPU_URL = "https://apicarto.ign.fr/api/gpu/zone-urba"


class RunInput(BaseModel):
    input: dict  # {"query": "43.6047,1.4442"} ou {"query": "12 rue de Rivoli Paris"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tool": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "requiert_internet": True,
    }


def _geocoder_adresse(adresse: str) -> tuple[float, float]:
    """Convertit une adresse textuelle en coordonnées (lat, lon) via l'API BAN."""
    resp = requests.get(BAN_URL, params={"q": adresse, "limit": 1}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    if not features:
        raise ValueError(f"Adresse introuvable via l'API BAN : '{adresse}'")
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    props = features[0]["properties"]
    label = props.get("label", adresse)
    return coords[1], coords[0], label  # lat, lon, label


def _parser_coordonnees(query: str) -> tuple[float, float, str]:
    """Détecte si query est 'lat,lon' ou une adresse, retourne (lat, lon, label)."""
    match = re.match(r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$", query)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Coordonnées hors limites : lat={lat}, lon={lon}")
        return lat, lon, f"{lat},{lon}"
    return _geocoder_adresse(query)


def _interroger_gpu(lat: float, lon: float) -> list[dict]:
    """Interroge l'API Carto GPU avec un point GeoJSON."""
    geom = {"type": "Point", "coordinates": [lon, lat]}
    resp = requests.get(
        GPU_URL,
        params={"geom": str(geom).replace("'", '"')},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", [])


def generer_url_carte_wms(lat: float, lon: float, zoom: int = 17) -> str:
    """Construit l'URL WMS Geoportail pour une carte cadastrale centree sur lat/lon."""
    bbox = f"{lon - 0.002},{lat - 0.002},{lon + 0.002},{lat + 0.002}"
    return (
        "https://wxs.ign.fr/geoportail/geoscroll/wms?"
        "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
        "&LAYERS=CADASTRALPARCELS.PARCELLAIRE_EXPRESS"
        f"&CRS=CRS:84&BBOX={bbox}"
        "&WIDTH=600&HEIGHT=400&FORMAT=image/png"
    )


CACHE_TTL_JOURS = int(os.getenv("CACHE_TTL_JOURS", "7"))


def _cache_key_from_coords(lat: float, lon: float) -> str:
    """Genere une cle de cache a partir de coordonnees arrondies.

    On arrondit a 3 decimales (~111m) car le PLU couvre des zones entieres.
    Deux adresses dans la meme rue auront la meme cle = meme resultat PLU.
    """
    return f"{round(lat, 3)},{round(lon, 3)}"


@app.post("/run")
def run(body: RunInput) -> dict:
    query = body.input.get("query", "")
    force_refresh = body.input.get("force_refresh", False)
    if not query:
        return {"output": "Erreur : paramètre 'query' requis (adresse ou coordonnées lat,lon)."}

    try:
        lat, lon, label = _parser_coordonnees(query)
    except ValueError as e:
        return {"output": str(e)}
    except Exception as e:
        return {"output": f"Erreur géocodage : {str(e)}"}

    # Verifier le cache avant d'appeler l'API
    cache_id = _cache_key_from_coords(lat, lon)
    if CACHE_AVAILABLE and not force_refresh:
        cached = get_cache("recherche_urbanisme", cache_id)
        if cached:
            logger.info(f"[CACHE HIT] recherche_urbanisme pour {cache_id}")
            return {"output": cached, "_cached": True}

    try:
        features = _interroger_gpu(lat, lon)
    except requests.exceptions.Timeout:
        return {"output": "Erreur : l'API Géoportail de l'Urbanisme n'a pas répondu (timeout 15s)."}
    except requests.exceptions.HTTPError as e:
        return {"output": f"Erreur API GPU (HTTP {e.response.status_code}) : {str(e)}"}
    except Exception as e:
        return {"output": f"Erreur API Géoportail de l'Urbanisme : {str(e)}"}

    if not features:
        return {"output": f"Aucun zonage PLU trouvé pour '{label}' ({lat}, {lon}). "
                          "La commune n'a peut-être pas de PLU numérisé sur le GPU."}

    output_parts = [f"ZONAGE PLU — {label} ({lat}, {lon})\n"]
    for f in features[:5]:
        props = f.get("properties", {})
        zone = props.get("libelle", props.get("typezone", "Inconnu"))
        type_zone = props.get("typezone", "")
        libelong = props.get("libelong", "")
        destdomi = props.get("destdomi", "")
        nomfic = props.get("nomfic", "")

        output_parts.append(
            f"Zone : {type_zone} — {zone}\n"
            f"  Libellé complet : {libelong if libelong else 'Non renseigné'}\n"
            f"  Destination dominante : {destdomi if destdomi else 'Non renseignée'}\n"
            f"  Document : {nomfic if nomfic else 'Non renseigné'}"
        )

    output_parts.append(
        "\nSource : Géoportail de l'Urbanisme (gpu.developpement-durable.gouv.fr)"
    )

    # Ajouter l'URL de la carte cadastrale WMS
    carte_url = generer_url_carte_wms(lat, lon)
    output_parts.append(f"\nMAP_URL:{carte_url}")

    result_text = "\n\n".join(output_parts)

    # Sauvegarder en cache pour les prochaines requetes
    if CACHE_AVAILABLE:
        try:
            set_cache("recherche_urbanisme", cache_id, result_text, CACHE_TTL_JOURS)
            logger.info(f"[CACHE SET] recherche_urbanisme pour {cache_id} (TTL {CACHE_TTL_JOURS}j)")
        except Exception as e:
            logger.warning(f"[CACHE] Erreur ecriture cache: {e}")

    return {"output": result_text}
