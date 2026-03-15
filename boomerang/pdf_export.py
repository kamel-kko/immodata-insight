"""
pdf_export.py -- Generation de rapports PDF pour BOOMERANG

Utilise fpdf2 (zero dependance systeme) pour produire un PDF
a partir de l'historique de conversation d'un projet.
"""

import re
from datetime import datetime
from fpdf import FPDF


def _nettoyer_contenu(content: str) -> str:
    """Nettoie le contenu Markdown pour le rendu PDF texte."""
    # Remplacer les blocs mermaid par un placeholder
    content = re.sub(
        r"```mermaid.*?```", "[Schema Mermaid - voir l'application]", content, flags=re.DOTALL
    )
    # Remplacer les blocs de code generiques
    content = re.sub(r"```(\w*)\n(.*?)```", r"\2", content, flags=re.DOTALL)
    # Supprimer les blocs APPEL_OUTIL (bruit technique)
    content = re.sub(
        r"\[APPEL_OUTIL\].*?\[/APPEL_OUTIL\]",
        "[Appel outil automatique]",
        content,
        flags=re.DOTALL,
    )
    # Supprimer les prefixes speciaux (charts, maps)
    content = re.sub(r"CHART:.*", "[Graphique - voir l'application]", content)
    content = re.sub(r"MAP_URL:.*", "[Carte cadastrale - voir l'application]", content)
    # Convertir le Markdown basique en texte
    content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)  # gras
    content = re.sub(r"\*(.+?)\*", r"\1", content)  # italique
    content = re.sub(r"^#{1,4}\s+", "", content, flags=re.MULTILINE)  # titres
    return content.strip()


_URL_RE = re.compile(r"https?://[^\s)\]]+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _extraire_liens(content: str) -> list:
    """Extrait les URLs du contenu et retourne une liste de (label, url).

    Detecte les liens Markdown [texte](url) et les URLs brutes.
    """
    liens = []
    seen = set()
    # Liens Markdown
    for m in _MD_LINK_RE.finditer(content):
        url = m.group(2)
        if url not in seen:
            liens.append((m.group(1), url))
            seen.add(url)
    # URLs brutes (pas deja capturees)
    for m in _URL_RE.finditer(content):
        url = m.group(0)
        if url not in seen:
            # Generer un label court
            if "geoportail" in url or "ign.fr" in url:
                label = "Geoportail IGN - Carte cadastrale"
            elif "georisques" in url:
                label = "Georisques - Risques naturels"
            elif "legifrance" in url:
                label = "Legifrance - Reference juridique"
            else:
                label = url[:60] + "..." if len(url) > 60 else url
            liens.append((label, url))
            seen.add(url)
    return liens


def _nettoyer_liens_du_texte(content: str) -> str:
    """Remplace les liens Markdown et URLs brutes par des placeholders lisibles."""
    # Remplacer [texte](url) par "texte (voir liens ci-dessous)"
    content = _MD_LINK_RE.sub(r"\1", content)
    # Remplacer les URLs WMS longues par un placeholder
    content = re.sub(
        r"https?://wxs\.ign\.fr[^\s]*",
        "[Carte Geoportail - voir lien ci-dessous]",
        content,
    )
    # Remplacer les autres URLs tres longues (>80 car.) par un placeholder
    def _shorten(m):
        url = m.group(0)
        if len(url) > 80:
            return "[Lien - voir ci-dessous]"
        return url
    content = _URL_RE.sub(_shorten, content)
    return content


def _safe_text(text: str) -> str:
    """Encode le texte pour fpdf2 en gerant les caracteres speciaux."""
    # Supprimer les emojis et caracteres hors Latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


class RapportPDF(FPDF):
    def __init__(self, nom_projet: str):
        super().__init__()
        self.nom_projet = nom_projet
        self.date_generation = datetime.now().strftime("%d/%m/%Y %H:%M")

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, _safe_text("BOOMERANG"), align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 10, _safe_text(self.date_generation), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 6, _safe_text(f"Projet : {self.nom_projet}"), new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, _safe_text(f"Page {self.page_no()}/{{nb}}"), align="C")


def generer_pdf_rapport(id_projet: str, messages: list) -> bytes:
    """Genere un PDF a partir de la liste de messages d'un projet.

    Args:
        id_projet: Identifiant du projet
        messages: Liste de dicts avec au minimum "role" et "content"

    Returns:
        Contenu PDF en bytes, pret pour st.download_button
    """
    pdf = RapportPDF(nom_projet=id_projet)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Collecter tous les liens du rapport pour un index en fin de document
    tous_les_liens = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        created_at = msg.get("created_at")

        if not content:
            continue

        # Extraire les liens avant nettoyage
        liens_msg = _extraire_liens(content)
        tous_les_liens.extend(liens_msg)

        content = _nettoyer_contenu(content)
        content = _nettoyer_liens_du_texte(content)

        # Horodatage si disponible
        if created_at:
            if isinstance(created_at, datetime):
                ts = created_at.strftime("%d/%m/%Y %H:%M")
            else:
                ts = str(created_at)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 4, _safe_text(ts), new_x="LMARGIN", new_y="NEXT")

        if role == "user":
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, _safe_text("Question :"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _safe_text(content))

        elif role == "assistant":
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 6, _safe_text("BOOMERANG :"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, _safe_text(content))

            # Afficher les liens cliquables sous la reponse
            if liens_msg:
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, _safe_text("Sources et liens :"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "U", 8)
                pdf.set_text_color(0, 80, 160)
                for label, url in liens_msg:
                    safe_label = _safe_text(label)
                    # Lien cliquable dans le PDF
                    pdf.cell(0, 4, safe_label, new_x="LMARGIN", new_y="NEXT", link=url)

        # Separateur entre les messages
        pdf.ln(3)
        y = pdf.get_y()
        if y < 270:
            pdf.set_draw_color(200, 200, 200)
            pdf.line(15, y, 195, y)
            pdf.ln(3)

    # Index des liens en fin de rapport
    if tous_les_liens:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 6, _safe_text("Index des sources"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(0, 51, 102)
        pdf.line(10, pdf.get_y(), 60, pdf.get_y())
        pdf.ln(3)

        seen = set()
        for idx, (label, url) in enumerate(tous_les_liens, 1):
            if url in seen:
                continue
            seen.add(url)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(8, 4, _safe_text(f"{idx}."))
            pdf.set_font("Helvetica", "U", 8)
            pdf.set_text_color(0, 80, 160)
            safe_label = _safe_text(label)
            pdf.cell(0, 4, safe_label, new_x="LMARGIN", new_y="NEXT", link=url)

    # Pied de rapport
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(
        0, 4,
        _safe_text(
            "Ce rapport a ete genere automatiquement par BOOMERANG. "
            "Les informations proviennent des APIs publiques (Geoportail de l'Urbanisme, "
            "Georisques, Legifrance). Verifier les references reglementaires avant usage."
        ),
    )

    return pdf.output()
