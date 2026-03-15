# REQUIERT_INTERNET: oui — appelle les APIs publiques BAN et Géorisques (BRGM)
import os
import re
import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
TOOL_NAME = "recherche_risques_parcelle"
TOOL_DESCRIPTION = (
    "Identifie les risques naturels et technologiques d'une adresse ou parcelle "
    "via l'API publique Géorisques du BRGM. "
    "Utiliser cet outil AVANT ou PENDANT l'instruction d'un permis de construire "
    "pour alerter sur des contraintes terrain : inondabilité (PPRI), sismicité, "
    "retrait-gonflement des argiles, aléa radon, cavités souterraines, installations SEVESO. "
    "NE PAS utiliser pour les règles d'urbanisme locales (PLU, zonage) ni pour les "
    "textes de loi nationaux (Code de la construction, arrêtés ERP). "
    "Entrée : coordonnées 'lat,lon' (ex: '43.6047,1.4442') ou adresse textuelle. "
    "Sortie : liste des risques détectés avec type, niveau et source réglementaire."
)

BAN_URL = "https://api-adresse.data.gouv.fr/search/"
GEORISQUES_URL = "https://georisques.gouv.fr/api/v1"


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


def _geocoder_adresse(adresse: str) -> tuple[float, float, str]:
    """Convertit une adresse en coordonnées (lat, lon) via l'API BAN."""
    resp = requests.get(BAN_URL, params={"q": adresse, "limit": 1}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    if not features:
        raise ValueError(f"Adresse introuvable via l'API BAN : '{adresse}'")
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    label = features[0]["properties"].get("label", adresse)
    return coords[1], coords[0], label


def _parser_coordonnees(query: str) -> tuple[float, float, str]:
    """Détecte si query est 'lat,lon' ou une adresse."""
    match = re.match(r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$", query)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        return lat, lon, f"{lat},{lon}"
    return _geocoder_adresse(query)


def _get_code_insee(lat: float, lon: float) -> str:
    """Récupère le code INSEE de la commune via l'API BAN (reverse geocoding)."""
    resp = requests.get(
        "https://api-adresse.data.gouv.fr/reverse/",
        params={"lat": lat, "lon": lon},
        timeout=10,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if features:
        return features[0]["properties"].get("citycode", "")
    return ""


def _risques_commune(code_insee: str) -> list[dict]:
    """Interroge Géorisques pour les risques d'une commune."""
    resp = requests.get(
        f"{GEORISQUES_URL}/gaspar/risques",
        params={"code_insee": code_insee, "page": 1, "page_size": 50},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def _risques_radon(code_insee: str) -> dict:
    """Interroge le potentiel radon d'une commune."""
    try:
        resp = requests.get(
            f"{GEORISQUES_URL}/radon",
            params={"code_insee": code_insee, "page": 1, "page_size": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0]
    except Exception:
        pass
    return {}


def _risques_argiles(lat: float, lon: float) -> dict:
    """Interroge l'aléa retrait-gonflement des argiles."""
    try:
        resp = requests.get(
            f"{GEORISQUES_URL}/mvt",
            params={"latlon": f"{lat},{lon}", "page": 1, "page_size": 5},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return {"mouvements_terrain": len(data), "details": data[:3]}
    except Exception:
        pass
    return {}


@app.post("/run")
def run(body: RunInput) -> dict:
    query = body.input.get("query", "")
    if not query:
        return {"output": "Erreur : paramètre 'query' requis (adresse ou coordonnées lat,lon)."}

    try:
        lat, lon, label = _parser_coordonnees(query)
    except ValueError as e:
        return {"output": str(e)}
    except Exception as e:
        return {"output": f"Erreur géocodage : {str(e)}"}

    try:
        code_insee = _get_code_insee(lat, lon)
    except Exception as e:
        return {"output": f"Erreur récupération code INSEE : {str(e)}"}

    if not code_insee:
        return {"output": f"Impossible de trouver le code INSEE pour '{label}' ({lat}, {lon})."}

    output_parts = [f"RISQUES NATURELS ET TECHNOLOGIQUES — {label} (INSEE: {code_insee})\n"]

    # Risques GASPAR (base principale)
    try:
        risques = _risques_commune(code_insee)
        if risques:
            output_parts.append("RISQUES IDENTIFIÉS (base GASPAR) :")
            for r in risques:
                lib = r.get("libelle_risque_long", r.get("libelle_risque_jo", "Inconnu"))
                num = r.get("num_risque", "")
                output_parts.append(f"  - {lib} (code: {num})")
        else:
            output_parts.append("Aucun risque GASPAR répertorié pour cette commune.")
    except requests.exceptions.Timeout:
        output_parts.append("API Géorisques GASPAR : timeout (15s).")
    except Exception as e:
        output_parts.append(f"Erreur API GASPAR : {str(e)}")

    # Radon
    radon = _risques_radon(code_insee)
    if radon:
        classe = radon.get("classe_potentiel", "Non renseigné")
        output_parts.append(f"\nPOTENTIEL RADON : classe {classe}/3")
        if str(classe) == "3":
            output_parts.append("  Zone à potentiel radon significatif — mesures obligatoires (arrêté 27/06/2018)")

    # Mouvements de terrain / argiles
    argiles = _risques_argiles(lat, lon)
    if argiles.get("mouvements_terrain"):
        output_parts.append(f"\nMOUVEMENTS DE TERRAIN : {argiles['mouvements_terrain']} événement(s) recensé(s)")

    output_parts.append(
        "\nSource : georisques.gouv.fr (BRGM / Ministère de la Transition écologique)"
    )
    return {"output": "\n".join(output_parts)}
