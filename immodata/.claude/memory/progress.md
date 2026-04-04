---
name: Progression ImmoData
description: Suivi étape par étape de la construction de l'extension Chrome ImmoData
type: project
---

# Progression ImmoData — Extension Chrome MV3

## Étapes

| # | Étape | Statut | Date |
|---|-------|--------|------|
| 1 | Fondations & Sécurité | Validée | 2026-04-04 |
| 2 | Service Worker & Communication | Validée | 2026-04-04 |
| 3 | Moteur de Scraping | Validée | 2026-04-04 |
| 4 | APIs essentielles (MVP) | En cours | — |
| 5 | APIs complémentaires | — | — |
| 6 | Design System Bento | — | — |
| 7 | Interface utilisateur | — | — |
| 8 | Affiliation & Tracker | — | — |
| 9 | Popup extension | — | — |
| 10 | Tests finaux & Optimisation | — | — |

## Décisions prises

- **Q1** : Code à la racine de `P:/CLAUDE CODE/immodata/`, pas de sous-dossier.
- **Q2** : ES Modules pour background.js, IIFE pour content script. Pas de bundler.
- **Q3** : Pas de clé ORS pour l'instant, fonctionnalité reportée.
