/**
 * ImmoData — Module API Mérimée (Monuments Historiques)
 *
 * Interroge la base Mérimée du Ministère de la Culture pour savoir
 * si un bien est dans le périmètre d'un monument historique (500m).
 * Cela implique des contraintes architecturales pour les travaux
 * mais peut aussi être un atout de charme.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:MERIMEE');

export async function handleFetchMerimee(payload) {
  const { lat, lon } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `merimee_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.merimee.ttl_days);
  if (cached.hit) return cached.data;

  const config = API_CONFIG.merimee;
  const url = new URL(config.endpoint);
  url.searchParams.set('where', `within_distance(coordonnees_ban, geom'POINT(${lon} ${lat})', 500m)`);
  url.searchParams.set('limit', '10');

  log.info(`Mérimée : recherche monuments autour de (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      return { success: false, error: 'API_ERROR', message: `Mérimée a répondu ${response.status}` };
    }
    const data = await response.json();
    const results = data.results || data.records || [];

    const monuments = results.map(r => {
      const f = r.fields || r;
      return {
        nom: f.appellation_courante || f.tico || f.denomination || '',
        protection: f.type_de_protection || f.prot || '',
        commune: f.commune || ''
      };
    });

    const result = {
      nb_monuments: monuments.length,
      monuments: monuments.slice(0, 5),
      dans_perimetre: monuments.length > 0,
      contrainte_travaux: monuments.length > 0
    };

    await setCache(cacheKey, result);
    log.info(`Mérimée : ${monuments.length} monument(s) dans le périmètre`);
    return result;
  } catch (err) {
    log.error('Mérimée erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
