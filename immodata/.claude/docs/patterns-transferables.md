# Patterns transferables — ImmoData v1.0.0

Lecons apprises et patterns reutilisables pour BOOMERANG et les futurs projets.
Derniere mise a jour : 2026-04-05.

---

## 1. Architecture Chrome Extension MV3

### Separation IIFE / ES Modules

Le probleme central de MV3 : les content scripts ne supportent pas `import/export`,
mais le service worker (background) les supporte.

```
background.js       → ES Modules (import/export)
  modules/api/*.js  → ES Modules importes dans background.js
content_script.js   → IIFE, s'enregistre sur self.__nomprojet
  ui/*.js           → IIFE
  utils/security.js → IIFE
```

**Regle** : si un module doit etre utilise dans un content script ET dans le background,
il faut soit le dupliquer (IIFE pour content, ES Module pour background), soit le mettre
uniquement en IIFE et le charger des deux cotes.

### Namespace partage via `self`

```js
// Toujours self (pas globalThis) dans les extensions Chrome MV3
self.__nomprojet = self.__nomprojet || {};
self.__nomprojet.monModule = { ... };
```

Pourquoi `self` et pas `globalThis` : dans les service workers, `globalThis` peut
poser des problemes de scope entre les IIFE. `self` est le standard web pour
"le contexte global actuel" (window dans une page, ServiceWorkerGlobalScope dans un SW).

### Message passing content → background

Pattern uniforme pour toutes les communications :

```js
// content_script.js
function sendToBackground(action, payload) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action, payload }, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ success: false, error: 'COMM_ERROR' });
        return;
      }
      resolve(response || { success: false, error: 'NO_RESPONSE' });
    });
  });
}

// background.js — message router
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const handler = HANDLERS[msg.action];
  if (handler) {
    handler(msg.payload).then(sendResponse);
    return true; // IMPORTANT : return true pour reponse async
  }
});
```

**Transferable** : ce pattern marche pour n'importe quelle extension.
Le `return true` est critique — sans lui, le port se ferme avant la reponse async.

---

## 2. Scraping defensif multi-site

### Strategie de selecteurs multi-fallback

Les sites web changent leurs selecteurs regulierement. Ne jamais dependre
d'un seul selecteur.

```js
const SELECTORS = [
  '[data-qa-id="price"]',           // selecteur semantique (ideal)
  '.ad-price .price-value',         // selecteur CSS classique
  'span[class*="Price"]',           // selecteur partiel
];

function extractPrice(root) {
  for (const sel of SELECTORS) {
    const el = root.querySelector(sel);
    if (el) return parseFloat(el.textContent.replace(/\s/g, ''));
  }
  // Fallback regex sur le texte brut
  const match = root.textContent.match(/(\d[\d\s]*)\s*€/);
  return match ? parseFloat(match[1].replace(/\s/g, '')) : null;
}
```

**Regle** : toujours finir par un fallback regex. Les selecteurs CSS cassent,
le format prix/surface reste stable.

### Separer selecteurs page annonce vs carte liste

Les memes donnees (prix, surface) ont des selecteurs differents selon
qu'on est sur la page de l'annonce ou sur une carte dans la liste.

```js
const SEL = { ... };       // page annonce
const SEL_CARD = { ... };  // carte dans la liste
```

---

## 3. APIs Open Data francaises

### Cache avec TTL par API

Chaque API a une duree de cache differente selon la frequence de mise a jour
des donnees :

```js
const API_CONFIG = {
  BAN:        { ttl: 30 * 24 * 3600 * 1000 },  // 30 jours (adresses stables)
  DVF:        { ttl: 7 * 24 * 3600 * 1000 },   // 7 jours (transactions)
  GEORISQUES: { ttl: 30 * 24 * 3600 * 1000 },  // 30 jours (risques stables)
  OVERPASS:   { ttl: 7 * 24 * 3600 * 1000 },   // 7 jours (commerces)
};
```

### Pipeline d'enrichissement en 4 etapes

```
Etape 1 : Geocodage BAN (prerequis — produit lat/lon/code_insee)
    ↓
Etape 2 : Promise.all([DVF, Georisques])  — APIs prioritaires
    ↓
Etape 3 : Calculs locaux (notaire, nego, CTP) — pas de reseau
    ↓
Etape 4 : Promise.all([Education, Overpass, RTE, Bruit, ...]) — APIs secondaires
```

