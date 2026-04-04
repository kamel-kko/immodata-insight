/**
 * ImmoData — Content Script Bootstrap
 *
 * Ce fichier est le PREMIER à se charger dans les content scripts.
 * Il initialise globalThis.__immodata et enregistre les utilitaires
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
  globalThis.__immodata = globalThis.__immodata || {};

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

  globalThis.__immodata.createLogger = createLogger;
  globalThis.__immodata.loggerConfig = { DEV, LEVELS, MIN_LEVEL };

  // ============================================================
  // SECURITY — Copie légère pour les content scripts
  // ============================================================

  const URL_ALLOWLIST = [
    'api-adresse.data.gouv.fr', 'api.dvf.gouv.fr', 'www.georisques.gouv.fr',
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

  globalThis.__immodata.security = {
    sanitizeText, sanitizeNumber, sanitizeUrl,
    validateLatLon, validatePostalCode,
    URL_ALLOWLIST, FRANCE_BOUNDS
  };

})();
