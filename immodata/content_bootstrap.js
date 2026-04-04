/**
 * ImmoData — Content Script Bootstrap
 *
 * Ce fichier est le PREMIER à se charger dans les content scripts.
 * Il initialise self.__immodata et enregistre les utilitaires
 * de base (security + logger) pour que tous les autres scripts IIFE
 * puissent les utiliser.
 *
 * POURQUOI ce fichier existe :
 * security.js et logger.js sont des ES Modules (avec export) pour
 * être importés par background.js. Mais les content scripts ne
 * supportent pas les ES Modules. Donc on recopie ici les fonctions
 * essentielles en mode IIFE (sans import/export).
 */

(function () {
  'use strict';

  // Initialiser le namespace global
  self.__immodata = self.__immodata || {};

  // ============================================================
  // LOGGER — Copie légère pour les content scripts
  // ============================================================

  const DEV = true;
  const LEVELS = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
  const MIN_LEVEL = DEV ? LEVELS.DEBUG : LEVELS.ERROR;

  function createLogger(moduleName) {
    const prefix = `[ImmoData][${moduleName}]`;
    return {
      debug(...args) { if (MIN_LEVEL <= LEVELS.DEBUG) console.debug(`${prefix}[DEBUG]`, ...args); },
      info(...args)  { if (MIN_LEVEL <= LEVELS.INFO)  console.info(`${prefix}[INFO]`, ...args); },
      warn(...args)  { if (MIN_LEVEL <= LEVELS.WARN)  console.warn(`${prefix}[WARN]`, ...args); },
      error(...args) { if (MIN_LEVEL <= LEVELS.ERROR) console.error(`${prefix}[ERROR]`, ...args); }
    };
  }

  self.__immodata.createLogger = createLogger;
  self.__immodata.loggerConfig = { DEV, LEVELS, MIN_LEVEL };

  // ============================================================
  // SECURITY — Copie légère pour les content scripts
  // ============================================================

  const URL_ALLOWLIST = [
    'api-adresse.data.gouv.fr', 'public.opendatasoft.com', 'www.georisques.gouv.fr',
    'data.education.gouv.fr', 'overpass-api.de', 'data.ademe.fr',
    'www.data.gouv.fr', 'opendata.reseaux-energies.fr', 'data.culture.gouv.fr',
    'api.insee.fr', 'api.openrouteservice.org', 'www.anil.org',
    'www.pretto.fr', 'www.meilleurtaux.com', 'www.moveezy.fr',
    'www.habitissimo.fr', 'www.luko.eu', 'www.diagamter.com'
  ];

  const FRANCE_BOUNDS = { latMin: 41.3, latMax: 51.1, lonMin: -5.2, lonMax: 9.6 };

  function sanitizeText(input) {
    if (typeof input !== 'string') return '';
    return input.replace(/<[^>]*>/g, '').slice(0, 500).trim();
  }

  function sanitizeNumber(input) {
    const num = Number(input);
    return Number.isFinite(num) ? num : null;
  }

  function sanitizeUrl(url, allowlist) {
    if (typeof url !== 'string') return null;
    const domains = allowlist || URL_ALLOWLIST;
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== 'https:') return null;
      if (!domains.includes(parsed.hostname)) return null;
      return parsed.href;
    } catch { return null; }
  }

  function validateLatLon(lat, lon) {
    const latNum = sanitizeNumber(lat);
    const lonNum = sanitizeNumber(lon);
    if (latNum === null || lonNum === null) return false;
    return latNum >= FRANCE_BOUNDS.latMin && latNum <= FRANCE_BOUNDS.latMax &&
           lonNum >= FRANCE_BOUNDS.lonMin && lonNum <= FRANCE_BOUNDS.lonMax;
  }

  function validatePostalCode(cp) {
    if (typeof cp !== 'string') return false;
    return /^\d{5}$/.test(cp.trim());
  }

  self.__immodata.security = {
    sanitizeText, sanitizeNumber, sanitizeUrl,
    validateLatLon, validatePostalCode,
    URL_ALLOWLIST, FRANCE_BOUNDS
  };

  // ============================================================
  // TRACKER D'ANNONCE — Historique de prix (chrome.storage.local)
  // ============================================================
  // Copie legere du tracker de cache.js pour les content scripts.
  // chrome.storage.local est accessible depuis les content scripts.

  const trackerLog = createLogger('TRACKER');

  function hashUrl(url) {
    let hash = 0;
    for (let i = 0; i < url.length; i++) {
      const ch = url.charCodeAt(i);
      hash = ((hash << 5) - hash) + ch;
      hash |= 0;
    }
    return 'tracker_' + Math.abs(hash).toString(36);
  }

  async function trackAnnonceVisit(url, prix, surface) {
    if (!url) return null;
    const key = hashUrl(url);
    try {
      const result = await chrome.storage.local.get(key);
      const now = Date.now();

      if (!result[key]) {
        const entry = {
          url: url.slice(0, 200),
          premiere_visite: now,
          derniere_visite: now,
          surface: surface,
          historique_prix: prix ? [{ prix, timestamp: now }] : []
        };
        await chrome.storage.local.set({ [key]: entry });
        trackerLog.debug('Premiere visite pour ' + url.slice(0, 60));
        return { jours_en_ligne: 0, nb_baisses_prix: 0, delta_premier_prix: null, historique: entry.historique_prix };
      }

      const entry = result[key];
      entry.derniere_visite = now;
      const lastPrix = entry.historique_prix.length > 0
        ? entry.historique_prix[entry.historique_prix.length - 1].prix : null;
      if (prix && prix !== lastPrix) {
        entry.historique_prix.push({ prix, timestamp: now });
        trackerLog.info('Changement de prix : ' + lastPrix + ' -> ' + prix);
      }
      if (entry.historique_prix.length > 20) {
        entry.historique_prix = entry.historique_prix.slice(-20);
      }
      await chrome.storage.local.set({ [key]: entry });

      const joursEnLigne = Math.floor((now - entry.premiere_visite) / (1000 * 60 * 60 * 24));
      const premierPrix = entry.historique_prix.length > 0 ? entry.historique_prix[0].prix : null;
      let nbBaisses = 0;
      for (let i = 1; i < entry.historique_prix.length; i++) {
        if (entry.historique_prix[i].prix < entry.historique_prix[i - 1].prix) nbBaisses++;
      }
      let deltaPremierPrix = null;
      if (premierPrix && prix && premierPrix !== prix) deltaPremierPrix = prix - premierPrix;

      return { jours_en_ligne: joursEnLigne, nb_baisses_prix: nbBaisses, delta_premier_prix: deltaPremierPrix, historique: entry.historique_prix };
    } catch (err) {
      trackerLog.error('Erreur tracker :', err);
      return null;
    }
  }

  self.__immodata.cache = {
    trackAnnonceVisit,
    hashUrl
  };

})();
