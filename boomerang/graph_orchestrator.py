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
import logging
from typing import Annotated, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from langfuse.langchain import CallbackHandler

from tool_runner import charger_outils

load_dotenv()

logger = logging.getLogger(__name__)


# ── Sélection LLM ──────────────────────────────────────

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        )
    elif provider == "together":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY", ""),
            model=os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
        )
    else:
        raise ValueError(f"LLM_PROVIDER inconnu : {provider}")


# ── Langfuse ────────────────────────────────────────────

def get_langfuse_handler() -> CallbackHandler:
    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
    )


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


# ── Noeuds du graphe ────────────────────────────────────

def agent_node(state: dict) -> dict:
    messages = state.get("messages", [])
    outils = charger_outils()
    llm = get_llm()

    if outils:
        llm_with_tools = llm.bind_tools(outils)
    else:
        llm_with_tools = llm

    response = llm_with_tools.invoke(messages)
    besoin = None
    if isinstance(response.content, str):
        besoin = _detecter_besoin_forge(response.content)

    return {
        "messages": [response],
        "besoin_forge": besoin,
    }


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

    memory = SqliteSaver.from_conn_string("/app/data/langgraph.db")
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


def invoke_graph(user_input: str, thread_id: str, status_widget=None) -> dict:
    graph = get_graph()
    config = {
        "configurable": {"thread_id": thread_id},
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
