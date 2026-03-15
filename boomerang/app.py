"""
app.py — BOOMERANG v2
Interface Bento Grid pour architectes.
Chaque tuile est un module independant.
"""

import os
import json
import requests
import streamlit as st

# ── Configuration ────────────────────────────────────────
st.set_page_config(
    page_title="BOOMERANG",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Chemins locaux / Docker ──────────────────────────────
if os.path.exists("/app/data"):
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ── Settings persistence ─────────────────────────────────
def load_settings() -> dict:
    defaults = {"last_model": "mistral-small", "last_address": ""}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except (ValueError, IOError):
            pass
    return defaults


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


# ── Ollama helpers ───────────────────────────────────────
def get_ollama_models() -> list[str]:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models if "name" in m] or ["mistral-small"]
    except Exception:
        return ["mistral-small"]


def ollama_status() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def chat_ollama(messages: list[dict], model: str) -> str:
    """Appel direct a Ollama /api/chat. Retourne la reponse texte."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "Pas de reponse.")
    except requests.exceptions.ConnectionError:
        return "Erreur : impossible de contacter Ollama. Verifiez qu'il est lance."
    except requests.exceptions.Timeout:
        return "Erreur : delai d'attente depasse (120s). Essayez un modele plus leger."
    except Exception as e:
        return f"Erreur : {e}"


# ── Session state ────────────────────────────────────────
_settings = load_settings()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = _settings.get("last_model", "mistral-small")
if "project_address" not in st.session_state:
    st.session_state.project_address = _settings.get("last_address", "")


# ══════════════════════════════════════════════════════════
#  CSS — Theme sombre Bento Grid
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* Reset Streamlit defaults */
    .stApp {
        background-color: #0E0E10;
    }
    header[data-testid="stHeader"] {
        background-color: #0E0E10;
    }
    section[data-testid="stSidebar"] {
        background-color: #161618;
    }

    /* Bento tile */
    .bento-tile {
        background-color: #1A1A1D;
        border: 1px solid #2A2A2E;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    .bento-tile:hover {
        border-color: #444;
    }

    /* Tile header */
    .tile-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid #2A2A2E;
    }
    .tile-icon {
        font-size: 18px;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background-color: #252528;
    }
    .tile-title {
        font-size: 13px;
        font-weight: 600;
        color: #ABABAB;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    .status-online {
        background-color: #0D2818;
        color: #34D399;
        border: 1px solid #166534;
    }
    .status-offline {
        background-color: #2D1215;
        color: #F87171;
        border: 1px solid #7F1D1D;
    }

    /* Chat messages */
    .chat-user {
        background-color: #1E3A5F;
        border-radius: 14px 14px 4px 14px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #E0E0E0;
        max-width: 85%;
        margin-left: auto;
    }
    .chat-assistant {
        background-color: #1E1E22;
        border: 1px solid #2A2A2E;
        border-radius: 14px 14px 14px 4px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #D0D0D0;
        max-width: 85%;
    }

    /* Info cards in dashboard */
    .info-card {
        background-color: #222225;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 4px 0;
    }
    .info-label {
        font-size: 11px;
        color: #777;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .info-value {
        font-size: 15px;
        color: #E0E0E0;
        font-weight: 500;
        margin-top: 2px;
    }

    /* Streamlit overrides */
    .stChatInput > div {
        background-color: #1A1A1D !important;
        border-color: #333 !important;
        border-radius: 12px !important;
    }
    .stSelectbox > div > div {
        background-color: #1A1A1D !important;
        border-color: #333 !important;
    }
    .stTextInput > div > div {
        background-color: #1A1A1D !important;
        border-color: #333 !important;
    }
    .stButton > button {
        background-color: #2563EB;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
        color: white;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Top bar */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0 20px 0;
        border-bottom: 1px solid #1E1E22;
        margin-bottom: 20px;
    }
    .top-bar-title {
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: 2px;
    }
    .top-bar-subtitle {
        font-size: 12px;
        color: #666;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  TOP BAR
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="top-bar">
    <div>
        <div class="top-bar-title">BOOMERANG</div>
        <div class="top-bar-subtitle">Assistant IA pour architectes</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  LAYOUT BENTO — 3 colonnes
# ══════════════════════════════════════════════════════════
col_left, col_center, col_right = st.columns([1, 2.5, 1.2])


# ── TUILE A : Dashboard Projet ───────────────────────────
with col_left:
    st.markdown("""
    <div class="bento-tile">
        <div class="tile-header">
            <div class="tile-icon">📋</div>
            <div class="tile-title">Projet</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Modele Ollama
    models = get_ollama_models()
    current_model = st.session_state.ollama_model
    if current_model not in models:
        models.insert(0, current_model)
    idx = models.index(current_model) if current_model in models else 0

    selected_model = st.selectbox(
        "Modele IA",
        models,
        index=idx,
        key="model_selector",
        label_visibility="collapsed",
    )
    if selected_model != st.session_state.ollama_model:
        st.session_state.ollama_model = selected_model
        s = load_settings()
        s["last_model"] = selected_model
        save_settings(s)

    # Adresse du projet
    address = st.text_input(
        "Adresse du projet",
        value=st.session_state.project_address,
        placeholder="Ex: 12 Rue de la Paix, 75002 Paris",
        key="address_input",
    )
    if address != st.session_state.project_address:
        st.session_state.project_address = address
        s = load_settings()
        s["last_address"] = address
        save_settings(s)

    # Info cards
    st.markdown(f"""
    <div class="info-card">
        <div class="info-label">Modele actif</div>
        <div class="info-value">{selected_model}</div>
    </div>
    """, unsafe_allow_html=True)

    if address:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-label">Adresse</div>
            <div class="info-value">{address}</div>
        </div>
        """, unsafe_allow_html=True)


# ── TUILE E : Statut de la Forge ─────────────────────────
with col_left:
    is_online = ollama_status()
    badge_class = "status-online" if is_online else "status-offline"
    badge_dot = "●" if is_online else "○"
    badge_text = "Ollama connecte" if is_online else "Ollama hors ligne"

    st.markdown(f"""
    <div class="bento-tile">
        <div class="tile-header">
            <div class="tile-icon">⚡</div>
            <div class="tile-title">Statut</div>
        </div>
        <div class="status-badge {badge_class}">
            {badge_dot} {badge_text}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── TUILE B : Chat Central ──────────────────────────────
