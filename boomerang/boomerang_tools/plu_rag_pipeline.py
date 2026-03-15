"""
plu_rag_pipeline.py -- Extraction de texte, chunking par article, indexation ChromaDB.

Pipeline : PDFs PLU -> extraction texte (PyMuPDF) -> decoupage par article
           -> embeddings (nomic-embed-text via Ollama) -> ChromaDB -> retriever MMR
"""

import os
import re
import logging
import hashlib
from typing import Optional

import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

CHROMA_DIR = os.environ.get("PLU_CHROMA_DIR", os.path.join(
    os.path.dirname(__file__), "..", "data", "plu_chroma"
))
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"

# Regex pour detecter les articles PLU (ex: "ARTICLE UA 1", "Article 2b", "ARTICLE N-3")
_ARTICLE_RE = re.compile(
    r"(?:ARTICLE|Article|article)\s+([A-Z]{1,4}[\s\-]?\d{1,2}[a-z]?)\b",
    re.IGNORECASE,
)

# Regex pour detecter les titres de section (ex: "TITRE II", "CHAPITRE 3", "SECTION 1")
_SECTION_RE = re.compile(
    r"(?:TITRE|CHAPITRE|SECTION|SOUS-SECTION)\s+[IVXLCDM\d]+",
    re.IGNORECASE,
)


# -- 2A — Extraction de texte depuis les PDFs ----------------------------

def extraire_texte_pdf(chemin_pdf: str) -> str:
    """Extrait le texte d'un PDF avec PyMuPDF (fitz).

    Retourne le texte brut concatene de toutes les pages.
    Si le PDF est un scan (peu de texte), retourne une chaine courte
    avec un avertissement.
    """
    try:
        doc = fitz.open(chemin_pdf)
    except Exception as e:
        logger.error(f"Impossible d'ouvrir {chemin_pdf}: {e}")
        return ""

    pages_texte = []
    for page in doc:
        pages_texte.append(page.get_text())
    doc.close()

    texte = "\n".join(pages_texte)

    # Nettoyage basique
    texte = re.sub(r"\n{3,}", "\n\n", texte)  # max 2 sauts de ligne
    texte = re.sub(r"[ \t]{2,}", " ", texte)   # espaces multiples
    texte = texte.strip()

    if len(texte) < 200:
        logger.warning(f"PDF probablement scanne (peu de texte): {chemin_pdf}")

    return texte


def extraire_texte_tous_pdfs(cache_dir: str, types_cibles: list = None) -> list:
    """Extrait le texte de tous les PDFs dans un dossier de cache PLU.

    Args:
        cache_dir: Dossier contenant les PDFs extraits du ZIP
        types_cibles: Liste de types a inclure (ex: ["reglement", "oap"]).
                      Si None, prend tout.

    Retourne une liste de dicts: {nom, chemin, type, texte, pages}
    """
    import json

    meta_path = os.path.join(cache_dir, "metadata.json")
    if not os.path.exists(meta_path):
        logger.error(f"Pas de metadata.json dans {cache_dir}")
        return []

    with open(meta_path, "r") as f:
        meta = json.load(f)

    resultats = []
    for finfo in meta.get("fichiers", []):
        doc_type = finfo.get("type", "autre")
        if types_cibles and doc_type not in types_cibles:
            continue

        chemin = finfo.get("chemin", "")
        if not os.path.exists(chemin):
            continue

        texte = extraire_texte_pdf(chemin)
        if not texte:
            continue

        resultats.append({
            "nom": finfo.get("nom", ""),
            "chemin": chemin,
            "type": doc_type,
            "texte": texte,
            "pages": finfo.get("pages", 0),
            "taille_mo": finfo.get("taille_mo", 0),
        })

    logger.info(f"Texte extrait de {len(resultats)} PDFs dans {cache_dir}")
    return resultats


# -- 2B — Chunking intelligent par article PLU ---------------------------

