# 🏠 ImmoData — Guide de Démarrage Windows

## Ce que contient ce dossier

```
immodata/
├── CLAUDE.md                  ← Cerveau IA (lu automatiquement par Claude Code)
├── README.md                  ← Ce fichier
├── ImmoData_Prompt_Final.md   ← Prompt complet de codage étape par étape
└── .claude/                   ← Configuration IA complète
    ├── skills/                ← 10 compétences spécialisées
    ├── agents/                ← 7 agents IA
    ├── commands/              ← 4 commandes /slash
    └── memory/                ← Mémoire persistante du projet
```

---

## Installation — Étape par étape (Windows)

### 1. Installer Claude Desktop
→ Aller sur **claude.com/download**
→ Télécharger la version Windows
→ Installer et se connecter avec ton compte Claude

### 2. Installer Claude Code (PowerShell)
```powershell
irm https://claude.ai/install.ps1 | iex
```
Vérification :
```powershell
claude --version
```

### 3. Placer ce dossier
Copier tout le dossier `immodata` dans :
```
P:\CLAUDE CODE\immodata\
```

### 4. Lancer le projet
```powershell
cd "P:\CLAUDE CODE\immodata"
claude
```
Claude Code lit `CLAUDE.md` automatiquement et charge tous les skills.

### 5. Première commande
```
/status
```

---

## Utilisation au quotidien

### Démarrer une session de travail
```powershell
cd "P:\CLAUDE CODE\immodata"
claude
```
Puis taper `/status` pour voir où en est le projet.

### Commencer une nouvelle étape de code
```
/dialogue-module etape-1-fondations
```
Le système te posera 3 questions pour affiner les objectifs
avant de générer le prompt de codage.

### Fin de session
```
/update-memory
/improve
```

---

## Commandes disponibles

| Commande | Ce que ça fait |
|----------|----------------|
| `/status` | État complet du projet |
| `/dialogue-module [nom]` | Discussion avant de coder un module |
| `/update-memory` | Sauvegarde les apprentissages de la session |
| `/improve` | Améliore les skills et agents automatiquement |
| `/audit-securite` | Vérifie la sécurité des fichiers modifiés |
| `/test-api [nom]` | Teste une API et met à jour le statut |

---

## Le prompt de codage complet

Le fichier `ImmoData_Prompt_Final.md` contient toutes les
spécifications techniques des 10 étapes de développement.

À utiliser au démarrage de chaque grande étape :
```
Lis ImmoData_Prompt_Final.md et commence l'étape [N].
```

---

## Support

Toute question → nouvelle session Claude Code dans ce dossier.
Claude a accès à toute la mémoire du projet via `.claude/memory/`.
