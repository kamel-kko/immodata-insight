"""
guide_depot_pc.py -- Guide pas-a-pas pour le depot de Permis de Construire

Wizard en 6 etapes qui collecte les infos du projet et appelle
automatiquement les outils BOOMERANG (urbanisme, risques, legal).
"""

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
    ("PCMI2", "Plan de masse coté dans les 3 dimensions (1/100 ou 1/200)"),
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


def _barre_progression(step: int):
    total = len(ETAPES)
    progress = (step) / total
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


def _etape_localisation():
    st.subheader("Localisation du projet")
    st.write("Entrez l'adresse du terrain ou les coordonnees GPS du projet.")

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
        st.info("L'adresse sera utilisee pour interroger le PLU et les risques naturels aux etapes suivantes.")


def _etape_plu(tool_registry: dict):
    st.subheader("Verification PLU / Zonage")

    data = st.session_state.guide_data
    adresse = data.get("adresse", "")

    if not adresse:
        st.warning("Retournez a l'etape 1 pour saisir une adresse.")
        return

    st.write(f"Recherche du zonage PLU pour : **{adresse}**")

    url_urba = tool_registry.get("recherche_urbanisme")

    if url_urba and _check_outil_dispo(url_urba):
        if "resultat_plu" not in data:
            with st.spinner("Interrogation du Geoportail de l'Urbanisme..."):
                resultat = _appeler_outil(url_urba, adresse)
                data["resultat_plu"] = resultat

        st.markdown("### Resultat PLU")
        st.markdown(data["resultat_plu"])
    else:
        st.warning(
            "L'outil urbanisme n'est pas disponible. "
            "Verifiez que le serveur tourne sur le bon port."
        )
        st.write("Vous pouvez noter manuellement les infos PLU :")
        zone_manuelle = st.text_area(
            "Zone PLU / regles connues",
            value=data.get("resultat_plu", ""),
        )
        if zone_manuelle:
            data["resultat_plu"] = zone_manuelle


def _etape_risques(tool_registry: dict):
    st.subheader("Risques naturels et technologiques")

    data = st.session_state.guide_data
    adresse = data.get("adresse", "")

    if not adresse:
        st.warning("Retournez a l'etape 1 pour saisir une adresse.")
        return

    st.write(f"Recherche des risques pour : **{adresse}**")

    url_risques = tool_registry.get("recherche_risques_parcelle")

    if url_risques and _check_outil_dispo(url_risques):
        if "resultat_risques" not in data:
            with st.spinner("Interrogation de l'API Georisques..."):
                resultat = _appeler_outil(url_risques, adresse)
                data["resultat_risques"] = resultat

        st.markdown("### Risques identifies")
        with st.expander("Voir les resultats", expanded=True):
            st.text(data["resultat_risques"])
    else:
        st.warning(
            "L'outil Georisques n'est pas disponible. "
            "Verifiez que le serveur tourne sur le bon port."
        )
        zone_manuelle = st.text_area(
            "Risques connus (inondation, sismicite, radon...)",
            value=data.get("resultat_risques", ""),
        )
        if zone_manuelle:
            data["resultat_risques"] = zone_manuelle


def _etape_description():
    st.subheader("Description du projet")
    st.write("Ces informations serviront a determiner les pieces complementaires requises.")

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
        st.write("**Informations ERP**")
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
    st.subheader("Pieces requises pour le dossier")

    data = st.session_state.guide_data
    type_projet = data.get("type_projet", "Maison individuelle")
    is_erp = type_projet == "ERP (commerce, bureau...)"
    resultat_risques = data.get("resultat_risques", "").lower()
    zone_inondable = any(mot in resultat_risques for mot in ["inondation", "ppri", "submersion"])
    zone_sismique = any(mot in resultat_risques for mot in ["sismique", "sismicit"])

    st.write("Cochez les pieces au fur et a mesure de leur preparation :")

    # Pieces obligatoires PCMI
    st.markdown("### Pieces obligatoires")
    if "checklist" not in data:
        data["checklist"] = {}

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
        st.markdown("### Pieces complementaires (selon votre projet)")
        for desc, _ in pieces_supp:
            key = f"check_supp_{desc[:20]}"
            checked = st.checkbox(
                desc,
                value=data["checklist"].get(key, False),
                key=key,
            )
            data["checklist"][key] = checked

    # Compteur
    total = len(PIECES_PCMI) + len(pieces_supp)
    done = sum(1 for k, v in data["checklist"].items() if v)
    st.write(f"**{done}/{total}** pieces preparees")
    if done == total and total > 0:
        st.success("Toutes les pieces sont pretes !")


def _etape_resume():
    st.subheader("Resume du dossier de depot PC")

    data = st.session_state.guide_data

    # Infos generales
    st.markdown("### Informations generales")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Adresse** : {data.get('adresse', 'Non renseignee')}")
        st.write(f"**Commune** : {data.get('commune', 'Non renseignee')}")
        st.write(f"**Parcelle** : {data.get('parcelle', 'Non renseignee')}")
    with col2:
        st.write(f"**Type** : {data.get('type_projet', 'Non renseigne')}")
        st.write(f"**Surface plancher** : {data.get('surface_plancher', 0)} m2")
        st.write(f"**Hauteur** : {data.get('hauteur', 0)} m")

    if data.get("architecte_obligatoire"):
        st.warning("Architecte obligatoire (surface > 150 m2)")

    # PLU
    if data.get("resultat_plu"):
        st.markdown("### Zonage PLU")
        with st.expander("Voir le resultat PLU", expanded=False):
            st.markdown(data["resultat_plu"])

    # Risques
    if data.get("resultat_risques"):
        st.markdown("### Risques identifies")
        with st.expander("Voir les risques", expanded=False):
            st.markdown(data["resultat_risques"])

    # Checklist
    checklist = data.get("checklist", {})
    if checklist:
        st.markdown("### Avancement des pieces")
        done = sum(1 for v in checklist.values() if v)
        total = len(checklist)
        st.progress(done / total if total > 0 else 0)
        st.write(f"**{done}/{total}** pieces pretes")

    # Export texte
    st.markdown("---")
    resume_txt = _generer_resume_texte(data)
    st.download_button(
        label="Telecharger le resume (texte)",
        data=resume_txt,
        file_name="resume_depot_pc.txt",
        mime="text/plain",
    )

    # Bouton retour au chat
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

    if data.get("resultat_plu"):
        lines.append("-" * 40)
        lines.append("ZONAGE PLU")
        lines.append("-" * 40)
        lines.append(data["resultat_plu"])
        lines.append("")

    if data.get("resultat_risques"):
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
            label = key.replace("check_", "").replace("check_supp_", "")
            status = "[X]" if val else "[ ]"
            lines.append(f"  {status} {label}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Genere par BOOMERANG")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_guide(id_projet: str, tool_registry: dict):
    step = st.session_state.guide_step

    st.title("Depot Permis de Construire")
    if id_projet:
        st.caption(f"Projet : {id_projet}")

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
