"""
tool_runner.py — Client HTTP centralisé pour appeler les outils containerisés

boomerang_app ne connaît pas les outils directement. Il passe par tool_runner.py qui :
- Maintient un registre {nom_outil: url_container}
- Expose des LangChain BaseTool qui font des appels HTTP
- Recharge le registre dynamiquement après validation HITL
"""

import requests
import os
from langchain.tools import BaseTool
from pydantic import BaseModel

TOOL_REGISTRY = {
    "recherche_web":              "http://tool_recherche_searxng:8001",
    "notice_securite":            "http://tool_notice_securite:8002",
    "recherche_urbanisme":        "http://tool_api_urbanisme:8003",
    "recherche_legale":           "http://tool_mcp_legal:8004",
    "recherche_risques_parcelle": "http://tool_georisques:8005",
}


class ContainerTool(BaseTool):
    name: str
    description: str
    tool_url: str

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
                outils.append(ContainerTool(
                    name=nom,
                    description=meta.get("description", f"Outil {nom}"),
                    tool_url=url,
                ))
        except Exception:
            pass  # Container outil indisponible — skip silencieux
    return outils