with col_center:
    st.markdown("""
    <div class="bento-tile" style="min-height: 500px;">
        <div class="tile-header">
            <div class="tile-icon">💬</div>
            <div class="tile-title">Chat</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Afficher l'historique
    for msg in st.session_state.messages:
        css_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
        if msg["role"] == "assistant":
            st.markdown(msg["content"])
        else:
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    # Bouton reset
    if st.session_state.messages:
        if st.button("Nouvelle conversation", key="btn_reset"):
            st.session_state.messages = []
            st.rerun()

    # Input chat
    prompt = st.chat_input("Posez votre question...")

    if prompt:
        # Ajouter le message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Preparer les messages pour Ollama
        system_msg = {
            "role": "system",
            "content": (
                "Tu es BOOMERANG, un assistant expert en reglementation francaise "
                "pour architectes (PLU, ERP, PMR, risques naturels). "
                "Reponds toujours en francais. Sois precis et structure."
            ),
        }
        ollama_messages = [system_msg] + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        # Appel Ollama
        with st.spinner("Reflexion en cours..."):
            response = chat_ollama(ollama_messages, st.session_state.ollama_model)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


# ── TUILE C : Visualiseur ───────────────────────────────
with col_right:
    st.markdown("""
    <div class="bento-tile" style="min-height: 250px;">
        <div class="tile-header">
            <div class="tile-icon">🗺️</div>
            <div class="tile-title">Visualisation</div>
        </div>
        <p style="color: #555; font-size: 13px; text-align: center; margin-top: 40px;">
            Les cartes et schemas apparaitront ici.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── TUILE D : Bibliotheque Documentaire ──────────────────
with col_right:
    st.markdown("""
    <div class="bento-tile">
        <div class="tile-header">
            <div class="tile-icon">📄</div>
            <div class="tile-title">Documents</div>
        </div>
        <p style="color: #555; font-size: 13px; text-align: center; margin-top: 20px;">
            Zone de depot PDF a venir.
        </p>
    </div>
    """, unsafe_allow_html=True)
