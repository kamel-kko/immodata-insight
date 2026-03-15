"""
tool_runner.py — Client HTTP centralise pour appeler les outils containerises

boomerang_app ne connait pas les outils directement. Il passe par tool_runner.py qui :
- Maintient un registre {nom_outil: url_container}
- Expose des LangChain BaseTool qui font des appels HTTP
- Recharge le registre dynamiquement apres validation HITL
"""

import logging
import os
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from db_manager import get_cache, set_cache
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False

_CACHE_ENABLED = os.getenv("CACHE_ENABLED", "1") != "0"
_CACHE_TTL_JOURS = int(os.getenv("CACHE_TTL_JOURS", "7"))

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

    def _make_cache_id(self, kwargs: dict) -> str:
        query = kwargs.get("query", "")
        return query.strip().lower() if query else ""

    def _run(self, **kwargs) -> str:
        cache_id = self._make_cache_id(kwargs)

        if _CACHE_AVAILABLE and _CACHE_ENABLED and cache_id:
            try:
                cached = get_cache(self.name, cache_id)
                if cached:
                    logger.info(f"[CACHE HIT] {self.name} pour '{cache_id}'")
                    return cached
            except Exception as e:
                logger.warning(f"[CACHE] Erreur lecture pour {self.name}: {e}")

        try:
            resp = requests.post(
                f"{self.tool_url}/run",
                json={"input": kwargs},
                timeout=30,
            )
            resp.raise_for_status()
            output = resp.json()["output"]
        except Exception as e:
            return f"Erreur outil {self.name} : {str(e)}"

        if _CACHE_AVAILABLE and _CACHE_ENABLED and cache_id:
            try:
                set_cache(self.name, cache_id, output, _CACHE_TTL_JOURS)
                logger.info(f"[CACHE SET] {self.name} pour '{cache_id}' (TTL {_CACHE_TTL_JOURS}j)")
            except Exception as e:
                logger.warning(f"[CACHE] Erreur ecriture pour {self.name}: {e}")

        return output

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


class LocalTool(BaseTool):
    """Outil local (pas de container Docker), appelle une fonction Python directement."""
    name: str
    description: str
    args_schema: type = QueryInput
    local_func: object = None

    def __init__(self, name, description, func, args_schema=QueryInput):
        super().__init__(name=name, description=description, args_schema=args_schema, local_func=func)

    def _run(self, **kwargs) -> str:
        try:
            result = self.local_func(**kwargs)
            if isinstance(result, dict):
                return result.get("output", str(result))
            return str(result)
        except Exception as e:
            return f"Erreur outil {self.name} : {str(e)}"

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


def charger_outils() -> list[BaseTool]:
    """Retourne tous les outils disponibles (containers HTTP + outils locaux)."""
    outils = []

    # Outils containerises (HTTP)
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
        except Exception as e:
            logger.warning(f"[charger_outils] Outil '{nom}' indisponible ({url}): {e}")

    # Outils locaux (pas de container)
    try:
        from boomerang_tools.tool_demander_dev import tool_demander_dev
        outils.append(LocalTool(
            name="tool_demander_dev",
            description=(
                "Enregistre une demande de developpement pour un outil manquant. "
                "Utiliser quand une analyse technique necessite un outil qui n'existe pas "
                "(ex: calcul thermique, analyse structurelle, calcul de surface). "
                "Parametres : outil_manquant (nom), description_fonctionnelle (ce qu'il doit faire)."
            ),
            func=tool_demander_dev,
            args_schema=DevRequestInput,
        ))
    except ImportError:
        pass

    return outils
