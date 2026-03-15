"""
graph_orchestrator.py — Coeur LangGraph de BOOMERANG

StateGraph avec 3 noeuds :
  - agent_node   : LLM Ollama/Together + outils boomerang_tools/
  - forge_node   : Détecte le besoin de forge, retourne statut spécial
  - hitl_node    : Point d'interruption (interrupt_before) — géré par Streamlit

Mémoire : SqliteSaver sur /app/data/langgraph.db
Observabilité : CallbackHandler Langfuse passé dans config["callbacks"]
"""

import os
import sqlite3
import logging
from typing import Annotated, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from langfuse.langchain import CallbackHandler

from tool_runner import charger_outils

load_dotenv()

# Garantir que le dossier de persistance SQLite existe
os.makedirs("/app/data", exist_ok=True)

logger = logging.getLogger(__name__)

# Modeles connus pour supporter nativement le tool calling Ollama.
# Les autres basculeront en mode "prompt-based" (instructions textuelles).
TOOL_CAPABLE_MODELS = [
    "llama3", "llama3.1", "llama3.2", "llama3.3",
    "qwen", "qwen2", "qwen2.5", "qwen3",
    "mistral", "mixtral", "mistral-small", "mistral-large",
    "gemma", "gemma2", "gemma3",
    "command-r", "command-r-plus",
    "firefunction",
    "hermes", "nous-hermes",
    "deepseek-v2", "deepseek-v3",
]


def _modele_supporte_tools(model_name: str) -> bool:
    """Verifie si le modele Ollama supporte le tool calling natif."""
    model_lower = model_name.lower().split(":")[0]
    for capable in TOOL_CAPABLE_MODELS:
        if capable in model_lower:
            return True
    return False


# ── Sélection LLM ──────────────────────────────────────

def get_llm(model_name: str = ""):
    """Retourne le LLM configuré selon LLM_PROVIDER.

    Args:
        model_name: Nom du modèle à utiliser (prioritaire sur .env).
                    Si vide, utilise OLLAMA_MODEL / TOGETHER_MODEL du .env.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            model=model_name or os.getenv("OLLAMA_MODEL", "llama3.2"),
        )
    elif provider == "together":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY", ""),
            model=model_name or os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
        )
    else:
        raise ValueError(f"LLM_PROVIDER inconnu : {provider}")


# ── Langfuse ────────────────────────────────────────────

def get_langfuse_handler() -> CallbackHandler:
    # Langfuse v4 : le constructeur ne prend plus public_key/secret_key/host.
    # Ces valeurs sont lues automatiquement depuis les variables d'environnement
    # LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST (définies dans .env).
    return CallbackHandler()


# ── State ───────────────────────────────────────────────

class AgentState(dict):
    messages: Annotated[list, add_messages]
    besoin_forge: Optional[str]
    code_temp: Optional[str]
    nom_outil_temp: Optional[str]


# ── Détection de besoin de forge ────────────────────────

FORGE_KEYWORDS = [
    "je n'ai pas d'outil pour",
    "outil manquant",
    "il me faudrait un outil",
    "je ne peux pas",
    "aucun outil disponible",
    "pas d'outil adapté",
    "impossible sans outil",
    "tool not found",
    "no tool available",
]


def _detecter_besoin_forge(contenu: str) -> Optional[str]:
    contenu_lower = contenu.lower()
    for kw in FORGE_KEYWORDS:
        if kw in contenu_lower:
            return contenu
    return None


# ── System prompt ──────────────────────────────────────

SYSTEM_PROMPT = """Tu es BOOMERANG, un assistant expert en reglementation francaise pour architectes.
Tu aides les architectes avec la conformite PLU, ERP, PMR et les risques naturels.

REGLES DE COMPORTEMENT :
1. Reponds TOUJOURS en francais.
2. Si l'utilisateur donne une adresse (rue, ville, code postal), utilise-la directement
   comme parametre 'query' de l'outil approprie. L'outil sait geocoder les adresses.
3. Si la demande est ambigue ou incomplete, pose UNE question de clarification precise.
   Exemple : "Confirmez-vous l'adresse : 9 Rue des Pyrenees, 40230 Saint-Vincent-de-Tyrosse ?"
4. Ne montre JAMAIS de messages d'erreur techniques a l'utilisateur.
   Si un outil echoue, reformule en langage simple et propose une alternative.
5. Quand tu appelles un outil, fournis TOUJOURS le parametre 'query' avec une valeur concrete.
   Ne laisse jamais un parametre requis vide.

OUTILS DISPONIBLES ET QUAND LES UTILISER :
- recherche_urbanisme : pour les regles locales (PLU, zonage, COS, hauteur, emprise)
  → Passer l'adresse complete ou les coordonnees GPS en query
- recherche_risques_parcelle : pour les risques naturels (inondation, sismicite, radon, argiles)
  → Passer l'adresse complete ou les coordonnees GPS en query
