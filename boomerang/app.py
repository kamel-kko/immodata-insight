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
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ───────────────────────────────────────

st.set_page_config(
    page_title="BOOMERANG",
    page_icon="🪃",
    layout="wide",
)

SAAS_MODE = os.getenv("SAAS_MODE", "false").lower() == "true"

# ── Persistance des settings ─────────────────────────
from pathlib import Path as _Path
import json as _json

SETTINGS_FILE = _Path("/app/data/settings.json")


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return _json.load(f)
        except (ValueError, IOError):
            return {}
    return {}


def save_settings(key: str, value: str) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    settings[key] = value
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        _json.dump(settings, f, ensure_ascii=False, indent=2)

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
from graph_orchestrator import invoke_graph, rebuild_graph, get_langfuse_handler
from tool_runner import TOOL_REGISTRY, charger_outils

if not SAAS_MODE:
    from forge_claude import forger_outil, ameliorer_outil

# ── Init DB ─────────────────────────────────────────────

init_db()

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
#  SIDEBAR
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.title("BOOMERANG")

    # ── Sélecteur de projet ─────────────────────────────
    projets = lister_projets()
    options = projets + ["+ Nouveau projet"]
    choix = st.selectbox("Projet", options, index=0 if projets else 0)

    if choix == "+ Nouveau projet":
        nouveau_nom = st.text_input("Nom du nouveau projet")
        if nouveau_nom:
            if st.session_state.id_projet != nouveau_nom:
                st.session_state.messages = []  # reset historique affiché
            st.session_state.id_projet = nouveau_nom
    else:
        if st.session_state.id_projet != choix:
            st.session_state.messages = []  # reset historique lors du changement de projet
        st.session_state.id_projet = choix

    id_projet = st.session_state.id_projet

    # ── Bouton vider historique ─────────────────────────
    if id_projet and st.button("🗑️ Vider historique"):
        count = supprimer_historique(id_projet)
        st.session_state.messages = []
        st.success(f"Historique vidé ({count} messages supprimés)")
        st.rerun()

    st.divider()

    # ── Outils forgés du projet ─────────────────────────
    if id_projet:
        outils_projet = lister_outils_projet(id_projet)
        if outils_projet:
            st.subheader("Outils forgés")
            for outil in outils_projet:
                nom = outil["nom_fichier"]
                url = TOOL_REGISTRY.get(
                    nom.replace("tool_", "", 1),
                    TOOL_REGISTRY.get(nom, "")
                )
                if url and _check_health(url):
                    st.write(f"🟢 {nom} — {outil['statut']}")
                else:
                    st.write(f"🔴 {nom} — {outil['statut']}")

    # ── Statut outils natifs ────────────────────────────
    st.subheader("Outils natifs")
    for nom, url in TOOL_REGISTRY.items():
        if _check_health(url):
            st.write(f"🟢 {nom}")
        else:
            st.write(f"🔴 {nom}")

    # ── Langfuse ────────────────────────────────────────
    st.divider()
    st.caption("📊 [Langfuse](http://localhost:3003)")

    # ── Section Rollback ────────────────────────────────
    if not SAAS_MODE:
        st.divider()
        st.subheader("🔄 Restaurer un outil")

        backups_dir = os.getenv("BACKUPS_DIR", "/app/backups")
        if os.path.exists(backups_dir):
            # Scanner les backups : format {nom_outil}_{YYYYMMDD_HHMMSS}/
            backups = {}
            for entry in os.listdir(backups_dir):
                full_path = os.path.join(backups_dir, entry)
                if os.path.isdir(full_path) and "_" in entry:
                    # Séparer nom_outil du timestamp
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
                    if st.button(f"↩️ Restaurer {nom_outil}", key=f"btn_rollback_{nom_outil}"):
                        version = next(v for v in versions if v["timestamp"] == selected)
                        service_name = f"tool_{nom_outil}"
                        # Arrêter le container
                        subprocess.run(
                            ["docker", "compose", "stop", service_name],
                            cwd="/app/project",
                            capture_output=True, timeout=30,
                        )
                        # Remplacer par le backup
                        dest = os.path.join(
                            os.getenv("TOOLS_DIR", "/app/boomerang_tools"),
                            service_name,
                        )
                        if os.path.exists(dest):
                            shutil.rmtree(dest)
                        shutil.copytree(version["path"], dest)
                        # Relancer
                        subprocess.run(
                            ["docker", "compose", "up", "-d", "--build", service_name],
                            cwd="/app/project",
                            capture_output=True, timeout=120,
                        )
                        # Attendre health
                        url = TOOL_REGISTRY.get(nom_outil, "")
                        if url and _attendre_health(url):
                            st.success(f"✓ {nom_outil} restauré à {selected}")
                        else:
                            st.warning(f"{nom_outil} restauré mais healthcheck timeout")
                        charger_outils()
                        st.rerun()
            else:
                st.caption("Aucun backup disponible")
        else:
            st.caption("Aucun backup disponible")


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
                subprocess.run(
                    ["docker", "compose", "up", "-d", "--build", nom_outil],
                    cwd="/app/project",
                    capture_output=True, timeout=120,
                )

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

                # Écrire le code modifié
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

