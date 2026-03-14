# REQUIERT_INTERNET: oui
import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
TOOL_NAME = "recherche_web"
TOOL_DESCRIPTION = (
    "Recherche des informations sur le web via SearXNG. "
    "Utilise pour trouver textes réglementaires, PLU, normes ERP/PMR."
)


class RunInput(BaseModel):
    input: dict  # {"query": "..."}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tool": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "requiert_internet": True,
    }


@app.post("/run")
def run(body: RunInput) -> dict:
    query = body.input.get("query", "")
    searxng_url = os.getenv("SEARXNG_URL", "http://searxng:8080")
    try:
        resp = requests.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json", "language": "fr"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])[:5]
        if not results:
            return {"output": "Aucun résultat trouvé."}
        output = []
        for r in results:
            output.append(
                f"**{r.get('title', 'Sans titre')}**\n"
                f"URL : {r.get('url', '')}\n"
                f"{r.get('content', '')[:300]}"
            )
        return {"output": "\n\n---\n\n".join(output)}
    except Exception as e:
        return {"output": f"Erreur SearXNG : {str(e)}"}