def _decouper_par_articles(texte: str, nom_fichier: str, doc_type: str) -> list:
    """Decoupe un texte PLU en chunks bases sur les articles.

    Chaque article devient un chunk avec ses metadonnees.
    Le texte entre les articles est rattache a l'article precedent.
    Les blocs trop gros (>2000 car.) sont re-decoupes.
    """
    chunks = []

    # Trouver toutes les positions d'articles
    matches = list(_ARTICLE_RE.finditer(texte))

    if not matches:
        # Pas d'articles detectes : decoupage par sections ou par taille
        return _decouper_fallback(texte, nom_fichier, doc_type)

    # Texte avant le premier article
    if matches[0].start() > 100:
        preambule = texte[:matches[0].start()].strip()
        if preambule:
            chunks.append({
                "texte": preambule,
                "article": "preambule",
                "fichier": nom_fichier,
                "type_doc": doc_type,
            })

    # Chaque article
    for i, m in enumerate(matches):
        article_id = m.group(1).strip()
        debut = m.start()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texte)
        contenu = texte[debut:fin].strip()

        if not contenu:
            continue

        # Si le contenu est trop long, le re-decouper
        if len(contenu) > 2000:
            sous_chunks = _redecouper_long(contenu, article_id, nom_fichier, doc_type)
            chunks.extend(sous_chunks)
        else:
            chunks.append({
                "texte": contenu,
                "article": article_id,
                "fichier": nom_fichier,
                "type_doc": doc_type,
            })

    return chunks


def _decouper_fallback(texte: str, nom_fichier: str, doc_type: str) -> list:
    """Decoupage de secours quand aucun article n'est detecte.

    Utilise RecursiveCharacterTextSplitter de LangChain.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " "],
    )
    morceaux = splitter.split_text(texte)

    chunks = []
    for i, morceau in enumerate(morceaux):
        # Essayer de detecter un titre de section
        section_match = _SECTION_RE.search(morceau[:200])
        label = section_match.group(0) if section_match else f"section_{i+1}"

        chunks.append({
            "texte": morceau,
            "article": label,
            "fichier": nom_fichier,
            "type_doc": doc_type,
        })

    return chunks


def _redecouper_long(contenu: str, article_id: str, nom_fichier: str, doc_type: str) -> list:
    """Re-decoupe un article trop long en sous-chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " "],
    )
    morceaux = splitter.split_text(contenu)

    chunks = []
    for i, morceau in enumerate(morceaux):
        suffix = f"_part{i+1}" if len(morceaux) > 1 else ""
        chunks.append({
            "texte": morceau,
            "article": f"{article_id}{suffix}",
            "fichier": nom_fichier,
            "type_doc": doc_type,
        })

    return chunks


def chunker_documents_plu(documents_texte: list) -> list:
    """Point d'entree : decoupe une liste de documents en chunks.

    Args:
        documents_texte: Liste de dicts retournes par extraire_texte_tous_pdfs()

    Retourne une liste de dicts chunk avec: texte, article, fichier, type_doc
    """
    tous_chunks = []
    for doc in documents_texte:
        chunks = _decouper_par_articles(
            doc["texte"],
            doc["nom"],
            doc["type"],
        )
        tous_chunks.extend(chunks)

    logger.info(f"Chunking termine : {len(tous_chunks)} chunks depuis {len(documents_texte)} documents")
    return tous_chunks


# -- 2C — Indexation ChromaDB + retriever --------------------------------

def _collection_id(code_insee: str) -> str:
    """Genere un nom de collection ChromaDB pour une commune."""
    return f"plu_{code_insee}"


def _embeddings():
    """Cree l'objet embeddings Ollama (nomic-embed-text)."""
    return OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE,
    )


