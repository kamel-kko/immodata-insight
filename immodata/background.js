/**
 * ImmoData — Service Worker (background.js)
 *
 * C'est le "cerveau" de l'extension. Il tourne en arrière-plan et :
 * 1. Reste éveillé grâce à une alarme toutes les 25 secondes
 * 2. Reçoit les messages du content script (la page web)
 * 3. Appelle les APIs Open Data pour enrichir les données
 * 4. Renvoie les résultats au content script
 *
 * Analogie : c'est comme un assistant en coulisses.
 * Le content script (sur scène) lui passe un mot, il va chercher l'info,
 * et revient avec la réponse.
 */

// --- Imports des utilitaires ---
import { createLogger } from './utils/logger.js';
import { checkCache, setCache, purgeExpiredEntries } from './utils/cache.js';
import { createDispatcher } from './utils/messageRouter.js';
import { sanitizeUrl, validateLatLon, validatePostalCode } from './utils/security.js';

// --- Imports des modules API (ES Modules) ---
import { handleFetchDvf } from './modules/api/dvf.js';
import { handleFetchGeorisques } from './modules/api/georisques.js';
import { handleFetchEducation } from './modules/api/education.js';
import { handleFetchOverpass } from './modules/api/overpass.js';
import { handleFetchAdeme } from './modules/api/ademe.js';
import { handleFetchLoyers } from './modules/api/loyers.js';
import { handleFetchRte } from './modules/api/rte.js';
import { handleFetchBruit } from './modules/api/bruit.js';
import { handleFetchMerimee } from './modules/api/merimee.js';
import { handleFetchSirene } from './modules/api/sirene.js';
import { handleFetchOrs } from './modules/api/ors.js';
import { handleFetchAnil } from './modules/api/anil.js';

// --- Imports des modules de calcul (IIFE, chargés via globalThis) ---
// Ces fichiers utilisent self.__immodata, pas d'export ES Module.
// On les importe ici pour qu'ils s'exécutent et s'enregistrent sur globalThis.
import './modules/calculs/notaire.js';
import './modules/calculs/negotiation.js';
import './modules/calculs/coutTotal.js';
import './modules/calculs/plusValue.js';
import './modules/calculs/liquidite.js';
import './modules/calculs/travaux.js';
import './modules/calculs/qualiteVie.js';
import './modules/calculs/rentabilite.js';

// --- Import de la config API ---
// On ne peut pas importer du JSON directement en ES Module dans un SW Chrome,
// donc on déclare la config en dur ici, identique à apis.json.
// Elle sera utilisée par buildApiUrl() pour construire les URLs.
const API_CONFIG = {
  ban: {
    endpoint: 'https://api-adresse.data.gouv.fr/search/',
    ttl_days: 90,
    timeout_ms: 5000
  },
  dvf: {
    endpoint: 'https://api.dvf.gouv.fr/api/georecords/',
    ttl_days: 7,
    timeout_ms: 8000,
    rayon_metres: 500,
    nb_mois_historique: 24
  },
  georisques_erial: {
    endpoint: 'https://www.georisques.gouv.fr/api/v1/erp',
    ttl_days: 30,
    timeout_ms: 6000
  },
  georisques_icpe: {
    endpoint: 'https://www.georisques.gouv.fr/api/v1/installations_classees',
    ttl_days: 30,
    timeout_ms: 6000
  },
  education_annuaire: {
    endpoint: 'https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-annuaire-education/records',
    ttl_days: 30,
    timeout_ms: 6000,
    rayon_km: 2
  },
  education_ival: {
    endpoint: 'https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-ival/records',
    ttl_days: 30,
    timeout_ms: 6000
  },
  overpass: {
    endpoint: 'https://overpass-api.de/api/interpreter',
    ttl_days: 7,
    timeout_ms: 10000,
    rayon_metres: 1000
  },
  ademe_dpe: {
    endpoint: 'https://data.ademe.fr/data-fair/api/v1/datasets/dpe-v2-logements-existants/lines',
    ttl_days: 7,
    timeout_ms: 5000
  },
  loyers: {
    dataset_url: 'https://www.data.gouv.fr/fr/datasets/r/9af8a134-0526-48c2-a9b1-9c659ad5b2ee',
    ttl_days: 30,
    timeout_ms: 5000
  },
  rte_lignes_ht: {
    endpoint: 'https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/lignes-aeriennes-rte-nv/records',
    ttl_days: 90,
    timeout_ms: 5000
  },
  merimee: {
    endpoint: 'https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records',
    ttl_days: 90,
    timeout_ms: 5000
  },
  sirene: {
    endpoint: 'https://api.insee.fr/entreprises/sirene/siret',
    ttl_days: 7,
    timeout_ms: 6000
  },
  ors_isochrones: {
    endpoint: 'https://api.openrouteservice.org/v2/isochrones/driving-car',
    ttl_days: 7,
    timeout_ms: 8000,
    api_key_required: true
  },
  anil_zonage: {
    endpoint: 'https://www.anil.org/outils/encadrement-des-loyers/',
    ttl_days: 30,
    timeout_ms: 5000
  }
};

