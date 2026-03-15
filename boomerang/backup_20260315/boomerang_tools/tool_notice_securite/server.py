from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
TOOL_NAME = "notice_securite_erp"
TOOL_DESCRIPTION = (
    "Génère une notice de sécurité incendie ERP selon la réglementation française. "
    "Paramètres : type_erp (str), capacite (int), description (str)."
)


class RunInput(BaseModel):
    input: dict  # {"type_erp": "M", "capacite": 300, "description": "..."}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tool": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "requiert_internet": False,
    }


@app.post("/run")
def run(body: RunInput) -> dict:
    p = body.input
    type_erp = str(p.get("type_erp", "N")).upper().strip()
    if not type_erp or len(type_erp) > 5:
        return {"output": "Erreur : type_erp invalide (attendu : M, L, N, O, R, W, etc.)"}

    try:
        capacite = int(p.get("capacite", 100))
    except (ValueError, TypeError):
        return {"output": "Erreur : capacite doit etre un nombre entier."}
    if capacite < 1 or capacite > 100000:
        return {"output": f"Erreur : capacite hors limites (1-100000). Recu : {capacite}"}

    description = str(p.get("description", ""))[:2000]

    if capacite > 1500:   cat_label = "1ère catégorie (>1500 pers.)"
    elif capacite > 700:  cat_label = "2ème catégorie (701-1500 pers.)"
    elif capacite > 300:  cat_label = "3ème catégorie (301-700 pers.)"
    elif capacite > 200:  cat_label = "4ème catégorie (201-300 pers.)"
    else:                 cat_label = "5ème catégorie (≤200 pers.)"
    cat = 1 if capacite > 1500 else 2 if capacite > 700 else 3 if capacite > 300 else 4 if capacite > 200 else 5

    notice = f"""NOTICE DE SÉCURITÉ INCENDIE — ERP
Type : {type_erp.upper()} — {cat_label} | Capacité : {capacite} pers.
Description : {description}

1. DÉGAGEMENTS
   • Sorties min. : {max(2, capacite // 500 + 1)}
   • Largeur min. : {2 if capacite > 500 else 1} UP (1 UP = 0,60 m)

2. ALARME — SSI : {'Catégorie A' if cat <= 2 else 'Catégorie E minimum'}

3. ÉCLAIRAGE — BAES obligatoires, autonomie 1h, ≥45 lm

4. EXTINCTION — 1 extincteur / 200 m²
   RIA : {'Obligatoires' if cat <= 3 else 'Selon avis commission'}

Réf. : Arrêté 25/06/1980 — Art. R.123-1 à R.123-55 CCH
⚠️ Notice indicative — validation par commission de sécurité obligatoire."""
    return {"output": notice}
