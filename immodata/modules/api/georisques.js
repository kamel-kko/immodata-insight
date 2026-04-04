/**
 * ImmoData — Module API Géorisques
 *
 * Interroge l'API Géorisques du gouvernement pour connaître les risques
 * naturels et industriels autour d'un point GPS.
 *
 * Deux appels combinés :
 * 1. ERIAL (ERP) : risques naturels (inondation, séisme, mouvement de terrain,
 *    radon, cavités souterraines)
 * 2. ICPE : installations classées pour la protection de l'environnement
 *    (usines, dépôts dangereux) dans un rayon de 2 km
 *
 * Analogie : c'est comme demander à la mairie "quels sont les dangers
 * potentiels autour de cette adresse ?". L'API du gouvernement répond
 * avec une liste de risques classés par gravité.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:GEORISQUES');

/**
 * Classifie un risque en CRITIQUE / MODERE / FAIBLE / AUCUN
 * selon le niveau renvoyé par l'API.
 */
function classifyRisk(level) {
  if (!level) return 'AUCUN';
  const l = String(level).toLowerCase();
  if (l.includes('fort') || l.includes('très') || l.includes('3') || l.includes('élevé')) return 'CRITIQUE';
  if (l.includes('moyen') || l.includes('modéré') || l.includes('2')) return 'MODERE';
  if (l.includes('faible') || l.includes('1')) return 'FAIBLE';
  // Si le risque est simplement "présent" sans niveau
  if (l.includes('oui') || l.includes('true') || l === 'present') return 'MODERE';
  return 'AUCUN';
}

/**
 * Appelle l'API Géorisques ERIAL (risques naturels).
 */
