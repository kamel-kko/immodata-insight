/**
 * ImmoData — Module API Encadrement des Loyers
 *
 * Récupère les données d'encadrement des loyers depuis data.gouv.fr.
 * Permet d'estimer un loyer de référence pour calculer la rentabilité
 * locative et comparer achat vs location.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:LOYERS');

// Estimation de loyer au m² par zone (si pas de données d'encadrement)
const LOYER_M2_ESTIMATION = {
  A_bis: 28, A: 18, B1: 13, B2: 10, C: 8
};

export async function handleFetchLoyers(payload) {
  const { code_insee, surface, nb_pieces } = payload;

  if (!code_insee) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Code INSEE manquant' };
  }

  const cacheKey = `loyers_${code_insee}`;
  const cached = await checkCache(cacheKey, API_CONFIG.loyers.ttl_days);
  if (cached.hit) return cached.data;

  log.info(`Loyers : recherche pour INSEE ${code_insee}`);

  const config = API_CONFIG.loyers;
  try {
    const response = await fetchWithTimeout(config.dataset_url, {}, config.timeout_ms);
    if (!response.ok) {
      log.warn(`Loyers : réponse ${response.status}`);
      // Pas de données d'encadrement, retourner estimation
      const estimation = estimerLoyer(surface, nb_pieces);
      return { ...estimation, source: 'estimation' };
    }
    const data = await response.json();
    // Chercher le code INSEE dans les données
    const records = Array.isArray(data) ? data : (data.records || data.results || []);
    const match = records.find(r => {
      const f = r.fields || r;
      return f.code_insee === code_insee || f.insee === code_insee;
    });

    if (match) {
      const f = match.fields || match;
      const result = {
        loyer_ref: f.loyer_reference || f.loyer_ref || null,
        loyer_ref_majore: f.loyer_reference_majore || null,
        loyer_ref_minore: f.loyer_reference_minore || null,
        zone: f.zone || null,
        source: 'encadrement'
      };
      await setCache(cacheKey, result);
      return result;
    }

    const estimation = estimerLoyer(surface, nb_pieces);
    await setCache(cacheKey, { ...estimation, source: 'estimation' });
    return { ...estimation, source: 'estimation' };
  } catch (err) {
    log.warn('Loyers erreur :', err.message);
    const estimation = estimerLoyer(surface, nb_pieces);
    return { ...estimation, source: 'estimation' };
  }
}

function estimerLoyer(surface, nb_pieces) {
  // Estimation grossière basée sur la surface
  const loyerM2 = 12; // Moyenne nationale
  const loyer = surface ? Math.round(surface * loyerM2) : null;
  return { loyer_ref: loyerM2, loyer_estime: loyer };
}
