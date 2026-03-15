# REQUIERT_INTERNET: oui — connexion au serveur MCP pour sources juridiques
import os
import asyncio
import logging
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
logger = logging.getLogger(__name__)

TOOL_NAME = "recherche_legale_et_publique"
TOOL_DESCRIPTION = (
    "Interroge les sources juridiques françaises via un serveur MCP "
    "(Légifrance / Open Legi / data.gouv.fr). "
    "Utiliser cet outil pour les LOIS NATIONALES : Code de la construction et de "
    "l'habitation (CCH), Code de l'urbanisme, arrêtés ERP (25/06/1980, 01/08/2006), "
    "normes PMR (arrêté du 20/04/2017), DTU, décrets et circulaires. "
    "NE PAS utiliser pour les règles locales (PLU, zonage — utiliser recherche_geoportail_urbanisme) "
    "ni pour les risques terrain (inondation, sismicité — utiliser recherche_risques_parcelle). "
    "Entrée : requête en langage naturel (ex: 'Réglementation incendie ERP type M effectif 300'). "
    "Sortie : textes de loi pertinents avec références et extraits."
)

MCP_LEGAL_SERVER_URL = os.getenv("MCP_LEGAL_SERVER_URL", "http://localhost:8000")


class RunInput(BaseModel):
    input: dict  # {"query": "Réglementation incendie ERP type 5"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tool": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "requiert_internet": True,
    }


async def _interroger_mcp(query: str) -> str:
    """Interroge le serveur MCP pour rechercher des textes juridiques.

    Tente la connexion MCP via le protocole standard.
    En cas d'échec, retourne un message d'erreur explicite.

    Args:
        query: Requête en langage naturel.

    Returns:
        Résultat de la recherche ou message d'erreur.
    """
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    except ImportError:
        return (
            "Module MCP non disponible. Installer avec : pip install mcp\n"
            "Le serveur MCP juridique n'est pas accessible."
        )

    try:
        async with sse_client(url=MCP_LEGAL_SERVER_URL) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools] if tools.tools else []

                search_tool = None
                for name in ["search", "recherche", "query", "search_law", "recherche_legale"]:
                    if name in tool_names:
                        search_tool = name
                        break

                if not search_tool and tool_names:
                    search_tool = tool_names[0]

                if not search_tool:
                    return "Serveur MCP connecté mais aucun outil de recherche disponible."

                result = await session.call_tool(search_tool, arguments={"query": query})

                if hasattr(result, "content") and result.content:
                    texts = []
                    for block in result.content:
                        if hasattr(block, "text"):
                            texts.append(block.text)
                    return "\n".join(texts) if texts else "Aucun résultat trouvé."

                return "Aucun résultat retourné par le serveur MCP."

    except ConnectionRefusedError:
        return (
            f"Serveur MCP juridique non accessible ({MCP_LEGAL_SERVER_URL}). "
            "Vérifiez que le serveur MCP est démarré et que MCP_LEGAL_SERVER_URL "
            "est correctement configuré dans le .env."
        )
    except asyncio.TimeoutError:
        return f"Timeout de connexion au serveur MCP ({MCP_LEGAL_SERVER_URL})."
    except Exception as e:
        return (
            f"Erreur de connexion au serveur MCP juridique : {str(e)}\n"
            f"URL tentée : {MCP_LEGAL_SERVER_URL}\n"
            "Vérifiez la configuration MCP_LEGAL_SERVER_URL dans le .env."
        )


@app.post("/run")
def run(body: RunInput) -> dict:
    query = body.input.get("query", "")
    if not query:
        return {"output": "Erreur : paramètre 'query' requis (requête juridique en langage naturel)."}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_interroger_mcp(query))
        loop.close()
    except Exception as e:
        result = f"Erreur inattendue lors de la recherche MCP : {str(e)}"

    return {"output": result}