# ── État NORMAL ─────────────────────────────────────────

else:

    # ── CSS custom inspire de Claude ──────────────────
    st.markdown("""
    <style>
    /* Masquer le label du file uploader */
    [data-testid="stFileUploader"] > label { display: none !important; }
    [data-testid="stFileUploader"] > div { margin-top: -1rem; }

    /* Masquer le label du text_input dans le conteneur de saisie */
    .input-box [data-testid="stTextInput"] > label { display: none !important; }
    .input-box [data-testid="stTextInput"] > div { margin-top: 0; }

    /* Conteneur de saisie unifie (texte + actions) */
    .input-box [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 1.5rem !important;
        border-color: rgba(255,255,255,0.2) !important;
        background: rgba(255,255,255,0.03) !important;
        padding: 0 !important;
    }
    .input-box [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.8rem 1rem 0.4rem 1rem !important;
    }

    /* Text input inside : pas de bordure propre */
    .input-box [data-testid="stTextInput"] input {
        border: none !important;
        background: transparent !important;
        padding: 0.3rem 0 !important;
        font-size: 1rem;
        color: rgba(255,255,255,0.9);
        box-shadow: none !important;
    }
    .input-box [data-testid="stTextInput"] input:focus {
        border: none !important;
        box-shadow: none !important;
    }
    .input-box [data-testid="stTextInput"] input::placeholder {
        color: rgba(255,255,255,0.4);
    }

    /* Boutons d'action dans la barre */
    .input-box button[kind="secondary"] {
        border-radius: 1.2rem !important;
        font-size: 0.82rem !important;
        padding: 0.25rem 0.8rem !important;
        border-color: rgba(255,255,255,0.15) !important;
        background: transparent !important;
    }
    .input-box button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.06) !important;
        border-color: rgba(255,255,255,0.3) !important;
    }
    .input-box button[kind="primary"] {
        border-radius: 1.2rem !important;
        font-size: 0.82rem !important;
        padding: 0.25rem 0.8rem !important;
    }

    /* Selectbox compact dans la barre */
    .input-box [data-testid="stSelectbox"] {
        min-width: 0 !important;
    }
    .input-box [data-testid="stSelectbox"] > label { display: none !important; }
    .input-box [data-testid="stSelectbox"] [data-baseweb="select"] {
        background: transparent !important;
        border-color: rgba(255,255,255,0.15) !important;
        border-radius: 1.2rem !important;
        font-size: 0.82rem !important;
    }

    /* Separateur discret entre texte et actions */
    .input-box hr {
        margin: 0.2rem 0 0.4rem 0;
        border-color: rgba(255,255,255,0.08);
    }

    /* Message de bienvenue centre */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 35vh;
        text-align: center;
        padding: 2rem;
    }
    .welcome-title {
        font-size: 2rem;
        font-weight: 300;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.5rem;
        font-family: 'Georgia', serif;
    }
    .welcome-subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.5);
        margin-bottom: 1rem;
    }

    /* Chips fichier joint */
    .file-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 0.75rem;
        padding: 0.4rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialiser le compteur de cle pour le text_input
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = None

    # Charger l'historique depuis la DB au premier affichage du projet
    if not st.session_state.messages:
        historique = charger_historique(id_projet)
        if historique:
            st.session_state.messages = historique

    has_messages = bool(st.session_state.messages) or st.session_state.pending_input is not None

    # ── Ecran de bienvenue (pas d'historique) ──────────
    if not has_messages:
        st.markdown("""
        <div class="welcome-container">
            <div class="welcome-title">Bonjour, bienvenue sur BOOMERANG</div>
            <div class="welcome-subtitle">Assistant reglementaire pour architectes</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Afficher les messages existants ─────────────────
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                _render_message_content(msg["content"])

    # ══════════════════════════════════════════════════════
    #  TRAITEMENT DU MESSAGE PENDING
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
        with st.chat_message("user"):
            st.markdown(display_text)
        sauvegarder_message(id_projet, "user", display_text)

        st.session_state.attached_file_ctx = None
        st.session_state.show_file_uploader = False

        current_model = st.session_state.ollama_model
        with st.chat_message("assistant"):
            with st.status("Agent en reflexion...") as status:
                try:
                    result = invoke_graph(
                        llm_text,
                        thread_id,
                        status_widget=status,
                        model_name=current_model,
                    )
                    st.session_state.last_working_model = current_model
                    save_settings("last_model", current_model)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Erreur invoke_graph: {e}")

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

            if result.get("besoin_forge") and not SAAS_MODE:
                st.session_state.besoin_forge = result["besoin_forge"]
                st.session_state.forge_mode = "pending"
                st.rerun()
            else:
                response = result.get("response", "")
                _render_message_content(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                sauvegarder_message(id_projet, "assistant", response)

    # ══════════════════════════════════════════════════════
    #  CONTENEUR DE SAISIE STYLE CLAUDE
    # ══════════════════════════════════════════════════════

    if st.session_state.get("id_projet"):

        # ── Chip fichier joint (au-dessus du conteneur) ──
        if st.session_state.attached_file_ctx and st.session_state.attached_file_ctx["type"] != "error":
            ctx = st.session_state.attached_file_ctx
            chip_col1, chip_col2 = st.columns([10, 1])
            with chip_col1:
                icon = "PDF" if ctx["filename"].lower().endswith(".pdf") else "TXT" if ctx["filename"].lower().endswith(".txt") else "IMG"
                st.markdown(f'<div class="file-chip">{icon} {ctx["filename"]}</div>', unsafe_allow_html=True)
            with chip_col2:
                if st.button("x", key="remove_file", help="Retirer le fichier"):
                    st.session_state.attached_file_ctx = None
                    st.session_state.show_file_uploader = False
                    st.rerun()

        # ── Conteneur unifie : texte + actions ───────────
        st.markdown('<div class="input-box">', unsafe_allow_html=True)
        with st.container(border=True):
            user_input = st.text_input(
                "Message",
                placeholder="Comment puis-je vous aider ?",
                label_visibility="collapsed",
                key=f"user_msg_{st.session_state.input_key}",
            )

            st.markdown("<hr>", unsafe_allow_html=True)

            act_cols = st.columns([1, 3, 4, 3])

            with act_cols[0]:
                if st.button("+", key="btn_attach", help="Joindre un fichier"):
                    st.session_state.show_file_uploader = not st.session_state.show_file_uploader
                    st.rerun()

            with act_cols[1]:
                web_label = "Recherche web" if not st.session_state.web_search_enabled else "Recherche web ON"
                web_type = "primary" if st.session_state.web_search_enabled else "secondary"
                if st.button(web_label, key="btn_web", type=web_type):
                    st.session_state.web_search_enabled = not st.session_state.web_search_enabled
                    st.rerun()

            with act_cols[3]:
                modeles = get_ollama_models()
                current = st.session_state.ollama_model
                idx = modeles.index(current) if current in modeles else 0
                choix_modele = st.selectbox(
                    "Modele",
                    options=modeles,
                    index=idx,
                    format_func=lambda x: x.replace(":latest", ""),
                    label_visibility="collapsed",
                    key="model_select_bar",
                )
                if choix_modele != st.session_state.ollama_model:
                    st.session_state.ollama_model = choix_modele
                    save_settings("last_model", choix_modele)
                    if st.session_state.id_projet:
                        rebuild_graph()
                    st.toast(f"Modele : {choix_modele}")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Zone file uploader (visible apres clic +) ────
        if st.session_state.show_file_uploader:
            uploaded_file = st.file_uploader(
                "Joindre un fichier",
                type=["pdf", "txt", "jpg", "jpeg", "png", "webp"],
                key="file_uploader",
                label_visibility="collapsed",
                help="Formats : PDF, TXT, JPG, PNG, WebP (max 10 Mo)",
            )
            if uploaded_file is not None:
                ctx = _preparer_contexte_fichier(uploaded_file)
                if ctx["type"] == "error":
                    st.error(ctx["content"])
                elif ctx["type"] == "image" and not _modele_supporte_vision(st.session_state.ollama_model):
                    st.warning(
                        f"Le modele {st.session_state.ollama_model} ne supporte pas les images. "
                        "Choisissez un modele vision (llava, qwen2-vl...) ou joignez un PDF/TXT."
                    )
                else:
                    st.session_state.attached_file_ctx = ctx
                    st.session_state.show_file_uploader = False
                    st.rerun()

        # ── Detecter nouvelle soumission ─────────────────
        if user_input:
            st.session_state.pending_input = user_input
            st.session_state.input_key += 1
            st.rerun()

    # ── Suggestions rapides (ecran de bienvenue, sous le conteneur) ──
    if not has_messages and st.session_state.get("id_projet"):
        suggestion_cols = st.columns(4)
        suggestions = [
            ("Urbanisme", "Zonage PLU pour une adresse"),
            ("Risques", "Risques naturels d'une parcelle"),
            ("ERP", "Notice de securite incendie"),
            ("Recherche", "Reglementation PMR"),
        ]
        prompts = [
            "Quel est le zonage PLU pour mon adresse ?",
            "Quels sont les risques naturels pour ma parcelle ?",
            "Genere une notice de securite ERP type M, 300 personnes",
            "Quelles sont les normes PMR pour un ERP neuf ?",
        ]
        for i, (label, hint) in enumerate(suggestions):
            with suggestion_cols[i]:
                if st.button(label, key=f"sugg_{i}", use_container_width=True, help=hint):
                    st.session_state.pending_input = prompts[i]
                    st.rerun()
