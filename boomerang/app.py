# ─────────────────────────────────────────────
#  app.py — BOOMERANG v3
#  Shell interface — aucune logique metier ici
# ─────────────────────────────────────────────

import subprocess
import json
import json as _json
import pathlib
import streamlit as st


# ── Config page ──────────────────────────────

st.set_page_config(
    page_title="BOOMERANG",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Helpers settings ─────────────────────────

SETTINGS_FILE = pathlib.Path("data/settings.json")


def load_settings() -> dict:
    SETTINGS_FILE.parent.mkdir(exist_ok=True)
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}


def save_settings(key: str, value) -> None:
    s = load_settings()
    s[key] = value
    SETTINGS_FILE.write_text(json.dumps(s, indent=2))


# ── Session state init ────────────────────────

DEFAULTS = {
    "messages":        [],
    "generating":      False,
    "project_name":    "",
    "project_address": "",
    "project_insee":   "",
    "project_commune": "",
    "project_zone":    "",
    "project_dept":    "",
    "project_lat":     None,
    "project_lon":     None,
    "model_choice":    load_settings().get("last_model", ""),
    "map_url":         None,
    "mermaid_code":    None,
    "schema_path":     None,
    "chroma_chunks":   0,
    "tool_statuses":   {},
    # PLU module
    "plu_loaded":      False,
    "plu_infos":       None,
    "plu_retriever":   None,
    "plu_chatbot":     None,
    "plu_fiche":       None,
    "plu_messages":    [],
    "plu_type_doc":    "",
    "plu_date_appro":  "",
    "plu_nb_chunks":   0,
    "plu_zones":       [],
    "plu_loading":     False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Fonction utilitaire Ollama ───────────────

def _get_ollama_models() -> list[str]:
    """Retourne la liste des modeles Ollama disponibles localement."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models if "name" in m]
    except Exception:
        pass
    # Fallback : lire settings si Ollama inaccessible
    last = load_settings().get("last_model", "")
    return [last] if last else []


# ══════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════

st.markdown("""<style>
/* ── Reset ── */
#root > div:first-child   { padding-top: 0 !important; }
.block-container          { padding: 0.5rem 0.8rem !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"] { background: #13161a; }
section[data-testid="stSidebar"]   { display: none; }

/* ── Tokens de design ── */
:root {
    --bg0:   #13161a;
    --bg1:   #1a1e24;
    --bg2:   #101317;
    --bdr:   #252b34;
    --acc:   #4a8fd4;
    --acc-b: #152233;
    --acc-d: #1a3050;
    --t1:    #dddbd4;
    --t2:    #838a96;
    --t3:    #3d444e;
    --ok:    #22c55e;
    --warn:  #f59e0b;
    --err:   #ef4444;
    --r:     12px;
    --rs:    8px;
}

/* ── Tuile Bento ── */
.tile {
    background: var(--bg1);
    border: 0.5px solid var(--bdr);
    border-radius: var(--r);
    overflow: hidden;
    margin-bottom: 8px;
}
.tile-head {
    padding: 6px 13px;
    border-bottom: 0.5px solid var(--bdr);
    font-size: 10px;
    font-weight: 500;
    color: var(--t3);
    text-transform: uppercase;
    letter-spacing: .07em;
    display: flex;
    align-items: center;
    gap: 7px;
}
.tile-head::before {
    content: '';
    width: 4px; height: 4px;
    border-radius: 50%;
    background: var(--acc);
    flex-shrink: 0;
}
.tile-body { padding: 11px 13px; }

/* ── Topbar ── */
.topbar {
    background: var(--bg1);
    border: 0.5px solid var(--bdr);
    border-radius: 10px;
    padding: 6px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 7px;
}
.logo    { font-size: 13px; font-weight: 600; color: var(--t1); letter-spacing: .05em; }
.logo em { font-style: normal; color: var(--acc); }
.chip {
    font-size: 10px; padding: 2px 8px;
    border-radius: 4px;
    background: var(--acc-b); color: var(--acc); border: 0.5px solid var(--acc-d);
}
.chip.ok   { background:#162516; color:var(--ok);  border-color:#1e3d1e; }
.chip.warn { background:#2a1f0a; color:var(--warn); border-color:#3d2e10; }
.chip.err  { background:#2a1010; color:var(--err);  border-color:#3d1818; }

/* ── Meta ── */
.meta { display:grid;grid-template-columns:1fr 1fr;gap:2px 10px;margin-top:8px; }
.meta-i { font-size:10px; color:var(--t3); line-height:1.9; }
.meta-i b { display:block; color:var(--t2); font-weight:500; font-size:11px; }
.hdiv  { height:0.5px; background:var(--bdr); margin:9px 0; }

/* ── Skeleton ── */
@keyframes sk{0%,100%{opacity:.25}50%{opacity:.55}}
.sk-wrap { display:flex; gap:9px; padding:6px 0; }
.sk-av   { width:26px;height:26px;border-radius:6px;
           background:var(--bdr);animation:sk 1.4s ease-in-out infinite;flex-shrink:0; }
.sk-col  { flex:1;display:flex;flex-direction:column;gap:5px; }
.sk-l    { height:8px;border-radius:4px;background:var(--bdr);animation:sk 1.4s ease-in-out infinite; }
.sk-l:nth-child(2){width:65%;animation-delay:.2s}
.sk-l:nth-child(3){width:42%;animation-delay:.4s}

/* ── Quick Actions ── */
.qa-row { display:flex;gap:5px;flex-wrap:wrap;
          padding:7px 13px;border-bottom:0.5px solid var(--bdr); }
.qa-chip {
    font-size:10px;padding:3px 10px;border-radius:20px;
    background:var(--acc-b);color:var(--acc);border:0.5px solid var(--acc-d);
    white-space:nowrap;
}

/* ── Upload zone ── */
.drop-zone {
    border:0.5px dashed var(--bdr);border-radius:var(--rs);
    padding:14px;text-align:center;
    font-size:10px;color:var(--t3);margin-bottom:8px;
}

/* ── Widgets Streamlit ── */
[data-testid="stButton"]>button {
    background:var(--acc-b)!important; color:var(--acc)!important;
    border:0.5px solid var(--acc-d)!important; border-radius:6px!important;
    font-size:11px!important; padding:4px 12px!important; font-weight:400!important;
}
[data-testid="stTextInput"] input {
    background:var(--bg2)!important; border:0.5px solid var(--bdr)!important;
    border-radius:6px!important; color:var(--t1)!important; font-size:12px!important;
}
[data-testid="stSelectbox"]>div>div {
    background:var(--bg2)!important; border:0.5px solid var(--bdr)!important;
    border-radius:6px!important; color:var(--t1)!important;
}
[data-testid="stChatMessage"]  { background:transparent!important;border:none!important; }
[data-testid="stExpander"]     { background:var(--bg2)!important;border:0.5px solid var(--bdr)!important;border-radius:8px!important; }
[data-testid="stStatus"]       { background:var(--bg2)!important;border:0.5px solid var(--bdr)!important;border-radius:8px!important; }
[data-testid="stFileUploader"] { background:var(--bg2)!important;border-radius:8px!important; }
::-webkit-scrollbar            { width:3px; }
::-webkit-scrollbar-thumb      { background:var(--bdr);border-radius:2px; }
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  TOPBAR
# ══════════════════════════════════════════════

def render_topbar():
    commune = st.session_state.project_commune
    zone    = st.session_state.project_zone
    model   = st.session_state.model_choice

    badge_proj = (
        f'<span class="chip">{commune} · Zone {zone}</span>'
        if commune
        else '<span class="chip warn">Aucun projet charge</span>'
    )
    badge_model = (
        f'<span class="chip">{model}</span>'
        if model
        else '<span class="chip err">Modele non selectionne</span>'
    )

    st.markdown(f"""
    <div class="topbar">
        <div class="logo">BOOM<em>ERANG</em></div>
        {badge_proj}
        {badge_model}
        <span class="chip ok" style="margin-left:auto">✓ Pret</span>
    </div>""", unsafe_allow_html=True)


render_topbar()


# ══════════════════════════════════════════════
#  GRILLE PRINCIPALE
# ══════════════════════════════════════════════

col_left, col_center, col_right = st.columns([1, 2.1, 1], gap="small")


# ════════════════════════════════════════════
#  COLONNE GAUCHE
#  Tuile A : Projet   |   Tuile E : Activite
# ════════════════════════════════════════════

with col_left:

    # ── Tuile A — Projet ──────────────────
    st.markdown(
        '<div class="tile">'
        '<div class="tile-head">Projet</div>'
        '<div class="tile-body">',
        unsafe_allow_html=True,
    )

    addr_input = st.text_input(
        "Adresse",
        placeholder="12 rue de la Mairie, 40230 Tosse",
        value=st.session_state.project_address,
        label_visibility="collapsed",
        key="addr_input",
    )

    if st.button("Analyser", key="btn_analyse", use_container_width=True):
        st.session_state.project_address = addr_input
        if addr_input.strip():
            st.session_state.plu_loading = True
            st.rerun()
        else:
            st.warning("Saisissez une adresse.")

    if st.session_state.project_commune:
        zone_display = st.session_state.project_zone or "—"
        plu_badge = ""
        if st.session_state.plu_type_doc:
            plu_badge = (
                f'<div style="display:inline-block;background:var(--acc-b);'
                f'color:var(--acc);border:0.5px solid var(--acc-d);'
                f'border-radius:4px;padding:2px 8px;font-size:10px;'
                f'margin:4px 0">Zone {zone_display} · {st.session_state.plu_type_doc}'
                f' {st.session_state.plu_date_appro[:4] if st.session_state.plu_date_appro else ""}</div>'
            )
        st.markdown(f"""
        {plu_badge}
        <div class="hdiv"></div>
        <div class="meta">
            <div class="meta-i">Commune<b>{st.session_state.project_commune}</b></div>
            <div class="meta-i">INSEE<b>{st.session_state.project_insee}</b></div>
            <div class="meta-i">Dept.<b>Landes ({st.session_state.project_dept})</b></div>
            <div class="meta-i">Georisques<b style="color:var(--warn)">—</b></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.write("")

    # ── Tuile E — Activite Forge ──────────
    st.markdown(
        '<div class="tile">'
        '<div class="tile-head">Activite</div>'
        '<div class="tile-body">',
        unsafe_allow_html=True,
    )

    activity_placeholder = st.empty()
    activity_placeholder.markdown(
        '<div style="font-size:11px;color:var(--t3)">En attente…</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Selecteur modele ─────────────────
    st.markdown(
        '<div class="tile">'
        '<div class="tile-head">Modele LLM</div>'
        '<div class="tile-body">',
        unsafe_allow_html=True,
    )

    available_models = _get_ollama_models()
    if available_models:
        idx = (
            available_models.index(st.session_state.model_choice)
            if st.session_state.model_choice in available_models
            else 0
        )
        choice = st.selectbox(
            "Modele",
            available_models,
            index=idx,
            label_visibility="collapsed",
            key="model_select",
        )
        if choice != st.session_state.model_choice:
            st.session_state.model_choice = choice
            save_settings("last_model", choice)
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--err)">Ollama non detecte</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════
#  COLONNE CENTRALE
#  Tuile B : Chat
# ════════════════════════════════════════════

with col_center:
    st.markdown('<div class="tile">', unsafe_allow_html=True)

    # Quick Actions
    QA = {
        "Verifier PLU":     "Analyse le PLU de la parcelle et verifie la conformite",
        "Synthese risques": "Genere une synthese des risques naturels Georisques",
        "Generer schema":   "Cree un schema de principe Mermaid pour ce projet",
        "Depot PC":         "Liste les pieces requises pour le permis de construire",
        "FORGE":            "FORGE — analyse technique approfondie et exhaustive",
    }

    st.markdown(
        '<div class="qa-row">'
        + "".join(f'<span class="qa-chip">{k}</span>' for k in QA)
        + "</div>",
        unsafe_allow_html=True,
    )

    qa_cols = st.columns(len(QA))
    for i, (label, prompt_text) in enumerate(QA.items()):
        with qa_cols[i]:
            if st.button(label, key=f"qa_{i}", use_container_width=True):
                st.session_state.messages.append(
                    {"role": "user", "content": prompt_text}
                )
                st.session_state.generating = True
                st.rerun()

    # Historique
    chat_area = st.container(height=480)
    with chat_area:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if st.session_state.generating:
            st.markdown("""
            <div class="sk-wrap">
                <div class="sk-av"></div>
                <div class="sk-col">
                    <div class="sk-l"></div>
                    <div class="sk-l"></div>
                    <div class="sk-l"></div>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════
#  COLONNE DROITE
#  Tuile C : Visualisation  |  Tuile D : Docs
# ════════════════════════════════════════════

with col_right:

    # ── Tuile C — Visualisation ───────────
    st.markdown(
        '<div class="tile">'
        '<div class="tile-head">Visualisation</div>'
        '<div class="tile-body">',
        unsafe_allow_html=True,
    )

    if st.session_state.map_url:
        st.image(st.session_state.map_url, use_container_width=True)
    elif st.session_state.schema_path:
        st.image(st.session_state.schema_path, use_container_width=True)
    elif st.session_state.mermaid_code:
        st.components.v1.html(
            "<div class='mermaid'>" + st.session_state.mermaid_code + "</div>"
            "<script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'></script>",
            height=200,
        )
    else:
        st.markdown(
            '<div class="drop-zone" style="height:90px;display:flex;'
            'align-items:center;justify-content:center">'
            "Carte · Schema · Graphique</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Tuile D — Documents ───────────────
    st.markdown(
        '<div class="tile">'
        '<div class="tile-head">Documents</div>'
        '<div class="tile-body">',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Deposer IFC / DXF / PDF",
        type=["pdf", "ifc", "dxf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="doc_uploader",
    )
    if uploaded:
        for f in uploaded:
            ext = f.name.rsplit(".", 1)[-1].upper()
            size = (
                f"{f.size / 1048576:.1f}Mo"
                if f.size > 1e6
                else f"{f.size // 1024}Ko"
            )
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:7px;padding:4px 0;'
                f'border-bottom:0.5px solid var(--bdr);font-size:10px;color:var(--t2)">'
                f'<span style="background:var(--acc-b);color:var(--acc);'
                f'border:0.5px solid var(--acc-d);border-radius:3px;'
                f'padding:1px 4px;font-size:9px">{ext}</span>'
                f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap">{f.name}</span>'
                f'<span style="color:var(--t3)">{size}</span></div>',
                unsafe_allow_html=True,
            )

    # Statut ChromaDB
    n = st.session_state.chroma_chunks
    st.markdown(
        f'<div class="hdiv"></div>'
        f'<div style="font-size:10px;color:var(--t3)">Base vectorielle</div>'
        f'<div style="font-size:11px;color:var(--t2);margin-top:2px">'
        f'{"Non initialisee" if n == 0 else f"{n} chunks indexes"}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div></div>", unsafe_allow_html=True)


# ── Chat input — hors colonnes (ancrage natif Streamlit) ──

if user_input := st.chat_input("Question reglementaire, analyse de site…"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.generating = True
    st.rerun()


# ── Traitement LLM — placeholder (module chat a venir) ───

if st.session_state.generating:
    last = st.session_state.messages[-1]["content"]
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            f"*Module LLM non encore connecte.* "
            f"Votre message : « {last} »"
        ),
    })
    st.session_state.generating = False
    st.rerun()