- recherche_web : pour chercher des informations generales, textes reglementaires, normes
  → Passer la requete de recherche en query
- recherche_legale : pour les lois nationales (CCH, Code urbanisme, arretes ERP, normes PMR)
  → Passer la question juridique en query
- notice_securite : pour generer une notice de securite incendie ERP
  → Passer type_erp, capacite, description

PROCESSUS POUR UNE FICHE DE SYNTHESE :
Quand l'utilisateur demande une fiche de synthese ou un rapport pour une adresse :
1. Appelle recherche_urbanisme avec l'adresse pour obtenir le zonage PLU
2. Appelle recherche_risques_parcelle avec l'adresse pour les risques
3. Si besoin, appelle recherche_web pour des informations complementaires
4. Synthetise les resultats dans un rapport structure et lisible

IMPORTANT : Utilise les outils de facon proactive. Si l'utilisateur donne une adresse
et demande des informations urbanistiques, appelle l'outil IMMEDIATEMENT sans demander
de reformuler. L'adresse fournie par l'utilisateur est suffisante."""


# ── Prompt-based tool instructions ─────────────────────
# Quand le modele ne supporte pas bind_tools(), on injecte les outils
# comme instructions textuelles dans le system prompt.

PROMPT_BASED_TOOLS_ADDENDUM = """

IMPORTANT — MODE SANS TOOL CALLING :
Le modele actuel ne supporte pas l'appel d'outils natif.
Tu ne peux PAS appeler les outils directement.
A la place, quand tu as besoin d'un outil, reponds EXACTEMENT dans ce format :

[APPEL_OUTIL]
outil: nom_de_l_outil
query: la requete ou l'adresse
[/APPEL_OUTIL]

Exemple :
[APPEL_OUTIL]
outil: recherche_urbanisme
query: 9 Rue des Pyrenees, 40230 Saint-Vincent-de-Tyrosse
[/APPEL_OUTIL]

Le systeme executera l'outil et te renverra le resultat.
N'invente JAMAIS de resultats. Utilise toujours le format ci-dessus."""


def _parse_prompt_based_tool_call(content: str) -> Optional[dict]:
    """Parse un appel d'outil au format texte [APPEL_OUTIL]...[/APPEL_OUTIL]."""
    import re
    match = re.search(
        r'\[APPEL_OUTIL\]\s*outil:\s*(.+?)\s*query:\s*(.+?)\s*\[/APPEL_OUTIL\]',
        content, re.DOTALL
    )
    if match:
        return {"outil": match.group(1).strip(), "query": match.group(2).strip()}
    return None


def _executer_outil_manuellement(nom_outil: str, query: str) -> str:
    """Execute un outil via HTTP en mode prompt-based (sans tool calling natif)."""
    import requests as req
    from tool_runner import TOOL_REGISTRY
    url = TOOL_REGISTRY.get(nom_outil, "")
    if not url:
        return f"Outil '{nom_outil}' introuvable. Outils disponibles : {', '.join(TOOL_REGISTRY.keys())}"
    try:
        resp = req.post(f"{url}/run", json={"input": {"query": query}}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("output", "Pas de resultat.")
    except Exception as e:
        return f"Erreur lors de l'appel a l'outil {nom_outil} : {str(e)}"


# ── Noeuds du graphe ────────────────────────────────────

def agent_node(state: dict, config: RunnableConfig) -> dict:
    from langchain_core.messages import SystemMessage

    messages = state.get("messages", [])
    outils = charger_outils()
    tool_retries = state.get("_tool_retries", 0)

    # Recuperer le modele depuis la config (passee par app.py via le selectbox)
    model_name = config.get("configurable", {}).get("model_name", "")
    llm = get_llm(model_name=model_name)

    # Determiner si le modele supporte le tool calling natif
    use_native_tools = _modele_supporte_tools(model_name) if model_name else True

    # Apres 2 echecs d'outils, forcer le mode sans outils
    if tool_retries >= 2:
        use_native_tools = False
        outils = []
        logger.warning(f"Fallback: desactivation des outils apres {tool_retries} echecs")

    # Binding d'outils ou mode prompt-based
    if outils and use_native_tools:
        try:
            llm_with_tools = llm.bind_tools(outils)
        except Exception as e:
            logger.warning(f"bind_tools echoue pour {model_name}: {e}. Bascule en mode prompt-based.")
            llm_with_tools = llm
            use_native_tools = False
    else:
        llm_with_tools = llm

    # Construire le system prompt
    sys_content = SYSTEM_PROMPT
    if outils and not use_native_tools:
        sys_content += PROMPT_BASED_TOOLS_ADDENDUM
    if tool_retries >= 2:
        sys_content += (
            "\n\nATTENTION : Les outils ont echoue plusieurs fois. "
            "Reponds uniquement avec tes connaissances internes. "
            "Ne tente plus d'appeler d'outils."
        )

    # Injecter le system prompt si absent ou le mettre a jour
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=sys_content)] + list(messages)
    else:
        messages = [SystemMessage(content=sys_content)] + list(messages[1:])

    # Appel LLM avec gestion d'erreur
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Erreur LLM invoke ({model_name}): {e}")

        if "tool" in error_str or "function" in error_str or "format" in error_str:
            # Erreur liee aux outils -> retry sans outils
            logger.warning(f"Retry sans outils pour {model_name}")
            try:
                response = llm.invoke(messages)
            except Exception as e2:
                logger.error(f"Retry sans outils echoue: {e2}")
                response = AIMessage(content=(
                    f"Je rencontre des difficultes avec le modele {model_name}. "
                    "Essayez un modele compatible comme **qwen3:14b**, "
                    "**llama3.2:3b** ou **gemma3:12b**."
                ))
        else:
            response = AIMessage(content=(
                f"Le modele {model_name} a rencontre une erreur. "
                "Essayez de reformuler votre question ou changez de modele "
                "(qwen3:14b, llama3.2:3b, gemma3:12b sont recommandes)."
            ))

    # Gerer les appels d'outils en mode prompt-based
    if not use_native_tools and isinstance(response.content, str):
        tool_call = _parse_prompt_based_tool_call(response.content)
        if tool_call and tool_retries < 2:
            result_text = _executer_outil_manuellement(tool_call["outil"], tool_call["query"])
            # Renvoyer le resultat au LLM pour qu'il synthetise
            followup_msg = HumanMessage(content=(
                f"Resultat de l'outil {tool_call['outil']} :\n\n{result_text}\n\n"
                "Synthetise ce resultat pour l'utilisateur de maniere claire et structuree."
            ))
            try:
                response = llm.invoke(messages + [response, followup_msg])
            except Exception:
                response = AIMessage(content=result_text)

    besoin = None
    if isinstance(response.content, str):
        besoin = _detecter_besoin_forge(response.content)

    result = {
        "messages": [response],
        "besoin_forge": besoin,
    }

    # Tracker les echecs d'outils pour le fallback
    if isinstance(response.content, str) and ("erreur" in response.content.lower() or "error" in response.content.lower()):
        result["_tool_retries"] = tool_retries + 1
    else:
        result["_tool_retries"] = 0

    return result