const log = createLogger('BACKGROUND');

// ============================================================
// KEEPALIVE — Empêcher le Service Worker de s'endormir
// ============================================================
// En MV3, Chrome peut "endormir" le SW après 30 secondes d'inactivité.
// On crée une alarme qui se déclenche toutes les 25 secondes pour le garder actif.
// C'est comme un réveil qui sonne régulièrement pour éviter de s'assoupir.

const KEEPALIVE_ALARM = 'immodata-keepalive';

chrome.alarms.create(KEEPALIVE_ALARM, { periodInMinutes: 25 / 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === KEEPALIVE_ALARM) {
    log.debug('Keepalive ping');
  }
});

// ============================================================
// ON INSTALLED — Actions au premier lancement / mise à jour
// ============================================================
// Quand l'extension est installée ou mise à jour, on purge le cache périmé.

chrome.runtime.onInstalled.addListener((details) => {
  log.info(`Extension ${details.reason} (v${chrome.runtime.getManifest().version})`);
  // Purger les entrées de cache de plus de 90 jours (le TTL max)
  purgeExpiredEntries(90);
});

// ============================================================
// FETCH WITH TIMEOUT — Appel réseau sécurisé avec limite de temps
// ============================================================
// Chaque appel API a un timeout (ex: 5 secondes). Si l'API ne répond pas
// à temps, on annule et on retourne une erreur propre.
// C'est comme commander au restaurant : si le plat n'arrive pas en 5 min,
// on annule la commande plutôt que d'attendre indéfiniment.

/**
 * @param {string} url - L'URL à appeler
 * @param {RequestInit} options - Options fetch (method, headers, etc.)
 * @param {number} timeoutMs - Timeout en millisecondes
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`TIMEOUT: l'API n'a pas répondu en ${timeoutMs}ms`);
    }
    throw err;
  }
}

// ============================================================
// BUILD API URL — Construire l'URL d'un appel API
// ============================================================
// Prend le nom de l'API et des paramètres, retourne l'URL complète.

/**
 * @param {string} apiName - Nom de l'API dans API_CONFIG (ex: "ban")
 * @param {Object} params - Paramètres query string (ex: { q: "1 rue..." })
 * @returns {{ url: string, timeout: number } | null}
 */
function buildApiUrl(apiName, params = {}) {
  const config = API_CONFIG[apiName];
  if (!config) {
    log.error(`API inconnue : "${apiName}"`);
    return null;
  }

  const endpoint = config.endpoint || config.dataset_url;
  if (!endpoint) {
    log.error(`Pas d'endpoint pour l'API "${apiName}"`);
    return null;
  }

  const url = new URL(endpoint);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }

  return {
    url: url.toString(),
    timeout: config.timeout_ms || 5000,
    ttl_days: config.ttl_days || 7
  };
}

// ============================================================
// HANDLERS — Fonctions de traitement par action
// ============================================================
// Chaque action autorisée (FETCH_BAN, FETCH_DVF, etc.) a sa fonction.
// Pour l'instant, seul FETCH_BAN est implémenté.
// Les autres retourneront "NOT_IMPLEMENTED" via le dispatcher.

/**
 * FETCH_BAN — Géocodage via l'API Base Adresse Nationale
 * Transforme une adresse texte en coordonnées GPS (latitude, longitude).
 */
