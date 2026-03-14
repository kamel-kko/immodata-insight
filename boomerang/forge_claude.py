"""
forge_claude.py — Boucle Basse de BOOMERANG

Utilise Claude Code CLI via subprocess (claude -p) — PAS l'API Anthropic payante.
Requiert : Claude Code installé et authentifié avec abonnement Pro/Max.
IMPORTANT : Ne pas définir ANTHROPIC_API_KEY dans l'environnement.

Fonction principale : forger_outil(besoin: str, id_projet: str) -> dict
"""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Optional

from langfuse import Langfuse

logger = logging.getLogger(__name__)

# Vérification au chargement du module
if os.environ.get("ANTHROPIC_API_KEY"):
    logger.warning(
        "⚠️ ANTHROPIC_API_KEY détectée dans l'environnement ! "
        "Claude Code va utiliser l'API payante au lieu de l'abonnement Pro/Max. "
        "Supprimez cette variable pour utiliser l'abonnement gratuit."
    )


# ── Appel subprocess Claude Code ────────────────────────

def _appeler_claude_forge(prompt_complet: str) -> dict:
    """Appelle Claude Code CLI via subprocess.

    Utilise l'abonnement Pro/Max — zéro coût API.

    Args:
        prompt_complet: Le prompt complet à envoyer à Claude.

    Returns:
        Dictionnaire JSON parsé depuis la réponse.

    Raises:
        RuntimeError: Si Claude Code n'est pas installé ou retourne une erreur.
    """
    if not shutil.which("claude"):
        raise RuntimeError(
            "Claude Code CLI introuvable. "
            "Installer : npm install -g @anthropic-ai/claude-code"
        )

    result = subprocess.run(
        ["claude", "-p", prompt_complet, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code erreur : {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', result.stdout, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise RuntimeError(f"Réponse non-JSON : {result.stdout[:200]}")


# ── Prompt de forge ─────────────────────────────────────

PROMPT_FORGE = """Tu es un ingénieur Python senior expert en outils LangChain et FastAPI.
Génère UN micro-service outil complet (server.py + Dockerfile + requirements.txt).

RÈGLES OBLIGATOIRES — sans exception :

1. TYPAGE MYPY STRICT
   - Tous les paramètres et retours de fonctions sont typés
   - Utiliser : str, int, float, bool, dict[str, Any], list[str], Optional[X]
   - Importer depuis typing : from typing import Any, Optional
   - Aucune fonction sans annotation de type

2. DOCSTRINGS GOOGLE STYLE
   - Chaque classe et fonction publique a une docstring
   - Format :
       def ma_fonction(param: str) -> str:
           \"\"\"Description courte.

           Args:
               param: Description du paramètre.

           Returns:
               Description du retour.

           Raises:
               ValueError: Si param est vide.
           \"\"\"

3. STRUCTURE server.py
   - FastAPI avec /health (GET) et /run (POST)
   - /health retourne : {{"status": "ok", "tool": nom, "description": desc, "requiert_internet": bool}}
   - /run accepte : {{"input": {{params}}}} et retourne {{"output": "résultat string"}}
   - Toutes les exceptions capturées, retournées comme {{"output": "Erreur : ..."}}

4. STRUCTURE Dockerfile
   - FROM python:3.12-slim
   - Expose le bon port
   - HEALTHCHECK avec urllib.request (pas de wget ni curl)

5. SI l'outil nécessite Internet (appels HTTP externes) :
   - Ajouter "requiert_internet": true dans /health
   - Commenter # REQUIERT_INTERNET: oui en haut du server.py

6. Si tu as besoin d'un package pip non-standard, indique : # PIP_REQUIRED: nom_package

Réponds UNIQUEMENT avec un JSON valide (pas de markdown, pas de backticks) :
{{
  "nom_outil": "nom_court",
  "port": 8010,
  "requiert_internet": false,
  "pip_package": "nom_package ou null",
  "server_py": "...contenu complet server.py...",
  "dockerfile": "...contenu complet Dockerfile...",
  "requirements_txt": "...contenu complet requirements.txt...",
  "test": "...code pytest complet avec typage..."
}}

Besoin : {besoin}"""


# ── Forge principale ────────────────────────────────────

def forger_outil(
    besoin: str,
    id_projet: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Forge un nouvel outil via Claude Code CLI.

    Args:
        besoin: Description du besoin en langage naturel.
        id_projet: Identifiant du projet actif.
        status_callback: Fonction optionnelle pour les mises à jour de statut.

    Returns:
        Dictionnaire avec les clés :
        - statut: "ok" ou "erreur"
        - nom_outil / nom_fichier: nom court de l'outil
        - port: port alloué
        - code: contenu du server.py
        - test: code pytest
        - tests_ok: bool
        - pytest_output: sortie pytest
        - requiert_internet: bool
    """
    langfuse = None
    trace = None
    try:
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
        )
        trace = langfuse.trace(name="forge_outil", input={"besoin": besoin, "projet": id_projet})
    except Exception:
        pass

    def _status(msg: str):
        if status_callback:
            status_callback(msg)

    _status("⚙️ Claude analyse le besoin...")

    prompt = PROMPT_FORGE.format(besoin=besoin)

    start_time = time.time()
    try:
        response = _appeler_claude_forge(prompt)
    except Exception as e:
        if trace:
            trace.update(output={"erreur": str(e)}, level="ERROR")
        return {"statut": "erreur", "message": str(e)}
    duration = time.time() - start_time

    _status("📝 Génération du code server.py...")

    nom_outil = response.get("nom_outil", f"outil_{id_projet}_{int(time.time())}")
    server_py = response.get("server_py", "")
    dockerfile = response.get("dockerfile", "")
    requirements_txt = response.get("requirements_txt", "fastapi>=0.110.0\nuvicorn>=0.29.0\n")
    test_code = response.get("test", "")
    requiert_internet = response.get("requiert_internet", False)
    pip_package = response.get("pip_package")

    if pip_package and pip_package != "null":
        _status(f"📦 Installation de {pip_package}...")
        subprocess.run(
            ["pip", "install", pip_package],
            capture_output=True, text=True, timeout=60,
        )

    # Écrire les fichiers dans temp_tools/
    temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
    tool_dir = os.path.join(temp_dir, f"tool_{nom_outil}")
    os.makedirs(tool_dir, exist_ok=True)

    _status("🐳 Création du Dockerfile...")

    with open(os.path.join(tool_dir, "server.py"), "w", encoding="utf-8") as f:
        f.write(server_py)

    with open(os.path.join(tool_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile)

    with open(os.path.join(tool_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(requirements_txt)

    # Écrire le test
    tests_dir = os.getenv("TESTS_DIR", "/app/tests")
    test_file = os.path.join(tests_dir, f"test_{nom_outil}.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_code)

    # Lancer pytest
    _status("🧪 Lancement des tests pytest...")
    pytest_result = subprocess.run(
        ["pytest", test_file, "-v", "--tb=short"],
        capture_output=True, text=True, timeout=120,
    )
    tests_ok = pytest_result.returncode == 0
    pytest_output = pytest_result.stdout + pytest_result.stderr

    # Si échec, retenter une fois
    if not tests_ok:
        _status("⚠️ Tests échoués — nouvelle tentative...")
        retry_prompt = (
            f"Le test suivant a échoué :\n\n{pytest_output}\n\n"
            f"Code original :\n{server_py}\n\n"
            f"Corrige le code et retourne le même JSON avec les corrections."
        )
        try:
            retry_response = _appeler_claude_forge(retry_prompt)
            server_py = retry_response.get("server_py", server_py)
            test_code = retry_response.get("test", test_code)

            with open(os.path.join(tool_dir, "server.py"), "w", encoding="utf-8") as f:
                f.write(server_py)
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)

            pytest_result = subprocess.run(
                ["pytest", test_file, "-v", "--tb=short"],
                capture_output=True, text=True, timeout=120,
            )
            tests_ok = pytest_result.returncode == 0
            pytest_output = pytest_result.stdout + pytest_result.stderr
        except Exception:
            pass

    if tests_ok:
        _status("✅ Tests OK — en attente de validation")
    else:
        _status("⚠️ Tests échoués — en attente de validation")

    if trace:
        trace.update(output={
            "nom_outil": nom_outil,
            "tests_ok": tests_ok,
            "duration": duration,
        })

    return {
        "statut": "ok",
        "nom_outil": nom_outil,
        "nom_fichier": f"tool_{nom_outil}",
        "port": None,  # alloué à la validation
        "code": server_py,
        "test": test_code,
        "tests_ok": tests_ok,
        "pytest_output": pytest_output,
        "requiert_internet": requiert_internet,
        "dockerfile": dockerfile,
        "requirements_txt": requirements_txt,
    }


# ── Amélioration d'un outil existant ────────────────────

def ameliorer_outil(
    code_actuel: str,
    instruction: str,
    nom_fichier: str,
) -> dict:
    """Envoie le code existant + instruction d'amélioration à Claude.

    Relance pytest sur le code amélioré.

    Args:
        code_actuel: Code Python actuel du server.py.
        instruction: Instructions d'amélioration en langage naturel.
        nom_fichier: Nom du fichier outil (ex: tool_recherche_plu).

    Returns:
        Dictionnaire avec code amélioré, résultat pytest.
    """
    prompt = f"""Tu es un ingénieur Python senior.
Tu reçois un outil LangChain existant et des instructions d'amélioration.
Retourne UNIQUEMENT un JSON valide :
{{"nom_fichier": "{nom_fichier}", "code": "...code amélioré complet...", "test": "...pytest complet..."}}

Ne modifie pas la structure de classe. Garde le nom de fichier identique.

Outil actuel ({nom_fichier}) :
```python
{code_actuel}
```

Instructions d'amélioration : {instruction}

Retourne le code amélioré en JSON."""

    try:
        response = _appeler_claude_forge(prompt)
    except Exception as e:
        return {
            "code": code_actuel,
            "tests_ok": False,
            "pytest_output": f"Erreur Claude : {str(e)}",
        }

    code_ameliore = response.get("code", code_actuel)
    test_code = response.get("test", "")

    # Écrire dans temp_tools
    temp_dir = os.getenv("TEMP_TOOLS_DIR", "/app/temp_tools")
    tool_dir = os.path.join(temp_dir, nom_fichier)
    os.makedirs(tool_dir, exist_ok=True)

    with open(os.path.join(tool_dir, "server.py"), "w", encoding="utf-8") as f:
        f.write(code_ameliore)

    tests_dir = os.getenv("TESTS_DIR", "/app/tests")
    nom_court = nom_fichier.replace("tool_", "", 1)
    test_file = os.path.join(tests_dir, f"test_{nom_court}.py")
    if test_code:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

    # Lancer pytest
    pytest_output = ""
    tests_ok = True
    if os.path.exists(test_file):
        pytest_result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short"],
            capture_output=True, text=True, timeout=120,
        )
        tests_ok = pytest_result.returncode == 0
        pytest_output = pytest_result.stdout + pytest_result.stderr

    return {
        "code": code_ameliore,
        "tests_ok": tests_ok,
        "pytest_output": pytest_output,
    }
