"""
app.py — Interface Streamlit de BOOMERANG
Assistant IA auto-génératif pour architectes français (PLU, ERP, PMR)
"""

import os
import io
import base64
import shutil
import subprocess
import time
import asyncio
from datetime import datetime

import nest_asyncio
nest_asyncio.apply()

import logging
import requests
import streamlit as st
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# ── Configuration ───────────────────────────────────────

st.set_page_config(
    page_title="BOOMERANG",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SAAS_MODE = os.getenv("SAAS_MODE", "false").lower() == "true"

# ── Persistance des settings ─────────────────────────
from pathlib import Path as _Path
import json as _json
import portalocker as _portalocker

SETTINGS_FILE = _Path("/app/data/settings.json")


_SETTINGS_DEFAULTS = {
    "streaming_enabled": True,
    "hybrid_mode": False,
    "model_fast": "llama3.2:1b",
    "model_slow": "qwen2.5:14b",
    "cache_enabled": True,
    "cache_ttl_jours": 7,
}


def load_settings() -> dict:
    defaults = dict(_SETTINGS_DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                _portalocker.lock(f, _portalocker.LOCK_SH)
                stored = _json.load(f)
                _portalocker.unlock(f)
                defaults.update(stored)
        except (ValueError, IOError):
            pass
    return defaults


def save_settings(key: str, value) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    settings[key] = value
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        _portalocker.lock(f, _portalocker.LOCK_EX)
        _json.dump(settings, f, ensure_ascii=False, indent=2)
        _portalocker.unlock(f)

# ── Imports internes ────────────────────────────────────

from db_manager import (
    init_db,
    lister_projets,
    sauvegarder_message,
    charger_historique,
    supprimer_historique,
    enregistrer_outil_forge,
    lister_outils_projet,
    get_prochain_port,
    enregistrer_port,
)
from graph_orchestrator import invoke_graph, stream_graph, rebuild_graph, get_langfuse_handler
from tool_runner import TOOL_REGISTRY, charger_outils

if not SAAS_MODE:
    from forge_claude import forger_outil, ameliorer_outil

# ── Init DB ─────────────────────────────────────────────

init_db()

# ── Authentification ────────────────────────────────────
# Deux modes :
#   1. Auth complete (streamlit-authenticator) si auth_config.yaml existe
#   2. Acces libre si le fichier n'existe pas (dev local)

import yaml
import streamlit_authenticator as stauth

_AUTH_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "auth_config.yaml")
_AUTH_ENABLED = os.path.exists(_AUTH_CONFIG_PATH)

if _AUTH_ENABLED:
    with open(_AUTH_CONFIG_PATH) as f:
        _auth_config = yaml.safe_load(f)

    authenticator = stauth.Authenticate(
        _auth_config["credentials"],
        _auth_config["cookie"]["name"],
        _auth_config["cookie"]["key"],
        _auth_config["cookie"]["expiry_days"],
    )

    authenticator.login()

    if st.session_state.get("authentication_status") is None:
        st.info("Entrez vos identifiants pour acceder a BOOMERANG.")
        st.stop()
    elif st.session_state.get("authentication_status") is False:
        st.error("Identifiant ou mot de passe incorrect.")
        st.stop()

# ── Session state defaults ──────────────────────────────

defaults = {
    "id_projet": None,
    "forge_mode": None,       # None | "pending" | "review" | "editing" | "improving"
    "code_temp": None,
    "code_edite": None,
    "nom_outil_temp": None,
    "besoin_forge": None,
    "forge_result": None,
    "messages": [],           # historique chat affiché dans la session courante
    "ollama_model": load_settings().get("last_model", os.getenv("OLLAMA_MODEL", "llama3.2")),
    "last_working_model": load_settings().get("last_model", os.getenv("OLLAMA_MODEL", "llama3.2")),
    "attached_file_ctx": None,  # contexte du fichier joint (dict ou None)
    "web_search_enabled": False,  # toggle recherche web
    "show_file_uploader": False,  # afficher/masquer le file uploader
    "guide_mode": None,           # None | "depot_pc"
    "guide_step": 0,              # etape courante du guide
    "guide_data": {},             # donnees collectees par le guide
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper : liste des modèles Ollama disponibles ───────

def get_ollama_models() -> list[str]:
    """Interroge l'API Ollama pour lister les modèles installés.

    Appelle GET http://<OLLAMA_BASE_URL>/api/tags.
    Si l'API est inaccessible, retourne une liste par défaut.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        noms = [m["name"] for m in models if "name" in m]
        return noms if noms else ["llama3.2"]
    except Exception:
        return ["llama3.2"]


# ── Helpers fichiers joints ───────────────────────────

MAX_FILE_SIZE_MB = 10

VISION_MODELS = [
    "llava", "llava-llama3", "llava-phi3", "bakllava",
    "moondream", "qwen2-vl", "llama3.2-vision", "minicpm-v",
    "cogvlm2", "internvl2",
]


def _modele_supporte_vision(model_name: str) -> bool:
    """Verifie si le modele Ollama selectionne supporte les images."""
    model_lower = model_name.lower()
    for v in VISION_MODELS:
        if v in model_lower:
            return True
    return False


def _extraire_texte_pdf(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier PDF."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        texte = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texte.append(t)
        return "\n\n".join(texte) if texte else "(PDF sans texte extractible)"
    except Exception as e:
        return f"(Erreur extraction PDF : {str(e)})"


def _preparer_contexte_fichier(uploaded_file) -> dict:
    """Prepare le contexte a injecter dans le message utilisateur.

    Retourne {"type": "text"|"image"|"error", "content": str, "filename": str}
    """
    filename = uploaded_file.name
    file_bytes = uploaded_file.read()
    size_mb = len(file_bytes) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        return {
            "type": "error",
            "content": f"Le fichier {filename} depasse la limite de {MAX_FILE_SIZE_MB} Mo ({size_mb:.1f} Mo).",
            "filename": filename,
        }

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        texte = _extraire_texte_pdf(file_bytes)
        return {"type": "text", "content": texte, "filename": filename}
    elif ext == "txt":
        try:
            texte = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            texte = file_bytes.decode("latin-1", errors="replace")
        return {"type": "text", "content": texte, "filename": filename}
    elif ext in ("jpg", "jpeg", "png", "webp"):
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return {"type": "image", "content": b64, "filename": filename, "ext": ext}
    else:
        return {
            "type": "error",
            "content": f"Format de fichier non supporte : .{ext}. Formats acceptes : PDF, TXT, JPG, PNG.",
            "filename": filename,
        }


# ── Rendu riche des messages (Mermaid, Matplotlib, WMS) ──

def _render_message_content(content: str):
    """Affiche le contenu d'un message avec support Mermaid, charts et cartes WMS."""
    import re as _re

    # Detecter les blocs Mermaid dans le contenu
    mermaid_blocks = _re.findall(r'```mermaid\s*\n(.*?)```', content, _re.DOTALL)
    if mermaid_blocks:
        # Afficher le texte avant le bloc Mermaid
        before = content.split("```mermaid")[0]
        if before.strip():
            st.markdown(before)
        for mermaid_code in mermaid_blocks:
            html = (
                '<div class="mermaid">\n'
                f'{mermaid_code.strip()}\n'
                '</div>\n'
                '<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>\n'
                '<script>mermaid.initialize({startOnLoad:true, theme:"dark"});</script>'
            )
            st.components.v1.html(html, height=400, scrolling=True)
        # Texte apres le dernier bloc Mermaid
        after_parts = content.split("```")
        if len(after_parts) > 2:
            trailing = after_parts[-1].strip()
            if trailing:
                st.markdown(trailing)
        return

    # Detecter les graphiques Matplotlib (chemin de fichier)
    if "CHART:" in content:
        parts = content.split("CHART:")
        if parts[0].strip():
            st.markdown(parts[0])
        chemin = parts[1].strip().split("\n")[0].strip()
        if os.path.exists(chemin):
            st.image(chemin, caption="Graphique genere par BOOMERANG")
        else:
            st.warning(f"Graphique introuvable : {chemin}")
        remaining = "\n".join(parts[1].strip().split("\n")[1:])
        if remaining.strip():
            st.markdown(remaining)
        return

    # Detecter les URLs de carte WMS
    if "MAP_URL:" in content:
        parts = content.split("MAP_URL:")
        if parts[0].strip():
            st.markdown(parts[0])
        url = parts[1].strip().split("\n")[0].strip()
        st.image(url, caption="Localisation cadastrale — Geoportail IGN")
        remaining = "\n".join(parts[1].strip().split("\n")[1:])
        if remaining.strip():
            st.markdown(remaining)
        return

    # Contenu standard : affichage Markdown classique
    st.markdown(content)


# ── Indicateurs de progression par outil ──────────────

TOOL_STATUS_MESSAGES = {
    "recherche_urbanisme":        "Interrogation du Geoportail de l'Urbanisme...",
    "recherche_risques_parcelle":  "Analyse des risques naturels (Georisques)...",
    "recherche_web":              "Recherche documentaire en cours...",
    "recherche_legale":           "Consultation des textes juridiques...",
    "notice_securite":            "Generation de la notice de securite...",
    "tool_demander_dev":          "Enregistrement demande developpeur...",
    "tool_generer_schema":        "Generation du schema...",
}


def _get_status_label(tool_name: str) -> str:
    return TOOL_STATUS_MESSAGES.get(tool_name, f"Execution de {tool_name}...")


# ── Streaming de la reponse avec indicateurs visuels ──

def _run_streaming(llm_text, thread_id, model_name, placeholder, status_container):
    """Execute le graphe en mode streaming avec affichage progressif."""
    full_text = ""
    current_status = None

    def on_token(chunk):
        nonlocal full_text
        full_text += chunk
        placeholder.markdown(full_text + " |")

    def on_tool_start(tool_name):
        nonlocal current_status
        label = _get_status_label(tool_name)
        current_status = status_container.status(label, expanded=False)
        current_status.write(f"Outil : `{tool_name}`")

    def on_tool_end(tool_name):
        nonlocal current_status
        if current_status:
            current_status.update(label=f"{_get_status_label(tool_name).rstrip('...')} OK", state="complete")
            current_status = None

    try:
        result = asyncio.run(stream_graph(
            llm_text,
            thread_id,
            model_name=model_name,
            on_token=on_token,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        ))
    except Exception as e:
        # Fallback sur invoke_graph synchrone si le streaming echoue
        import logging
        logging.getLogger(__name__).warning(f"Streaming echoue, fallback synchrone: {e}")
        result = invoke_graph(llm_text, thread_id, model_name=model_name)
        full_text = result.get("response", "")

    # Affichage final sans curseur
    if full_text:
        placeholder.markdown(full_text)
    else:
        full_text = result.get("response", "")
        placeholder.markdown(full_text)

    return {
        "response": full_text,
        "besoin_forge": result.get("besoin_forge"),
    }


# ── Langfuse handler (une seule fois) ──────────────────

if "langfuse_handler" not in st.session_state:
    try:
        st.session_state.langfuse_handler = get_langfuse_handler()
    except Exception:
        st.session_state.langfuse_handler = None


# ── Helper : ajouter service docker-compose ─────────────

def _ajouter_service_compose(nom, port, requiert_internet, compose_path="/app/project/docker-compose.yml"):
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True

    with open(compose_path, "r") as f:
        data = yaml.load(f)

    service_name = f"tool_{nom}"
    if service_name in data.get("services", {}):
        raise ValueError(f"Service {service_name} existe déjà dans docker-compose.yml")

    networks = ["tools_net"]
    if requiert_internet:
        networks.append("boomerang_net")

    data["services"][service_name] = {
        "build": f"./boomerang_tools/tool_{nom}",
        "container_name": service_name,
        "ports": [f"{port}:{port}"],
        "restart": "unless-stopped",
        "networks": networks,
    }

    with open(compose_path, "w") as f:
        yaml.dump(data, f)


# ── Helper : vérifier health d'un container ─────────────

def _check_health(url, timeout=2):
    try:
        resp = requests.get(f"{url}/health", timeout=timeout)
        return resp.json().get("status") == "ok"
    except Exception:
        return False


# ── Helper : attendre healthcheck ────────────────────────

def _attendre_health(url, timeout_total=30, intervalle=2):
    debut = time.time()
    while time.time() - debut < timeout_total:
        if _check_health(url):
            return True
        time.sleep(intervalle)
    return False


# ══════════════════════════════════════════════════════════
#  SIDEBAR (minimale — les controles sont dans la grille Bento)
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.title("BOOMERANG")

    # ── Logout ─────────────────────────────────────────
    if _AUTH_ENABLED:
        st.caption(f"Connecte : **{st.session_state.get('name', '')}**")
        authenticator.logout("Deconnexion", "sidebar")

    st.divider()
    st.caption("[Langfuse](http://localhost:3003)")

    # ── Section Rollback (admin) ────────────────────────
    if not SAAS_MODE:
        st.divider()
        st.subheader("Restaurer un outil")

        backups_dir = os.getenv("BACKUPS_DIR", "/app/backups")
        if os.path.exists(backups_dir):
            backups = {}
            for entry in os.listdir(backups_dir):
                full_path = os.path.join(backups_dir, entry)
                if os.path.isdir(full_path) and "_" in entry:
                    parts = entry.rsplit("_", 2)
                    if len(parts) >= 3:
                        nom_outil = "_".join(parts[:-2])
                        timestamp = f"{parts[-2]}_{parts[-1]}"
                        if nom_outil not in backups:
                            backups[nom_outil] = []
                        backups[nom_outil].append({"timestamp": timestamp, "path": full_path})

            if backups:
                for nom_outil, versions in backups.items():
                    versions.sort(key=lambda v: v["timestamp"], reverse=True)
                    timestamps = [v["timestamp"] for v in versions]
                    selected = st.selectbox(
                        f"Versions de {nom_outil}",
                        timestamps,
                        key=f"rollback_{nom_outil}",
                    )
                    if st.button(f"Restaurer {nom_outil}", key=f"btn_rollback_{nom_outil}"):
                        version = next(v for v in versions if v["timestamp"] == selected)
                        service_name = f"tool_{nom_outil}"
                        try:
                            subprocess.run(
                                ["docker", "compose", "stop", service_name],
                                cwd="/app/project",
                                capture_output=True, timeout=30,
                            )
                            dest = os.path.join(
                                os.getenv("TOOLS_DIR", "/app/boomerang_tools"),
                                service_name,
                            )
                            if os.path.exists(dest):
                                shutil.rmtree(dest)
                            shutil.copytree(version["path"], dest)
                            subprocess.run(
                                ["docker", "compose", "up", "-d", "--build", service_name],
                                cwd="/app/project",
                                capture_output=True, timeout=120,
                            )
                        except Exception as e:
                            logger.error(f"[rollback] Erreur restauration {nom_outil}: {e}")
                            st.error(f"Erreur lors de la restauration : {e}")
                        url = TOOL_REGISTRY.get(nom_outil, "")
                        if url and _attendre_health(url):
                            st.success(f"{nom_outil} restaure a {selected}")
                        else:
                            st.warning(f"{nom_outil} restaure mais healthcheck timeout")
                        charger_outils()
                        st.rerun()
            else:
                st.caption("Aucun backup disponible")
        else:
            st.caption("Aucun backup disponible")

id_projet = st.session_state.id_projet


# ══════════════════════════════════════════════════════════
#  ZONE PRINCIPALE
# ══════════════════════════════════════════════════════════

if not id_projet:
    st.info("Sélectionnez ou créez un projet dans la sidebar.")
    st.stop()

thread_id = f"projet_{id_projet}"

# ── État FORGE ──────────────────────────────────────────

if not SAAS_MODE and st.session_state.forge_mode is not None:

    st.warning("🔨 Outil forgé — révision requise avant intégration")

    # ── PENDING : forge en cours ────────────────────────
    if st.session_state.forge_mode == "pending":
        with st.status("🔨 Forge en cours — ne pas fermer cette fenêtre") as status:
            def _status_cb(msg):
                status.update(label=msg)

            result = forger_outil(
                besoin=st.session_state.besoin_forge,
                id_projet=id_projet,
                status_callback=_status_cb,
            )
            st.session_state.forge_result = result

            if result["statut"] == "erreur":
                st.error(f"Erreur forge : {result['message']}")
                st.session_state.forge_mode = None
                st.rerun()

            st.session_state.code_temp = result["code"]
            st.session_state.code_edite = result["code"]
            st.session_state.nom_outil_temp = result["nom_fichier"]
            st.session_state.forge_mode = "review"
            st.rerun()

    # ── REVIEW : code affiché, attente décision ─────────
    elif st.session_state.forge_mode == "review":
        result = st.session_state.forge_result

        if result:
            tests_ok = result.get("tests_ok", False)
            st.info(f"Tests : {'✅ OK' if tests_ok else '⚠️ Échec'}")
            with st.expander("Voir le rapport pytest"):
                st.code(result.get("pytest_output", ""), language="text")

        st.code(st.session_state.code_edite, language="python")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Valider et intégrer"):
                nom_outil = st.session_state.nom_outil_temp
                nom_court = nom_outil.replace("tool_", "", 1)
                tools_dir = os.getenv("TOOLS_DIR", "/app/boomerang_tools")
                backups_dir_val = os.getenv("BACKUPS_DIR", "/app/backups")
                dest = os.path.join(tools_dir, nom_outil)

                # Backup si outil existant
                if os.path.exists(dest):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_dest = os.path.join(backups_dir_val, f"{nom_court}_{ts}")
                    shutil.copytree(dest, backup_dest)

                # Copier temp -> boomerang_tools
                temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
                src = os.path.join(temp_dir, nom_outil)
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

                # Allouer port
                port = get_prochain_port()
                requiert_internet = (st.session_state.forge_result or {}).get("requiert_internet", False)

                # Modifier docker-compose.yml
                try:
                    _ajouter_service_compose(nom_court, port, requiert_internet)
                except ValueError:
                    pass  # service existe déjà

                # Lancer le container
                try:
                    subprocess.run(
                        ["docker", "compose", "up", "-d", "--build", nom_outil],
                        cwd="/app/project",
                        capture_output=True, timeout=120,
                    )
                except Exception as e:
                    logger.error(f"[deploy] docker compose up {nom_outil} echoue: {e}")
                    st.error(f"Erreur deploiement Docker : {e}")

                # Attendre healthcheck
                url = f"http://{nom_outil}:{port}"
                _attendre_health(url)

                # Enregistrer
                enregistrer_port(nom_court, port)
                TOOL_REGISTRY[nom_court] = url
                enregistrer_outil_forge(
                    id_projet, nom_outil,
                    st.session_state.besoin_forge or "", "validated",
                )

                # Recharger
                charger_outils()
                rebuild_graph()

                # Réinitialiser état forge
                st.session_state.forge_mode = None
                st.session_state.code_temp = None
                st.session_state.code_edite = None
                st.session_state.nom_outil_temp = None
                st.session_state.besoin_forge = None
                st.session_state.forge_result = None

                st.success(f"✓ Outil {nom_outil} intégré sur le port {port}")

                # Relancer le graphe pour continuer
                with st.status("🔄 Reprise de la conversation..."):
                    result = invoke_graph(
                        f"L'outil {nom_court} est maintenant disponible. Continue ta réponse.",
                        thread_id,
                        model_name=st.session_state.ollama_model,
                    )
                    sauvegarder_message(id_projet, "assistant", result["response"])
                st.rerun()

        with col2:
            if st.button("✏️ Modifier"):
                st.session_state.forge_mode = "editing"
                st.rerun()

        with col3:
            if st.button("❌ Rejeter"):
                nom_outil = st.session_state.nom_outil_temp
                temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
                tool_path = os.path.join(temp_dir, nom_outil)
                if os.path.exists(tool_path):
                    shutil.rmtree(tool_path)

                enregistrer_outil_forge(
                    id_projet, nom_outil or "",
                    st.session_state.besoin_forge or "", "rejected",
                )

                st.session_state.forge_mode = None
                st.session_state.code_temp = None
                st.session_state.code_edite = None
                st.session_state.nom_outil_temp = None
                st.session_state.besoin_forge = None
                st.session_state.forge_result = None

                st.info("Outil rejeté. L'agent va continuer sans cet outil.")

                with st.status("🔄 Reprise sans l'outil..."):
                    result = invoke_graph(
                        "L'outil forgé a été rejeté par l'utilisateur. Continue sans cet outil.",
                        thread_id,
                        model_name=st.session_state.ollama_model,
                    )
                    sauvegarder_message(id_projet, "assistant", result["response"])
                st.rerun()

    # ── EDITING : édition manuelle ──────────────────────
    elif st.session_state.forge_mode == "editing":
        st.subheader("✏️ Éditeur de code")
        st.info("Modifiez directement le code puis choisissez une action.")

        code_modifie = st.text_area(
            label="Code Python",
            value=st.session_state.code_edite,
            height=500,
            key="editeur_code",
        )

        st.caption("💡 Astuce : modifiez le code puis cliquez sur 'Tester' pour valider vos changements.")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button("🧪 Tester mes modifications"):
                st.session_state.code_edite = code_modifie
                nom_outil = st.session_state.nom_outil_temp
                nom_court = (nom_outil or "").replace("tool_", "", 1)

                # Validation de securite AVANT ecriture sur disque
                from forge_claude import _valider_code_forge
                problemes = _valider_code_forge(code_modifie)
                if problemes:
                    st.error("Code rejete — problemes de securite detectes :")
                    for p in problemes:
                        st.write(f"- {p}")
                    st.stop()

                # Écrire le code modifié (valide)
                temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
                tool_dir = os.path.join(temp_dir, nom_outil or "")
                os.makedirs(tool_dir, exist_ok=True)
                with open(os.path.join(tool_dir, "server.py"), "w", encoding="utf-8") as f:
                    f.write(code_modifie)

                # Lancer pytest
                tests_dir = os.getenv("TESTS_DIR", "/app/tests")
                test_file = os.path.join(tests_dir, f"test_{nom_court}.py")
                if os.path.exists(test_file):
                    pytest_result = subprocess.run(
                        ["pytest", test_file, "-v", "--tb=short"],
                        capture_output=True, text=True, timeout=120,
                    )
                    if pytest_result.returncode == 0:
                        st.success("✅ Tests OK")
                    else:
                        st.error("❌ Tests échoués")
                    st.code(pytest_result.stdout + pytest_result.stderr, language="text")
                else:
                    st.warning("Aucun fichier test trouvé")

                # Mettre à jour le résultat
                if st.session_state.forge_result:
                    st.session_state.forge_result["code"] = code_modifie

                st.session_state.forge_mode = "review"
                st.rerun()

        with col_b:
            if st.button("🤖 Améliorer avec Claude"):
                st.session_state.code_edite = code_modifie
                st.session_state.forge_mode = "improving"
                st.rerun()

        with col_c:
            if st.button("↩️ Annuler l'édition"):
                st.session_state.forge_mode = "review"
                st.rerun()

    # ── IMPROVING : amélioration Claude ─────────────────
    elif st.session_state.forge_mode == "improving":
        st.subheader("🤖 Amélioration par Claude")
        st.code(st.session_state.code_edite, language="python")

        instruction = st.text_area(
            label="Instructions d'amélioration",
            placeholder="Ex: Ajoute la gestion des erreurs HTTP 429, améliore le parsing JSON, ajoute un cache de 5 minutes...",
            height=100,
            key="instruction_amelioration",
        )

        col_x, col_y = st.columns(2)

        with col_x:
            if st.button("🚀 Lancer l'amélioration", disabled=not instruction):
                with st.status("🤖 Claude améliore le code...") as s:
                    s.update(label="📝 Envoi des instructions à Claude Code...")
                    result = ameliorer_outil(
                        code_actuel=st.session_state.code_edite,
                        instruction=instruction,
                        nom_fichier=st.session_state.nom_outil_temp or "",
                    )

                st.session_state.code_edite = result["code"]

                # Écrire dans temp_tools
                nom_outil = st.session_state.nom_outil_temp
                temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
                tool_dir = os.path.join(temp_dir, nom_outil or "")
                os.makedirs(tool_dir, exist_ok=True)
                with open(os.path.join(tool_dir, "server.py"), "w", encoding="utf-8") as f:
                    f.write(result["code"])

                # Mettre à jour le résultat
                if st.session_state.forge_result:
                    st.session_state.forge_result["code"] = result["code"]
                    st.session_state.forge_result["tests_ok"] = result["tests_ok"]
                    st.session_state.forge_result["pytest_output"] = result["pytest_output"]

                st.session_state.forge_mode = "review"
                st.rerun()

        with col_y:
            if st.button("↩️ Retour sans modification"):
                st.session_state.forge_mode = "review"
                st.rerun()

# ── État GUIDE ──────────────────────────────────────────

elif st.session_state.guide_mode == "depot_pc":
    from guide_depot_pc import render_guide
    render_guide(id_projet, TOOL_REGISTRY)

# ── État NORMAL ─────────────────────────────────────────

else:

    # ── CSS Bento Grid ──────────────────────────────────
    BOOMERANG_CSS = """
    <style>
    /* ── Reset marges Streamlit ── */
    #root > div:first-child { padding-top: 0 !important; }
    .block-container {
        padding: 0.75rem 1rem !important;
        max-width: 100% !important;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #1a1d21;
    }
    /* ── Palette Architecte ── */
    :root {
        --bg-app:      #1a1d21;
        --bg-panel:    #22262c;
        --bg-deep:     #16191d;
        --border:      #2e333a;
        --accent:      #4A90D9;
        --accent-dark: #1a2633;
        --accent-border: #2a3d52;
        --text-primary:   #e8e6e0;
        --text-secondary: #9ca3af;
        --text-muted:     #4b5563;
        --success:     #22c55e;
        --warning:     #f59e0b;
    }
    /* ── Panneaux Bento ── */
    .bento-panel {
        background: var(--bg-panel);
        border: 0.5px solid var(--border);
        border-radius: 12px;
        padding: 0;
        overflow: hidden;
    }
    .bento-head {
        padding: 8px 14px;
        border-bottom: 0.5px solid var(--border);
        font-size: 10px;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .bento-head::before {
        content: '';
        display: block;
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--accent);
        flex-shrink: 0;
    }
    .bento-body {
        padding: 12px 14px;
    }
    /* ── Topbar ── */
    .bento-topbar {
        background: var(--bg-panel);
        border: 0.5px solid var(--border);
        border-radius: 10px;
        padding: 8px 16px;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    .bento-logo {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: 0.04em;
    }
    .bento-logo span { color: var(--accent); }
    .bento-badge {
        font-size: 10px;
        padding: 2px 9px;
        border-radius: 4px;
        background: var(--accent-dark);
        color: var(--accent);
        border: 0.5px solid var(--accent-border);
    }
    .bento-badge.success {
        background: #1a2a1a;
        color: var(--success);
        border-color: #1f3d1f;
    }
    /* ── Quick Actions ── */
    .qa-strip {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        padding: 8px 14px;
        border-bottom: 0.5px solid var(--border);
    }
    .qa-chip {
        font-size: 10px;
        padding: 3px 10px;
        border-radius: 20px;
        background: var(--accent-dark);
        color: var(--accent);
        border: 0.5px solid var(--accent-border);
        cursor: pointer;
        white-space: nowrap;
        transition: background 0.15s;
    }
    .qa-chip:hover { background: #1e2e45; }
    /* ── Skeleton loader ── */
    @keyframes shimmer {
        0%   { opacity: 0.35; }
        50%  { opacity: 0.7; }
        100% { opacity: 0.35; }
    }
    .skeleton-wrap {
        display: flex;
        gap: 10px;
        align-items: flex-start;
        padding: 6px 0;
    }
    .skeleton-avatar {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: var(--border);
        animation: shimmer 1.4s ease-in-out infinite;
        flex-shrink: 0;
    }
    .skeleton-lines {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .skeleton-line {
        height: 9px;
        border-radius: 4px;
        background: var(--border);
        animation: shimmer 1.4s ease-in-out infinite;
    }
    .skeleton-line:nth-child(2) { width: 72%; animation-delay: 0.2s; }
    .skeleton-line:nth-child(3) { width: 48%; animation-delay: 0.4s; }
    /* ── Metadonnees projet ── */
    .meta-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px 8px;
        margin-top: 8px;
    }
    .meta-item {
        font-size: 10px;
        color: var(--text-muted);
    }
    .meta-item span {
        display: block;
        color: var(--text-secondary);
        font-weight: 500;
        margin-top: 1px;
    }
    .meta-divider {
        height: 0.5px;
        background: var(--border);
        margin: 10px 0;
    }
    /* ── Zone d'upload ── */
    .upload-zone {
        border: 0.5px dashed var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        font-size: 10px;
        color: var(--text-muted);
        cursor: pointer;
        margin-bottom: 10px;
        transition: border-color 0.15s;
    }
    .upload-zone:hover { border-color: var(--accent); color: var(--accent); }
    /* ── Boutons Streamlit dans les panneaux ── */
    [data-testid="stButton"] > button {
        background: var(--accent-dark) !important;
        color: var(--accent) !important;
        border: 0.5px solid var(--accent-border) !important;
        border-radius: 6px !important;
        font-size: 11px !important;
        padding: 4px 12px !important;
        font-weight: 400 !important;
        transition: background 0.15s !important;
    }
    [data-testid="stButton"] > button:hover {
        background: #1e2e45 !important;
    }
    /* ── Bouton primaire ── */
    button[kind="primary"] {
        background: var(--accent) !important;
        color: #ffffff !important;
        border-color: var(--accent) !important;
    }
    /* ── Inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] select {
        background: var(--bg-deep) !important;
        border: 0.5px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        font-size: 12px !important;
    }
    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
    }
    /* ── Selectbox ── */
    [data-testid="stSelectbox"] > div > div {
        background: var(--bg-deep) !important;
        border: 0.5px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
    }
    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: var(--bg-deep) !important;
        border: 0.5px solid var(--border) !important;
        border-radius: 8px !important;
    }
    /* ── Status widget ── */
    [data-testid="stStatus"] {
        background: var(--bg-deep) !important;
        border: 0.5px solid var(--border) !important;
        border-radius: 8px !important;
    }
    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
    /* ── File chip ── */
    .file-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: var(--accent-dark);
        border: 0.5px solid var(--accent-border);
        border-radius: 0.5rem;
        padding: 0.3rem 0.6rem;
        font-size: 10px;
        color: var(--accent);
    }
    /* ── Masquer labels inutiles ── */
    [data-testid="stFileUploader"] > label { display: none !important; }
    [data-testid="stFileUploader"] > div { margin-top: -0.5rem; }
    </style>
    """
    st.markdown(BOOMERANG_CSS, unsafe_allow_html=True)

    # ── Initialisation ──────────────────────────────────
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = None
    if "generating" not in st.session_state:
        st.session_state.generating = False

    # Charger l'historique depuis la DB au premier affichage du projet
    if not st.session_state.messages:
        historique = charger_historique(id_projet)
        if historique:
            st.session_state.messages = historique

    has_messages = bool(st.session_state.messages) or st.session_state.pending_input is not None

    # ── Topbar ──────────────────────────────────────────
    plu_info = st.session_state.get("plu_commune", "")
    topbar_badge = f"PLU charge &middot; {plu_info}" if plu_info else "Aucun projet charge"
    st.markdown(f"""
    <div class="bento-topbar">
      <div class="bento-logo">BOOM<span>ERANG</span></div>
      <div class="bento-badge">{topbar_badge}</div>
      <div class="bento-badge success" style="margin-left:auto">Session active</div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    #  GRILLE BENTO 3 COLONNES
    # ══════════════════════════════════════════════════════

    col_left, col_center, col_right = st.columns([1, 2.2, 1], gap="small")

    # ── COLONNE GAUCHE ───────────────────────────────────
    with col_left:
        # -- Bloc Projet --
        st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
        st.markdown('<div class="bento-head">Projet</div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-body">', unsafe_allow_html=True)

        projets = lister_projets()
        options = projets + ["+ Nouveau projet"]
        choix = st.selectbox("Projet", options, index=0 if projets else 0,
                             label_visibility="collapsed", key="bento_projet_select")
        if choix == "+ Nouveau projet":
            nouveau_nom = st.text_input("Nom du nouveau projet", key="bento_new_project",
                                        label_visibility="collapsed",
                                        placeholder="Nom du nouveau projet")
            if nouveau_nom:
                if st.session_state.id_projet != nouveau_nom:
                    st.session_state.messages = []
                st.session_state.id_projet = nouveau_nom
                id_projet = nouveau_nom
        else:
            if st.session_state.id_projet != choix:
                st.session_state.messages = []
            st.session_state.id_projet = choix
            id_projet = choix

        adresse = st.session_state.get("plu_adresse_normalisee", "")
        commune = st.session_state.get("plu_commune", "")
        insee = st.session_state.get("plu_code_insee", "")
        zone = st.session_state.get("plu_zone", "")
        type_doc = st.session_state.get("plu_type_document", "")
        georisques = st.session_state.get("georisques_count", "")

        if adresse:
            st.markdown(f"""
            <div style="font-size:11px;color:#9ca3af;margin-top:6px">Adresse</div>
            <div style="font-size:12px;color:#e8e6e0;font-weight:500;line-height:1.4">{adresse}</div>
            """, unsafe_allow_html=True)
        if zone:
            st.markdown(f"""
            <div style="margin-top:6px;display:inline-block;font-size:10px;
                        padding:2px 8px;border-radius:4px;
                        background:#1a2633;color:#4A90D9;border:0.5px solid #2a3d52">
                Zone {zone} &middot; {type_doc}
            </div>
            """, unsafe_allow_html=True)
        if commune or insee or georisques:
            st.markdown(f"""
            <div class="meta-divider"></div>
            <div class="meta-grid">
                <div class="meta-item">Commune<span>{commune or "—"}</span></div>
                <div class="meta-item">INSEE<span>{insee or "—"}</span></div>
                <div class="meta-item">Georisques
                    <span style="color:#f59e0b">{georisques or "—"}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Actions projet
        if id_projet:
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("Vider", key="bento_clear_hist", use_container_width=True):
                    count = supprimer_historique(id_projet)
                    st.session_state.messages = []
                    st.rerun()
            with btn_cols[1]:
                if st.session_state.messages:
                    from pdf_export import generer_pdf_rapport
                    from db_manager import charger_historique_complet
                    messages_complets = charger_historique_complet(id_projet)
                    if messages_complets:
                        pdf_bytes = generer_pdf_rapport(id_projet, messages_complets)
                        st.download_button(
                            label="PDF",
                            data=pdf_bytes,
                            file_name=f"BOOMERANG_{id_projet}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            key="bento_pdf_export",
                            use_container_width=True,
                        )

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.write("")

        # -- Bloc Modele LLM --
        st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
        st.markdown('<div class="bento-head">Modele LLM</div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-body">', unsafe_allow_html=True)

        modeles = get_ollama_models()
        current = st.session_state.ollama_model
        idx = modeles.index(current) if current in modeles else 0
        choix_modele = st.selectbox(
            "Modele",
            options=modeles,
            index=idx,
            format_func=lambda x: x.replace(":latest", ""),
            label_visibility="collapsed",
            key="bento_model_select",
        )
        if choix_modele != st.session_state.ollama_model:
            st.session_state.ollama_model = choix_modele
            save_settings("last_model", choix_modele)
            if st.session_state.id_projet:
                rebuild_graph()
            st.toast(f"Modele : {choix_modele}")

        # Statut Ollama
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        try:
            _r = requests.get(f"{ollama_base}/api/tags", timeout=2)
            ollama_ok = _r.status_code == 200
        except Exception:
            ollama_ok = False
        status_color = "#22c55e" if ollama_ok else "#ef4444"
        status_label = "Ollama connecte" if ollama_ok else "Ollama hors ligne"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:6px;font-size:10px;color:#6b7280;margin-top:6px">
            <div style="width:5px;height:5px;border-radius:50%;background:{status_color}"></div>
            {status_label}
        </div>
        """, unsafe_allow_html=True)

        # Statut outils
        st.markdown('<div class="meta-divider"></div>', unsafe_allow_html=True)
        for nom, url in TOOL_REGISTRY.items():
            ok = _check_health(url)
            dot = "#22c55e" if ok else "#ef4444"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:5px;font-size:10px;color:#9ca3af;padding:1px 0">
                <div style="width:4px;height:4px;border-radius:50%;background:{dot};flex-shrink:0"></div>
                {nom}
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.write("")

        # -- Bloc Guide depot PC --
        if id_projet:
            st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
            st.markdown('<div class="bento-head">Actions</div>', unsafe_allow_html=True)
            st.markdown('<div class="bento-body">', unsafe_allow_html=True)
            if st.button("Guide depot PC", key="bento_guide_pc", use_container_width=True):
                st.session_state.guide_mode = "depot_pc"
                st.session_state.guide_step = 0
                st.session_state.guide_data = {}
                st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

    # ── COLONNE CENTRALE ─────────────────────────────────
    with col_center:
        st.markdown('<div class="bento-panel" style="display:flex;flex-direction:column">', unsafe_allow_html=True)

        # Quick Actions (chips decoratifs + vrais boutons)
        QUICK_ACTIONS = {
            "Verifier PLU":      "Analyse le PLU de la parcelle et verifie la conformite du projet",
            "Synthese risques":  "Genere une synthese des risques naturels et technologiques",
            "Generer schema":    "Cree un schema de principe du projet",
            "Depot PC":          "Liste les pieces necessaires au depot du permis de construire",
        }
        if not SAAS_MODE:
            QUICK_ACTIONS["FORGE"] = "FORGE — analyse technique approfondie"

        qa_html = '<div class="qa-strip">'
        for label in QUICK_ACTIONS:
            qa_html += f'<div class="qa-chip">{label}</div>'
        qa_html += '</div>'
        st.markdown(qa_html, unsafe_allow_html=True)

        # Vrais boutons (invisibles visuellement, declenchent l'action)
        qa_cols = st.columns(len(QUICK_ACTIONS))
        clicked_action = None
        for i, (label, prompt) in enumerate(QUICK_ACTIONS.items()):
            with qa_cols[i]:
                if st.button(label, key=f"qa_{i}", help=prompt, use_container_width=True):
                    clicked_action = prompt
        if clicked_action:
            st.session_state.messages.append({"role": "user", "content": clicked_action})
            st.session_state.pending_input = clicked_action
            st.rerun()

        # Historique chat (conteneur scrollable)
        chat_container = st.container(height=500)
        with chat_container:
            if not has_messages:
                st.markdown("""
                <div style="display:flex;flex-direction:column;align-items:center;
                            justify-content:center;min-height:300px;text-align:center;padding:2rem">
                    <div style="font-size:1.5rem;font-weight:300;color:#e8e6e0;margin-bottom:0.5rem">
                        Bonjour, bienvenue sur BOOMERANG
                    </div>
                    <div style="font-size:0.9rem;color:#9ca3af">
                        Assistant reglementaire pour architectes
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        _render_message_content(msg["content"])

            # Skeleton pendant la generation
            if st.session_state.get("generating", False):
                st.markdown("""
                <div class="skeleton-wrap">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-lines">
                        <div class="skeleton-line"></div>
                        <div class="skeleton-line"></div>
                        <div class="skeleton-line"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── COLONNE DROITE ───────────────────────────────────
    with col_right:
        # -- Bloc Carte --
        st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
        st.markdown('<div class="bento-head">Localisation</div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-body">', unsafe_allow_html=True)

        map_url = st.session_state.get("plu_map_url")
        if map_url:
            st.image(map_url, use_container_width=True, caption="Geoportail IGN")
            lat = st.session_state.get("plu_latitude", "")
            lon = st.session_state.get("plu_longitude", "")
            if lat and lon:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:10px;
                            color:#6b7280;margin-top:4px">
                    <span>Lat {lat}</span><span>Lon {lon}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="upload-zone" style="height:80px;display:flex;align-items:center;justify-content:center">
                Carte disponible apres chargement PLU
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.write("")

        # -- Bloc Documents --
        st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
        st.markdown('<div class="bento-head">Documents</div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-body">', unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Deposer fichier",
            type=["pdf", "txt", "jpg", "jpeg", "png", "webp", "ifc", "dxf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="bento_doc_uploader",
        )
        if uploaded:
            for f in uploaded:
                ext = f.name.split(".")[-1].upper()
                size = f"{f.size / 1024 / 1024:.1f} Mo" if f.size > 1e6 \
                       else f"{f.size // 1024} Ko"
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;padding:5px 0;
                            border-bottom:0.5px solid #2e333a;font-size:10px;color:#9ca3af">
                    <div style="width:18px;height:18px;border-radius:3px;
                                background:#1a2633;border:0.5px solid #2a3d52;
                                display:flex;align-items:center;justify-content:center;
                                font-size:8px;color:#4A90D9;flex-shrink:0">{ext}</div>
                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;
                                 white-space:nowrap">{f.name}</span>
                    <span style="color:#4b5563">{size}</span>
                </div>
                """, unsafe_allow_html=True)
                # Attacher le premier fichier au contexte si pas deja fait
                if not st.session_state.attached_file_ctx:
                    ctx = _preparer_contexte_fichier(f)
                    if ctx["type"] != "error":
                        st.session_state.attached_file_ctx = ctx

        # Chip fichier attache
        if st.session_state.attached_file_ctx and st.session_state.attached_file_ctx["type"] != "error":
            ctx = st.session_state.attached_file_ctx
            icon = "PDF" if ctx["filename"].lower().endswith(".pdf") else "TXT" if ctx["filename"].lower().endswith(".txt") else "IMG"
            st.markdown(f'<div class="file-chip" style="margin-top:6px">{icon} {ctx["filename"]}</div>', unsafe_allow_html=True)
            if st.button("Retirer", key="bento_remove_file"):
                st.session_state.attached_file_ctx = None
                st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.write("")

        # -- Bloc Cache --
        st.markdown('<div class="bento-panel">', unsafe_allow_html=True)
        st.markdown('<div class="bento-head">Cache API</div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-body">', unsafe_allow_html=True)

        settings = load_settings()
        cache_on = st.toggle(
            "Activer le cache",
            value=settings.get("cache_enabled", True),
            key="bento_toggle_cache",
        )
        if cache_on != settings.get("cache_enabled", True):
            save_settings("cache_enabled", cache_on)
        if cache_on:
            try:
                from db_manager import stats_cache, purge_cache
                cache_stats = stats_cache()
                st.markdown(f"""
                <div style="font-size:10px;color:#9ca3af;margin-top:4px">
                    Actifs : {cache_stats['actifs']} &middot; Expires : {cache_stats['expires']}
                </div>
                """, unsafe_allow_html=True)
                if cache_stats["expires"] > 0:
                    if st.button("Purger", key="bento_purge_cache"):
                        purge_cache()
                        st.rerun()
            except ImportError:
                pass

        st.markdown('</div></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    #  INPUT CHAT (hors colonnes pour ancrage bas natif)
    # ══════════════════════════════════════════════════════

    if st.session_state.get("id_projet"):
        if user_input := st.chat_input(
            "Posez votre question reglementaire...",
            key="main_chat_input",
        ):
            st.session_state.pending_input = user_input
            st.session_state.input_key += 1
            st.rerun()

    # ══════════════════════════════════════════════════════
    #  TRAITEMENT DU MESSAGE PENDING
    #  (logique LangGraph — NE PAS DEPLACER)
    # ══════════════════════════════════════════════════════

    if st.session_state.get("id_projet") and st.session_state.pending_input:
        user_input_text = st.session_state.pending_input
        st.session_state.pending_input = None

        file_ctx = st.session_state.attached_file_ctx
        display_text = user_input_text
        llm_text = user_input_text

        if file_ctx and file_ctx["type"] == "text":
            llm_text = (
                f"{user_input_text}\n\n"
                f"--- CONTENU DU FICHIER JOINT : {file_ctx['filename']} ---\n"
                f"{file_ctx['content'][:15000]}"
            )
            display_text = f"{user_input_text}\n\n*Fichier joint : {file_ctx['filename']}*"
        elif file_ctx and file_ctx["type"] == "image":
            llm_text = (
                f"{user_input_text}\n\n"
                f"[Image jointe : {file_ctx['filename']}]"
            )
            display_text = f"{user_input_text}\n\n*Image jointe : {file_ctx['filename']}*"

        if st.session_state.web_search_enabled:
            llm_text = (
                f"[RECHERCHE WEB DEMANDEE] L'utilisateur souhaite que tu utilises "
                f"l'outil recherche_web pour enrichir ta reponse.\n\n{llm_text}"
            )

        st.session_state.messages.append({"role": "user", "content": display_text})
        sauvegarder_message(id_projet, "user", display_text)

        st.session_state.attached_file_ctx = None
        st.session_state.generating = True

        current_model = st.session_state.ollama_model

        # Verifier si le streaming est active dans les settings
        settings = load_settings()
        use_streaming = settings.get("streaming_enabled", True)

        with col_center:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                status_container = st.container()

                try:
                    if use_streaming:
                        result = _run_streaming(
                            llm_text, thread_id, current_model,
                            placeholder, status_container,
                        )
                    else:
                        with st.status("Agent en reflexion...") as status:
                            result = invoke_graph(
                                llm_text, thread_id,
                                status_widget=status, model_name=current_model,
                            )
                    st.session_state.last_working_model = current_model
                    save_settings("last_model", current_model)
                except Exception as e:
                    logger.error(f"Erreur invoke/stream: {e}")

                    last_ok = st.session_state.get("last_working_model", "")
                    suggestion = f" Essayez **{last_ok}** qui a fonctionne precedemment." if last_ok and last_ok != current_model else ""

                    result = {
                        "response": (
                            f"Le modele **{current_model}** a rencontre une difficulte "
                            f"avec votre demande.{suggestion}\n\n"
                            "Vous pouvez :\n"
                            "- Reformuler votre question\n"
                            "- Changer de modele\n"
                            "- Reessayer dans quelques instants"
                        ),
                        "besoin_forge": None,
                    }

                st.session_state.generating = False

                if result.get("besoin_forge") and not SAAS_MODE:
                    st.session_state.besoin_forge = result["besoin_forge"]
                    st.session_state.forge_mode = "pending"
                    st.rerun()
                else:
                    response = result.get("response", "")
                    if not use_streaming:
                        _render_message_content(response)
                    elif response:
                        placeholder.empty()
                        _render_message_content(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    sauvegarder_message(id_projet, "assistant", response)
