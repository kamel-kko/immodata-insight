/**
 * ImmoData — Module API DVF (Demandes de Valeurs Foncières)
 *
 * Interroge l'API DVF Etalab pour récupérer les transactions immobilières
 * récentes autour d'un point GPS. Ça permet de comparer le prix d'une annonce
 * avec le prix réel du marché dans le même quartier.
 *
 * Analogie : c'est comme consulter les prix de vente réels chez le notaire
 * pour savoir si un bien est vendu au bon prix par rapport aux voisins.
 *
 * API : https://api.dvf.gouv.fr/api/georecords/
 * Documentation : https://dvf.etalab.gouv.fr/
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon, sanitizeNumber } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:DVF');

/**
 * Calcule la médiane d'un tableau de nombres.
 * La médiane, c'est la valeur du milieu quand on trie les nombres.
 * Exemple : [3, 1, 7, 2, 5] → trié [1, 2, 3, 5, 7] → médiane = 3
 */
function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

/**
 * Convertit un type de bien ImmoData vers le format DVF.
 * L'API DVF utilise des noms comme "Appartement", "Maison", etc.
 */
function mapTypeBienDvf(typeBien) {
  const mapping = {
    appartement: 'Appartement',
    maison: 'Maison',
    terrain: 'Terrain',
    parking: 'Parking',
    autre: null
  };
  return mapping[typeBien] || null;
}

/**
 * Récupère et analyse les transactions DVF autour d'un point GPS.
 *
 * @param {Object} payload
 * @param {number} payload.lat - Latitude
 * @param {number} payload.lon - Longitude
 * @param {string} payload.type_bien - Type de bien (appartement, maison, etc.)
 * @param {number} payload.surface - Surface en m²
 * @param {number} [payload.prix_annonce] - Prix de l'annonce (pour calculer le delta)
 * @param {string} [payload.code_insee] - Code INSEE de la commune
 */
