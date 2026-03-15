"""
plu_synthese.py -- Fiche de synthese PLU + export PDF.

Genere une fiche structuree a partir des infos PLU (geocodage, GPU, zone)
et du contenu RAG (articles pertinents extraits par le retriever).
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# -- 3A — Generation de la fiche de synthese -----------------------------

def generer_fiche_synthese(
    infos_geo: dict,
    infos_plu: dict,
    articles_rag: list = None,
    infos_risques: dict = None,
) -> dict:
    """Genere une fiche de synthese structuree pour une parcelle.

    Args:
        infos_geo: Dict retourne par geocoder_adresse()
        infos_plu: Dict retourne par rechercher_plu_gpu()
        articles_rag: Liste de Documents LangChain retournes par le retriever
        infos_risques: Dict optionnel avec les risques naturels (Georisques)

    Retourne un dict structure avec toutes les sections de la fiche.
    """
    fiche = {
        "date_generation": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "adresse": infos_geo.get("adresse_normalisee", ""),
        "commune": infos_geo.get("commune", ""),
        "code_insee": infos_geo.get("code_insee", ""),
        "departement": infos_geo.get("departement", ""),
        "coordonnees": {
            "latitude": infos_geo.get("latitude", 0),
            "longitude": infos_geo.get("longitude", 0),
        },
    }

    # Section PLU
    if infos_plu.get("statut") == "trouve":
        fiche["plu"] = {
            "type_document": infos_plu.get("type_document", ""),
            "nom_document": infos_plu.get("nom_document", ""),
            "titre": infos_plu.get("titre", ""),
            "date_approbation": infos_plu.get("date_approbation", ""),
            "zone": infos_plu.get("zone_parcelle", ""),
            "nomfic": infos_plu.get("nomfic", ""),
            "partition": infos_plu.get("partition", ""),
        }
    elif infos_plu.get("statut") == "commune_rnu":
        fiche["plu"] = {
            "type_document": "RNU",
            "message": infos_plu.get("message", ""),
        }
    else:
        fiche["plu"] = {
            "type_document": "inconnu",
            "message": infos_plu.get("message", "Erreur lors de la recherche"),
        }

    # Section reglements extraits par RAG
    if articles_rag:
        fiche["reglements"] = []
        for doc in articles_rag:
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            fiche["reglements"].append({
                "article": meta.get("article", ""),
                "type_doc": meta.get("type_doc", ""),
                "fichier": meta.get("fichier", ""),
                "contenu": doc.page_content if hasattr(doc, "page_content") else str(doc),
            })

    # Section risques
    if infos_risques:
        fiche["risques"] = infos_risques

    return fiche


def formater_fiche_texte(fiche: dict) -> str:
    """Formate la fiche de synthese en texte lisible (Markdown)."""
    lines = []
    lines.append(f"# Fiche PLU -- {fiche.get('adresse', '')}")
    lines.append(f"*Generee le {fiche.get('date_generation', '')}*")
    lines.append("")

    # Localisation
    lines.append("## Localisation")
    lines.append(f"- **Adresse** : {fiche.get('adresse', '')}")
    lines.append(f"- **Commune** : {fiche.get('commune', '')} ({fiche.get('code_insee', '')})")
    lines.append(f"- **Departement** : {fiche.get('departement', '')}")
    coords = fiche.get("coordonnees", {})
    lines.append(f"- **Coordonnees** : {coords.get('latitude', '')}, {coords.get('longitude', '')}")
    lines.append("")

    # PLU
    plu = fiche.get("plu", {})
    lines.append("## Document d'urbanisme")
    if plu.get("type_document") == "RNU":
        lines.append(f"**Attention** : {plu.get('message', 'Commune soumise au RNU')}")
    else:
        lines.append(f"- **Type** : {plu.get('type_document', '')}")
        if plu.get("nom_document"):
            lines.append(f"- **Nom** : {plu.get('nom_document', '')}")
        if plu.get("titre"):
            lines.append(f"- **Titre** : {plu.get('titre', '')}")
        if plu.get("date_approbation"):
            lines.append(f"- **Date d'approbation** : {plu.get('date_approbation', '')}")
        if plu.get("zone"):
            lines.append(f"- **Zone** : {plu.get('zone', '')}")
    lines.append("")

    # Reglements RAG
    reglements = fiche.get("reglements", [])
    if reglements:
        lines.append("## Regles applicables (extraits du reglement)")
        for reg in reglements:
            art = reg.get("article", "")
            type_doc = reg.get("type_doc", "")
            lines.append(f"### {art} ({type_doc})")
            lines.append(reg.get("contenu", ""))
            lines.append("")

    # Risques
    risques = fiche.get("risques", {})
    if risques:
        lines.append("## Risques naturels et technologiques")
        if isinstance(risques, dict):
            for k, v in risques.items():
                lines.append(f"- **{k}** : {v}")
        lines.append("")

    return "\n".join(lines)


# -- 3B — Export PDF avec fpdf2 ------------------------------------------

def exporter_fiche_pdf(fiche: dict) -> bytes:
    """Exporte la fiche de synthese en PDF.

    Retourne le contenu PDF en bytes.
    """
    from fpdf import FPDF

    def _safe(text: str) -> str:
        return text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # En-tete
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, _safe("Fiche PLU"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, _safe(fiche.get("adresse", "")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 5, _safe(f"Generee le {fiche.get('date_generation', '')}"), new_x="LMARGIN", new_y="NEXT")

    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(6)

    # Localisation
    _section(pdf, "Localisation")
    _field(pdf, "Commune", f"{fiche.get('commune', '')} ({fiche.get('code_insee', '')})")
    _field(pdf, "Departement", fiche.get("departement", ""))
    coords = fiche.get("coordonnees", {})
    _field(pdf, "Coordonnees", f"{coords.get('latitude', '')}, {coords.get('longitude', '')}")
    pdf.ln(3)

    # PLU
    plu = fiche.get("plu", {})
    _section(pdf, "Document d'urbanisme")
    if plu.get("type_document") == "RNU":
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(180, 0, 0)
        pdf.multi_cell(0, 5, _safe(plu.get("message", "Commune soumise au RNU")))
        pdf.set_text_color(0, 0, 0)
    else:
        _field(pdf, "Type", plu.get("type_document", ""))
        if plu.get("nom_document"):
            _field(pdf, "Nom", plu.get("nom_document", ""))
        if plu.get("date_approbation"):
            _field(pdf, "Approbation", plu.get("date_approbation", ""))
        if plu.get("zone"):
            _field(pdf, "Zone", plu.get("zone", ""))
    pdf.ln(3)

    # Reglements RAG
    reglements = fiche.get("reglements", [])
    if reglements:
        _section(pdf, "Regles applicables")
        for reg in reglements:
            art = reg.get("article", "")
            type_doc = reg.get("type_doc", "")
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 5, _safe(f"{art} ({type_doc})"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            contenu = reg.get("contenu", "")
            # Tronquer si trop long
            if len(contenu) > 800:
                contenu = contenu[:800] + "..."
            pdf.multi_cell(0, 4, _safe(contenu))
            pdf.ln(2)

    # Risques
    risques = fiche.get("risques", {})
    if risques:
        _section(pdf, "Risques")
        if isinstance(risques, dict):
            for k, v in risques.items():
                _field(pdf, str(k), str(v))

    # Pied de page
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(140, 140, 140)
    pdf.multi_cell(0, 3.5, _safe(
        "Ce document est genere automatiquement par BOOMERANG a partir des donnees "
        "du Geoportail de l'Urbanisme (GPU). Les informations sont indicatives et "
        "ne se substituent pas a un certificat d'urbanisme officiel."
    ))

    return bytes(pdf.output())


def _section(pdf, titre: str):
    """Affiche un titre de section dans le PDF."""
    def _safe(t): return t.encode("latin-1", errors="replace").decode("latin-1")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 7, _safe(titre), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y()
    pdf.set_draw_color(0, 51, 102)
    pdf.line(10, y, 70, y)
    pdf.ln(2)


def _field(pdf, label: str, value: str):
    """Affiche un champ label: valeur dans le PDF."""
    def _safe(t): return t.encode("latin-1", errors="replace").decode("latin-1")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(45, 5, _safe(f"{label} :"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, _safe(value), new_x="LMARGIN", new_y="NEXT")
