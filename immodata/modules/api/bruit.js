/**
 * ImmoData — Module API Plan d'Exposition au Bruit (PEB)
 *
 * Vérifie si un bien est dans une zone de bruit aérien (DGAC).
 * Les zones vont de A (très fort bruit) à D (bruit modéré).
 * Impacte la valeur du bien : zone B = décote estimée ~8%.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout } from '../../background.js';

const log = createLogger('API:BRUIT');

const PEB_ENDPOINT = 'https://www.georisques.gouv.fr/api/v1/erp';
const TTL_DAYS = 90;
const TIMEOUT_MS = 6000;

const DECOTES_PEB = { A: -15, B: -8, C: -4, D: -2 };

export async function handleFetchBruit(payload) {
  const { lat, lon } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `bruit_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, TTL_DAYS);
  if (cached.hit) return cached.data;

  log.info(`PEB : vérification bruit aérien (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const url = new URL(PEB_ENDPOINT);
    url.searchParams.set('latlon', `${lon},${lat}`);
    url.searchParams.set('rayon', '500');

    const response = await fetchWithTimeout(url.toString(), {}, TIMEOUT_MS);
    if (!response.ok) {
      return { success: false, error: 'API_ERROR', message: `PEB a répondu ${response.status}` };
    }

    const data = await response.json();
    // Chercher un indicateur de zone de bruit dans la réponse
    const results = data.results || data.data || (Array.isArray(data) ? data : [data]);

    let zonePeb = null;
    for (const item of (Array.isArray(results) ? results : [results])) {
      if (!item) continue;
      if (item.zone_bruit || item.peb) {
        zonePeb = item.zone_bruit || item.peb;
        break;
      }
    }

    const result = {
      zone_peb: zonePeb,
      risque: zonePeb ? (zonePeb <= 'B' ? 'CRITIQUE' : 'MODERE') : 'AUCUN',
      decote_estimee: zonePeb ? (DECOTES_PEB[zonePeb] || 0) : 0
    };

    await setCache(cacheKey, result);
    log.info(`PEB : zone ${zonePeb || 'aucune'}`);
    return result;
  } catch (err) {
    log.error('PEB erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }
}
