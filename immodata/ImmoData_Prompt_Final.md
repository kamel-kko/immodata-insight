# PROMPT CLAUDE CODE — ImmoData
# Extension Chrome MV3 — Prompt Exhaustif, Complet & Sécurisé

---

## 🎯 RÔLE & DIRECTIVES DE TRAVAIL

Tu es un développeur senior expert en :
- Extensions Chrome Manifest V3 (Service Worker, content scripts, message-passing)
- Web Scraping défensif avec sélecteurs multi-fallback
- Intégration d'APIs Open Data françaises (DVF, BAN, Géorisques, Éducation, INSEE)
- UI/UX Shadow DOM avec design system Bento dark
- Sécurité des extensions (CSP stricte, permissions minimales, isolation totale)
- Monétisation non-intrusive par affiliation contextuelle

### Règles de travail impératives

1. Tu travailles en autonomie complète — aucune confirmation demandée avant d'exécuter
2. Tu signales les blocages potentiels AVANT de coder, jamais après
3. Chaque étape se termine par une checklist de vérification fonctionnelle explicite
4. Tout code est commenté, modulaire et immédiatement opérationnel
5. Tu ne passes JAMAIS à l'étape N+1 sans avoir validé l'étape N
6. En cas d'ambiguïté sur une API, tu choisis l'implémentation la plus robuste
   et tu documentes le choix dans un commentaire inline
7. Tu respectes strictement l'ordre des étapes numérotées ci-dessous

---

## 📋 PROJET

**Nom :** ImmoData
**Type :** Extension Chrome uniquement (Manifest V3 — Phase 1)
**Cibles :** SeLoger, LeBonCoin, Bien'ici
**Mission :** Enrichir les annonces immobilières en temps réel avec des données
Open Data françaises, des algorithmes d'analyse patrimoniale, une interface
Bento dark non-intrusive, et une monétisation par affiliation contextuelle
intelligente et respectueuse de l'utilisateur.

### Contraintes absolues

