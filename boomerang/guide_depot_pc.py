"""
guide_depot_pc.py -- Guide pas-a-pas pour le depot de Permis de Construire

Wizard en 6 etapes qui collecte les infos du projet et appelle
automatiquement les outils BOOMERANG (urbanisme, risques, legal).
"""

import re
import streamlit as st
import requests
import logging

logger = logging.getLogger(__name__)

ETAPES = [
    {"titre": "Localisation du projet", "icone": "1"},
    {"titre": "Verification PLU / zonage", "icone": "2"},
    {"titre": "Risques naturels et technologiques", "icone": "3"},
    {"titre": "Description du projet", "icone": "4"},
    {"titre": "Pieces requises (checklist CERFA)", "icone": "5"},
    {"titre": "Resume et export", "icone": "6"},
]

# Pieces PCMI (Permis de Construire Maison Individuelle) selon R431-35 et suivants
PIECES_PCMI = [
    ("PCMI1", "Plan de situation du terrain (1/5000 ou 1/25000)"),
    ("PCMI2", "Plan de masse cote dans les 3 dimensions (1/100 ou 1/200)"),
    ("PCMI3", "Plan de coupe du terrain et de la construction (1/100 ou 1/200)"),
    ("PCMI4", "Notice decrivant le terrain et le projet"),
    ("PCMI5", "Plan des facades et des toitures"),
    ("PCMI6", "Document graphique d'insertion du projet dans l'environnement"),
    ("PCMI7", "Photographie de l'environnement proche"),
    ("PCMI8", "Photographie de l'environnement lointain"),
]

PIECES_SUPPLEMENTAIRES = [
    ("Si ERP", "Notice de securite incendie (type + categorie)"),
    ("Si ERP", "Notice d'accessibilite PMR"),
    ("Si zone inondable", "Etude hydraulique ou attestation de non-aggravation"),
    ("Si zone sismique >= 2", "Attestation parasismique (apres travaux)"),
    ("Si RT2020", "Attestation de prise en compte de la RE2020"),
    ("Si lotissement", "Certificat d'achevement des equipements communs"),
    ("Si architecte obligatoire", "Recepisse d'inscription a l'Ordre"),
]


# ── Appels outils ─────────────────────────────────────────

