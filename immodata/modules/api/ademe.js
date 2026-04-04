/**
 * ImmoData — Module API ADEME DPE
 *
 * Interroge la base DPE de l'ADEME pour récupérer le diagnostic
 * de performance énergétique officiel d'un bien, si disponible.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:ADEME');

export async function handleFetchAdeme(payload) {
  const { lat, lon, adresse_normalisee } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `ademe_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.ademe_dpe.ttl_days);
  if (cached.hit) return cached.data;

  const config = API_CONFIG.ademe_dpe;
  const url = new URL(config.endpoint);
  url.searchParams.set('geo_distance', `${lon},${lat},200`);
  url.searchParams.set('size', '5');
  url.searchParams.set('sort', 'date_etablissement_dpe:-1');

  log.info(`ADEME : recherche DPE autour de (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      return { success: false, error: 'API_ERROR', message: `ADEME a répondu ${response.status}` };
    }
    const data = await response.json();
    const results = data.results || data.data || [];

    if (results.length === 0) {
      const empty = { dpe_officiel: null, nb_resultats: 0 };
      await setCache(cacheKey, empty);
      return empty;
    }

    const dpe = results[0];
    const result = {
      dpe_officiel: dpe.classe_consommation_energie || dpe.etiquette_dpe || null,
      ges_officiel: dpe.classe_estimation_ges || dpe.etiquette_ges || null,
      conso_energie: dpe.consommation_energie || null,
      date_dpe: dpe.date_etablissement_dpe || null,
      nb_resultats: results.length
    };

    await setCache(cacheKey, result);
    log.info(`ADEME : DPE ${result.dpe_officiel}, GES ${result.ges_officiel}`);
    return result;
  } catch (err) {
    log.error('ADEME erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