**Regle** : paralleliser au maximum avec `Promise.all`, mais respecter les
dependances (BAN avant tout, DVF avant nego).

### APIs mortes — toujours avoir un plan B

L'API DVF Etalab (`api.dvf.gouv.fr`) est morte depuis fin 2024.
Solution : OpenDataSoft heberge le meme dataset en acces libre.

**Regle** : pour chaque API, documenter une alternative.
Les APIs gouvernementales francaises ont une esperance de vie de 2-5 ans.

---

## 4. UI en Shadow DOM

### Pourquoi Shadow DOM

L'UI d'une extension injectee dans des sites tiers doit etre isolee du CSS
de la page hote. Sans Shadow DOM, les styles de SeLoger/LeBonCoin ecrasent
les notres.

```js
const host = document.createElement('div');
host.id = 'monprojet-host';
document.body.appendChild(host);
const shadow = host.attachShadow({ mode: 'closed' });
// mode:'closed' = invisible depuis la page hote
```

### Charger les CSS dans le Shadow DOM

Les CSS du Shadow DOM ne peuvent pas etre dans un `<link>` externe classique.
Solution : `fetch()` le fichier CSS local de l'extension, puis l'injecter
dans une balise `<style>` :

```js
const cssUrl = chrome.runtime.getURL('ui/components.css');
const cssText = await fetch(cssUrl).then(r => r.text());
const style = document.createElement('style');
style.textContent = cssText;
shadow.appendChild(style);
```

Declarer les CSS dans `web_accessible_resources` du manifest.

### Popups hover sur pages liste

Pour les popups qui apparaissent au survol d'une carte dans une liste,
utiliser `position:fixed` ancre sur `document.body` (pas relative a la carte) :

```js
const popup = document.createElement('div');
popup.style.position = 'fixed';
document.body.appendChild(popup);
```

Pourquoi : les cartes liste sont souvent dans des conteneurs avec
`overflow:hidden`, ce qui coupe les popups positionnes en relatif.

---

## 5. Securite — checklist transferable

| # | Verification | Comment |
|---|-------------|---------|
| 1 | CSP strict | `script-src 'self'; object-src 'self'; style-src 'self'` |
| 2 | Pas de `fetch()` dans content scripts | Tout passe par le background |
| 3 | Shadow DOM `mode:'closed'` | Invisible depuis la page hote |
| 4 | `escHtml()` sur tout texte scrape | Avant injection dans `innerHTML` |
| 5 | `sanitizeUrl()` avec whitelist | Valider chaque URL avant `fetch()` |
| 6 | Pas de `eval()` / `new Function()` | Jamais |
| 7 | Pas de `window.open()` | Liens ouverts via background `chrome.tabs.create()` |
| 8 | Pas de secrets en dur | Cles API saisies par l'utilisateur |
| 9 | Permissions minimales | Supprimer chaque permission inutilisee |
| 10 | `mode:'closed'` sur Shadow DOM | Empeche l'acces depuis la page hote |

```js
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#039;');
}
```

---

## 6. Memory leaks — checklist transferable

| Source | Solution |
|--------|----------|
| `setInterval()` | Stocker l'ID, `clearInterval()` dans `destroy()` |
| `window.addEventListener()` | Ref nommee, `removeEventListener()` dans `destroy()` |
| `MutationObserver` | `observer.disconnect()` + `observer = null` |
| Popups DOM | Limiter le nombre actif (`activePopups.length > MAX`) |
| Caches en memoire | `cache.clear()` dans `destroy()` |

**Regle** : chaque module UI doit avoir une fonction `destroy()` qui nettoie
tout ce qu'il a cree (DOM, listeners, intervals, caches).

---

## 7. Affiliation et monetisation

### CTA contextuels avec regles de priorite

```js
const CTA_RULES = [
  { id: 'credit', priority: 1, condition: (d) => d.prix > 80000, partners: ['pretto', 'meilleurtaux'] },
  { id: 'travaux', priority: 2, condition: (d) => ['D','E','F','G'].includes(d.dpe) },
  { id: 'assurance', priority: 5, condition: () => true },  // toujours
];

function evaluateRules(data) {
  return CTA_RULES
    .filter(r => r.condition(data))
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 3);  // max 3 CTAs visibles
}
```

