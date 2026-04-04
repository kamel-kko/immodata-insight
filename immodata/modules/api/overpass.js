/**
 * ImmoData — Module API Overpass (OpenStreetMap)
 *
 * Interroge l'API Overpass pour trouver les équipements et services
 * autour d'un point GPS : transports, commerces, santé, culture, sports.
 * Une seule requête Overpass QL combinée pour tout récupérer d'un coup.
 *
 * La distance à pied est estimée avec la formule de Haversine × 1.3
 * (facteur de détour urbain) divisée par 5 km/h.
 */

import { createLogger } from '../../utils/logger.js';
import { checkCache, setCache } from '../../utils/cache.js';
import { validateLatLon } from '../../utils/security.js';
import { fetchWithTimeout, API_CONFIG } from '../../background.js';

const log = createLogger('API:OVERPASS');

/**
 * Calcule la distance en mètres entre deux points GPS (formule de Haversine).
 */
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Convertit une distance en mètres en minutes de marche.
 * Facteur 1.3 = détour urbain, vitesse 5 km/h.
 */
function distanceToMinutes(meters) {
  return Math.round((meters * 1.3) / (5000 / 60));
}

export async function handleFetchOverpass(payload) {
  const { lat, lon } = payload;

  if (!validateLatLon(lat, lon)) {
    return { success: false, error: 'INVALID_COORDS', message: 'Coordonnées GPS invalides' };
  }

  const cacheKey = `overpass_${lat.toFixed(3)}_${lon.toFixed(3)}`;
  const cached = await checkCache(cacheKey, API_CONFIG.overpass.ttl_days);
  if (cached.hit) return cached.data;

  const rayon = API_CONFIG.overpass.rayon_metres;
  // Requête Overpass QL combinée — tout en une seule requête
  const query = `[out:json][timeout:10];(
    node[public_transport=stop_position](around:${rayon},${lat},${lon});
    node[railway=station](around:${rayon},${lat},${lon});
    node[shop=supermarket](around:${rayon},${lat},${lon});
    node[shop=bakery](around:${rayon},${lat},${lon});
    node[amenity=hospital](around:${rayon},${lat},${lon});
    node[amenity=pharmacy](around:${rayon},${lat},${lon});
    node[amenity=cinema](around:${rayon},${lat},${lon});
    node[amenity=library](around:${rayon},${lat},${lon});
    node[leisure=sports_centre](around:${rayon},${lat},${lon});
    node[leisure=swimming_pool](around:${rayon},${lat},${lon});
    node[amenity=post_office](around:${rayon},${lat},${lon});
    node[amenity=bank](around:${rayon},${lat},${lon});
  );out body;`;

  log.info(`Overpass : requête rayon ${rayon}m autour de (${lat.toFixed(4)}, ${lon.toFixed(4)})`);

  let elements = [];
  try {
    const response = await fetchWithTimeout(
      API_CONFIG.overpass.endpoint,
      { method: 'POST', body: `data=${encodeURIComponent(query)}`, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
      API_CONFIG.overpass.timeout_ms
    );
    if (!response.ok) {
      log.warn(`Overpass : réponse ${response.status}`);
      return { success: false, error: 'API_ERROR', message: `Overpass a répondu ${response.status}` };
    }
    const data = await response.json();
    elements = data.elements || [];
  } catch (err) {
    log.error('Overpass erreur :', err.message);
    return { success: false, error: 'NETWORK_ERROR', message: err.message };
  }

  // Classer les éléments par catégorie
  const categories = {
    transports: { tags: ['public_transport', 'railway'], items: [] },
    commerces: { tags: ['shop'], items: [] },
    sante: { tags: ['hospital', 'pharmacy'], items: [] },
    culture: { tags: ['cinema', 'library'], items: [] },
    sports: { tags: ['sports_centre', 'swimming_pool'], items: [] },
    services: { tags: ['post_office', 'bank'], items: [] }
  };

  for (const el of elements) {
    if (!el.lat || !el.lon) continue;
    const dist = haversine(lat, lon, el.lat, el.lon);
    const minutes = distanceToMinutes(dist);
    const tags = el.tags || {};
    const name = tags.name || tags.operator || '';
    const item = { name, distance_m: Math.round(dist), minutes_a_pied: minutes };

    if (tags.public_transport || tags.railway) categories.transports.items.push(item);
    else if (tags.shop) categories.commerces.items.push(item);
    else if (tags.amenity === 'hospital' || tags.amenity === 'pharmacy') categories.sante.items.push(item);
    else if (tags.amenity === 'cinema' || tags.amenity === 'library') categories.culture.items.push(item);
    else if (tags.leisure) categories.sports.items.push(item);
    else if (tags.amenity === 'post_office' || tags.amenity === 'bank') categories.services.items.push(item);
  }

  // Trier chaque catégorie par distance et garder le plus proche
  const resume = {};
  for (const [cat, data] of Object.entries(categories)) {
    data.items.sort((a, b) => a.distance_m - b.distance_m);
    resume[cat] = {
      nb: data.items.length,
      plus_proche: data.items[0] || null,
      items: data.items.slice(0, 5)
    };
  }

  const result = { categories: resume, nb_total: elements.length };
  await setCache(cacheKey, result);
  log.info(`Overpass : ${elements.length} élément(s) trouvé(s)`);
  return result;
}