export async function handleFetchDvf(payload) {
  const { lat, lon, type_bien, surface, prix_annonce, code_insee } = payload;

  // Validation
  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const surfaceNum = sanitizeNumber(surface);
  if (!surfaceNum || surfaceNum <= 0) {
    return { success: false, error: 'INVALID_PAYLOAD', message: 'Surface invalide' };
  }

  // Clé de cache : on arrondit la surface par tranche de 20m² pour grouper
  // les requêtes similaires (ex: 45m² et 55m² → même tranche "40")
  const surfaceBucket = Math.round(surfaceNum / 20) * 20;
  const cacheKey = `dvf_${code_insee || `${lat.toFixed(3)}_${lon.toFixed(3)}`}_${type_bien}_${surfaceBucket}`;
  const cached = await checkCache(cacheKey, API_CONFIG.dvf.ttl_days);
  if (cached.hit) {
    log.debug('DVF cache hit');
    return cached.data;
  }

  // Construire l'URL DVF
  // L'API attend : lat, lon, dist (rayon en mètres)
  const config = API_CONFIG.dvf;
  const url = new URL(config.endpoint);

  // Calculer la date limite (24 mois en arrière)
  const dateLimit = new Date();
  dateLimit.setMonth(dateLimit.getMonth() - config.nb_mois_historique);
  const dateLimitStr = dateLimit.toISOString().split('T')[0];

  url.searchParams.set('lat', lat.toFixed(6));
  url.searchParams.set('lon', lon.toFixed(6));
  url.searchParams.set('dist', config.rayon_metres);

  log.info(`DVF: recherche autour de (${lat.toFixed(4)}, ${lon.toFixed(4)}), rayon ${config.rayon_metres}m`);

  let response;
  try {
    response = await fetchWithTimeout(url.toString(), {}, config.timeout_ms);
  } catch (err) {
    log.error('DVF: erreur réseau', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }

  if (!response.ok) {
    log.warn(`DVF: réponse ${response.status}`);
    return { success: false, error: 'API_ERROR', message: `DVF a répondu ${response.status}` };
  }

  const data = await response.json();

  // L'API retourne un tableau de "records" (transactions)
  // Chaque record a : date_mutation, nature_mutation, valeur_fonciere,
  // type_local, surface_reelle_bati, etc.
  const records = data.records || data.results || data || [];
  const allTransactions = Array.isArray(records) ? records : [];

  if (allTransactions.length === 0) {
    log.warn('DVF: aucune transaction trouvée dans le rayon');
    const emptyResult = {
      mediane_m2: null,
      nb_transactions: 0,
      tendance: 'indetermine',
      delta_pct: null,
      date_last_transaction: null,
      transactions_brutes: 0
    };
    await setCache(cacheKey, emptyResult);
    return emptyResult;
  }

  // Filtrer les transactions pertinentes :
  // 1. Nature mutation = "Vente"
  // 2. Type de bien correspondant (si disponible)
  // 3. Surface dans une fourchette de ±20% par rapport à l'annonce
  const typeDvf = mapTypeBienDvf(type_bien);
  const surfaceMin = surfaceNum * 0.8;
  const surfaceMax = surfaceNum * 1.2;

  const filtered = allTransactions.filter((tx) => {
    // Normaliser : l'API peut retourner les données à différents niveaux
    const t = tx.fields || tx;

    // Vente uniquement
    const nature = t.nature_mutation || '';
    if (!nature.toLowerCase().includes('vente')) return false;

    // Filtrer par type de bien si on le connaît
    if (typeDvf) {
      const typeLocal = t.type_local || '';
      if (typeLocal && !typeLocal.includes(typeDvf)) return false;
    }

    // Filtrer par surface (±20%)
    const surfaceTx = parseFloat(t.surface_reelle_bati || t.surface || 0);
    if (surfaceTx > 0 && (surfaceTx < surfaceMin || surfaceTx > surfaceMax)) return false;

    // Filtrer par date (24 derniers mois)
    const dateMut = t.date_mutation || '';
    if (dateMut && dateMut < dateLimitStr) return false;

    // Avoir un prix valide
    const valeur = parseFloat(t.valeur_fonciere || 0);
    if (valeur <= 0) return false;

    return true;
  });

  // Calculer les prix au m² de chaque transaction
  const prixM2List = [];
  const dates = [];

  for (const tx of filtered) {
    const t = tx.fields || tx;
    const valeur = parseFloat(t.valeur_fonciere);
    const surfaceTx = parseFloat(t.surface_reelle_bati || t.surface || 0);
    if (surfaceTx > 0 && valeur > 0) {
      prixM2List.push(valeur / surfaceTx);
      if (t.date_mutation) dates.push(t.date_mutation);
    }
  }

  const medianeM2 = prixM2List.length > 0 ? Math.round(median(prixM2List)) : null;

  // Calculer la tendance sur 12 mois :
  // Comparer la médiane des 12 premiers mois vs les 12 derniers mois
  let tendance = 'indetermine';
  if (prixM2List.length >= 4) {
    const dateMid = new Date();
    dateMid.setMonth(dateMid.getMonth() - 12);
    const dateMidStr = dateMid.toISOString().split('T')[0];

    const ancien = [];
    const recent = [];
    for (const tx of filtered) {
      const t = tx.fields || tx;
      const dateMut = t.date_mutation || '';
      const valeur = parseFloat(t.valeur_fonciere);
      const surfaceTx = parseFloat(t.surface_reelle_bati || t.surface || 0);
      if (surfaceTx > 0 && valeur > 0) {
        const pm2 = valeur / surfaceTx;
        if (dateMut < dateMidStr) ancien.push(pm2);
        else recent.push(pm2);
      }
    }

    if (ancien.length >= 2 && recent.length >= 2) {
      const medAncien = median(ancien);
      const medRecent = median(recent);
      const evolution = ((medRecent - medAncien) / medAncien) * 100;
      if (evolution > 3) tendance = 'hausse';
      else if (evolution < -3) tendance = 'baisse';
      else tendance = 'stable';
    }
  }

  // Calculer le delta entre le prix de l'annonce et la médiane du marché
  let deltaPct = null;
  if (medianeM2 && prix_annonce && surfaceNum) {
    const prixM2Annonce = prix_annonce / surfaceNum;
    deltaPct = Math.round(((prixM2Annonce - medianeM2) / medianeM2) * 100);
  }

  // Dernière date de transaction
  dates.sort();
  const dateLastTransaction = dates.length > 0 ? dates[dates.length - 1] : null;

  const result = {
    mediane_m2: medianeM2,
    nb_transactions: prixM2List.length,
    transactions_brutes: allTransactions.length,
    tendance,
    delta_pct: deltaPct,
    date_last_transaction: dateLastTransaction
  };

  await setCache(cacheKey, result);
  log.info(`DVF: ${prixM2List.length} transactions filtrées, médiane ${medianeM2}€/m², tendance ${tendance}`);

  return result;
}
