"""
tool_runner.py — Client HTTP centralise pour appeler les outils containerises

boomerang_app ne connait pas les outils directement. Il passe par tool_runner.py qui :
- Maintient un registre {nom_outil: url_container}
- Expose des LangChain BaseTool qui font des appels HTTP
- Recharge le registre dynamiquement apres validation HITL
"""

import requests
import os
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

TOOL_REGISTRY = {
    "recherche_web":              "http://tool_recherche_searxng:8001",
    "notice_securite":            "http://tool_notice_securite:8002",
    "recherche_urbanisme":        "http://tool_api_urbanisme:8003",
    "recherche_legale":           "http://tool_mcp_legal:8004",
    "recherche_risques_parcelle": "http://tool_georisques:8005",
}


class QueryInput(BaseModel):
    """Schema d'entree pour les outils de recherche."""
    query: str = Field(
        description="Requete de recherche ou adresse complete. "
        "Pour les outils geographiques, fournir l'adresse complete "
        "(ex: '9 Rue des Pyrenees, 40230 Saint-Vincent-de-Tyrosse') "
        "ou des coordonnees GPS 'lat,lon' (ex: '43.6047,1.4442')."
    )


class NoticeInput(BaseModel):
    """Schema d'entree pour l'outil notice de securite."""
    type_erp: str = Field(description="Type d'ERP (ex: M, L, N, O, R, W)")
    capacite: int = Field(description="Capacite d'accueil en nombre de personnes")
    description: str = Field(default="", description="Description du projet")


class DevRequestInput(BaseModel):
    """Schema d'entree pour l'outil de demande de developpement."""
    outil_manquant: str = Field(description="Nom de l'outil manquant a developper")
    description_fonctionnelle: str = Field(description="Description fonctionnelle de ce que l'outil doit faire")


# Mapping des schemas d'entree par nom d'outil
_INPUT_SCHEMAS = {
    "notice_securite": NoticeInput,
    "tool_demander_dev": DevRequestInput,
}


class ContainerTool(BaseTool):
    name: str
    description: str
    tool_url: str
    args_schema: type = QueryInput

    def _run(self, **kwargs) -> str:
        try:
            resp = requests.post(
                f"{self.tool_url}/run",
                json={"input": kwargs},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["output"]
        except Exception as e:
            return f"Erreur outil {self.name} : {str(e)}"

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


def charger_outils() -> list[BaseTool]:
    """Retourne tous les outils disponibles comme BaseTool HTTP."""
    outils = []
    for nom, url in TOOL_REGISTRY.items():
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            if resp.json().get("status") == "ok":
                meta = resp.json()
                schema = _INPUT_SCHEMAS.get(nom, QueryInput)
                outils.append(ContainerTool(
                    name=nom,
                    description=meta.get("description", f"Outil {nom}"),
                    tool_url=url,
                    args_schema=schema,
                ))
        except Exception:
            pass  # Container outil indisponible — skip silencieux
    return outils
