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
| 4 | APIs essentielles (MVP) | Validée | 2026-04-04 |
| 5 | APIs complémentaires | Validée | 2026-04-04 |
| 6 | Design System Bento | Validée | 2026-04-04 |
| 7 | Interface utilisateur | Validée | 2026-04-05 |
| 8 | Affiliation & Tracker | Créée | 2026-04-05 |
| 9 | Popup extension | Validée | 2026-04-05 |
| 10 | Tests finaux & Optimisation | En cours | 2026-04-05 |

## Décisions prises

- **Q1** : Code à la racine de `P:/CLAUDE CODE/immodata/`, pas de sous-dossier.
- **Q2** : ES Modules pour background.js, IIFE pour content script. Pas de bundler.
- **Q3** : Pas de clé ORS pour l'instant, fonctionnalité reportée.
- **Q4** : API DVF migrée de `api.dvf.gouv.fr` (hors-ligne) vers OpenDataSoft (2026-04-05).
- **Q5** : Score négo : jamais 0 quand DVF disponible. Delta négatif → score faible (2-6), pas zéro.
