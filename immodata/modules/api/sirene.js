/**
 * ImmoData — Module API INSEE SIRENE
 *
 * Interroge l'API SIRENE pour évaluer le tissu économique local :
 * nombre d'établissements actifs autour du bien. Un centre-ville
 * dynamique avec beaucoup de commerces = bon signe pour la valorisation.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:SIRENE');

export async function handleFetchSirene(payload) {
  const { code_insee } = payload;

  if (!code_insee) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Code INSEE manquant' };
  }

  const cacheKey = `sirene_${code_insee}`;
  const cached = await checkCache(cacheKey, API_CONFIG.sirene.ttl_days);
  if (cached.hit) return cached.data;

  log.info(`SIRENE : recherche établissements pour INSEE ${code_insee}`);

  const config = API_CONFIG.sirene;
  const url = new URL(config.endpoint);
  url.searchParams.set('q', `codeCommuneEtablissement:${code_insee} AND etatAdministratifEtablissement:A`);
  url.searchParams.set('nombre', '0'); // On veut juste le count

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      // L'API SIRENE nécessite souvent une clé API
      log.warn(`SIRENE : réponse ${response.status} (clé API probablement requise)`);
      return { success: false, error: 'API_ERROR', message: `SIRENE a répondu ${response.status}` };
    }

    const data = await response.json();
    const nbTotal = data.header?.total || data.total || 0;

    const result = {
      nb_etablissements: nbTotal,
      dynamisme: nbTotal > 500 ? 'fort' : nbTotal > 100 ? 'moyen' : 'faible'
    };

    await setCache(cacheKey, result);
    log.info(`SIRENE : ${nbTotal} établissement(s) actif(s)`);
    return result;
  } catch (err) {
    log.error('SIRENE erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
