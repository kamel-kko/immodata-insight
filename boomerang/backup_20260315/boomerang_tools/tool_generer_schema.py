"""
tool_generer_schema.py — Generation de diagrammes Mermaid et graphiques Matplotlib.

Fonctions :
- generer_mermaid : produit du code Mermaid.js valide
- generer_graphique_matplotlib : produit un graphique PNG sauvegarde dans data/charts/
"""

import os
from pathlib import Path
from datetime import datetime


def generer_mermaid(titre: str, type_diagramme: str, elements: list[dict]) -> str:
    """Genere du code Mermaid.js valide.

    Args:
        titre: titre du diagramme
        type_diagramme: 'flowchart', 'gantt', 'erDiagram'
        elements: liste de dicts decrivant les elements
            Pour flowchart : [{"from": "A", "to": "B", "label": "etape"}]
            Pour gantt : [{"task": "Nom", "start": "2024-01-01", "duration": "30d"}]
            Pour erDiagram : [{"entity": "Nom", "fields": ["id int", "nom string"]}]

    Returns:
        Code Mermaid.js sous forme de string
    """
    if type_diagramme == "flowchart":
        lines = [f"---", f"title: {titre}", f"---", "flowchart TD"]
        for el in elements:
            src = el.get("from", "A")
            dst = el.get("to", "B")
            label = el.get("label", "")
            if label:
                lines.append(f"    {src} -->|{label}| {dst}")
            else:
                lines.append(f"    {src} --> {dst}")
        return "\n".join(lines)

    elif type_diagramme == "gantt":
        lines = ["gantt", f"    title {titre}", "    dateFormat YYYY-MM-DD"]
        section = "Taches"
        lines.append(f"    section {section}")
        for el in elements:
            task = el.get("task", "Tache")
            start = el.get("start", "2024-01-01")
            duration = el.get("duration", "30d")
            lines.append(f"    {task} : {start}, {duration}")
        return "\n".join(lines)

    elif type_diagramme == "erDiagram":
        lines = ["erDiagram"]
        for el in elements:
            entity = el.get("entity", "Entity")
            fields = el.get("fields", [])
            lines.append(f"    {entity} {{")
            for field in fields:
                lines.append(f"        {field}")
            lines.append("    }")
        return "\n".join(lines)

    else:
        return f"graph TD\n    A[{titre}] --> B[Type '{type_diagramme}' non supporte]"


def generer_graphique_matplotlib(titre: str, type_graphique: str, donnees: dict) -> str:
    """Genere un graphique et le sauvegarde dans data/charts/.

    Args:
        titre: titre du graphique
        type_graphique: 'bar', 'pie', 'line'
        donnees: dict avec "labels" (list[str]) et "values" (list[float])

    Returns:
        Chemin du fichier PNG genere
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    charts_dir = Path("/app/data/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)

    labels = donnees.get("labels", [])
    values = donnees.get("values", [])

    fig, ax = plt.subplots(figsize=(8, 5))

    if type_graphique == "bar":
        ax.bar(labels, values, color="#4A90D9")
    elif type_graphique == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    elif type_graphique == "line":
        ax.plot(labels, values, marker="o", color="#4A90D9", linewidth=2)
    else:
        ax.bar(labels, values, color="#4A90D9")

    ax.set_title(titre, fontsize=14, fontweight="bold")
    fig.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chart_{timestamp}.png"
    filepath = charts_dir / filename
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return str(filepath)
