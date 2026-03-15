"""
plu_chatbot.py -- Chatbot RAG specialise PLU.

Permet de poser des questions sur le reglement PLU d'une commune
en s'appuyant sur le retriever ChromaDB (articles indexes).
Utilise un modele Ollama local pour la generation.
"""

import os
import logging
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("PLU_CHAT_MODEL", "mistral-small")

# Prompt systeme specialise PLU
PLU_SYSTEM_PROMPT = """Tu es un assistant specialise en urbanisme et en Plans Locaux d'Urbanisme (PLU).
Tu reponds aux questions en te basant UNIQUEMENT sur les extraits du reglement PLU fournis ci-dessous.

Regles strictes :
1. Ne reponds qu'a partir des extraits fournis. Si l'information n'est pas dans les extraits, dis-le clairement.
2. Cite toujours l'article et le document source (ex: "Selon l'article UB-7 du reglement...").
3. Utilise un langage clair et accessible, pas de jargon juridique inutile.
4. Si la question concerne un sujet hors urbanisme, decline poliment.
5. Structure ta reponse avec des puces ou des paragraphes courts.

Contexte de la parcelle :
- Commune : {commune}
- Zone PLU : {zone}
- Document : {type_document}

Extraits du reglement PLU :
{context}
"""


def _format_docs(docs: list) -> str:
    """Formate les documents recuperes pour le contexte du prompt."""
    parties = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        article = meta.get("article", "?")
        type_doc = meta.get("type_doc", "?")
        fichier = meta.get("fichier", "")
        # Nom court du fichier
        nom_court = fichier.split("/")[-1] if "/" in fichier else fichier
        parties.append(
            f"--- Extrait {i} (Article {article}, {type_doc}, {nom_court}) ---\n"
            f"{doc.page_content}\n"
        )
    return "\n".join(parties)


def creer_chaine_rag(
    retriever,
    commune: str = "",
    zone: str = "",
    type_document: str = "",
    model: str = None,
):
    """Cree une chaine RAG (retriever -> prompt -> LLM -> reponse).

    Args:
        retriever: Retriever LangChain (retourne par creer_retriever())
        commune: Nom de la commune (pour le contexte)
        zone: Zone PLU de la parcelle (ex: "UBc")
        type_document: Type de doc (ex: "PLUi")
        model: Modele Ollama a utiliser (defaut: mistral-small)

    Retourne une chaine invocable avec .invoke({"question": "..."})
    """
    llm = ChatOllama(
        model=model or CHAT_MODEL,
        base_url=OLLAMA_BASE,
        temperature=0.1,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", PLU_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{question}"),
    ])

    chain = (
        {
            "context": lambda x: _format_docs(retriever.invoke(x["question"])),
            "question": lambda x: x["question"],
            "commune": lambda _: commune,
            "zone": lambda _: zone,
            "type_document": lambda _: type_document,
            "history": lambda x: x.get("history", []),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


class PLUChatbot:
    """Chatbot PLU avec historique de conversation.

    Utilisation:
        bot = PLUChatbot(retriever, commune="Pau", zone="UBc")
        reponse = bot.poser_question("Quelle est la hauteur max?")
        reponse2 = bot.poser_question("Et pour les reculs?")
    """

    def __init__(
        self,
        retriever,
        commune: str = "",
        zone: str = "",
        type_document: str = "",
        model: str = None,
        max_history: int = 10,
    ):
        self.retriever = retriever
        self.commune = commune
        self.zone = zone
        self.type_document = type_document
        self.model = model
        self.max_history = max_history
        self.history = []
        self.chain = creer_chaine_rag(
            retriever, commune, zone, type_document, model
        )
        self._derniers_sources = []

    def poser_question(self, question: str) -> str:
        """Pose une question au chatbot et retourne la reponse.

        Maintient l'historique de conversation pour le suivi contextuel.
        """
        # Recuperer les documents sources
        docs = self.retriever.invoke(question)
        self._derniers_sources = docs

        try:
            reponse = self.chain.invoke({
                "question": question,
                "history": self.history[-self.max_history * 2:],
            })
        except Exception as e:
            logger.error(f"Erreur chatbot PLU: {e}")
            reponse = (
                f"Desole, une erreur s'est produite lors de la generation de la reponse. "
                f"Erreur : {str(e)[:200]}"
            )

        # Mettre a jour l'historique
        self.history.append(HumanMessage(content=question))
        self.history.append(AIMessage(content=reponse))

        return reponse

    def get_sources(self) -> list:
        """Retourne les documents sources de la derniere reponse."""
        sources = []
        for doc in self._derniers_sources:
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            sources.append({
                "article": meta.get("article", ""),
                "type_doc": meta.get("type_doc", ""),
                "fichier": meta.get("fichier", ""),
                "extrait": doc.page_content[:300] if hasattr(doc, "page_content") else "",
            })
        return sources

    def reinitialiser(self):
        """Remet a zero l'historique de conversation."""
        self.history = []
        self._derniers_sources = []


def creer_chatbot_plu(retriever, code_insee: str, zone_parcelle: str = None,
                      commune: str = "", type_document: str = "",
                      model: str = None):
    """Cree une instance PLUChatbot configuree. Wrapper conforme au spec."""
    return PLUChatbot(
        retriever=retriever,
        commune=commune,
        zone=zone_parcelle or "",
        type_document=type_document,
        model=model,
    )


def interroger_chatbot(chatbot, question: str, historique: list = None) -> dict:
    """Pose une question et retourne un dict structure. Wrapper conforme au spec."""
    reponse = chatbot.poser_question(question)
    sources = chatbot.get_sources()

    # Evaluer la confiance basee sur les sources
    if sources and len(sources) >= 3:
        confiance = "haute"
    elif sources:
        confiance = "moyenne"
    else:
        confiance = "faible"

    return {
        "reponse": reponse,
        "sources": sources,
        "confiance": confiance,
        "question_reformulee": question,
    }