def _appeler_outil(tool_url: str, query: str, timeout: int = 30) -> str:
    try:
        resp = requests.post(
            f"{tool_url}/run",
            json={"input": {"query": query}},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("output", "Pas de resultat.")
    except Exception as e:
        return f"Erreur : {e}"


def _check_outil_dispo(tool_url: str) -> bool:
    try:
        r = requests.get(f"{tool_url}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ── Parsers pour structurer les reponses brutes des outils ──

def _parser_plu(raw: str) -> dict:
    """Parse la reponse brute de tool_api_urbanisme en dict structure."""
    result = {
        "adresse_normalisee": "",
        "coords": "",
        "zones": [],
        "source": "",
        "map_url": "",
    }

    # Adresse et coords depuis la premiere ligne
    m = re.search(r"ZONAGE PLU\s*(?:--|—)\s*(.+?)\s*\(([^)]+)\)", raw)
    if m:
        result["adresse_normalisee"] = m.group(1).strip()
        result["coords"] = m.group(2).strip()

    # Zones (peut y en avoir plusieurs)
    for zm in re.finditer(
        r"Zone\s*:\s*(\S+)\s*(?:--|—)\s*(.+?)(?:\n|$)"
        r"(?:.*?Libell[eé] complet\s*:\s*(.+?)(?:\n|$))?"
        r"(?:.*?Destination dominante\s*:\s*(.+?)(?:\n|$))?"
        r"(?:.*?Document\s*:\s*(.+?)(?:\n|$))?",
        raw, flags=re.DOTALL
    ):
        zone = {
            "type": zm.group(1).strip(),
            "libelle": zm.group(2).strip() if zm.group(2) else "",
            "libelle_complet": zm.group(3).strip() if zm.group(3) else "",
            "destination": zm.group(4).strip() if zm.group(4) else "",
            "document": zm.group(5).strip() if zm.group(5) else "",
        }
        result["zones"].append(zone)

    # Source
    m_src = re.search(r"Source\s*:\s*(.+?)(?:\n|$)", raw)
    if m_src:
        result["source"] = m_src.group(1).strip()

    # MAP_URL
    m_map = re.search(r"MAP_URL:\s*(https?://\S+)", raw)
    if m_map:
        result["map_url"] = m_map.group(1).strip()

    return result


def _parser_risques(raw: str) -> dict:
    """Parse la reponse brute de tool_georisques en dict structure."""
    result = {
        "commune": "",
        "code_insee": "",
        "risques": [],
        "radon_classe": "",
        "radon_detail": "",
        "mouvements_terrain": "",
    }

    # Commune et INSEE
    m = re.search(r"(?:--|—)\s*(.+?)\s*\(INSEE\s*:\s*(\d+)\)", raw)
    if m:
        result["commune"] = m.group(1).strip()
        result["code_insee"] = m.group(2).strip()

    # Risques individuels
    for rm in re.finditer(r"^\s*-\s*(.+?)(?:\(code\s*:\s*(\w+)\))?$", raw, re.MULTILINE):
        risque_text = rm.group(1).strip().rstrip(" (")
        code = rm.group(2).strip() if rm.group(2) else ""
        result["risques"].append({"libelle": risque_text, "code": code})

    # Radon
    m_rad = re.search(r"POTENTIEL RADON\s*:\s*classe\s*(\d)/3", raw)
    if m_rad:
        result["radon_classe"] = m_rad.group(1)
    m_rad_detail = re.search(r"POTENTIEL RADON.*?\n\s*(.+?)(?:\n|$)", raw)
    if m_rad_detail and "classe" not in m_rad_detail.group(1).lower():
        result["radon_detail"] = m_rad_detail.group(1).strip()

    # Mouvements de terrain
    m_mvt = re.search(r"MOUVEMENTS DE TERRAIN\s*:\s*(.+?)(?:\n|$)", raw)
    if m_mvt:
        result["mouvements_terrain"] = m_mvt.group(1).strip()

    return result


# ── Composants UI ─────────────────────────────────────────

def _barre_progression(step: int):
    total = len(ETAPES)
    progress = step / total
    st.progress(progress)
    cols = st.columns(total)
    for i, etape in enumerate(ETAPES):
        with cols[i]:
            if i < step:
                st.markdown(f"**:green[{etape['icone']}]**")
            elif i == step:
                st.markdown(f"**:blue[{etape['icone']}]**")
            else:
                st.markdown(f":gray[{etape['icone']}]")


def _nav_buttons(step: int):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if step > 0 and st.button("Precedent"):
            st.session_state.guide_step = step - 1
            st.rerun()
    with col3:
        if step < len(ETAPES) - 1 and st.button("Suivant", type="primary"):
            st.session_state.guide_step = step + 1
            st.rerun()


def _metric_card(label: str, value: str, color: str = "#4A90D9"):
    """Affiche une metrique dans un mini-panneau style."""
    st.markdown(f"""
    <div style="background:#22262c;border:0.5px solid #2e333a;border-radius:8px;
                padding:10px 14px;margin-bottom:6px">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;
                    letter-spacing:0.04em">{label}</div>
        <div style="font-size:14px;color:{color};font-weight:500;margin-top:2px">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def _risk_badge(libelle: str, code: str = ""):
    """Affiche un risque sous forme de badge colore."""
    # Couleur selon le type de risque
    text_lower = libelle.lower()
    if "inondation" in text_lower or "submersion" in text_lower:
        bg, border, color = "#1e2a3a", "#2a4a6a", "#60a5fa"
    elif "sism" in text_lower:
        bg, border, color = "#2a1e1e", "#6a2a2a", "#f87171"
    elif "mouvement" in text_lower or "terrain" in text_lower:
        bg, border, color = "#2a2a1e", "#6a5a2a", "#fbbf24"
    elif "transport" in text_lower or "industriel" in text_lower:
        bg, border, color = "#2a1e2a", "#5a2a6a", "#c084fc"
    else:
        bg, border, color = "#1e2a22", "#2a5a3a", "#4ade80"

    code_str = f"<span style='font-size:9px;color:#6b7280;margin-left:6px'>({code})</span>" if code else ""
    st.markdown(f"""
    <div style="background:{bg};border:0.5px solid {border};border-radius:6px;
                padding:8px 12px;margin-bottom:4px;display:flex;align-items:center">
        <div style="width:6px;height:6px;border-radius:50%;background:{color};
                    flex-shrink:0;margin-right:8px"></div>
        <span style="font-size:12px;color:{color}">{libelle}</span>
        {code_str}
    </div>
    """, unsafe_allow_html=True)


# ── Etapes du guide ───────────────────────────────────────

def _etape_localisation():
    st.markdown("Entrez l'adresse du terrain ou les coordonnees GPS du projet.")

    data = st.session_state.guide_data

    adresse = st.text_input(
        "Adresse du terrain",
        value=data.get("adresse", ""),
        placeholder="Ex: 12 rue de Rivoli, 75001 Paris",
    )
    if adresse:
        data["adresse"] = adresse

    col1, col2 = st.columns(2)
    with col1:
        parcelle = st.text_input(
            "Reference cadastrale (optionnel)",
            value=data.get("parcelle", ""),
            placeholder="Ex: AB 123",
        )
        if parcelle:
            data["parcelle"] = parcelle
    with col2:
        commune = st.text_input(
            "Commune",
            value=data.get("commune", ""),
            placeholder="Ex: Paris 1er",
        )
        if commune:
            data["commune"] = commune

    if adresse:
        st.success(
            "Adresse enregistree. Cliquez sur **Suivant** pour lancer "
            "l'analyse PLU automatique."
        )


def _etape_plu(tool_registry: dict):
    data = st.session_state.guide_data
    adresse = data.get("adresse", "")

    if not adresse:
        st.warning("Retournez a l'etape 1 pour saisir une adresse.")
        return

    url_urba = tool_registry.get("recherche_urbanisme")

    # Appel outil si pas encore fait
    if url_urba and _check_outil_dispo(url_urba):
        if "resultat_plu" not in data:
            with st.spinner("Interrogation du Geoportail de l'Urbanisme..."):
                resultat = _appeler_outil(url_urba, adresse)
                data["resultat_plu"] = resultat
                data["plu_parsed"] = _parser_plu(resultat)
    else:
        st.warning(
            "L'outil urbanisme n'est pas disponible. "
            "Vous pouvez saisir les infos manuellement."
        )
        zone_manuelle = st.text_area(
            "Zone PLU / regles connues",
            value=data.get("resultat_plu", ""),
        )
        if zone_manuelle:
            data["resultat_plu"] = zone_manuelle
        return

    # Affichage structure
    plu = data.get("plu_parsed", {})
    if not plu:
        plu = _parser_plu(data.get("resultat_plu", ""))
        data["plu_parsed"] = plu

    # Adresse normalisee
    if plu.get("adresse_normalisee"):
        _metric_card("Adresse normalisee (BAN)", plu["adresse_normalisee"], "#e8e6e0")

    # Zones PLU
    if plu.get("zones"):
        for zone in plu["zones"]:
            col_z, col_d = st.columns([1, 2])
            with col_z:
                _metric_card("Zone PLU", zone["type"])
            with col_d:
                libelle = zone.get("libelle_complet") or zone.get("libelle", "")
                _metric_card("Designation", libelle or "Non renseignee", "#9ca3af")

            if zone.get("document"):
                st.caption(f"Document de reference : {zone['document']}")
    else:
        st.info("Aucune zone PLU trouvee pour cette adresse.")

    # Carte cadastrale
    if plu.get("map_url"):
        st.markdown("---")
        st.markdown("**Carte cadastrale**")
        try:
            st.image(plu["map_url"], caption="Geoportail IGN - Parcellaire", use_container_width=True)
        except Exception:
            st.markdown(f"[Voir la carte]({plu['map_url']})")

        # Stocker les coords pour la colonne droite de l'app
        if plu.get("coords"):
            parts = plu["coords"].split(",")
            if len(parts) == 2:
                try:
                    st.session_state["plu_latitude"] = parts[0].strip()
                    st.session_state["plu_longitude"] = parts[1].strip()
                except ValueError:
                    pass

    # Source
    if plu.get("source"):
        st.caption(f"Source : {plu['source']}")

    # Donnees brutes en accordeon
    with st.expander("Donnees brutes de l'outil", expanded=False):
        st.code(data.get("resultat_plu", ""), language=None)


def _etape_risques(tool_registry: dict):
    data = st.session_state.guide_data
    adresse = data.get("adresse", "")

    if not adresse:
        st.warning("Retournez a l'etape 1 pour saisir une adresse.")
        return

    url_risques = tool_registry.get("recherche_risques_parcelle")

    # Appel outil si pas encore fait
    if url_risques and _check_outil_dispo(url_risques):
        if "resultat_risques" not in data:
            with st.spinner("Interrogation de l'API Georisques..."):
                resultat = _appeler_outil(url_risques, adresse)
                data["resultat_risques"] = resultat
                data["risques_parsed"] = _parser_risques(resultat)
    else:
        st.warning(
            "L'outil Georisques n'est pas disponible. "
            "Vous pouvez saisir les risques manuellement."
        )
        zone_manuelle = st.text_area(
            "Risques connus (inondation, sismicite, radon...)",
            value=data.get("resultat_risques", ""),
        )
        if zone_manuelle:
            data["resultat_risques"] = zone_manuelle
        return

    # Affichage structure
    risques = data.get("risques_parsed", {})
    if not risques:
        risques = _parser_risques(data.get("resultat_risques", ""))
        data["risques_parsed"] = risques

    # En-tete commune
    col1, col2 = st.columns(2)
    with col1:
        if risques.get("commune"):
            _metric_card("Commune", risques["commune"], "#e8e6e0")
    with col2:
        if risques.get("code_insee"):
            _metric_card("Code INSEE", risques["code_insee"])

    # Liste des risques
    if risques.get("risques"):
        st.markdown("---")
        nb = len(risques["risques"])
        color = "#f87171" if nb >= 3 else "#fbbf24" if nb >= 1 else "#4ade80"
        st.markdown(f"""
        <div style="font-size:12px;color:{color};font-weight:500;margin-bottom:8px">
            {nb} risque(s) identifie(s) sur la commune
        </div>
        """, unsafe_allow_html=True)
        for r in risques["risques"]:
            _risk_badge(r["libelle"], r.get("code", ""))
    else:
        st.success("Aucun risque majeur identifie sur cette commune.")

    # Radon
    if risques.get("radon_classe"):
        st.markdown("---")
        classe = risques["radon_classe"]
        if classe == "3":
            radon_color = "#f87171"
            radon_label = "Eleve"
        elif classe == "2":
            radon_color = "#fbbf24"
            radon_label = "Modere"
        else:
            radon_color = "#4ade80"
            radon_label = "Faible"
        _metric_card(f"Potentiel radon (classe {classe}/3)", radon_label, radon_color)

    # Mouvements de terrain
    if risques.get("mouvements_terrain"):
        _metric_card("Mouvements de terrain", risques["mouvements_terrain"], "#fbbf24")

    # Donnees brutes en accordeon
    with st.expander("Donnees brutes de l'outil", expanded=False):
        st.code(data.get("resultat_risques", ""), language=None)


def _etape_description():
    st.markdown("Ces informations serviront a determiner les pieces complementaires requises.")

    data = st.session_state.guide_data

    type_projet = st.selectbox(
        "Type de projet",
        ["Maison individuelle", "Extension", "Renovation lourde",
         "Immeuble collectif", "ERP (commerce, bureau...)", "Autre"],
        index=["Maison individuelle", "Extension", "Renovation lourde",
               "Immeuble collectif", "ERP (commerce, bureau...)", "Autre"].index(
            data.get("type_projet", "Maison individuelle")
        ),
    )
    data["type_projet"] = type_projet

    col1, col2 = st.columns(2)
    with col1:
        surface_plancher = st.number_input(
            "Surface de plancher creee (m2)",
            min_value=0, max_value=50000,
            value=data.get("surface_plancher", 0),
        )
        data["surface_plancher"] = surface_plancher
    with col2:
        surface_terrain = st.number_input(
            "Surface du terrain (m2)",
            min_value=0, max_value=500000,
            value=data.get("surface_terrain", 0),
        )
        data["surface_terrain"] = surface_terrain

    hauteur = st.number_input(
        "Hauteur maximale du projet (m)",
        min_value=0.0, max_value=200.0, step=0.5,
        value=data.get("hauteur", 0.0),
    )
    data["hauteur"] = hauteur

    if type_projet == "ERP (commerce, bureau...)":
        st.markdown("---")
        st.markdown("**Informations ERP**")
        col1, col2 = st.columns(2)
        with col1:
            type_erp = st.text_input(
                "Type ERP (M, N, L, O, W...)",
                value=data.get("type_erp", ""),
            )
            if type_erp:
                data["type_erp"] = type_erp
        with col2:
            capacite = st.number_input(
                "Capacite d'accueil (personnes)",
                min_value=0, max_value=50000,
                value=data.get("capacite", 0),
            )
            data["capacite"] = capacite

    architecte_obligatoire = surface_plancher > 150
    data["architecte_obligatoire"] = architecte_obligatoire
    if architecte_obligatoire:
        st.info(
            "Surface > 150 m2 : le recours a un architecte est obligatoire "
            "(article R431-2 du Code de l'urbanisme)."
        )


def _etape_checklist():
    data = st.session_state.guide_data
    type_projet = data.get("type_projet", "Maison individuelle")
    is_erp = type_projet == "ERP (commerce, bureau...)"
    resultat_risques = data.get("resultat_risques", "").lower()
    zone_inondable = any(mot in resultat_risques for mot in ["inondation", "ppri", "submersion"])
    zone_sismique = any(mot in resultat_risques for mot in ["sismique", "sismicit"])

    st.markdown("Cochez les pieces au fur et a mesure de leur preparation.")

    if "checklist" not in data:
        data["checklist"] = {}

    # Pieces obligatoires PCMI
    st.markdown("**Pieces obligatoires (PCMI)**")
    for code, desc in PIECES_PCMI:
        key = f"check_{code}"
        checked = st.checkbox(
            f"**{code}** -- {desc}",
            value=data["checklist"].get(key, False),
            key=key,
        )
        data["checklist"][key] = checked

    # Pieces supplementaires conditionnelles
    pieces_supp = []
    if is_erp:
        pieces_supp.append(("Notice securite incendie", True))
        pieces_supp.append(("Notice accessibilite PMR", True))
    if zone_inondable:
        pieces_supp.append(("Etude hydraulique / attestation non-aggravation", True))
    if zone_sismique:
        pieces_supp.append(("Attestation parasismique", True))
    if data.get("surface_plancher", 0) > 50:
        pieces_supp.append(("Attestation RE2020 (prise en compte)", True))
    if data.get("architecte_obligatoire"):
        pieces_supp.append(("Recepisse inscription Ordre des architectes", True))

    if pieces_supp:
        st.markdown("---")
        st.markdown("**Pieces complementaires (selon votre projet)**")
        for desc, _ in pieces_supp:
            key = f"check_supp_{desc[:20]}"
            checked = st.checkbox(
                desc,
                value=data["checklist"].get(key, False),
                key=key,
            )
            data["checklist"][key] = checked

    # Compteur et barre de progression
    st.markdown("---")
    total = len(PIECES_PCMI) + len(pieces_supp)
    done = sum(1 for k, v in data["checklist"].items() if v)
    st.progress(done / total if total > 0 else 0)
    st.markdown(f"**{done}/{total}** pieces preparees")
    if done == total and total > 0:
        st.success("Toutes les pieces sont pretes !")


def _etape_resume():
    data = st.session_state.guide_data

    # Infos generales
    col1, col2 = st.columns(2)
    with col1:
        _metric_card("Adresse", data.get("adresse", "Non renseignee"), "#e8e6e0")
        _metric_card("Commune", data.get("commune", "Non renseignee"), "#9ca3af")
        _metric_card("Parcelle", data.get("parcelle", "Non renseignee"), "#9ca3af")
    with col2:
        _metric_card("Type de projet", data.get("type_projet", "Non renseigne"))
        _metric_card("Surface plancher", f"{data.get('surface_plancher', 0)} m2")
        _metric_card("Hauteur", f"{data.get('hauteur', 0)} m")

    if data.get("architecte_obligatoire"):
        st.warning("Architecte obligatoire (surface > 150 m2)")

    # PLU
    plu = data.get("plu_parsed", {})
    if plu and plu.get("zones"):
        st.markdown("---")
        st.markdown("**Zonage PLU**")
        for zone in plu["zones"]:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                _metric_card("Zone", zone["type"])
            with col_b:
                _metric_card("Designation", zone.get("libelle_complet") or zone.get("libelle", ""), "#9ca3af")

    # Risques
    risques = data.get("risques_parsed", {})
    if risques and risques.get("risques"):
        st.markdown("---")
        st.markdown("**Risques identifies**")
        for r in risques["risques"]:
            _risk_badge(r["libelle"], r.get("code", ""))

    # Checklist
    checklist = data.get("checklist", {})
    if checklist:
        st.markdown("---")
        st.markdown("**Avancement des pieces**")
        done = sum(1 for v in checklist.values() if v)
        total = len(checklist)
        st.progress(done / total if total > 0 else 0)
        st.markdown(f"**{done}/{total}** pieces pretes")

    # Export
    st.markdown("---")
    resume_txt = _generer_resume_texte(data)
    st.download_button(
        label="Telecharger le resume (texte)",
        data=resume_txt,
        file_name="resume_depot_pc.txt",
        mime="text/plain",
    )

    if st.button("Revenir au mode conversation", type="primary"):
        st.session_state.guide_mode = None
        st.rerun()


def _generer_resume_texte(data: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("BOOMERANG -- Resume Depot Permis de Construire")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Adresse    : {data.get('adresse', 'Non renseignee')}")
    lines.append(f"Commune    : {data.get('commune', 'Non renseignee')}")
    lines.append(f"Parcelle   : {data.get('parcelle', 'Non renseignee')}")
    lines.append(f"Type       : {data.get('type_projet', 'Non renseigne')}")
    lines.append(f"Surface    : {data.get('surface_plancher', 0)} m2")
    lines.append(f"Hauteur    : {data.get('hauteur', 0)} m")
    lines.append(f"Architecte : {'Obligatoire' if data.get('architecte_obligatoire') else 'Non obligatoire'}")
    lines.append("")

    # PLU structure
    plu = data.get("plu_parsed", {})
    if plu and plu.get("zones"):
        lines.append("-" * 40)
        lines.append("ZONAGE PLU")
        lines.append("-" * 40)
        for zone in plu["zones"]:
            lines.append(f"  Zone : {zone['type']}")
            if zone.get("libelle_complet"):
                lines.append(f"  Designation : {zone['libelle_complet']}")
            if zone.get("document"):
                lines.append(f"  Document : {zone['document']}")
        lines.append("")
    elif data.get("resultat_plu"):
        lines.append("-" * 40)
        lines.append("ZONAGE PLU")
        lines.append("-" * 40)
        lines.append(data["resultat_plu"])
        lines.append("")

    # Risques structures
    risques = data.get("risques_parsed", {})
    if risques and risques.get("risques"):
        lines.append("-" * 40)
        lines.append("RISQUES IDENTIFIES")
        lines.append("-" * 40)
        for r in risques["risques"]:
            code_str = f" ({r['code']})" if r.get("code") else ""
            lines.append(f"  - {r['libelle']}{code_str}")
        if risques.get("radon_classe"):
            lines.append(f"  Radon : classe {risques['radon_classe']}/3")
        if risques.get("mouvements_terrain"):
            lines.append(f"  Mouvements de terrain : {risques['mouvements_terrain']}")
        lines.append("")
    elif data.get("resultat_risques"):
        lines.append("-" * 40)
        lines.append("RISQUES IDENTIFIES")
        lines.append("-" * 40)
        lines.append(data["resultat_risques"])
        lines.append("")

    checklist = data.get("checklist", {})
    if checklist:
        lines.append("-" * 40)
        lines.append("CHECKLIST PIECES")
        lines.append("-" * 40)
        for key, val in checklist.items():
            label = key.replace("check_supp_", "").replace("check_", "")
            status = "[X]" if val else "[ ]"
            lines.append(f"  {status} {label}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Genere par BOOMERANG")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_guide(id_projet: str, tool_registry: dict):
    step = st.session_state.guide_step

    _barre_progression(step)
    st.markdown(f"### Etape {step + 1}/{len(ETAPES)} -- {ETAPES[step]['titre']}")
    st.markdown("---")

    if step == 0:
        _etape_localisation()
    elif step == 1:
        _etape_plu(tool_registry)
    elif step == 2:
        _etape_risques(tool_registry)
    elif step == 3:
        _etape_description()
    elif step == 4:
        _etape_checklist()
    elif step == 5:
        _etape_resume()

    _nav_buttons(step)

    # Bouton quitter le guide (toujours visible)
    st.markdown("---")
    if st.button("Quitter le guide"):
        st.session_state.guide_mode = None
        st.rerun()