async function handleFetchBan(payload) {
  const { adresse, cp, ville } = payload;

  // Validation des entrées
  if (!ville || typeof ville !== 'string') {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Ville manquante' };
  }
  if (cp && !validatePostalCode(cp)) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Code postal invalide' };
  }

  // Construire la requête de recherche
  // On combine adresse + CP + ville pour maximiser la précision
  const query = [adresse, cp, ville].filter(Boolean).join(' ');

  // Vérifier le cache
  const cacheKey = `ban_${cp || ''}_${ville}_${(adresse || '').slice(0, 30)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.ban.ttl_days);
  if (cached.hit) {
    return cached.data;
  }

  // Construire l'URL et appeler l'API
  const apiInfo = buildApiUrl('ban', { q: query, limit: 1 });
  if (!apiInfo) {
    return { success: false, error: 'CONFIG_ERROR', message: 'Configuration BAN manquante' };
  }

  // Si on a un code postal, on l'ajoute comme filtre pour plus de précision
  if (cp) {
    const url = new URL(apiInfo.url);
    url.searchParams.set('postcode', cp);
    apiInfo.url = url.toString();
  }

  log.info(`BAN: géocodage "${query}"`);

  const response = await fetchWithTimeout(apiInfo.url, {}, apiInfo.timeout);
  if (!response.ok) {
    return {
      success: false,
      error: 'API_ERROR',
      message: `BAN a répondu ${response.status}`
    };
  }

  const data = await response.json();

  if (!data.features || data.features.length === 0) {
    // Fallback : essayer avec CP + ville uniquement si on avait une adresse
    if (adresse && cp && ville) {
      log.warn('BAN: adresse imprécise, fallback sur CP + ville');
      return handleFetchBan({ cp, ville });
    }
    return {
      success: false,
      error: 'NO_RESULT',
      message: 'Aucune adresse trouvée par BAN'
    };
  }

  const feature = data.features[0];
  const result = {
    lat: feature.geometry.coordinates[1],
    lon: feature.geometry.coordinates[0],
    adresse_normalisee: feature.properties.label || '',
    code_insee: feature.properties.citycode || '',
    fiabilite_score: feature.properties.score || 0
  };

  // Valider que les coordonnées sont bien en France
  if (!validateLatLon(result.lat, result.lon)) {
    return {
      success: false,
      error: 'INVALID_COORDS',
      message: 'Coordonnées hors France métropolitaine'
    };
  }

  // Mettre en cache
  await setCache(cacheKey, result);

  return result;
}

/**
 * GET_CACHE — Lire une valeur du cache
 */
async function handleGetCache(payload) {
  const { key, ttl_days } = payload;
  if (!key) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Clé manquante' };
  }
  const result = await checkCache(key, ttl_days || 7);
  return { hit: result.hit, data: result.data, age_hours: result.age_hours };
}

/**
 * SET_CACHE — Écrire une valeur dans le cache
 */
async function handleSetCache(payload) {
  const { key, data } = payload;
  if (!key) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Clé manquante' };
  }
  await setCache(key, data);
  return { stored: true };
}

/**
 * CLEAR_CACHE — Vider tout le cache
 */
async function handleClearCache() {
  const { clearAllCache } = await import('./utils/cache.js');
  await clearAllCache();
  return { cleared: true };
}

/**
 * OPEN_AFFILIATE_URL — Ouvrir un lien partenaire dans un nouvel onglet
 * L'URL est vérifiée contre la liste blanche avant ouverture.
 */
async function handleOpenAffiliateUrl(payload) {
  const { url } = payload;
  const safeUrl = sanitizeUrl(url);
  if (!safeUrl) {
    log.warn(`URL affiliation refusée : "${url}"`);
    return { success: false, error: 'INVALID_URL', message: 'URL non autorisée' };
  }
  await chrome.tabs.create({ url: safeUrl });
  return { opened: true };
}

// ============================================================
// HANDLERS CALCULS — Exécutés localement (pas d'appel réseau)
// ============================================================

/**
 * CALC_NOTAIRE — Calcule les frais de notaire
 */
function handleCalcNotaire(payload) {
  return self.__immodata.calculs.notaire.calculerFraisNotaire(payload);
}

/**
 * CALC_NEGOTIATION — Calcule le score de négociation
 */
function handleCalcNegociation(payload) {
  return self.__immodata.calculs.negotiation.calculerScoreNegociation(payload);
}

/**
 * CALC_COUT_TOTAL — Calcule le Coût Total de Possession
 */
function handleCalcCoutTotal(payload) {
  return self.__immodata.calculs.coutTotal.calculerCoutTotal(payload);
}

/**
 * CALC_PLUS_VALUE — Score Potentiel de Plus-Value (0-100)
 */
function handleCalcPlusValue(payload) {
  return self.__immodata.calculs.plusValue.calculerScorePlusValue(payload);
}

/**
 * CALC_LIQUIDITE — Profil de liquidité et délai de vente
 */
function handleCalcLiquidite(payload) {
  return self.__immodata.calculs.liquidite.calculerLiquidite(payload);
}

/**
 * CALC_TRAVAUX — Estimation travaux + MaPrimeRénov'
 */
function handleCalcTravaux(payload) {
  return self.__immodata.calculs.travaux.estimerTravaux(payload);
}

/**
 * CALC_QUALITE_VIE — Score composite qualité de vie (0-100)
 */
function handleCalcQualiteVie(payload) {
  return self.__immodata.calculs.qualiteVie.calculerQualiteVie(payload);
}

/**
 * CALC_RENTABILITE — 4 stratégies locatives
 */
function handleCalcRentabilite(payload) {
  return self.__immodata.calculs.rentabilite.calculerRentabilite(payload);
}

// ============================================================
// DISPATCHER — Branchement des handlers sur les actions
// ============================================================
// On associe chaque action à sa fonction de traitement.
// Les actions non listées ici mais présentes dans ALLOWED_ACTIONS
// retourneront "NOT_IMPLEMENTED" automatiquement via le dispatcher.

const handlers = {
  FETCH_BAN: handleFetchBan,
  FETCH_DVF: handleFetchDvf,
  FETCH_GEORISQUES: handleFetchGeorisques,
  FETCH_EDUCATION: handleFetchEducation,
  FETCH_OVERPASS: handleFetchOverpass,
  FETCH_ADEME: handleFetchAdeme,
  FETCH_LOYERS: handleFetchLoyers,
  FETCH_RTE: handleFetchRte,
  FETCH_BRUIT: handleFetchBruit,
  FETCH_MERIMEE: handleFetchMerimee,
  FETCH_SIRENE: handleFetchSirene,
  FETCH_ORS: handleFetchOrs,
  FETCH_ANIL: handleFetchAnil,
  GET_CACHE: handleGetCache,
  SET_CACHE: handleSetCache,
  CLEAR_CACHE: handleClearCache,
  OPEN_AFFILIATE_URL: handleOpenAffiliateUrl,
  CALC_NOTAIRE: handleCalcNotaire,
  CALC_NEGOTIATION: handleCalcNegociation,
  CALC_COUT_TOTAL: handleCalcCoutTotal,
  CALC_PLUS_VALUE: handleCalcPlusValue,
  CALC_LIQUIDITE: handleCalcLiquidite,
  CALC_TRAVAUX: handleCalcTravaux,
  CALC_QUALITE_VIE: handleCalcQualiteVie,
  CALC_RENTABILITE: handleCalcRentabilite
};

const dispatch = createDispatcher(handlers);

// ============================================================
// LISTENER MESSAGES — Point d'entrée des messages
// ============================================================
// Quand le content script envoie un message, il arrive ici.
// Le dispatcher valide l'action et appelle le bon handler.
//
// IMPORTANT : on retourne `true` dans le listener pour indiquer
// à Chrome qu'on enverra la réponse de manière asynchrone
// (sinon le canal se ferme avant qu'on ait fini).

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  dispatch(message, sender, sendResponse);
  return true;
});

log.info('Service Worker démarré');

// Rendre fetchWithTimeout et buildApiUrl accessibles aux modules API
// qui seront importés dans les prochaines étapes
export { fetchWithTimeout, buildApiUrl, API_CONFIG };
