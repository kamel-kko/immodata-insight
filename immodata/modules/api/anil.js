/**
 * ImmoData — Module API ANIL (Zonage Pinel/LMNP)
 *
 * Détermine la zone fiscale d'une commune (A bis, A, B1, B2, C)
 * pour savoir si le bien est éligible aux dispositifs Pinel ou Denormandie.
 * Basé sur le code INSEE.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';

const log = createLogger('API:ANIL');

// Zonage simplifié des grandes villes (les principales)
// En production, on utiliserait l'API ANIL complète
const ZONAGE_CONNU = {
  '75056': 'A_bis', // Paris
  '13055': 'A',     // Marseille
  '69123': 'A',     // Lyon
  '31555': 'B1',    // Toulouse
  '06088': 'A',     // Nice
  '44109': 'B1',    // Nantes
  '34172': 'A',     // Montpellier
  '67482': 'B1',    // Strasbourg
  '33063': 'B1',    // Bordeaux
  '59350': 'B1',    // Lille
  '35238': 'B1',    // Rennes
  '64445': 'B1',    // Pau
  '21231': 'B1',    // Dijon
  '76540': 'B1',    // Rouen
  '42218': 'B1',    // Saint-Étienne
};

const PINEL_ELIGIBLE = ['A_bis', 'A', 'B1'];

export async function handleFetchAnil(payload) {
  const { code_insee } = payload;

  if (!code_insee) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Code INSEE manquant' };
  }

  const cacheKey = `anil_${code_insee}`;
  const cached = await checkCache(cacheKey, 30);
  if (cached.hit) return cached.data;

  log.info(`ANIL : zonage pour INSEE ${code_insee}`);

  // Vérifier dans le zonage connu
  const zone = ZONAGE_CONNU[code_insee] || 'C'; // Par défaut zone C

  const result = {
    zone,
    pinel_eligible: PINEL_ELIGIBLE.includes(zone),
    denormandie_eligible: !PINEL_ELIGIBLE.includes(zone), // Denormandie = zones B2/C
    lmnp_eligible: true // LMNP est toujours possible
  };

  const { setCache: sc } = await import('../../utils/cache.js');
  await sc(cacheKey, result);
  log.info(`ANIL : zone ${zone}, Pinel ${result.pinel_eligible ? 'oui' : 'non'}`);
  return result;
}
