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
    # Supprimer les prefixes speciaux (charts, maps)
    content = re.sub(r"CHART:.*", "[Graphique - voir l'application]", content)
    content = re.sub(r"MAP_URL:.*", "[Carte cadastrale - voir l'application]", content)
    # Convertir le Markdown basique en texte
    content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)  # gras
    content = re.sub(r"\*(.+?)\*", r"\1", content)  # italique
    content = re.sub(r"^#{1,4}\s+", "", content, flags=re.MULTILINE)  # titres
    return content.strip()


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

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        created_at = msg.get("created_at")

        if not content:
            continue

        content = _nettoyer_contenu(content)

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

        # Separateur entre les messages
        pdf.ln(3)
        y = pdf.get_y()
        if y < 270:
            pdf.set_draw_color(200, 200, 200)
            pdf.line(15, y, 195, y)
            pdf.ln(3)

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