async function fetchErial(lat, lon) {
  const config = API_CONFIG.georisques_erial;
  const url = new URL(config.endpoint);
  url.searchParams.set('latlon', `${lon},${lat}`);
  // Rayon en mètres (1000m par défaut)
  url.searchParams.set('rayon', '1000');

  log.debug(`ERIAL: requête (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      log.warn(`ERIAL: réponse ${response.status}`);
      return { success: false, risques: [] };
    }
    const data = await response.json();
    return { success: true, data };
  } catch (err) {
    log.error('ERIAL: erreur réseau', err.message);
    return { success: false, risques: [] };
  }
}

/**
 * Appelle l'API Géorisques ICPE (installations classées).
 */
async function fetchIcpe(lat, lon) {
  const config = API_CONFIG.georisques_icpe;
  const url = new URL(config.endpoint);
  url.searchParams.set('latlon', `${lon},${lat}`);
  url.searchParams.set('rayon', '2000'); // 2 km pour les ICPE

  log.debug(`ICPE: requête (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  try {
    const response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
    if (!response.ok) {
      log.warn(`ICPE: réponse ${response.status}`);
      return { success: false, installations: [] };
    }
    const data = await response.json();
    return { success: true, data };
  } catch (err) {
    log.error('ICPE: erreur réseau', err.message);
    return { success: false, installations: [] };
  }
}

/**
 * Parse les risques naturels depuis la réponse ERIAL.
 * L'API renvoie des structures différentes selon les risques détectés.
 */
function parseRisquesNaturels(erialData) {
  const risques = [];
  if (!erialData || !erialData.data) return risques;

  const data = erialData.data;
  // L'API peut renvoyer les données dans différents formats
  const results = data.results || data.data || (Array.isArray(data) ? data : [data]);

  for (const item of (Array.isArray(results) ? results : [results])) {
    if (!item) continue;

    // Risque inondation
    if (item.risques_inondation || item.zone_inondable) {
      risques.push({
        type: 'inondation',
        niveau: classifyRisk(item.risques_inondation || item.zone_inondable),
        detail: 'Zone inondable détectée'
      });
    }

    // Risque séisme
    if (item.zone_sismicite || item.risques_seisme) {
      risques.push({
        type: 'seisme',
        niveau: classifyRisk(item.zone_sismicite || item.risques_seisme),
        detail: `Zone sismicité : ${item.zone_sismicite || 'détectée'}`
      });
    }

    // Mouvement de terrain
    if (item.mouvement_terrain || item.risques_mouvement_terrain) {
      risques.push({
        type: 'mouvement_terrain',
        niveau: classifyRisk(item.mouvement_terrain || item.risques_mouvement_terrain),
        detail: 'Mouvement de terrain possible'
      });
    }

    // Radon
    if (item.potentiel_radon || item.classe_potentiel_radon) {
      const niveau = item.potentiel_radon || item.classe_potentiel_radon;
      risques.push({
        type: 'radon',
        niveau: classifyRisk(niveau),
        detail: `Potentiel radon : ${niveau}`
      });
    }

    // Cavités souterraines
    if (item.cavites || item.risques_cavites) {
      risques.push({
        type: 'cavites',
        niveau: classifyRisk(item.cavites || item.risques_cavites),
        detail: 'Cavités souterraines détectées'
      });
    }

    // Argiles (retrait-gonflement)
    if (item.retrait_gonflement_argiles || item.argiles) {
      risques.push({
        type: 'argiles',
        niveau: classifyRisk(item.retrait_gonflement_argiles || item.argiles),
        detail: 'Retrait-gonflement des argiles'
      });
    }
  }

  return risques;
}

/**
 * Parse les installations classées depuis la réponse ICPE.
 */
function parseIcpe(icpeData) {
  const installations = [];
  if (!icpeData || !icpeData.data) return installations;

  const data = icpeData.data;
  const results = data.results || data.data || (Array.isArray(data) ? data : []);

  for (const item of (Array.isArray(results) ? results : [])) {
    if (!item) continue;
    installations.push({
      nom: item.nom_etablissement || item.raisonSociale || 'Installation classée',
      regime: item.regime || item.seveso || 'Non Seveso',
      activite: item.lib_activite || item.activite || '',
      distance_m: item.distance || null
    });
  }

  return installations;
}

/**
 * Calcule un score global de risque (0 = aucun risque, 100 = très risqué).
 */
function calculateGlobalScore(risques, icpeCount) {
  let score = 0;

  for (const r of risques) {
    switch (r.niveau) {
      case 'CRITIQUE': score += 25; break;
      case 'MODERE': score += 12; break;
      case 'FAIBLE': score += 5; break;
    }
  }

  // ICPE : chaque installation ajoute du risque
  score += Math.min(icpeCount * 5, 20);

  return Math.min(score, 100);
}

/**
 * Handler principal — Récupère les risques naturels et ICPE.
 *
 * @param {Object} payload
 * @param {number} payload.lat - Latitude
 * @param {number} payload.lon - Longitude
 */
export async function handleFetchGeorisques(payload) {
  const { lat, lon } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  // Vérifier le cache
  const cacheKey = `georisques_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.georisques_erial.ttl_days);
  if (cached.hit) {
    log.debug('Géorisques cache hit');
    return cached.data;
  }

  log.info(`Géorisques: analyse risques (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  // Lancer les deux appels en parallèle pour gagner du temps
  const [erialResult, icpeResult] = await Promise.all([
    fetchErial(lat, lon),
    fetchIcpe(lat, lon)
  ]);

  const risquesNaturels = parseRisquesNaturels(erialResult);
  const icpeProches = parseIcpe(icpeResult);
  const scoreGlobal = calculateGlobalScore(risquesNaturels, icpeProches.length);

  const result = {
    risques_naturels: risquesNaturels,
    icpe_proches: icpeProches,
    nb_risques: risquesNaturels.filter(r => r.niveau !== 'AUCUN').length,
    nb_icpe: icpeProches.length,
    score_global: scoreGlobal,
    erial_disponible: erialResult.success,
    icpe_disponible: icpeResult.success
  };

  await setCache(cacheKey, result);
  log.info(`Géorisques: ${result.nb_risques} risque(s) naturel(s), ${result.nb_icpe} ICPE`);

  return result;
}