### Analytics 100% locales (RGPD-friendly)

Pas besoin de Google Analytics. Un simple compteur dans `chrome.storage.local` :

```js
const STORAGE_KEY = 'monprojet_analytics';
const DEFAULT = { annonces: 0, listes: 0, impressions: {}, clicks: {} };

async function trackClick(ctaId) {
  const stats = await getStats();
  stats.clicks[ctaId] = (stats.clicks[ctaId] || 0) + 1;
  chrome.storage.local.set({ [STORAGE_KEY]: stats });
}
```

### Liens affilies via background (jamais window.open)

```js
// content_script.js — envoie au background
chrome.runtime.sendMessage({ action: 'OPEN_AFFILIATE_URL', payload: { url } });

// background.js — ouvre l'onglet
chrome.tabs.create({ url, active: false });
```

Pourquoi : `window.open()` est bloque par les popup blockers.
`chrome.tabs.create()` fonctionne toujours.

---

## 8. Design system Bento dark

### Tokens CSS reutilisables

```css
:host {
  --bg-primary: #0F0F11;
  --bg-surface: #1A1A1F;
  --bg-elevated: #242429;
  --border: #2A2A2F;
  --accent: #6C63FF;
  --text-1: #FFFFFF;
  --text-2: #B0B0B0;
  --text-3: #666666;
  --success: #4ADE80;
  --danger: #F87171;
  --warn: #FBBF24;
  --radius: 12px;
}
```

### Skeleton loaders

Afficher des squelettes animes pendant le chargement, pas un spinner :

```js
function skeleton(size, lines) {
  let html = '<div class="skeleton skeleton-label"></div>';
  html += '<div class="skeleton skeleton-value"></div>';
  for (let i = 0; i < lines; i++) {
    html += `<div class="skeleton skeleton-line" style="width:${70 + i*10}%"></div>`;
  }
  return `<div class="bento-card idi-card-${size}">${html}</div>`;
}
```

---

## 9. Chrome Web Store — checklist

| # | Element | Conseil |
|---|---------|---------|
| 1 | Icones | 16x16, 48x48, 128x128 PNG. Generables avec Pillow |
| 2 | Description courte | 132 chars max, commence par un verbe d'action |
| 3 | Description longue | Fonctionnalites par section, sources de donnees, vie privee |
| 4 | Privacy policy | Page HTML statique hebergeable sur GitHub Pages |
| 5 | Permissions | Justifier CHAQUE permission dans la description |
| 6 | CSP | La plus stricte possible |
| 7 | Zip | Exclure .git, .claude, node_modules, tests, docs |

---

## 10. Workflow de developpement valide

### Pipeline en 10 etapes

```
1. Infrastructure (manifest, background, SW)
2. Scraping (selecteurs, fallback, SPA)
3. APIs (modules, cache, fetchWithTimeout)
4. Calculs locaux (notaire, nego, CTP)
5. Enrichissement (pipeline orchestrateur)
6. UI composants (design tokens, CSS, grid)
7. UI integration (dashboard, quickview)
8. Monetisation (affiliation, analytics, tracker)
9. Popup extension (toggle, params, stats)
10. Audits + Store (securite, perf, UX, zip)
```

### Audits a faire AVANT publication

1. **Securite** : CSP, XSS, permissions, secrets, eval
2. **Performance** : tailles fichiers, injection time, storage, memory leaks
3. **UX** : etats vides, erreurs gracieuses, messages clairs

---

## Applicabilite a BOOMERANG

| Pattern ImmoData | Equivalent BOOMERANG |
|-----------------|---------------------|
| `self.__immodata` namespace | `self.__boomerang` namespace |
| Message passing content/background | Meme architecture |
| Shadow DOM pour UI injectee | Dashboard BOOMERANG isole du site |
| Scraping multi-fallback | Scraping avec selecteurs adaptatifs |
| Cache avec TTL par API | Cache des donnees recoltees |
| Analytics locales | Stats d'utilisation BOOMERANG |
| `escHtml()` anti-XSS | Meme protection sur tout texte injecte |
| `destroy()` avec cleanup complet | Meme pattern pour navigation SPA |
| Privacy policy RGPD | Meme template adaptable |
| Design tokens Bento dark | Meme systeme de theming |