- AUCUNE dépendance CDN externe (CSP MV3 — tout bundlé localement)
- AUCUN appel API depuis un content script (CORS) → tout passe par background.js
- AUCUNE donnée utilisateur ne quitte le navigateur (RGPD by design)
- AUCUNE librairie d'analytics tiers — tracking local chrome.storage uniquement
- Timeout 5 secondes sur chaque appel API avec état dégradé UI gracieux
- Permissions manifest déclarées au strict minimum nécessaire
- Shadow DOM obligatoire pour toute injection UI (isolation CSS totale)
- Service Worker keepalive via chrome.alarms (éviter l'endormissement MV3)

---

## 🗂️ ARBORESCENCE COMPLÈTE

```
immodata/
│
├── manifest.json                      # Chrome MV3 — permissions exhaustives
├── background.js                      # Service Worker + keepalive + API router
├── content_script.js                  # Orchestrateur injection UI
├── popup.html                         # Popup extension (settings + cache)
├── popup.js                           # Logique popup
├── popup.css                          # Styles popup
│
├── /config/
│   ├── selectors.json                 # Sélecteurs CSS multi-fallback par site
│   ├── apis.json                      # Endpoints, TTL cache, timeouts
│   └── partners.json                  # Partenaires affiliation + UTMs
│
├── /modules/
│   ├── /scraper/
│   │   ├── detector.js                # Détection site + type de page
│   │   ├── seloger.js                 # Extracteur SeLoger
│   │   ├── leboncoin.js               # Extracteur LeBonCoin
│   │   └── bienici.js                 # Extracteur Bien'ici
│   │
│   ├── /api/
│   │   ├── ban.js                     # Géocodage BAN (lat/lon) — REQUIS EN 1er
│   │   ├── dvf.js                     # DVF Etalab — prix marché médian
│   │   ├── georisques.js              # ERIAL + ICPE
│   │   ├── education.js               # Annuaire + IVAL établissements
│   │   ├── overpass.js                # OSM Overpass — équipements/transports
│   │   ├── ademe.js                   # DPE ADEME officiel
│   │   ├── loyers.js                  # Encadrement loyers data.gouv.fr
│   │   ├── rte.js                     # Lignes HT RTE Open Data
│   │   ├── bruit.js                   # Plan Exposition Bruit DGAC
│   │   ├── merimee.js                 # Monuments Historiques
│   │   ├── sirene.js                  # INSEE SIRENE géolocalisé
│   │   ├── ors.js                     # Isochrones OpenRouteService
│   │   └── anil.js                    # Zonage Pinel/LMNP ANIL
│   │
│   ├── /calculs/
│   │   ├── notaire.js                 # Frais notaire par tranches officielles
│   │   ├── rentabilite.js             # Rendement brut/net + stratégie locative
│   │   ├── negotiation.js             # Score négociation 0-100 + delta DVF
│   │   ├── coutTotal.js               # Coût Total de Possession sur 5/10/20 ans
│   │   ├── plusValue.js               # Score Potentiel de Plus-Value (SPV)
│   │   ├── liquidite.js               # Profil de liquidité + délai vente médian
│   │   ├── travaux.js                 # Estimateur travaux + MaPrimeRénov'
│   │   └── qualiteVie.js              # Score qualité de vie composite
│   │
│   └── /affiliation/
│       ├── triggers.js                # Logique contextuelle (quand afficher quoi)
│       ├── ctaRenderer.js             # Générateur cartes CTA dans le bento
│       └── analytics.js              # Tracking local RGPD-compliant
│
├── /ui/
│   ├── design-tokens.css              # Variables CSS — palette Bento dark
│   ├── bento-grid.css                 # Grille Bento — tailles XL/L/M/S
│   ├── components.css                 # Cards, badges, pills, loaders
│   ├── animations.css                 # Transitions, skeleton loaders
│   ├── sideDashboard.js               # Panneau latéral — page annonce
│   ├── quickView.js                   # Popup hover — page liste
│   └── /icons/
│       └── icons.js                   # SVG icons inline (pas de fichiers externes)
│
└── /utils/
    ├── cache.js                       # checkCache(key, ttlDays) + clearCache()
    ├── messageRouter.js               # Routeur messages content ↔ background
    ├── logger.js                      # Logger centralisé (dev/prod modes)
    └── security.js                    # Sanitisation inputs + validation URLs
```

---

## 🔒 SÉCURITÉ — SPÉCIFICATIONS OBLIGATOIRES

### Content Security Policy
```json
"content_security_policy": {
  "extension_pages": "script-src 'self'; object-src 'self'; style-src 'self'"
}
```

### Règles de sécurité à implémenter dans chaque fichier

**security.js** doit exposer :
```javascript
// Sanitiser tout texte extrait du DOM avant usage
sanitizeText(input)         // Strip HTML, limiter longueur 500 chars
sanitizeNumber(input)       // Valider que c'est bien un nombre
sanitizeUrl(url, allowlist) // Vérifier que l'URL est dans la liste blanche
validateLatLon(lat, lon)    // Vérifier plage France métropolitaine
validatePostalCode(cp)      // Regex 5 chiffres France

// Toutes les URLs de redirection affiliation passent par background.js
// jamais directement depuis le content script
```

**messageRouter.js** — Validation des messages entrants dans background.js :
```javascript
// Chaque message reçu est validé :
// - action doit être dans la liste blanche des actions autorisées
// - payload ne doit pas contenir de propriétés inattendues
// - les coordonnées GPS sont revalidées côté background
const ALLOWED_ACTIONS = [
  'SCRAPE_DATA', 'FETCH_BAN', 'FETCH_DVF', 'FETCH_GEORISQUES',
  'FETCH_EDUCATION', 'FETCH_OVERPASS', 'FETCH_ADEME', 'FETCH_LOYERS',
  'FETCH_RTE', 'FETCH_BRUIT', 'FETCH_MERIMEE', 'FETCH_SIRENE',
  'FETCH_ORS', 'FETCH_ANIL', 'GET_CACHE', 'SET_CACHE', 'CLEAR_CACHE',
  'TRACK_CLICK', 'OPEN_AFFILIATE_URL'
];
```

**Isolation Shadow DOM** — Obligatoire pour toute injection :
```javascript
// Tout conteneur UI est injecté dans un Shadow DOM fermé
const shadow = container.attachShadow({ mode: 'closed' });
// Les styles sont injectés dans le shadow, jamais dans document.head
// Aucun accès au DOM parent depuis l'intérieur du shadow
```

---

## ⚙️ FICHIERS DE CONFIGURATION DE RÉFÉRENCE

### /config/selectors.json

```json
{
  "seloger": {
    "prix": [
      "[data-testid='price']",
      ".Price__price",
      "span[class*='Price']",
      "meta[property='product:price:amount'][content]"
    ],
    "surface": [
      "[data-testid='surface']",
      "span[class*='Surface']",
      "div[class*='surface']"
    ],
    "dpe": [
      "[data-testid='dpe-letter']",
      "span[class*='Dpe']",
      ".energy-diagnostic span"
    ],
    "ville": [
      "[data-testid='city']",
      "span[class*='City']",
      "meta[property='og:locality']"
    ],
    "cp": [
      "[data-testid='postalcode']",
      "span[class*='PostalCode']"
    ],
    "adresse": [
      "[data-testid='address']",
      "span[class*='Address']"
    ],
    "description": [
      "[data-testid='description']",
      ".Description__content",
      "div[class*='Description']"
    ],
    "type_bien": [
      "[data-testid='property-type']",
      "span[class*='PropertyType']"
    ],
    "nb_pieces": [
      "[data-testid='rooms']",
      "span[class*='Rooms']"
    ],
    "annee_construction": [
      "[data-testid='construction-year']",
      "span[class*='ConstructionYear']"
    ],
    "page_annonce": [
      "[data-testid='classified-detail']",
      ".ClassifiedDetail",
      "div[class*='AdDetail']"
    ],
    "card_liste": [
      "[data-testid='card-list']",
      ".ListCard",
      "div[class*='Card']"
    ]
  },
  "leboncoin": {
    "prix": [
      "[data-qa-id='adview_price']",
      "span[class*='price']",
      "[itemprop='price']"
    ],
    "surface": [
      "[data-qa-id='criteria_item_square']",
      "div[class*='surface']"
    ],
    "dpe": [
      "[data-qa-id='criteria_item_energy_rate']",
      "div[class*='energy']"
    ],
    "ville": [
      "[data-qa-id='adview_location_informations']",
      "[itemprop='addressLocality']"
    ],
    "cp": [
      "[itemprop='postalCode']",
      "[data-qa-id='adview_location_informations'] span:last-child"
    ],
    "adresse": [
      "[itemprop='streetAddress']",
      "[data-qa-id='adview_location_informations']"
    ],
    "description": [
      "[data-qa-id='adview_description_container']",
      "div[class*='description']"
    ],
    "type_bien": [
      "[data-qa-id='criteria_item_real_estate_type']"
    ],
    "nb_pieces": [
      "[data-qa-id='criteria_item_rooms']"
    ],
    "annee_construction": [
      "[data-qa-id='criteria_item_square_land_surface']"
    ],
    "page_annonce": [
      "[data-qa-id='adview_container']",
      "div[class*='adview']"
    ],
    "card_liste": [
      "[data-qa-id='aditem_container']",
      "li[class*='aditem']"
    ]
  },
  "bienici": {
    "prix": [
      "span[class*='mainPrice']",
      "p[class*='price']",
      "[data-testid='price']"
    ],
    "surface": [
      "span[class*='surface']",
      "[data-testid='surface']"
    ],
    "dpe": [
      "div[class*='dpe']",
      "[data-testid='dpe']"
    ],
    "ville": [
      "span[class*='city']",
      "[itemprop='addressLocality']"
    ],
    "cp": [
      "span[class*='postalCode']",
      "[itemprop='postalCode']"
    ],
    "adresse": [
      "div[class*='address']",
      "[itemprop='streetAddress']"
    ],
    "description": [
      "div[class*='description']",
      "[data-testid='description']"
    ],
    "type_bien": [
      "span[class*='propertyType']"
    ],
    "nb_pieces": [
      "span[class*='rooms']"
    ],
    "annee_construction": [
      "span[class*='constructionYear']"
    ],
    "page_annonce": [
      "div[class*='detailPage']",
      "main[class*='adDetail']"
    ],
    "card_liste": [
      "div[class*='listCard']",
      "article[class*='propertyCard']"
    ]
  },
  "regex": {
    "jardin":         "(?i)\\b(jardin|terrain\\s+privatif|extérieur\\s+privatif)\\b",
    "balcon":         "(?i)\\b(balcon|terrasse|loggia)\\b",
    "neuf_vefa":      "(?i)\\b(neuf|vefa|programme\\s+neuf|livraison|promoteur|RT2020|RE2020)\\b",
    "travaux":        "(?i)\\b(travaux|à\\s+rénover|à\\s+rafraîchir|rénovation|remise\\s+en\\s+état|gros\\s+travaux)\\b",
    "taxe_fonciere":  "taxe\\s+foncière[^\\d]{0,20}(\\d[\\s\\d]*\\d?)\\s*€?",
    "cave":           "(?i)\\b(cave|cellier|sous-sol\\s+privatif)\\b",
    "parking":        "(?i)\\b(parking|garage|stationnement|box\\s+fermé|place\\s+de\\s+parking)\\b",
    "ascenseur":      "(?i)\\b(ascenseur|élévateur)\\b",
    "gardien":        "(?i)\\b(gardien|concierge|interphone\\s+vidéo)\\b",
    "piscine":        "(?i)\\b(piscine|jacuzzi|spa)\\b",
    "urgent":         "(?i)\\b(urgent|mutation|cause\\s+départ|à\\s+saisir|opportunité)\\b",
    "copropriete":    "(?i)\\b(copropriété|syndic|charges\\s+de\\s+copro)\\b"
  }
}
```

### /config/partners.json

```json
{
  "credit": [
    {
      "name": "Pretto",
      "logo": "pretto",
      "url_base": "https://www.pretto.fr/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=credit",
      "label": "Simuler mon taux",
      "sublabel": "Sans engagement · 2 min",
      "cpl_estimate": 45,
      "min_price": 80000
    },
    {
      "name": "Meilleurtaux",
      "logo": "meilleurtaux",
      "url_base": "https://www.meilleurtaux.com/credit-immobilier/simulation-de-pret/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=credit",
      "label": "Comparer les taux",
      "sublabel": "100% gratuit",
      "cpl_estimate": 38,
      "min_price": 80000
    }
  ],
  "demenagement": [
    {
      "name": "Moveezy",
      "logo": "moveezy",
      "url_base": "https://www.moveezy.fr/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=demenagement",
      "label": "Devis déménagement",
      "sublabel": "Gratuit · 3 devis",
      "cpa_estimate": 18
    }
  ],
  "travaux": [
    {
      "name": "Habitissimo",
      "logo": "habitissimo",
      "url_base": "https://www.habitissimo.fr/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=travaux",
      "label": "Devis artisans locaux",
      "sublabel": "Gratuit · Sans engagement",
      "cpl_estimate": 25,
      "trigger_dpe": ["E", "F", "G"],
      "trigger_age_before": 1975
    }
  ],
  "assurance": [
    {
      "name": "Luko",
      "logo": "luko",
      "url_base": "https://www.luko.eu/fr/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=assurance",
      "label": "Assurance dès 5€/mois",
      "sublabel": "Résiliation gratuite",
      "cpa_estimate": 22
    }
  ],
  "diagnostics": [
    {
      "name": "Diagamter",
      "logo": "diagamter",
      "url_base": "https://www.diagamter.com/",
      "utm": "?utm_source=immodata&utm_medium=extension&utm_campaign=diagnostics",
      "label": "Pack diagnostics",
      "sublabel": "DPE · Amiante · Électricité",
      "cpl_estimate": 20,
      "trigger_age_before": 1997
    }
  ],
  "rapport_pdf": {
    "enabled": true,
    "price": 4.90,
    "label": "Rapport d'analyse complet",
    "items": [
      "Historique DVF 5 ans détaillé",
      "Score de négociation argumenté",
      "Stratégie locative optimale",
      "Analyse copropriété",
      "Projection valeur 2030"
    ]
  }
}
```

### /config/apis.json

```json
{
  "ban": {
    "endpoint": "https://api-adresse.data.gouv.fr/search/",
    "ttl_days": 90,
    "timeout_ms": 5000
  },
  "dvf": {
    "endpoint": "https://api.dvf.gouv.fr/api/georecords/",
    "ttl_days": 7,
    "timeout_ms": 8000,
    "rayon_metres": 500,
    "nb_mois_historique": 24
  },
  "georisques_erial": {
    "endpoint": "https://www.georisques.gouv.fr/api/v1/erp",
    "ttl_days": 30,
    "timeout_ms": 6000
  },
  "georisques_icpe": {
    "endpoint": "https://www.georisques.gouv.fr/api/v1/installations_classees",
    "ttl_days": 30,
    "timeout_ms": 6000
  },
  "education_annuaire": {
    "endpoint": "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-annuaire-education/records",
    "ttl_days": 30,
    "timeout_ms": 6000,
    "rayon_km": 2
  },
  "education_ival": {
    "endpoint": "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-ival/records",
    "ttl_days": 30,
    "timeout_ms": 6000
  },
  "overpass": {
    "endpoint": "https://overpass-api.de/api/interpreter",
    "ttl_days": 7,
    "timeout_ms": 10000,
    "rayon_metres": 1000
  },
  "ademe_dpe": {
    "endpoint": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe-v2-logements-existants/lines",
    "ttl_days": 7,
    "timeout_ms": 5000
  },
  "loyers": {
    "dataset_url": "https://www.data.gouv.fr/fr/datasets/r/9af8a134-0526-48c2-a9b1-9c659ad5b2ee",
    "ttl_days": 30,
    "timeout_ms": 5000
  },
  "rte_lignes_ht": {
    "endpoint": "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/lignes-aeriennes-rte-nv/records",
    "ttl_days": 90,
    "timeout_ms": 5000
  },
  "merimee": {
    "endpoint": "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records",
    "ttl_days": 90,
    "timeout_ms": 5000
  },
  "sirene": {
    "endpoint": "https://api.insee.fr/entreprises/sirene/siret",
    "ttl_days": 7,
    "timeout_ms": 6000
  },
  "ors_isochrones": {
    "endpoint": "https://api.openrouteservice.org/v2/isochrones/driving-car",
    "ttl_days": 7,
    "timeout_ms": 8000,
    "api_key_required": true,
    "api_key_source": "chrome.storage.local:ors_api_key"
  },
  "anil_zonage": {
    "endpoint": "https://www.anil.org/outils/encadrement-des-loyers/",
    "ttl_days": 30,
    "timeout_ms": 5000
  }
}
```

---

## 🎨 DESIGN SYSTEM BENTO DARK

### Tokens CSS (/ui/design-tokens.css)

```css
:host {
  /* Fond et surfaces */
  --idi-bg:           #0F0F11;
  --idi-surface:      #1A1A1F;
  --idi-surface-2:    #242429;
  --idi-surface-3:    #2E2E36;
  --idi-border:       rgba(255,255,255,0.07);

  /* Accents */
  --idi-accent:       #6C63FF;
  --idi-accent-glow:  rgba(108,99,255,0.18);
  --idi-green:        #00D4AA;
  --idi-green-glow:   rgba(0,212,170,0.15);

  /* Sémantique */
  --idi-warn:         #F59E0B;
  --idi-danger:       #EF4444;
  --idi-success:      #22C55E;
  --idi-neutral:      #64748B;

  /* Typographie */
  --idi-text-1:       #F2F2F7;
  --idi-text-2:       #A0A0B0;
  --idi-text-3:       #5C5C6E;
  --idi-font:         'Inter', 'Segoe UI', system-ui, sans-serif;
  --idi-font-mono:    'JetBrains Mono', 'Fira Code', monospace;

  /* Grille Bento */
  --idi-gap:          8px;
  --idi-radius:       12px;
  --idi-radius-sm:    8px;
  --idi-padding:      14px;
  --idi-width:        360px;

  /* Ombres */
  --idi-shadow:       0 4px 24px rgba(0,0,0,0.4);
  --idi-shadow-card:  0 2px 8px rgba(0,0,0,0.25);
}
```

### Structure de la grille Bento

```
TAILLES DE CARTES (sur grille 2 colonnes) :
┌─────────────────────────────┐  ← Largeur totale : 360px
│  [XL] full-width            │  ← col-span: 2 / hauteur variable
├──────────────┬──────────────┤
│  [L] 2/3     │  [M] 1/2    │
├───────┬──────┴──────┬───────┤
│  [S]  │  [S]        │  [S]  │  ← col-span: 1 / hauteur fixe 72px
└───────┴─────────────┴───────┘

Hiérarchie visuelle par carte :
- Chiffre clé   : font-mono 22-28px bold, var(--idi-text-1)
- Label         : 10px uppercase letter-spacing: 0.08em, var(--idi-text-2)
- Delta/badge   : pill 11px, position absolute top-right
- Icône         : 18px SVG inline, var(--idi-text-2)
- Skeleton      : shimmer animation pendant le chargement
```

### Comportement du Side Dashboard

```
Position      : fixed right: 0, top: 50%, transform: translateY(-50%)
Largeur       : 360px (réduit à 40px quand replié)
Animation     : slide-in depuis la droite, 280ms ease-out
Z-index       : 2147483647 (maximum)
Toggle        : bouton tab visible sur le côté gauche du panel
Onglets       : Finance | Quartier | Risques | Investir | Avenir
Scroll        : overflow-y auto avec scrollbar custom dark
```

### Comportement QuickView (hover liste)

```
Déclencheur   : mouseenter sur card annonce + délai 800ms
Disparition   : mouseleave immédiat
Position      : absolute, au-dessus de la card
Contenu max   : 4 cartes Bento S (prix/m² DVF, delta marché, DPE, durée ligne)
Animation     : fade-in 150ms
Taille        : 340px x 100px max
```

---

## 📊 SPÉCIFICATIONS FONCTIONNELLES COMPLÈTES

### Module Scraper — Données extraites

Pour chaque annonce, extraire et valider :
```
- prix            : number, en euros, sans espaces ni symboles
- surface         : number, en m², entier
- prix_m2         : calculé = prix / surface
- dpe             : string, une lettre A-G ou null
- ges             : string, une lettre A-G ou null
- ville           : string, normalisée
- cp              : string, 5 chiffres France valide
- adresse_brute   : string, pour géocodage BAN
- type_bien       : enum ['appartement','maison','terrain','parking','autre']
- nb_pieces       : number ou null
- annee_constr    : number ou null
- description     : string, 2000 chars max
- url_annonce     : string, URL complète normalisée
- site            : enum ['seloger','leboncoin','bienici']
- timestamp_scrape: number, Date.now()
- flags_regex     : {
    jardin, balcon, neuf_vefa, travaux, cave,
    parking, ascenseur, urgent, taxe_fonciere (montant ou null)
  }
```

### Module API BAN — Géocodage

```javascript
// Entrée : adresse_brute + cp + ville
// Sortie : { lat, lon, adresse_normalisee, code_insee, fiabilite_score }
// Fallback si adresse imprécise : géocodage sur cp + ville uniquement
// Cache key : `ban_${cp}_${ville}_${adresse_hash}`
// TTL : 90 jours
```

### Module API DVF — Prix marché

```javascript
// Entrée : lat, lon, type_bien, surface
// Requête : rayon 500m, 24 derniers mois, nature_mutation=Vente
// Calculs :
//   - médiane prix/m² (filtré par type_bien + surface ±20%)
//   - nombre de transactions (profondeur de marché)
//   - tendance 12 mois (hausse/baisse/stable)
//   - delta avec prix annonce : ((prix_annonce/m²) - mediane) / mediane * 100
// Sortie : { mediane_m2, nb_transactions, tendance, delta_pct, date_last_transaction }
// Cache key : `dvf_${code_insee}_${type_bien}_${Math.round(surface/20)*20}`
// TTL : 7 jours
```

### Module Calculs — Frais de Notaire

```javascript
// Calcul officiel par tranches (art. A444-91 Code de commerce)
// Ancien (> 5 ans) :
//   Tranche 1 : 0 - 6 500€         → 3,870%
//   Tranche 2 : 6 500 - 17 000€    → 1,596%
//   Tranche 3 : 17 000 - 60 000€   → 1,064%
//   Tranche 4 : > 60 000€          → 0,799%
//   + TVA 20% sur émoluments
//   + Droits enregistrement : 5,80665% (base)
//   + Débours fixes : ~1 200€
// Neuf/VEFA (< 5 ans) :
//   Droits enregistrement : 0,715%
//   Émoluments notaire identiques
// Fourchette affichée : min (département favorable) / max (département défavorable)
// Sortie : { frais_min, frais_max, frais_median, type_calcul }
```

### Module Calculs — Score de Négociation

```javascript
// Score 0-100 (100 = fort potentiel de baisse)
// Facteurs et pondérations :
//   delta_dvf      : delta% vs médiane DVF         (40 pts max)
//   duree_ligne    : jours depuis 1ère publication (20 pts max — tracker)
//   urgence_texte  : mots-clés "urgent/mutation"  (15 pts max — regex)
//   nb_photos      : < 5 photos                    (10 pts max)
//   dpe_mauvais    : DPE F ou G                    (15 pts max)
// Affichage : badge coloré + message court
//   0-25  : "Prix dans la norme marché"          🟡
//   26-50 : "Légère marge de négociation"        🟠
//   51-75 : "+8-12% vs marché — négociable"      🔴
//   76-100: "Surévalué — marge estimée 12-20%"   🔴🔴
```

### Module Calculs — Coût Total de Possession (CTP)

```javascript
// Entrée : prix, surface, type_bien, dpe, annee_constr, cp
// Paramètres utilisateur (configurables dans popup) :
//   apport          : % du prix (défaut 20%)
//   duree_credit    : années (défaut 20)
//   taux_credit     : récupéré OAT 10 ans Banque de France ou saisi
// Calculs mensuels :
//   mensualite_credit         : formule amortissement standard
//   taxe_fonciere_mensuelle   : données DVF/cadastre ou estimation 1.2% valeur/an
//   charges_copro_mensuelles  : ratio 3€/m²/mois (< 1980) ou 1.5€/m²/mois (récent)
//   couts_energetiques        : DPE → kWh/m²/an × surface × tarif EDF (0.2516€/kWh)
//   provision_travaux          : (DPE ≥ D || age > 40 ans) ? surface × 15€/mois : surface × 5€/mois
// Total mensuel = somme de tous les postes
// Comparatif : loyer équivalent marché (données encadrement loyers)
// Seuil de rentabilité achat vs location : calculé en années
// Sortie : { mensualite_credit, total_mensuel, loyer_equivalent, rentabilite_annees, detail_postes }
```

### Module Calculs — Score Potentiel de Plus-Value (SPV)

```javascript
// Score 0-100 sur 5 ans
// Sources et pondérations :
//   tendance_dvf_5ans     : évolution prix/m² zone DVF 5 ans    (35 pts)
//   projets_urbains       : ZAC/tramway/métro détectés IGN      (25 pts)
//   pression_fonciere     : ratio transactions/parc zone         (20 pts)
//   evolution_tissu_eco   : SIRENE ouvertures/fermetures        (10 pts)
//   score_qualite_vie     : composite écoles/transports          (10 pts)
// Badge résultat :
//   75-100 : "Zone en forte mutation +" 🟢
//   50-74  : "Marché porteur stable"    🟡
//   25-49  : "Zone à surveiller"        🟠
//   0-24   : "Signal de déclin détecté" 🔴
```

### Module Calculs — Stratégie Locative

```javascript
// Analyse pour 4 stratégies :
// 1. Location nue classique
//    loyer_mensuel    : données encadrement loyers ou estimation
//    rendement_brut   : (loyer × 12) / prix × 100
//    rendement_net    : déduction charges + fiscalité TMI 30%
//
// 2. LMNP Meublé
//    loyer_mensuel    : +20% vs nu
//    amortissement    : 3% prix bien/an déductible
//    rendement_net    : calcul après amortissement et CFE
//
// 3. Colocation (si nb_pieces >= 3)
//    loyer_total      : prix_chambre × nb_chambres (données OSM/annonces)
//    rendement_brut   : loyer_total × 12 / prix × 100
//    contrainte_legal : alerter si Paris/ville avec encadrement pièces
//
// 4. Court terme type Airbnb (si non interdit)
//    taux_occupation  : estimation 55-70% selon zone
//    prix_nuitee      : données Inside Airbnb dataset local (à bundler)
//    revenus_annuels  : taux_occupation × 365 × prix_nuitee
//    alerte_legal     : vérifier zone > 90 jours Paris / règlement local
//
// Vérification zone Pinel/Denormandie via API ANIL
// Recommandation : afficher stratégie optimale + delta de rendement
```

### Module Risques Cachés

```javascript
// Sources combinées :
// 1. Géorisques ERIAL : inondation, séisme, mouvement terrain, radon, cavités
// 2. Géorisques ICPE  : installations classées dans rayon 2km
// 3. RTE Open Data    : lignes haute tension, distance pylône le + proche
// 4. DGAC PEB         : zone de bruit aérien (A/B/C/D/E)
// 5. Mérimée          : périmètre monument historique (contraintes architecturales)
// Chaque risque est classé : CRITIQUE 🔴 / MODÉRÉ 🟠 / FAIBLE 🟡 / AUCUN ✅
// Affichage : badge "X risques détectés" → liste dépliable avec explication
// Décote estimée (informatif) : HT -5%, ICPE -3%, PEB B -8%, Monument +/-0%
```

### Module Équipements (OSM Overpass)

```javascript
// Requête Overpass QL combinée (1 seul appel, rayon 1000m) :
// - Transports : node[public_transport=stop_position], node[railway=station]
// - Commerces   : node[shop=supermarket], node[shop=bakery]
// - Santé        : node[amenity=hospital], node[amenity=pharmacy]
// - Culture      : node[amenity=cinema], node[amenity=library]
// - Sports       : node[leisure=sports_centre], node[leisure=swimming_pool]
// - Services     : node[amenity=post_office], node[amenity=bank]
// Pour chaque catégorie : nombre + distance au + proche (en minutes à pied)
// Calcul distance à pied : Haversine × 1.3 (facteur détour urbain) / 5km/h
```

### Module Isochrones (ORS)

```javascript
// Calcul zones accessibles en 15/30 min :
//   - voiture
//   - transports en commun
//   - vélo
// API ORS gratuite jusqu'à 2000 req/jour
// Clé API configurée par l'utilisateur dans popup (settings)
// Si pas de clé : afficher message "Configurez votre clé ORS gratuite"
// Cache key : `ors_${lat}_${lon}_${mode}` — TTL 7 jours
```

---

## 💰 SYSTÈME D'AFFILIATION — LOGIQUE COMPLÈTE

### triggers.js — Règles de déclenchement contextuel

```javascript
// RÈGLES STRICTES :
// Maximum 2 CTAs visibles simultanément dans le dashboard
// CTAs jamais dans le QuickView (hover liste)
// Ouverture TOUJOURS dans un nouvel onglet via background.js
// URLs construites par background.js uniquement (jamais en content script)

const CTA_RULES = {
  credit: {
    show: (data) => data.prix > 80000,               // Toujours si prix > 80k
    position: 'finance_bottom',
    priority: 1
  },
  travaux: {
    show: (data) => ['E','F','G'].includes(data.dpe) || data.annee_constr < 1975,
    position: 'finance_conditional',
    priority: 2
  },
  diagnostics: {
    show: (data) => data.annee_constr < 1997 || !data.dpe,
    position: 'risques_bottom',
    priority: 3
  },
  demenagement: {
    show: (data) => data.page_type === 'annonce',    // Jamais sur page liste
    position: 'finance_footer',
    priority: 4
  },
  assurance: {
    show: () => true,                                 // Toujours, position discrète
    position: 'footer_minimal',
    priority: 5
  }
};

// Rotation A/B entre partenaires crédit : Pretto pair / Meilleurtaux impair
// basée sur Date.now() % 2
```

### analytics.js — Tracking local RGPD-compliant

```javascript
// Stockage exclusivement dans chrome.storage.local
// Données collectées (anonymes, jamais envoyées) :
//   - nb_impressions par CTA
//   - nb_clics par CTA
//   - CTR calculé localement
//   - nb_annonces analysées (total)
// Aucun identifiant utilisateur, aucune URL d'annonce stockée
// Données réinitialisables via bouton popup "Effacer les statistiques"
```

---

## 🔧 UTILITAIRES — SPÉCIFICATIONS

### cache.js

```javascript
// Fonctions exposées :
async function checkCache(key, ttlDays)
  // Retourne : { hit: bool, data: any, age_hours: number }
  // Calcule l'âge en heures depuis timestamp stocké

async function setCache(key, data)
  // Stocke avec timestamp : { data, timestamp: Date.now() }

async function clearCacheByPattern(pattern)
  // Efface toutes les clés correspondant au pattern (regex)

async function getCacheStats()
  // Retourne : { nb_keys, total_size_kb, oldest_key, newest_key }

async function clearAllCache()
  // Efface tout — appelé depuis popup "Effacer le cache"

// Limite de sécurité : ne pas dépasser 4MB sur chrome.storage.local
// Purge automatique des entrées expirées à chaque démarrage du SW
```

### logger.js

```javascript
// Niveaux : DEBUG / INFO / WARN / ERROR
// En production (mode extension installée) : ERROR uniquement
// En développement (flag DEV=true) : tous les niveaux
// Format : [ImmoData][MODULE][LEVEL] message
// Jamais de console.log direct dans le code — toujours via logger
```

---

## 📱 POPUP EXTENSION (popup.html)

### Sections de la popup

```
┌────────────────────────────┐
│  🏠 ImmoData       │
│  v1.0.0                    │
├────────────────────────────┤
│  ✅ Extension active       │
│  ○ Pause temporaire        │
├────────────────────────────┤
│  📊 Statistiques           │
│  Annonces analysées : 127  │
│  Cache utilisé : 1.2 MB    │
├────────────────────────────┤
│  ⚙️ Paramètres crédit      │
│  Apport : [20%  ▼]         │
│  Durée  : [20 ans ▼]       │
├────────────────────────────┤
│  🔑 Clé API ORS (optionnel)│
│  [________________________]│
├────────────────────────────┤
│  🔒 Vie privée & Cache     │
│  [Effacer le cache]        │
│  [Effacer les statistiques]│
├────────────────────────────┤
│  Aucune donnée ne quitte   │
│  votre navigateur. ✅      │
└────────────────────────────┘
```

---

## 📋 PROGRAMME DE CODAGE — ÉTAPES PAS À PAS

---

### ═══ ÉTAPE 1 — FONDATIONS & SÉCURITÉ ═══

**Objectif :** Créer la structure du projet, les fichiers de configuration
et les utilitaires de base. Rien ne doit fonctionner en dehors de
cette base solide.

**Fichiers à créer dans l'ordre :**

1.1. Générer l'arborescence complète avec tous les fichiers vides
1.2. `manifest.json` — complet avec toutes les permissions listées ci-dessus
1.3. `utils/security.js` — sanitizeText, sanitizeNumber, sanitizeUrl,
     validateLatLon, validatePostalCode
1.4. `utils/logger.js` — système de log centralisé avec niveaux
1.5. `utils/cache.js` — checkCache, setCache, clearCacheByPattern,
     getCacheStats, clearAllCache
1.6. `utils/messageRouter.js` — validation ALLOWED_ACTIONS + dispatcher
1.7. `config/selectors.json` — contenu complet fourni ci-dessus
1.8. `config/apis.json` — contenu complet fourni ci-dessus
1.9. `config/partners.json` — contenu complet fourni ci-dessus

**✅ CHECKLIST DE VALIDATION ÉTAPE 1 :**
```
□ manifest.json validé via https://chromeextension.info/manifest-validator
□ Toutes les host_permissions correspondent aux APIs listées
□ security.js : tester sanitizeText("<script>alert(1)</script>") → ""
□ security.js : tester validateLatLon(48.8566, 2.3522) → true (Paris)
□ security.js : tester validateLatLon(0, 0) → false (hors France)
□ cache.js : tester setCache/checkCache avec TTL 1 jour → hit correct
□ cache.js : simuler TTL expiré → hit: false
□ logger.js : vérifier que DEBUG ne s'affiche pas en mode prod
□ messageRouter.js : tester action inconnue → rejetée avec log WARN
□ Aucun fichier ne contient de console.log direct (→ logger uniquement)
□ L'arborescence correspond exactement au plan ci-dessus
```

---

### ═══ ÉTAPE 2 — SERVICE WORKER & COMMUNICATION ═══

**Objectif :** Implémenter background.js avec keepalive, le router de messages
et la fonction de fetch sécurisée. C'est le cœur de l'architecture.

**Fichiers à créer :**

2.1. `background.js` — Structure complète :
```javascript
// - Import des modules API (/modules/api/*.js)
// - Keepalive via chrome.alarms (alarme toutes les 25 secondes)
// - Listener chrome.runtime.onInstalled : purge cache expiré
// - Listener chrome.runtime.onMessage : dispatch via messageRouter
// - Fonction fetchWithTimeout(url, options, timeoutMs) sécurisée
// - Fonction buildApiUrl(apiName, params) via apis.json
// - Gestion erreurs globale : tout appel API échoué retourne
//   { success: false, error: 'TYPE_ERREUR', message: 'msg lisible' }
```

2.2. Chaque fichier `/modules/api/*.js` reçoit en paramètre
     les données scrapées et retourne les données enrichies.
     Structure uniforme :
```javascript
export async function fetch[NomAPI](payload) {
  // 1. Vérifier cache (checkCache)
  // 2. Valider payload (security.js)
  // 3. Construire URL (buildApiUrl)
  // 4. fetchWithTimeout
  // 5. Parser et normaliser la réponse
  // 6. Mettre en cache (setCache)
  // 7. Retourner données normalisées
  // Sur erreur : retourner { success: false, error, message }
}
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 2 :**
```
□ Charger l'extension dans Chrome (chrome://extensions → mode développeur)
□ Vérifier dans chrome://extensions que le SW est "actif" sans erreur
□ Ouvrir DevTools background → onglet Console → aucune erreur au démarrage
□ Tester keepalive : attendre 35 secondes, vérifier SW toujours actif
□ Depuis DevTools background, simuler un message :
  chrome.runtime.sendMessage({action:'FETCH_BAN', payload:{adresse:'1 rue de la Paix',cp:'75001',ville:'Paris'}})
  → Doit retourner {success:true, lat:48.8..., lon:2.3...}
□ Tester action non autorisée → retourne {success:false, error:'UNAUTHORIZED_ACTION'}
□ Tester timeout : simuler API lente (fetch vers URL inexistante) → timeout 5s
□ Vérifier que fetchWithTimeout n'expose pas la clé API dans les logs
□ Tester setCache puis rechargement SW → checkCache retourne toujours le hit
```

---

### ═══ ÉTAPE 3 — MOTEUR DE SCRAPING ═══

**Objectif :** Détecter le site, le type de page (liste/annonce),
extraire toutes les données avec multi-fallback et validation.

**Fichiers à créer :**

3.1. `modules/scraper/detector.js`
```javascript
// Détecte :
// - site : 'seloger' | 'leboncoin' | 'bienici' | null
// - pageType : 'liste' | 'annonce' | 'inconnu'
// - Observe mutations DOM pour SPA (MutationObserver sur #app ou body)
// - Émet événement custom 'immodata:page-changed' quand navigation SPA détectée
```

3.2. `modules/scraper/seloger.js`, `leboncoin.js`, `bienici.js`
```javascript
// Chaque scraper expose :
export function extractAnnonceData(document)
  // Itère les sélecteurs multi-fallback depuis selectors.json
  // Pour chaque champ : essayer sélecteur[0], si null → sélecteur[1]...
  // Logger WARN si aucun sélecteur ne fonctionne
  // Appliquer toutes les regex (jardin, balcon, etc.)
  // Retourner objet normalisé (voir spécifications scraper ci-dessus)
  // Valider via security.js avant de retourner

export function extractCardsData(document)
  // Extraire liste des cards sur page liste
  // Retourner tableau d'objets {element, prix, surface, dpe, url}
  // Minimum viable : prix + surface (si les deux sont null → card ignorée)
```

3.3. `content_script.js` — Orchestrateur principal
```javascript
// 1. Importer detector.js
// 2. Sur DOMContentLoaded ET sur événement 'immodata:page-changed' :
//    a. Détecter site + pageType
//    b. Scraper les données
//    c. Envoyer au background via chrome.runtime.sendMessage
//    d. Déclencher injection UI selon pageType
// 3. Ne jamais appeler fetch() directement
// 4. Gérer le cas où l'extension est mise en pause (flag chrome.storage)
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 3 :**
```
□ Ouvrir SeLoger.com/annonce-type → DevTools content script → aucune erreur
□ Vérifier dans console : [ImmoData][SCRAPER] log avec données extraites
□ Tester chaque champ : prix ✓ surface ✓ DPE ✓ ville ✓ CP ✓
□ Simuler sélecteur cassé : commenter sélecteur[0] → fallback sur [1] ✓
□ Ouvrir LeBonCoin immo → même vérification
□ Ouvrir Bien'ici → même vérification
□ Naviguer SPA (cliquer une annonce depuis liste) → re-scraping déclenché ✓
□ Vérifier qu'aucune donnée n'est envoyée si prix ET surface sont null
□ Tester regex jardin/travaux/urgent sur description avec ces mots → flags true
□ Vérifier sanitizeText appliqué sur description (pas de <script> en sortie)
```

---

### ═══ ÉTAPE 4 — APIs ESSENTIELLES (MVP) ═══

**Objectif :** Implémenter les 3 APIs du MVP : BAN (géocodage),
DVF (prix marché), Géorisques (risques). Ces 3 APIs sont
le socle de toute l'analyse.

**Fichiers à implémenter :**

4.1. `modules/api/ban.js`
- Input : adresse_brute + cp + ville
- Output : lat, lon, adresse_normalisee, code_insee, fiabilite
- Fallback : si adresse imprécise → géocoder cp + ville uniquement
- Cache TTL : 90 jours

4.2. `modules/api/dvf.js`
- Input : lat, lon, type_bien, surface
- Output : mediane_m2, nb_transactions, tendance, delta_pct
- Calcul médiane sur transactions filtrées (type + surface ±20%)
- Cache TTL : 7 jours

4.3. `modules/api/georisques.js`
- Input : lat, lon
- Deux appels combinés : ERIAL + ICPE
- Output : { risques_naturels[], icpe_proches[], score_global }
- Cache TTL : 30 jours

4.4. `modules/calculs/notaire.js` — Calcul frais notaire
4.5. `modules/calculs/negotiation.js` — Score négociation 0-100
4.6. `modules/calculs/coutTotal.js` — CTP mensuel

**✅ CHECKLIST DE VALIDATION ÉTAPE 4 :**
```
□ Tester BAN sur adresse connue : "1 place du Capitole, 31000 Toulouse"
  → lat ≈ 43.604, lon ≈ 1.444, code_insee = 31555
□ Tester BAN fallback : adresse invalide → géocode sur CP seul ✓
□ Tester DVF : Paris 75011, appartement 50m²
  → médiane > 8000€/m² (cohérent avec le marché)
□ Tester DVF cache : 2ème appel même coordonnées → retour immédiat (cache hit)
□ Tester Géorisques : zone inondable connue (ex: coord bords de Loire)
  → risque inondation détecté ✓
□ Tester notaire : 200 000€ ancien → fourchette 14 500 - 17 000€ environ
□ Tester notaire : 300 000€ neuf → fourchette 6 500 - 8 500€ environ
□ Tester score négociation : annonce +20% vs DVF → score > 70
□ Tester score négociation : annonce -5% vs DVF → score < 30
□ Tester CTP : 250 000€, 20% apport, 20 ans → mensualité cohérente
□ Vérifier que les erreurs API retournent { success:false } et non une exception
□ Vérifier logs WARN si API renvoie 0 résultat DVF (zone sans transaction)
```

---

### ═══ ÉTAPE 5 — APIs COMPLÉMENTAIRES ═══

**Objectif :** Implémenter les APIs secondaires pour enrichir
l'analyse quartier, risques cachés et investissement.

**Fichiers à implémenter :**

5.1. `modules/api/education.js` — Annuaire + IVAL (cache 30j)
5.2. `modules/api/overpass.js` — Équipements OSM (cache 7j)
5.3. `modules/api/ademe.js` — DPE officiel ADEME (cache 7j)
5.4. `modules/api/loyers.js` — Encadrement loyers (cache 30j)
5.5. `modules/api/rte.js` — Lignes HT (cache 90j)
5.6. `modules/api/bruit.js` — PEB aérien (cache 90j)
5.7. `modules/api/merimee.js` — Monuments Historiques (cache 90j)
5.8. `modules/api/sirene.js` — Tissu économique local (cache 7j)
5.9. `modules/api/ors.js` — Isochrones (cache 7j, clé API user)
5.10. `modules/api/anil.js` — Zonage Pinel/LMNP (cache 30j)

5.11. Compléter les modules calculs :
- `modules/calculs/plusValue.js` — Score SPV
- `modules/calculs/liquidite.js` — Profil liquidité
- `modules/calculs/travaux.js` — Estimation travaux + MaPrimeRénov'
- `modules/calculs/qualiteVie.js` — Score composite
- `modules/calculs/rentabilite.js` — 4 stratégies locatives

**✅ CHECKLIST DE VALIDATION ÉTAPE 5 :**
```
□ Overpass : tester sur Paris 75011 → retourner stations de métro proches ✓
□ Overpass : vérifier timeout 10s respecté + état dégradé si dépassé
□ Education : tester sur code INSEE d'une commune avec lycées connus ✓
□ Loyers : tester Paris (encadrement actif) vs commune rurale (pas de données)
□ RTE : tester zone avec ligne HT connue → distance retournée ✓
□ Mérimée : tester adresse dans périmètre monument historique → détecté ✓
□ SIRENE : tester centre-ville actif → nb établissements > 0 ✓
□ ORS : sans clé API → retourner { success:false, error:'NO_API_KEY' }
□ ORS : avec clé API → isochrone 15min voiture retourné ✓
□ Score SPV : tester zone en mutation connue → score > 60
□ Score qualité vie : tester centre-ville vs zone rurale → scores cohérents
□ Calcul travaux : DPE G + 1960 → estimation travaux + MaPrimeRénov' calculée
□ Rentabilité LMNP : vérifier que rendement LMNP > nu (logique attendue)
□ Vérifier cache : toutes les clés respectent le pattern `{api}_{code_insee}_{params}`
```

---

### ═══ ÉTAPE 6 — DESIGN SYSTEM BENTO ═══

**Objectif :** Implémenter les tokens CSS, la grille Bento dark
et tous les composants UI réutilisables, injectés via Shadow DOM.

**Fichiers à créer :**

6.1. `ui/design-tokens.css` — Variables CSS complètes (voir ci-dessus)
6.2. `ui/bento-grid.css` — Grille 2 colonnes avec tailles XL/L/M/S
6.3. `ui/components.css` — Cards, badges pills, loaders skeleton,
     boutons, onglets, scrollbar custom
6.4. `ui/animations.css` — Transitions, shimmer skeleton,
     slide-in panel, fade-in quickview
6.5. `ui/icons/icons.js` — Tous les SVGs inline exportés

**Règles de style :**
```css
/* Chaque carte Bento respecte cette structure */
.bento-card {
  background: var(--idi-surface);
  border: 1px solid var(--idi-border);
  border-radius: var(--idi-radius);
  padding: var(--idi-padding);
  position: relative;
  transition: background 150ms ease;
}
.bento-card:hover { background: var(--idi-surface-2); }

/* Chiffre clé */
.bento-value {
  font-family: var(--idi-font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--idi-text-1);
  letter-spacing: -0.02em;
}

/* Label */
.bento-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--idi-text-2);
  margin-bottom: 4px;
}

/* Skeleton loader */
.skeleton {
  background: linear-gradient(90deg, var(--idi-surface-2) 25%,
    var(--idi-surface-3) 50%, var(--idi-surface-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--idi-radius-sm);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 6 :**
```
□ Créer un fichier test.html standalone avec Shadow DOM → vérifier rendu
□ Grille Bento : tester les 4 tailles de cartes → affichage correct
□ Skeleton loader : vérifier animation shimmer fluide (60fps)
□ Slide-in panel : animation entrée 280ms ease-out ✓
□ QuickView : fade-in 150ms ✓
□ Hover card : transition background 150ms ✓
□ Badges pills : couleurs success/warn/danger ✓
□ Onglets : actif/inactif visuellement distincts ✓
□ Scrollbar custom dark visible sur overflow ✓
□ Vérifier qu'aucun style ne fuit hors du Shadow DOM
  (inspecter DOM parent → aucune classe idi-* visible)
□ Tester sur fond blanc SeLoger → panel dark bien visible ✓
□ Tester sur fond sombre LeBonCoin → panel cohérent ✓
```

---

### ═══ ÉTAPE 7 — INTERFACE UTILISATEUR COMPLÈTE ═══

**Objectif :** Assembler le Side Dashboard et le QuickView
avec toutes les données calculées, dans la grille Bento.

**Fichiers à créer :**

7.1. `ui/sideDashboard.js` — Panneau latéral complet

```javascript
// Structure du Side Dashboard :
//
// Header : "🏠 ImmoData" + adresse + bouton fermer + bouton replier
//
// Onglet FINANCE (défaut) :
//   [XL] Score de Négociation + delta DVF (badge coloré)
//   [L]  Coût Total de Possession mensuel
//   [M]  Frais de Notaire (fourchette)  [M] Prix /m² vs médiane DVF
//   [S]  Taxe foncière estimée  [S] Charges copro  [S] Coût énergie
//   [XL] CTA Crédit (contextuel)
//   [M]  CTA Travaux (si DPE ≥ D)  [M] CTA Déménagement
//
// Onglet QUARTIER :
//   [XL] Carte isochrones (si clé ORS) ou liste à pied
//   [L]  Écoles (liste + indicateurs IVAL)
//   [M]  Transports (+ proche + temps à pied)  [M] Commerces
//   [M]  Équipements sports/culture  [M] Qualité de l'air
//   [S]  Score Qualité de Vie global (0-100)
//
// Onglet RISQUES :
//   [XL] Radar risques naturels (Géorisques ERIAL)
//   [L]  Risques cachés (HT + PEB + MH + ICPE)
//   [M]  Zone inondable  [M] Zone séisme
//   [M]  Installations classées  [M] Plan bruit
//   [S]  CTA Diagnostics (si ancien ou DPE absent)
//
// Onglet INVESTIR :
//   [XL] Comparatif 4 stratégies locatives (tableau)
//   [L]  Rendement optimal recommandé
//   [M]  Profil de liquidité  [M] Délai vente médian
//   [S]  Zone Pinel  [S] Zone LMNP  [S] Airbnb légal ?
//
// Onglet AVENIR :
//   [XL] Score Potentiel de Plus-Value (jauge animée)
//   [L]  Score Environnemental 2030-2050
//   [M]  Projets urbains détectés  [M] Évolution tissu économique
//   [S]  Îlot chaleur  [S] Qualité air  [S] Espaces verts
//
// Footer commun tous onglets :
//   [XL] CTA Rapport PDF (4,90€) — avec liste des 5 bénéfices
//   [minimal] CTA Assurance + mention RGPD

// Comportement :
// - Injecter dans Shadow DOM sur <body>
// - Afficher skeleton loaders immédiatement
// - Remplir les cartes au fur et à mesure des réponses API
// - Si API échoue → carte en état dégradé avec message court
// - Toggle replier/déplier via tab latérale
// - Mémoriser onglet actif dans chrome.storage.session
```

7.2. `ui/quickView.js` — Popup hover page liste

```javascript
// Structure QuickView (4 cartes S max) :
//   [S] Delta DVF (ex: -8% vs marché)  [S] Prix /m² médian DVF
//   [S] DPE lettre + couleur           [S] Durée en ligne (tracker)
//
// Bouton "Analyse complète →" → ouvre l'annonce dans nouvel onglet
//
// Comportement :
// - Attacher sur chaque card de la liste via MutationObserver
// - Délai 800ms avant affichage (éviter survols accidentels)
// - Disparaître immédiatement au mouseleave
// - Appel API limité : uniquement BAN + DVF (cache only si dispo)
// - Si pas en cache → afficher "Chargement..." puis données
// - Maximum 3 QuickViews simultanés en mémoire (garbage collect)
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 7 :**
```
□ Side Dashboard s'affiche sur page annonce SeLoger ✓
□ Side Dashboard s'affiche sur page annonce LeBonCoin ✓
□ Side Dashboard s'affiche sur page annonce Bien'ici ✓
□ Skeleton loaders visibles immédiatement avant données ✓
□ Onglet Finance : toutes les cartes remplies avec vraies données ✓
□ Onglet Quartier : liste des transports proches ✓
□ Onglet Risques : au moins Géorisques affiché ✓
□ Onglet Investir : 4 stratégies locatives calculées ✓
□ Onglet Avenir : Score SPV affiché ✓
□ Badge score négociation coloré selon valeur ✓
□ CTA Crédit présent sur bien > 80 000€ ✓
□ CTA Travaux présent si DPE E/F/G ✓
□ CTA Travaux ABSENT si DPE A/B/C ✓
□ QuickView apparaît après 800ms hover sur card liste ✓
□ QuickView disparaît immédiatement au mouseleave ✓
□ QuickView : 4 cartes affichées avec données ✓
□ Panel replié/déplié fonctionne ✓
□ Aucun conflit CSS avec le site hôte (Shadow DOM isolé) ✓
□ Navigation SPA : panel se met à jour sur nouvelle annonce ✓
□ Extension en pause (popup) : aucune injection UI ✓
```

---

### ═══ ÉTAPE 8 — AFFILIATION & TRACKER D'ANNONCE ═══

**Objectif :** Implémenter la logique d'affiliation contextuelle,
le tracker d'historique de prix et le système d'analytics local.

**Fichiers à créer/compléter :**

8.1. `modules/affiliation/triggers.js` — Logique CTA_RULES complète
8.2. `modules/affiliation/ctaRenderer.js` — Générateur HTML cartes CTA
8.3. `modules/affiliation/analytics.js` — Tracking local clics/impressions
8.4. Tracker d'annonce dans `utils/cache.js` :

```javascript
// Tracker prix : à chaque visite d'une annonce
async function trackAnnonceVisit(url, prix, surface)
  // Stocker dans chrome.storage.local : `tracker_${urlHash}`
  // Format : { url, premiere_visite: timestamp, historique_prix: [{prix, timestamp}] }
  // Si prix change → ajouter entrée dans historique_prix
  // Calculer : jours_en_ligne, nb_baisses_prix, delta_premier_prix

// Exposer dans dashboard (onglet Finance) :
// "En ligne depuis X jours" + "Baisse de Y€ le DD/MM" si applicable
```

8.5. `background.js` — Ajouter gestion OPEN_AFFILIATE_URL :
```javascript
// Toutes les URLs affiliation sont construites et ouvertes
// exclusivement depuis background.js
// chrome.tabs.create({ url: sanitizeUrl(partnerUrl + utm) })
// Jamais window.open() depuis content script
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 8 :**
```
□ Cliquer CTA Crédit → nouvel onglet Pretto/Meilleurtaux avec UTM ✓
□ Vérifier UTM params dans l'URL : utm_source=immodata ✓
□ Rotation A/B crédit : vérifier alternance Pretto/Meilleurtaux ✓
□ CTA Travaux absent sur DPE A → présent sur DPE F ✓
□ CTA Diagnostics présent sur bien 1965 ✓
□ Analytics : après clic → incrément chrome.storage impressions/clics ✓
□ Popup stats → "Annonces analysées : N" incrémente ✓
□ Tracker prix : visiter même annonce 2 fois → "En ligne depuis X jours" ✓
□ Simuler changement prix : modifier manuallement storage → "Baisse détectée" ✓
□ Vérifier qu'aucune URL externe n'est construite dans content_script.js ✓
□ "Effacer statistiques" popup → analytics remis à zéro ✓
```

---

### ═══ ÉTAPE 9 — POPUP EXTENSION ═══

**Objectif :** Implémenter la popup de l'extension avec settings,
statistiques et gestion du cache.

**Fichiers à créer :**

9.1. `popup.html` — Structure HTML complète (voir spécifications ci-dessus)
9.2. `popup.css` — Styles dark cohérents avec le design system Bento
9.3. `popup.js` — Logique complète :
```javascript
// - Toggle activation/pause → chrome.storage.local:enabled
// - Lire et afficher stats (nb_annonces, cache_size)
// - Sauvegarder paramètres crédit (apport%, durée)
// - Sauvegarder clé API ORS
// - Bouton "Effacer le cache" → clearAllCache() + mise à jour affichage
// - Bouton "Effacer statistiques" → reset analytics
// - Afficher version depuis manifest.json
// - Mention RGPD : "Aucune donnée ne quitte votre navigateur"
```

**✅ CHECKLIST DE VALIDATION ÉTAPE 9 :**
```
□ Popup s'ouvre sans erreur ✓
□ Toggle pause → extension ne s'injecte plus sur les pages ✓
□ Toggle réactivation → extension s'injecte à nouveau ✓
□ Statistiques affichées et à jour ✓
□ Paramètres apport/durée sauvegardés et utilisés dans CTP ✓
□ Clé ORS sauvegardée → isochrones fonctionnels ✓
□ "Effacer le cache" → getCacheStats() retourne 0 ✓
□ Popup fermée puis rouverte → paramètres persistants ✓
□ Design dark cohérent avec le dashboard ✓
```

---

### ═══ ÉTAPE 10 — TESTS FINAUX, SÉCURITÉ & OPTIMISATION ═══

**Objectif :** Audit complet de sécurité, performance et expérience
utilisateur avant soumission au Chrome Web Store.

10.1. **Audit de sécurité :**
```
□ Vérifier CSP manifest : aucune source externe dans script-src
□ Vérifier que toutes les URLs externes sont dans la whitelist security.js
□ Tester injection XSS : description avec <img onerror=alert(1)> → neutralisé
□ Vérifier qu'aucune clé API utilisateur n'apparaît dans les logs
□ Vérifier isolation Shadow DOM : aucun accès depuis page parente
□ Audit des permissions : supprimer toute permission inutilisée
□ Vérifier que chrome.storage ne stocke pas de données personnelles
□ Tester avec extension uBlock Origin activée → pas de blocage
```

10.2. **Audit de performance :**
```
□ Mesurer temps injection dashboard depuis DOMContentLoaded : < 200ms
□ Mesurer temps affichage premières données (BAN + DVF) : < 3 secondes
□ Vérifier chrome.storage total : < 4MB après 50 annonces analysées
□ Vérifier absence de memory leaks (MutationObserver correctement disconnecté)
□ QuickView : vérifier garbage collect des instances > 3
□ Tester sur connexion lente (DevTools throttling 3G) → skeletons corrects
□ Vérifier qu'un seul appel API par type est fait (pas de doublons)
```

10.3. **Audit UX :**
```
□ Tester sur 10 annonces SeLoger réelles → données cohérentes
□ Tester sur 10 annonces LeBonCoin réelles → données cohérentes
□ Tester sur 5 annonces Bien'ici réelles → données cohérentes
□ Vérifier qu'aucune API échouée ne bloque l'affichage des autres
□ Score négociation : vérifier cohérence sur annonces connues
□ CTP mensuel : comparer à un simulateur manuel → écart < 5%
□ Frais notaire : comparer à notaires.fr calculateur → écart < 2%
□ Vérifier que le panel ne cache pas les CTA/boutons du site hôte
□ Tester navigation rapide (clic rapide 5 annonces) → pas de doublon UI
□ Vérifier accessibilité : aria-labels sur tous les boutons
```

10.4. **Préparation Chrome Web Store :**
```
□ Générer les icônes 16x16, 48x48, 128x128 (format PNG)
□ Vérifier manifest.json : name, description, version, icons complets
□ Créer screenshots 1280x800 pour le store
□ Rédiger description store (max 132 chars pour le résumé)
□ Vérifier politique de confidentialité (peut être une page GitHub Pages)
□ Zipper l'extension (sans node_modules si applicable)
□ Valider sur https://chromeextension.info/manifest-validator
□ Test final : installer depuis ZIP → tout fonctionne ✓
```

---

## 🚀 ORDRE D'EXÉCUTION FINAL

```
ÉTAPE 1  → Fondations & sécurité         [~2h]
ÉTAPE 2  → Service Worker & communication [~2h]
ÉTAPE 3  → Moteur de scraping             [~3h]
ÉTAPE 4  → APIs essentielles MVP          [~3h]
ÉTAPE 5  → APIs complémentaires           [~4h]
ÉTAPE 6  → Design system Bento            [~2h]
ÉTAPE 7  → Interface utilisateur          [~4h]
ÉTAPE 8  → Affiliation & tracker          [~2h]
ÉTAPE 9  → Popup extension                [~1h]
ÉTAPE 10 → Tests finaux & optimisation    [~3h]
```

**COMMENCE MAINTENANT PAR L'ÉTAPE 1.**
Génère l'arborescence complète, puis les fichiers dans l'ordre indiqué.
Affiche la checklist de validation de chaque étape avant de passer à la suivante.
Signale immédiatement tout problème de compatibilité API détecté.
