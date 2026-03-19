# CLAUDE.md — Project Instructions for Claude Code

This file contains standing instructions for Claude Code when working in this project directory. Claude should follow these rules throughout every session.

*Dernière mise à jour : 2026-02-23 — test hook v2*

---

## Communication Style

- L'utilisateur est **débutant en codage** : adapter le niveau de langage en conséquence.
- Pour chaque réponse impliquant du code ou une action technique, **toujours inclure une section d'explication** qui :
  - Décrit ce que fait le code en langage simple, sans jargon.
  - Explique *pourquoi* ce choix a été fait (pas seulement *quoi*).
  - Donne un exemple concret ou une analogie si c'est utile pour comprendre.
- Provide **detailed, thorough responses** — explain reasoning, include context, and use examples where helpful.
- When referencing code, always include the file path and line number (e.g., `src/main.py:42`) so the user can navigate directly.
- Use GitHub-flavored Markdown for formatting (headers, code blocks, lists).
- Do **not** use emojis unless explicitly requested.
- Communicate in **French** by default, unless the user writes in another language.

---

## Coding Style

- Prefer clarity and readability over cleverness.
- Use consistent naming conventions for each language (snake_case for Python, camelCase for JS/TS, etc.).
- Do not add unnecessary comments — only comment where logic is non-obvious.
- Do not add docstrings, type annotations, or error handling to code that wasn't already using them, unless explicitly asked.
- Avoid over-engineering: solve the immediate problem, do not design for hypothetical future needs.
- Do not introduce abstraction layers (helpers, utilities, wrappers) for one-time operations.

---

## Workflow Rules

- **Read files before modifying them.** Never propose changes to code you haven't read.
- Prefer editing existing files over creating new ones.
- Do not create documentation files (README, .md files) unless explicitly requested.
- Before running destructive or irreversible commands, state what you're about to do and confirm with the user.
- Do not auto-commit. Only commit when the user explicitly asks.
- When staging files for a commit, add specific files by name — never `git add -A` or `git add .` blindly.

---

## Tools & Stack

- This is a **mixed/general** project — language and tooling vary by context.
- Follow the conventions already present in each file or subdirectory.
- Prefer the tool already in use (e.g., if npm is present, don't switch to bun without being asked).
- Check for existing config files (`.eslintrc`, `pyproject.toml`, etc.) before assuming defaults.

---

## Security Rules

- Never introduce vulnerabilities: no SQL injection, XSS, command injection, hardcoded secrets, or OWASP Top 10 issues.
- Never commit secrets, credentials, API keys, or `.env` files. Warn the user if they ask.
- Do not bypass safety hooks or validation checks (no `--no-verify`, no disabling linters without reason).
- Do not write code that exfiltrates data, opens network listeners, or modifies system files.
- Flag any suspicious patterns in existing code when you encounter them.

---

## Memory

- Consult `~/.claude/projects/P--CLAUDE-CODE/memory/MEMORY.md` for notes from past sessions.
- When a new stable pattern or user preference is discovered, save it to memory.
- Do not save session-specific or speculative information to memory.

---

## gstack
Utilise toujours /browse pour la navigation web (jamais mcp__claude-in-chrome__*).
Si un skill ne fonctionne pas : cd ~/.claude/skills/gstack && ./setup
Skills disponibles :
- /office-hours         : brainstorming libre, nouvelles idées
- /plan-ceo-review      : revue stratégique du plan
- /plan-eng-review      : revue technique + génère plan de tests
- /plan-design-review   : valide états vides, erreurs, mobile, dark mode
- /design-consultation  : génère maquettes + écrit DESIGN.md
- /design-review        : audit visuel 80 critères sur site live
- /review               : code review + sécurité (smart routing)
- /ship                 : crée PR + déploiement automatisé
- /browse               : Chromium headless 100-200ms, screenshots
- /qa                   : tests visuels + fixes + tests de régression
- /qa-only              : QA sans autres actions
- /retro                : retrospective, mesure signal/bruit
- /investigate          : debug avec auto-freeze du module concerné
- /document-release     : documentation de release
- /codex                : référence codebase
- /careful              : avertit avant commande destructive
- /freeze               : verrouille éditions à un répertoire
- /guard                : active /careful + /freeze
- /unfreeze             : désactive /freeze
- /gstack-upgrade       : met à jour gstack