def forge_node(state: dict) -> dict:
    besoin = state.get("besoin_forge", "")
    return {
        "messages": [AIMessage(content=f"[FORGE REQUISE] Besoin détecté : {besoin}")],
        "besoin_forge": besoin,
    }


def hitl_node(state: dict) -> dict:
    return state


# ── Routage ─────────────────────────────────────────────

def router_apres_agent(state: dict) -> str:
    messages = state.get("messages", [])
    last = messages[-1] if messages else None

    if last and hasattr(last, "tool_calls") and last.tool_calls:
        return "action_node"

    if state.get("besoin_forge"):
        return "forge_node"

    return END


# ── Construction du graphe ──────────────────────────────

def build_graph():
    outils = charger_outils()
    action_node = ToolNode(outils) if outils else ToolNode([])

    workflow = StateGraph(dict)

    workflow.add_node("agent_node", agent_node)
    workflow.add_node("action_node", action_node)
    workflow.add_node("forge_node", forge_node)
    workflow.add_node("hitl_node", hitl_node)

    workflow.add_edge(START, "agent_node")
    workflow.add_conditional_edges(
        "agent_node",
        router_apres_agent,
        {
            "action_node": "action_node",
            "forge_node": "forge_node",
            END: END,
        },
    )
    workflow.add_edge("action_node", "agent_node")
    workflow.add_edge("forge_node", END)

    # SqliteSaver.from_conn_string() retourne un context manager, pas l'instance.
    # Comme le graph vit en global (_graph), un bloc `with` fermerait la connexion
    # trop tôt. On crée la connexion manuellement pour maîtriser sa durée de vie.
    conn = sqlite3.connect("/app/data/langgraph.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    memory.setup()  # crée les tables de checkpoint si nécessaire
    graph = workflow.compile(checkpointer=memory, interrupt_before=["hitl_node"])

    return graph


# ── Invocation ──────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def rebuild_graph():
    global _graph
    _graph = build_graph()
    return _graph


def invoke_graph(user_input: str, thread_id: str, status_widget=None, model_name: str = "") -> dict:
    graph = get_graph()
    config = {
        "configurable": {
            "thread_id": thread_id,
            "model_name": model_name,
        },
        "callbacks": [get_langfuse_handler()],
    }

    if status_widget:
        status_widget.update(label="🔍 Agent en réflexion...")

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    messages = result.get("messages", [])
    last_msg = messages[-1] if messages else None
    response_text = last_msg.content if last_msg else ""
    besoin_forge = result.get("besoin_forge")

    if status_widget:
        if besoin_forge:
            status_widget.update(label="⚙️ Outil manquant détecté...")
        else:
            status_widget.update(label="✅ Réponse prête")

    return {
        "response": response_text,
        "besoin_forge": besoin_forge,
        "messages": messages,
    }
