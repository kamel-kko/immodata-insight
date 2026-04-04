/**
 * ImmoData — Module API OpenRouteService (Isochrones)
 *
 * Calcule les zones accessibles en 15/30 min en voiture, transport
 * ou vélo. Nécessite une clé API gratuite configurée par l'utilisateur.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:ORS');

export async function handleFetchOrs(payload) {
  const { lat, lon, mode } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  // Récupérer la clé API depuis chrome.storage
  const storage = await chrome.storage.local.get('immodata_ors_key');
  const apiKey = storage.immodata_ors_key;

  if (!apiKey) {
    log.warn('ORS : pas de clé API configurée');
    return { success: false, error: 'NO_API_KEY', message: 'Configurez votre clé ORS dans les paramètres' };
  }

  const profile = mode || 'driving-car';
  const cacheKey = `ors_${lat.toFixed(3)}_${lon.toFixed(3)}_${profile}`;
  const cached = await checkCache(cacheKey, API_CONFIG.ors_isochrones.ttl_days);
  if (cached.hit) return cached.data;

  log.info(`ORS : isochrone ${profile} depuis (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(
      API_CONFIG.ors_isochrones.endpoint,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': apiKey
        },
        body: JSON.stringify({
          locations: [[lon, lat]],
          range: [900, 1800], // 15 min et 30 min en secondes
          range_type: 'time'
        })
      },
      API_CONFIG.ors_isochrones.timeout_ms
    );

    if (!response.ok) {
      return { success: false, error: 'API_ERROR', message: `ORS a répondu ${response.status}` };
    }

    const data = await response.json();
    const result = {
      profile,
      isochrones: data.features || [],
      nb_zones: (data.features || []).length
    };

    await setCache(cacheKey, result);
    log.info(`ORS : ${result.nb_zones} isochrone(s) calculée(s)`);
    return result;
  } catch (err) {
    log.error('ORS erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