def indexer_chunks(chunks: list, code_insee: str, force: bool = False) -> Chroma:
    """Indexe les chunks dans ChromaDB.

    Args:
        chunks: Liste de dicts chunk (texte, article, fichier, type_doc)
        code_insee: Code INSEE de la commune (utilise comme nom de collection)
        force: Si True, reindexe meme si la collection existe deja

    Retourne l'objet Chroma vectorstore.
    """
    os.makedirs(CHROMA_DIR, exist_ok=True)

    collection_name = _collection_id(code_insee)
    embed = _embeddings()

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Verifier si la collection existe deja
    if force:
        try:
            client.delete_collection(collection_name)
            logger.info(f"Collection {collection_name} supprimee (force=True)")
        except Exception:
            pass
    else:
        try:
            existing = client.list_collections()
            existing_names = [c.name if hasattr(c, 'name') else c for c in existing]
            if collection_name in existing_names:
                coll = client.get_collection(collection_name)
                if coll.count() > 0:
                    logger.info(f"Collection {collection_name} existe deja ({coll.count()} docs), skip.")
                    return Chroma(
                        collection_name=collection_name,
                        embedding_function=embed,
                        persist_directory=CHROMA_DIR,
                    )
        except Exception as e:
            logger.warning(f"Erreur verification collection: {e}")

    # Convertir les chunks en Documents LangChain
    documents = []
    ids = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk["texte"],
            metadata={
                "article": chunk["article"],
                "fichier": chunk["fichier"],
                "type_doc": chunk["type_doc"],
                "code_insee": code_insee,
            },
        )
        documents.append(doc)
        # ID unique base sur le contenu
        content_hash = hashlib.md5(chunk["texte"][:500].encode()).hexdigest()[:12]
        ids.append(f"{code_insee}_{i}_{content_hash}")

    if not documents:
        logger.warning("Aucun document a indexer")
        return None

    logger.info(f"Indexation de {len(documents)} chunks dans {collection_name}...")

    # Indexer par batches (ChromaDB a une limite de ~5000 par batch)
    BATCH_SIZE = 500
    vectorstore = None

    for start in range(0, len(documents), BATCH_SIZE):
        batch_docs = documents[start:start + BATCH_SIZE]
        batch_ids = ids[start:start + BATCH_SIZE]

        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch_docs,
                embedding=embed,
                collection_name=collection_name,
                persist_directory=CHROMA_DIR,
                ids=batch_ids,
            )
        else:
            vectorstore.add_documents(batch_docs, ids=batch_ids)

        logger.info(f"  Batch {start//BATCH_SIZE + 1}: {len(batch_docs)} docs indexes")

    logger.info(f"Indexation terminee: {len(documents)} chunks dans {collection_name}")
    return vectorstore


def creer_retriever(code_insee: str, k: int = 6, fetch_k: int = 20) -> Optional[object]:
    """Cree un retriever MMR pour une commune deja indexee.

    MMR (Maximal Marginal Relevance) equilibre pertinence et diversite :
    il evite de retourner 6 chunks quasi-identiques.

    Args:
        code_insee: Code INSEE de la commune
        k: Nombre de documents a retourner
        fetch_k: Nombre de candidats a considerer pour le re-ranking MMR

    Retourne un retriever LangChain ou None si la collection n'existe pas.
    """
    collection_name = _collection_id(code_insee)
    embed = _embeddings()

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embed,
            persist_directory=CHROMA_DIR,
        )
        # Verifier que la collection a du contenu
        if vectorstore._collection.count() == 0:
            logger.warning(f"Collection {collection_name} vide")
            return None
    except Exception as e:
        logger.error(f"Impossible de charger la collection {collection_name}: {e}")
        return None

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": 0.7,  # 0=diversite max, 1=pertinence max
        },
    )
    logger.info(f"Retriever MMR cree pour {collection_name} (k={k})")
    return retriever


# -- 2D — Pipeline complet : PDF -> index --------------------------------

def pipeline_indexation_plu(
    cache_dir: str,
    code_insee: str,
    types_cibles: list = None,
    force: bool = False,
) -> dict:
    """Pipeline complet : extraction texte -> chunking -> indexation.

    Args:
        cache_dir: Dossier contenant les PDFs extraits
        code_insee: Code INSEE de la commune
        types_cibles: Types de docs a indexer (defaut: reglement + oap)
        force: Forcer la reindexation

    Retourne un dict avec les stats du pipeline.
    """
    if types_cibles is None:
        types_cibles = ["reglement", "oap", "padd"]

    # Etape 1 : extraction texte
    documents = extraire_texte_tous_pdfs(cache_dir, types_cibles)
    if not documents:
        return {
            "statut": "erreur",
            "message": f"Aucun PDF exploitable dans {cache_dir}",
            "nb_documents": 0,
            "nb_chunks": 0,
        }

    # Etape 2 : chunking
    chunks = chunker_documents_plu(documents)
    if not chunks:
        return {
            "statut": "erreur",
            "message": "Chunking n'a produit aucun resultat",
            "nb_documents": len(documents),
            "nb_chunks": 0,
        }

    # Etape 3 : indexation
    vectorstore = indexer_chunks(chunks, code_insee, force=force)

    return {
        "statut": "ok",
        "nb_documents": len(documents),
        "nb_chunks": len(chunks),
        "types_indexes": list(set(c["type_doc"] for c in chunks)),
        "collection": _collection_id(code_insee),
        "articles_detectes": len([c for c in chunks if not c["article"].startswith("section_")]),
    }
