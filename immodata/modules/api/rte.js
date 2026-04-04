/**
 * ImmoData — Module API RTE (Lignes Haute Tension)
 *
 * Interroge l'Open Data RTE pour détecter les lignes haute tension
 * à proximité d'un bien. Une ligne HT proche peut impacter la valeur
 * du bien (décote estimée d'environ 5%).
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:RTE');

export async function handleFetchRte(payload) {
  const { lat, lon } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `rte_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.rte_lignes_ht.ttl_days);
  if (cached.hit) return cached.data;

  const config = API_CONFIG.rte_lignes_ht;
  const url = new URL(config.endpoint);
  url.searchParams.set('where', `within_distance(geo_point_2d, geom'POINT(${lon} ${lat})', 2km)`);
  url.searchParams.set('limit', '10');

  log.info(`RTE : recherche lignes HT autour de (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      return { success: false, error: 'API_ERROR', message: `RTE a répondu ${response.status}` };
    }
    const data = await response.json();
    const results = data.results || data.records || [];

    const lignes = results.map(r => {
      const f = r.fields || r;
      return {
        nom: f.nom_ligne || f.name || '',
        tension_kv: f.tension || null,
        exploitant: f.exploitant || 'RTE'
      };
    });

    const result = {
      nb_lignes: lignes.length,
      lignes: lignes.slice(0, 5),
      risque: lignes.length > 0 ? 'MODERE' : 'AUCUN',
      decote_estimee: lignes.length > 0 ? -5 : 0
    };

    await setCache(cacheKey, result);
    log.info(`RTE : ${lignes.length} ligne(s) HT détectée(s)`);
    return result;
  } catch (err) {
    log.error('RTE erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
