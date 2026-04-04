# 🔀 Décisions Techniques — ImmoData Insight

> Chaque choix non trivial est documenté ici avec sa justification

---

## Décisions initiales (pré-développement)

### D1 — Chrome uniquement pour le MVP
**Choix** : Pas de Firefox/Edge/Opera en v1
**Raison** : Chrome = 65% du marché FR. Le polyfill webextension-polyfill ne résout pas
tout (Shadow DOM bugs Firefox, chrome.storage quirks Edge). Scope net = code propre.
Claude Code travaille mieux avec un scope ciblé.
**Date** : 2026-04-04

### D2 — Tout dans background.js (pas de modules ES)
**Choix** : Pas d'import/export ES modules dans le Service Worker
**Raison** : MV3 ne supporte pas les modules ES dans les SW de manière fiable.
importScripts() est déprécié. Solution pragmatique : tout dans un fichier unique
avec sections commentées. Refactoring en modules possible en v2 avec un bundler.
**Date** : 2026-04-04

### D3 — DVF via app.dvf.etalab.gouv.fr (pas api.dvf.gouv.fr)
**Choix** : Endpoint `app.dvf.etalab.gouv.fr/api/mutations3/{code_insee}`
**Raison** : L'endpoint `api.dvf.gouv.fr/api/georecords/` n'existe pas.
L'API de Christian Quest (api.cquest.org) est communautaire sans SLA.
L'endpoint Etalab retourne toutes les mutations par commune, filtrage côté client.
**Date** : 2026-04-04

### D4 — SIRENE supprimé du MVP
**Choix** : Pas d'API INSEE SIRENE en v1
**Raison** : Nécessite clé Bearer + inscription portail-api.insee.fr.
Trop de friction pour un MVP. Le tissu économique est approximé via
Overpass (POI commerces/services). SIRENE prévu en v2.
**Date** : 2026-04-04

### D5 — Données zonage/loyers bundlées en JSON local
**Choix** : zonage_pinel.json et loyers_reference.json dans /config/
**Raison** : ANIL n'a pas d'API REST (page web interactive).
Les loyers de référence sont un CSV statique sur data.gouv.fr.
Bundler = pas de dépendance réseau, pas de CORS, données toujours dispo.
Mise à jour manuelle 1x/an lors d'un update de l'extension.
**Date** : 2026-04-04

### D6 — Géorisques v1 (sans jeton) plutôt que v2
**Choix** : Utiliser les endpoints /api/v1/ sans authentification
**Raison** : Les v2 nécessitent un jeton Cerbère/FranceConnect (gratuit mais
nécessite inscription). Pour le MVP, v1 suffit. Migration v2 possible si
les v1 sont dépréciées.
**Date** : 2026-04-04

## Décisions pendant le développement

(À remplir au fur et à mesure)
