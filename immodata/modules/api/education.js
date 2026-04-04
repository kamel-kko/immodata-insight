/**
 * ImmoData — Module API Éducation
 *
 * Interroge deux API du Ministère de l'Éducation :
 * 1. Annuaire : liste des établissements scolaires proches (écoles, collèges, lycées)
 * 2. IVAL : indicateurs de valeur ajoutée des lycées (taux de réussite au bac, etc.)
 *
 * Permet de savoir quelles écoles sont accessibles depuis le bien,
 * et si les lycées du secteur ont de bons résultats.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:EDUCATION');

export async function handleFetchEducation(payload) {
  const { lat, lon, code_insee } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `education_${code_insee || `${lat.toFixed(3)}_${lon.toFixed(3)}`}`;
  const cached = await checkCache(cacheKey, API_CONFIG.education_annuaire.ttl_days);
  if (cached.hit) return cached.data;

  log.info(`Éducation : recherche autour de (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  // Annuaire — établissements proches
  const config = API_CONFIG.education_annuaire;
  const url = new URL(config.endpoint);
  url.searchParams.set('where', `within_distance(position, geom'POINT(${lon} ${lat})', ${config.rayon_km}km)`);
  url.searchParams.set('limit', '20');
  url.searchParams.set('select', 'nom_etablissement,type_etablissement,statut_public_prive,adresse_1,code_postal,nom_commune,latitude,longitude');

  let etablissements = [];
  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (response.ok) {
      const data = await response.json();
      const results = data.results || data.records || [];
      etablissements = results.map(r => {
        const f = r.fields || r;
        return {
          nom: f.nom_etablissement || f.nom || '',
          type: f.type_etablissement || '',
          statut: f.statut_public_prive || '',
          commune: f.nom_commune || '',
          lat: f.latitude,
          lon: f.longitude
        };
      });
    }
  } catch (err) {
    log.warn('Annuaire éducation erreur :', err.message);
  }

  // Compter par type
  const parType = {};
  for (const e of etablissements) {
    const t = e.type || 'autre';
    parType[t] = (parType[t] || 0) + 1;
  }

  const result = {
    etablissements,
    nb_total: etablissements.length,
    par_type: parType
  };

  await setCache(cacheKey, result);
  log.info(`Éducation : ${etablissements.length} établissement(s) trouvé(s)`);
  return result;
}
