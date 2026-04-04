/**
 * ImmoData — Gestionnaire de cache
 * Utilise chrome.storage.local pour stocker les résultats d'API.
 * Chaque entrée a un timestamp pour savoir quand elle a été créée.
 * Le TTL (Time To Live) détermine combien de temps une donnée reste valide.
 *
 * Analogie : c'est comme un frigo avec des dates de péremption.
 * On vérifie la date avant de consommer, et on jette ce qui est périmé.
 */

import { createLogger } from './logger.js';

const log = createLogger('CACHE');

// Limite de sécurité : 4 MB max dans chrome.storage.local
const MAX_STORAGE_BYTES = 4 * 1024 * 1024;

/**
 * Vérifie si une donnée est en cache et encore valide.
 *
 * @param {string} key - La clé de cache (ex: "ban_75001_Paris")
 * @param {number} ttlDays - Durée de validité en jours
 * @returns {{ hit: boolean, data: any, age_hours: number }}
 */
async function checkCache(key, ttlDays) {
  try {
    const result = await chrome.storage.local.get(key);
    if (!result[key]) {
      return { hit: false, data: null, age_hours: 0 };
    }

    const entry = result[key];
    const ageMs = Date.now() - entry.timestamp;
    const ageHours = ageMs / (1000 * 60 * 60);
    const ttlMs = ttlDays * 24 * 60 * 60 * 1000;

    if (ageMs > ttlMs) {
      log.debug(`Cache expiré pour "${key}" (âge: ${ageHours.toFixed(1)}h)`);
      return { hit: false, data: null, age_hours: ageHours };
    }

    log.debug(`Cache hit pour "${key}" (âge: ${ageHours.toFixed(1)}h)`);
    return { hit: true, data: entry.data, age_hours: ageHours };
  } catch (err) {
    log.error(`Erreur lecture cache "${key}":`, err);
    return { hit: false, data: null, age_hours: 0 };
  }
}

/**
 * Stocke une donnée en cache avec un timestamp.
 *
 * @param {string} key - La clé de cache
 * @param {any} data - Les données à stocker
 */
async function setCache(key, data) {
  try {
    await chrome.storage.local.set({
      [key]: { data, timestamp: Date.now() }
    });
    log.debug(`Cache set pour "${key}"`);
  } catch (err) {
    log.error(`Erreur écriture cache "${key}":`, err);
  }
}

/**
 * Efface toutes les clés de cache qui correspondent à un pattern (regex).
 * Utile pour purger toutes les données d'une API en particulier.
 *
 * Exemple : clearCacheByPattern(/^dvf_/) efface tous les caches DVF.
 *
 * @param {RegExp} pattern - Expression régulière pour filtrer les clés
 */
async function clearCacheByPattern(pattern) {
  try {
    const all = await chrome.storage.local.get(null);
    const keysToRemove = Object.keys(all).filter(k => pattern.test(k));
    if (keysToRemove.length > 0) {
      await chrome.storage.local.remove(keysToRemove);
      log.info(`Cache purgé : ${keysToRemove.length} clé(s) supprimée(s) (pattern: ${pattern})`);
    }
  } catch (err) {
    log.error('Erreur purge cache par pattern:', err);
  }
}

/**
 * Retourne des statistiques sur le cache :
 * combien de clés, la taille totale estimée, la plus ancienne et la plus récente.
 */
async function getCacheStats() {
  try {
    const all = await chrome.storage.local.get(null);
    const keys = Object.keys(all);
    const totalSizeKb = Math.round(JSON.stringify(all).length / 1024);

    let oldestKey = null;
    let newestKey = null;
    let oldestTime = Infinity;
    let newestTime = 0;

    for (const key of keys) {
      const entry = all[key];
      if (entry && entry.timestamp) {
        if (entry.timestamp < oldestTime) {
          oldestTime = entry.timestamp;
          oldestKey = key;
        }
        if (entry.timestamp > newestTime) {
          newestTime = entry.timestamp;
          newestKey = key;
        }
      }
    }

    return {
      nb_keys: keys.length,
      total_size_kb: totalSizeKb,
      oldest_key: oldestKey,
      newest_key: newestKey
    };
  } catch (err) {
    log.error('Erreur lecture stats cache:', err);
    return { nb_keys: 0, total_size_kb: 0, oldest_key: null, newest_key: null };
  }
}

/**
 * Efface tout le cache. Appelé depuis le bouton "Effacer le cache" dans la popup.
 */
async function clearAllCache() {
  try {
    await chrome.storage.local.clear();
    log.info('Cache entièrement vidé');
  } catch (err) {
    log.error('Erreur vidage cache:', err);
  }
}

/**
 * Purge automatique : supprime les entrées dont le TTL est dépassé.
 * Appelé au démarrage du Service Worker pour faire le ménage.
 *
 * @param {number} maxTtlDays - TTL maximum à appliquer (ex: 90 jours)
 */
async function purgeExpiredEntries(maxTtlDays) {
  try {
    const all = await chrome.storage.local.get(null);
    const now = Date.now();
    const maxAge = maxTtlDays * 24 * 60 * 60 * 1000;
    const expired = [];

    for (const [key, entry] of Object.entries(all)) {
      if (entry && entry.timestamp && (now - entry.timestamp) > maxAge) {
        expired.push(key);
      }
    }

    if (expired.length > 0) {
      await chrome.storage.local.remove(expired);
      log.info(`Purge auto : ${expired.length} entrée(s) expirée(s) supprimée(s)`);
    }
  } catch (err) {
    log.error('Erreur purge auto:', err);
  }
}

if (typeof globalThis.__immodata === 'undefined') {
  globalThis.__immodata = {};
}
globalThis.__immodata.cache = {
  checkCache,
  setCache,
  clearCacheByPattern,
  getCacheStats,
  clearAllCache,
  purgeExpiredEntries
};

export {
  checkCache,
  setCache,
  clearCacheByPattern,
  getCacheStats,
  clearAllCache,
  purgeExpiredEntries,
  MAX_STORAGE_BYTES
};
