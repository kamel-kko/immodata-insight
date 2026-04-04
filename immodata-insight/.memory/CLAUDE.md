# 🧠 CLAUDE.md — ImmoData Insight
# Extension Chrome MV3 — Analyse Immobilière Enrichie par Open Data

> Version: 1.0.0
> Date: 2026-04-04
> Propriétaire: Kamel — Architecte DPLG, SASU MON CAD
> Héritage: KAMEL-BRAIN v1.0

---

## 🎯 MISSION

ImmoData Insight est une **extension Chrome MV3** qui enrichit les annonces
immobilières (SeLoger, LeBonCoin, Bien'ici) en temps réel avec des données
Open Data françaises, des algorithmes d'analyse patrimoniale, une interface
Bento dark non-intrusive, et une monétisation par affiliation contextuelle.

**Principe hérité du KAMEL-BRAIN** : Chaque étape validée enrichit la mémoire
projet. Chaque erreur devient une leçon. Chaque pattern réussi est documenté.

---

## 📋 PROTOCOLE DE DÉMARRAGE (OBLIGATOIRE)

À chaque session Claude Code, exécuter dans cet ordre :

```
1. LIRE ce fichier CLAUDE.md en entier
2. LIRE .memory/progress.md — état d'avancement actuel
3. LIRE .memory/lessons.md — erreurs rencontrées et solutions
4. LIRE .memory/decisions.md — choix techniques documentés
5. IDENTIFIER l'étape en cours → reprendre là où on s'est arrêté
6. LIRE le code existant des étapes précédentes AVANT de coder
7. NE JAMAIS passer à l'étape N+1 sans checklist N validée
```

---

## ⚖️ RÈGLES DE TRAVAIL IMPÉRATIVES

1. **TOUJOURS lire avant d'écrire** — lire les fichiers existants avant modification
2. **UN objectif par session** — une étape = une session Claude Code max
3. **Signaler les blocages AVANT de coder**, jamais après
4. **Tout code est commenté**, modulaire et immédiatement opérationnel
5. **Jamais de console.log direct** — toujours via logger.js
6. **En cas d'ambiguïté API**, choisir l'implémentation la plus robuste et documenter le choix dans .memory/decisions.md
7. **Après chaque étape**, mettre à jour .memory/progress.md et .memory/lessons.md
8. **Tester sur des données réelles** quand c'est possible (vrais sites, vraies APIs)

---

## 🗂️ STRUCTURE DU PROJET

```
immodata-insight/
│
├── CLAUDE.md                          ← CE FICHIER — lu automatiquement
├── .memory/                           ← Mémoire projet persistante
│   ├── progress.md                    # État d'avancement par étape
│   ├── lessons.md                     # Erreurs → solutions
│   ├── decisions.md                   # Choix techniques documentés
│   └── selectors-audit.md            # Audit des sélecteurs CSS réels
│
├── manifest.json                      # Chrome MV3
├── background.js                      # Service Worker + keepalive + API router
├── content_script.js                  # Orchestrateur injection UI
├── popup.html / popup.js / popup.css  # Popup extension
│
├── config/
│   ├── selectors.json                 # Sélecteurs CSS multi-fallback par site
│   ├── apis.json                      # Endpoints vérifiés (voir section APIS)
│   ├── partners.json                  # Partenaires affiliation + UTMs
│   ├── zonage_pinel.json              # Zones A/Abis/B1/B2/C par code INSEE
│   └── loyers_reference.json          # Loyers de référence (villes encadrées)
│
├── modules/
│   ├── scraper/
│   │   ├── detector.js                # Détection site + type de page + SPA
│   │   ├── seloger.js                 # Extracteur SeLoger
│   │   ├── leboncoin.js               # Extracteur LeBonCoin
│   │   └── bienici.js                 # Extracteur Bien'ici
│   │
│   ├── api/
│   │   ├── ban.js                     # Géocodage BAN → lat/lon/code_insee
│   │   ├── dvf.js                     # DVF Etalab → prix marché médian
│   │   ├── georisques.js              # Risques naturels + ICPE + cavités
│   │   ├── education.js               # Annuaire écoles + IVAL lycées
│   │   ├── overpass.js                # OSM → équipements/transports/commerces
│   │   ├── ademe.js                   # DPE officiel ADEME
│   │   ├── rte.js                     # Lignes haute tension
│   │   ├── merimee.js                 # Monuments historiques (périmètre ABF)
│   │   └── ors.js                     # Isochrones (clé API utilisateur)
│   │
│   ├── calculs/
│   │   ├── notaire.js                 # Frais notaire par tranches officielles
│   │   ├── rentabilite.js             # 4 stratégies locatives comparées
│   │   ├── negotiation.js             # Score négociation 0-100
│   │   ├── coutTotal.js               # Coût Total de Possession mensuel
│   │   ├── plusValue.js               # Score Potentiel Plus-Value (SPV)
│   │   ├── liquidite.js               # Profil de liquidité
│   │   ├── travaux.js                 # Estimateur travaux + MaPrimeRénov'
│   │   └── qualiteVie.js              # Score qualité de vie composite
│   │
│   └── affiliation/
│       ├── triggers.js                # Logique contextuelle CTA
│       ├── ctaRenderer.js             # Générateur cartes CTA bento
│       └── analytics.js               # Tracking local RGPD-compliant
│
├── ui/
│   ├── design-tokens.css              # Variables CSS palette Bento dark
│   ├── bento-grid.css                 # Grille Bento 2 colonnes XL/L/M/S
│   ├── components.css                 # Cards, badges, pills, loaders
│   ├── animations.css                 # Transitions, skeleton, slide-in
│   ├── sideDashboard.js               # Panneau latéral page annonce
│   ├── quickView.js                   # Popup hover page liste
│   └── icons/
│       └── icons.js                   # SVG inline (pas de fichiers externes)
│
├── utils/
│   ├── cache.js                       # Cache chrome.storage.local + TTL
│   ├── messageRouter.js               # Routeur + validation messages
│   ├── logger.js                      # Logger centralisé DEV/PROD
│   └── security.js                    # Sanitisation + validation
│
└── store/                             # Préparation Chrome Web Store
    ├── description.md                 # Texte description store
    ├── privacy-policy.md              # Politique de confidentialité
    └── screenshots/                   # Screenshots 1280x800
```

---

## 🔒 CONTRAINTES ABSOLUES

- AUCUNE dépendance CDN externe (CSP MV3 — tout bundlé localement)
- AUCUN appel API depuis content script (CORS) → tout via background.js
- AUCUNE donnée utilisateur ne quitte le navigateur (RGPD by design)
- AUCUNE librairie analytics tiers — tracking local chrome.storage uniquement
- Timeout 5s sur chaque appel API avec état dégradé UI gracieux
- Permissions manifest au strict minimum nécessaire
- Shadow DOM fermé obligatoire pour toute injection UI
- Service Worker keepalive via chrome.alarms (25 secondes)
- MV3 : pas d'ES modules dans SW ni content scripts → tout dans des fichiers uniques

---

## 🌐 APIS VÉRIFIÉES (Avril 2026)

### APIs fonctionnelles — Pas de clé requise

| API | Endpoint | TTL cache | Timeout |
|-----|----------|-----------|---------|
| **BAN** | `https://api-adresse.data.gouv.fr/search/` | 90j | 5s |
| **DVF** | `https://app.dvf.etalab.gouv.fr/api/mutations3/{code_insee}` | 7j | 8s |
| **Géorisques Rapport** | `https://georisques.gouv.fr/api/v1/resultats_rapport_risques` | 30j | 6s |
| **Géorisques CatNat** | `https://georisques.gouv.fr/api/v1/gaspar/catnat` | 30j | 6s |
| **Géorisques ICPE** | `https://georisques.gouv.fr/api/v1/installations_classees` | 30j | 6s |
| **Géorisques Cavités** | `https://georisques.gouv.fr/api/v1/cavites` | 30j | 6s |
| **Éducation Annuaire** | `https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-annuaire-education/records` | 30j | 6s |
| **Éducation IVAL** | `https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-ival/records` | 30j | 6s |
| **Overpass OSM** | `https://overpass-api.de/api/interpreter` | 7j | 10s |
| **ADEME DPE** | `https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines` | 7j | 5s |
| **RTE Lignes HT** | `https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/lignes-aeriennes-rte-nv/records` | 90j | 5s |
| **Mérimée** | `https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records` | 90j | 5s |

### API avec clé utilisateur

| API | Endpoint | Note |
|-----|----------|------|
| **ORS Isochrones** | `https://api.openrouteservice.org/v2/isochrones/driving-car` | Clé gratuite configurée dans popup |

### Données bundlées localement (pas d'API)

| Donnée | Fichier | Raison |
|--------|---------|--------|
| Zonage Pinel/LMNP | `config/zonage_pinel.json` | ANIL n'a pas d'API REST |
| Loyers de référence | `config/loyers_reference.json` | Fichier CSV statique sur data.gouv.fr |

### APIs exclues du MVP

| API | Raison | Prévu en |
|-----|--------|----------|
| SIRENE INSEE | Nécessite clé Bearer + inscription | v2 |
| PEB Bruit DGAC | Pas d'API REST, données WMS uniquement | v2 |

### ⚠️ Points de vigilance API

```
DVF : L'endpoint retourne TOUTES les mutations de la commune.
      Filtrer côté client : nature_mutation=Vente, type_local, surface ±20%, 24 mois.
      Le code_insee vient obligatoirement du module BAN.

GEORISQUES : Le endpoint /api/v1/erp concerne les ERP (établissements),
             PAS les risques naturels. Utiliser /resultats_rapport_risques.
             Les APIs v1 sont sans jeton. Les v2 nécessitent un jeton Cerbère.

ADEME : Le dataset s'appelle "dpe03existant" (pas "dpe-v2-logements-existants").
        Rate limit : 10 appels/seconde/IP.

OVERPASS : Ajouter overpass-api.de dans host_permissions du manifest.
           Fallback : overpass.kumi.systems si l'API principale est down.
           Rate-limited côté serveur — ne pas spammer.
```

---

## 🎨 DESIGN SYSTEM

### Tokens CSS (dans :host du Shadow DOM)

```
Fond        : #0F0F11 / #1A1A1F / #242429 / #2E2E36
Accent      : #6C63FF (glow rgba 0.18) / #00D4AA (glow rgba 0.15)
Sémantique  : warn #F59E0B / danger #EF4444 / success #22C55E / neutral #64748B
Texte       : #F2F2F7 / #A0A0B0 / #5C5C6E
Typo        : Inter/Segoe UI (text) — JetBrains Mono/Fira Code (chiffres)
Grille      : gap 8px, radius 12px, padding 14px, width 360px
```

### Dashboard latéral

```
Position    : fixed right:0, top:50%, translateY(-50%)
Largeur     : 360px (réduit 40px replié)
Animation   : slide-in 280ms ease-out
Z-index     : 2147483647
Onglets     : Finance | Quartier | Risques | Investir | Avenir
```

### QuickView (hover liste)

```
Déclencheur : mouseenter 800ms
Disparition : mouseleave immédiat
Contenu     : 4 cartes S max (delta DVF, prix/m², DPE, durée en ligne)
Max         : 3 instances en mémoire (garbage collect)
```

---

## 💰 MONÉTISATION — Logique héritée du KAMEL-BRAIN Agent Monétisation

### Règles strictes
- Max **2 CTAs visibles simultanément** dans le dashboard
- CTAs **jamais** dans le QuickView (hover liste)
- Ouverture **toujours** dans un nouvel onglet via background.js
- URLs construites par **background.js uniquement** (jamais content script)
- Mention de transparence dans la popup et le footer du dashboard

### Déclencheurs contextuels

| CTA | Condition | Position | Priorité |
|-----|-----------|----------|----------|
| Crédit (Pretto/Meilleurtaux) | prix > 80 000€ | finance_bottom | 1 |
| Travaux (Habitissimo) | DPE E/F/G ou année < 1975 | finance_conditional | 2 |
| Diagnostics (Diagamter) | année < 1997 ou DPE absent | risques_bottom | 3 |
| Déménagement (Moveezy) | page annonce uniquement | finance_footer | 4 |
| Assurance (Luko) | toujours, discret | footer_minimal | 5 |

### ⚠️ Note importante sur l'affiliation réelle
Les URLs avec UTM seuls ne génèrent PAS de revenus.
Pour une vraie monétisation, signer des contrats d'affiliation
via Awin, CJ Affiliate, ou en direct avec chaque partenaire.
Documenter l'état de chaque contrat dans .memory/decisions.md.

---

## 📊 SPÉCIFICATIONS FONCTIONNELLES CLÉS

### Scraper — Données extraites par annonce

```
prix, surface, prix_m2 (calculé), dpe, ges, ville, cp, adresse_brute,
type_bien (appartement|maison|terrain|parking|autre),
nb_pieces, annee_constr, description (2000 chars max),
url_annonce, site (seloger|leboncoin|bienici), timestamp_scrape,
flags_regex: { jardin, balcon, neuf_vefa, travaux, cave,
  parking, ascenseur, urgent, taxe_fonciere, copropriete, piscine }
```

### Score de Négociation (0-100)

```
delta_dvf      : delta% vs médiane DVF           40 pts
duree_ligne    : jours depuis 1ère publication    20 pts
urgence_texte  : mots-clés urgent/mutation        15 pts
nb_photos      : < 5 photos                      10 pts
dpe_mauvais    : DPE F ou G                       15 pts

0-25  → "Prix dans la norme marché"          🟡
26-50 → "Légère marge de négociation"        🟠
51-75 → "+8-12% vs marché — négociable"      🔴
76-100→ "Surévalué — marge 12-20%"           🔴🔴
```

### Frais de Notaire (Art. A444-91)

```
Ancien (> 5 ans) : émoluments par 4 tranches + TVA 20%
  + droits enregistrement 5,80665% + débours ~1200€
Neuf/VEFA : droits 0,715% (reste identique)
```

### Coût Total de Possession mensuel

```
= mensualité_crédit + taxe_foncière/12 + charges_copro
  + coûts_énergie + provision_travaux
Paramètres user (popup) : apport% (défaut 20), durée (défaut 20 ans)
```

### Score Potentiel Plus-Value (0-100)

```
tendance_dvf_5ans    35 pts
projets_urbains      25 pts
pression_foncière    20 pts
tissu_économique     10 pts (via Overpass POI, pas SIRENE)
qualité_vie          10 pts
```

---

## 🔧 PLAN D'EXÉCUTION EN 10 ÉTAPES

Chaque étape est une session Claude Code autonome.
Ne jamais commencer une étape sans avoir validé la précédente.

### ÉTAPE 1 — Fondations & Sécurité (~2h)

**Objectif** : Créer l'arborescence, le manifest, les utilitaires de base, les configs.

**Fichiers à coder** :
- Arborescence complète (tous les fichiers avec header commenté)
- .memory/progress.md, .memory/lessons.md, .memory/decisions.md (initiaux)
- manifest.json — MV3 complet avec TOUTES les host_permissions ci-dessus
- utils/security.js — sanitizeText, sanitizeNumber, sanitizeUrl, validateLatLon, validatePostalCode
- utils/logger.js — niveaux DEBUG/INFO/WARN/ERROR, format [ImmoData][MODULE][LEVEL]
- utils/cache.js — checkCache(key,ttl), setCache(key,data), clearCacheByPattern, getCacheStats, clearAllCache
- utils/messageRouter.js — ALLOWED_ACTIONS whitelist, validateMessage, dispatch
- config/apis.json — COPIER le tableau d'APIs vérifiées ci-dessus
- config/selectors.json — sélecteurs multi-fallback (à auditer manuellement ensuite)
- config/partners.json — partenaires affiliation avec conditions

**Checklist obligatoire** :
```
□ manifest.json : toutes host_permissions correspondent aux APIs
□ security.js : sanitizeText("<script>alert(1)</script>") → ""
□ security.js : validateLatLon(48.8566, 2.3522) → true
□ security.js : validateLatLon(0, 0) → false
□ cache.js : syntaxiquement correct, fonctions exportées
□ messageRouter.js : action inconnue → rejetée avec log WARN
□ Aucun console.log direct dans aucun fichier
□ .memory/progress.md mis à jour avec "Étape 1 : ✅ Terminée"
```

---

### ÉTAPE 2 — Service Worker & Communication (~2h)

**Prérequis** : Lire utils/*, config/apis.json, manifest.json

**Objectif** : Implémenter background.js — SW keepalive, router, fetchWithTimeout.

**Fichiers à coder** :
- background.js complet :
  - chrome.alarms keepalive (25 secondes)
  - fetchWithTimeout(url, options, timeoutMs) avec AbortController
  - buildApiUrl(apiName, params) via apis.json
  - chrome.runtime.onInstalled → purge cache expiré
  - chrome.runtime.onMessage → dispatch via messageRouter
  - Handlers GET_CACHE, SET_CACHE, CLEAR_CACHE implémentés
  - Handlers FETCH_* → { success: false, error: 'NOT_IMPLEMENTED' } pour l'instant

**Note MV3** : pas d'ES modules dans SW. Tout dans background.js avec sections commentées.

**Checklist** :
```
□ Extension chargée dans chrome://extensions → aucune erreur
□ SW actif dans DevTools background → aucune erreur console
□ Keepalive : après 35 secondes → SW toujours actif
□ Message GET_CACHE → réponse correcte
□ Message action inconnue → { success: false, error: 'UNAUTHORIZED_ACTION' }
□ fetchWithTimeout sur URL inexistante → timeout ~5s
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 3 — Moteur de Scraping (~3h)

**Prérequis** : Lire config/selectors.json, utils/security.js, background.js

**Objectif** : Détecter site + page type, extraire données, gérer SPA.

**Fichiers à coder** :
- modules/scraper/detector.js — detectSite(), detectPageType(), setupSPAObserver()
- modules/scraper/seloger.js — extractAnnonceData(), extractCardsData()
- modules/scraper/leboncoin.js — idem
- modules/scraper/bienici.js — idem
- content_script.js — orchestrateur principal

**Note MV3** : pas d'ES modules en content script. Tout dans content_script.js.

**Logique** :
- Sélecteurs itérés en fallback depuis selectors.json
- Regex appliquées sur description (jardin, balcon, travaux, urgent...)
- Sanitisation via security.js avant envoi
- MutationObserver avec debounce 500ms pour SPA
- Vérifier chrome.storage.local:enabled avant injection

**Checklist** :
```
□ Annonce SeLoger → log avec données extraites (prix, surface, DPE, ville, CP)
□ Sélecteur[0] cassé → fallback sur [1] → WARN dans les logs
□ Annonce LeBonCoin → même vérification
□ Annonce Bien'ici → même vérification
□ Navigation SPA → re-scraping déclenché
□ Prix ET surface null → aucune donnée envoyée
□ Description avec <script> → sanitisée
□ .memory/selectors-audit.md mis à jour avec résultats tests réels
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 4 — APIs Essentielles MVP (~3h)

**Prérequis** : Lire background.js, config/apis.json, utils/cache.js, utils/security.js

**Objectif** : BAN + DVF + Géorisques + Frais notaire + Score négociation + CTP.

**Modules à coder** (fonctions dans background.js) :
- fetchBan(payload) — géocodage, fallback CP seul si fiabilité < 0.5
- fetchDvf(payload) — filtrage côté client, médiane, tendance, delta
- fetchGeorisques(payload) — 3 appels combinés (rapport + ICPE + cavités)
- calcNotaire(payload) — tranches officielles, ancien vs neuf
- calcNegociation(payload) — score 0-100, label, couleur
- calcCoutTotal(payload) — mensualité + 5 postes détaillés

**Connecter** les handlers FETCH_BAN, FETCH_DVF, FETCH_GEORISQUES.

**Checklist** :
```
□ BAN : "1 place du Capitole, 31000 Toulouse" → lat ≈ 43.604, code_insee 31555
□ BAN fallback : adresse invalide → géocode sur CP+ville
□ DVF : résultats filtrés, médiane cohérente
□ DVF : 2ème appel même params → cache hit
□ Géorisques : zone inondable connue → risque détecté
□ Notaire : 200k€ ancien → ~14 500-17 000€
□ Score négo : annonce +20% vs DVF → score > 70
□ CTP : 250k€, 20% apport, 20 ans → mensualité cohérente
□ Erreur API → { success: false } (pas d'exception non catchée)
□ .memory/progress.md et .memory/lessons.md mis à jour
```

---

### ÉTAPE 5 — APIs Complémentaires (~4h)

**Prérequis** : Lire background.js complet (modules BAN/DVF/Géorisques)

**Modules à coder** :
- fetchEducation — écoles + IVAL lycées
- fetchOverpass — requête Overpass QL combinée, POI par catégorie, distance à pied
- fetchAdeme — DPE officiel
- fetchRte — lignes HT, distance pylône
- fetchMerimee — monuments historiques, périmètre ABF
- fetchOrs — isochrones (avec vérification clé API)
- calcPlusValue — score SPV 0-100
- calcLiquidite — profil liquidité
- calcTravaux — estimation + MaPrimeRénov'
- calcQualiteVie — score composite
- calcRentabilite — 4 stratégies locatives

**Checklist** :
```
□ Overpass : Paris 75011 → stations métro retournées
□ Éducation : commune avec lycées → résultats IVAL
□ RTE : zone avec ligne HT → distance retournée
□ Mérimée : près monument historique → détecté
□ ORS sans clé → { success: false, error: 'NO_API_KEY' }
□ Rentabilité LMNP > rendement nu
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 6 — Design System Bento (~2h)

**Prérequis** : Aucune dépendance aux autres modules

**Fichiers à coder** :
- ui/design-tokens.css — variables dans :host
- ui/bento-grid.css — grille 2 colonnes, tailles XL/L/M/S
- ui/components.css — cards, badges, pills, skeleton, onglets, scrollbar
- ui/animations.css — shimmer, slide-in, fade-in
- ui/icons/icons.js — tous les SVG inline exportés dans un objet ICONS

**Checklist** :
```
□ Test standalone avec Shadow DOM → rendu correct
□ 4 tailles de cartes OK
□ Skeleton shimmer fluide
□ Onglets actif/inactif distincts
□ Aucun style ne fuit hors du Shadow DOM
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 7 — Interface Utilisateur (~4h)

**Prérequis** : Lire content_script.js, tout le dossier ui/, background.js

**Fichiers à coder** :
- ui/sideDashboard.js — panneau latéral complet avec 5 onglets
- ui/quickView.js — popup hover sur cards liste
- Modifier content_script.js — intégrer dashboard + quickView

**Comportement** :
- Shadow DOM fermé, skeleton loaders immédiats
- Chaque carte se remplit indépendamment au retour de son API
- API échouée → carte état dégradé "Données indisponibles"
- Toggle replier/déplier, onglet mémorisé en session
- QuickView : 800ms délai, mouseleave immédiat, max 3 instances

**Checklist** :
```
□ Dashboard sur SeLoger, LeBonCoin, Bien'ici
□ Skeleton loaders visibles
□ Badge score négociation coloré
□ Panel replié/déplié OK
□ QuickView après 800ms hover → disparaît au leave
□ Aucun conflit CSS avec site hôte
□ Navigation SPA → dashboard se met à jour
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 8 — Affiliation & Tracker (~2h)

**Prérequis** : Lire config/partners.json, background.js, sideDashboard.js

**Fichiers à coder** :
- modules/affiliation/triggers.js — CTA_RULES, max 2 visibles
- modules/affiliation/ctaRenderer.js — HTML cartes CTA bento
- modules/affiliation/analytics.js — tracking local chrome.storage
- Ajouter trackAnnonceVisit() dans utils/cache.js
- Ajouter handler OPEN_AFFILIATE_URL dans background.js

**Checklist** :
```
□ CTA Crédit → nouvel onglet avec UTM utm_source=immodata
□ Rotation A/B crédit → alternance Pretto/Meilleurtaux
□ CTA Travaux absent DPE A → présent DPE F
□ Tracker : même annonce 2x → "En ligne depuis X jours"
□ Aucune URL externe construite dans content_script.js
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 9 — Popup Extension (~1h)

**Prérequis** : Lire utils/cache.js, modules/affiliation/analytics.js

**Fichiers à coder** :
- popup.html — structure dark, sections : toggle, stats, paramètres, cache, RGPD
- popup.css — dark cohérent avec le design system
- popup.js — toggle, stats, paramètres crédit, clé ORS, effacer cache/stats

**Checklist** :
```
□ Popup s'ouvre sans erreur
□ Toggle pause → extension ne s'injecte plus
□ Paramètres persistants après fermeture
□ "Effacer le cache" → stats à 0
□ .memory/progress.md mis à jour
```

---

### ÉTAPE 10 — Audit Final & Store (~3h)

**Prérequis** : Lire TOUS les fichiers du projet

**Objectif** : Audit sécurité + performance + UX. Préparer la publication.

**Audits** :
- Sécurité : CSP, XSS, Shadow DOM isolation, permissions minimales
- Performance : MutationObserver disconnect, garbage collect, pas de doublons API
- UX : données cohérentes sur 10 annonces réelles par site

**Préparation Store** :
- store/description.md — titre (max 45 chars), résumé (max 132 chars), description complète
- store/privacy-policy.md — politique RGPD (aucune donnée ne quitte le navigateur)
- Placeholder icônes 16/48/128
- README.md avec instructions installation dev

**Checklist** :
```
□ 0 erreur console background
□ 0 erreur console content script
□ Extension installable depuis ZIP
□ Dashboard fonctionnel sur au moins 1 site réel
□ Popup fonctionnelle
□ Aucune donnée ne quitte le navigateur
□ store/description.md et store/privacy-policy.md créés
□ .memory/progress.md → "Étape 10 : ✅ MVP Terminé"
□ .memory/lessons.md → bilan final du projet
```

---

## 🔄 PROTOCOLE POST-ÉTAPE (Auto-amélioration)

Après chaque étape terminée, Claude Code doit :

```
1. Mettre à jour .memory/progress.md :
   - Étape N : ✅ Terminée — Date — Durée estimée
   - Problèmes rencontrés (le cas échéant)

2. Mettre à jour .memory/lessons.md :
   - Si erreur API → documenter endpoint, erreur, solution
   - Si sélecteur CSS cassé → documenter dans selectors-audit.md
   - Si pattern réutilisable trouvé → documenter

3. Mettre à jour .memory/decisions.md :
   - Tout choix technique non trivial
   - Pourquoi tel endpoint plutôt qu'un autre
   - Pourquoi telle structure de données
```

---

## 📚 LEÇONS HÉRITÉES DU KAMEL-BRAIN

```
LEÇON 1 : TOUJOURS lire le code existant avant modification.
           Anti-pattern BOOMERANG : coder sans lire → code qui casse.

LEÇON 2 : UN objectif par prompt. Pas de prompts multi-tâches.
           Chaque étape = scope limité = code propre.

LEÇON 3 : Les sélecteurs CSS des sites changent régulièrement.
           Architecture data-driven obligatoire (selectors.json).

LEÇON 4 : Les APIs françaises ont des endpoints instables.
           Toujours vérifier les endpoints avant de coder.
           Documenter les endpoints qui fonctionnent dans decisions.md.

LEÇON 5 : Chrome MV3 tue le Service Worker après ~30 secondes.
           Keepalive obligatoire via chrome.alarms.

LEÇON 6 : CORS bloque tout fetch depuis content script.
           Architecture message-passing obligatoire.

LEÇON 7 : Commencer simple (MVP) puis enrichir.
           Ne pas viser la perfection au premier passage.
```

---

## 🚀 POUR DÉMARRER

```
Ouvre Claude Code dans le dossier immodata-insight/
Claude Code lira ce CLAUDE.md automatiquement.
Dis simplement : "Commence l'étape 1"
```
