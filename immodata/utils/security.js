/**
 * ImmoData — Module de sécurité
 * Sanitisation des inputs et validation des données
 */

// Liste blanche des domaines autorisés pour les URLs
const URL_ALLOWLIST = [
  'api-adresse.data.gouv.fr',
  'api.dvf.gouv.fr',
  'www.georisques.gouv.fr',
  'data.education.gouv.fr',
  'overpass-api.de',
  'data.ademe.fr',
  'www.data.gouv.fr',
  'opendata.reseaux-energies.fr',
  'data.culture.gouv.fr',
  'api.insee.fr',
  'api.openrouteservice.org',
  'www.anil.org',
  'www.pretto.fr',
  'www.meilleurtaux.com',
  'www.moveezy.fr',
  'www.habitissimo.fr',
  'www.luko.eu',
  'www.diagamter.com'
];

// Bornes géographiques de la France métropolitaine (avec marge)
const FRANCE_BOUNDS = {
  latMin: 41.3,   // Corse sud
  latMax: 51.1,   // Nord
  lonMin: -5.2,   // Bretagne ouest
  lonMax: 9.6     // Alsace est
};

/**
 * Supprime tout HTML d'une chaîne et limite sa longueur.
 * Imagine un filtre qui ne laisse passer que le texte brut,
 * comme un tamis qui retient les morceaux dangereux.
 */
function sanitizeText(input) {
  if (typeof input !== 'string') return '';
  // Supprimer toutes les balises HTML
  const cleaned = input.replace(/<[^>]*>/g, '');
  // Limiter à 500 caractères
  return cleaned.slice(0, 500).trim();
}

/**
 * Vérifie qu'une valeur est bien un nombre valide et fini.
 * Retourne le nombre ou null si ce n'est pas exploitable.
 */
function sanitizeNumber(input) {
  const num = Number(input);
  if (Number.isFinite(num)) return num;
  return null;
}

/**
 * Vérifie qu'une URL appartient à la liste blanche des domaines autorisés.
 * C'est comme un videur à l'entrée : seuls les domaines connus passent.
 *
 * @param {string} url - L'URL à vérifier
 * @param {string[]} [allowlist] - Liste de domaines autorisés (défaut: URL_ALLOWLIST)
 * @returns {string|null} L'URL validée ou null si refusée
 */
function sanitizeUrl(url, allowlist) {
  if (typeof url !== 'string') return null;
  const domains = allowlist || URL_ALLOWLIST;
  try {
    const parsed = new URL(url);
    // N'accepter que https
    if (parsed.protocol !== 'https:') return null;
    // Vérifier que le domaine est dans la liste blanche
    if (!domains.includes(parsed.hostname)) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

/**
 * Vérifie que des coordonnées GPS sont bien en France métropolitaine.
 * La France va environ de 41°N (Corse) à 51°N (Nord),
 * et de -5°E (Bretagne) à 9.6°E (Alsace).
 */
function validateLatLon(lat, lon) {
  const latNum = sanitizeNumber(lat);
  const lonNum = sanitizeNumber(lon);
  if (latNum === null || lonNum === null) return false;
  return (
    latNum >= FRANCE_BOUNDS.latMin &&
    latNum <= FRANCE_BOUNDS.latMax &&
    lonNum >= FRANCE_BOUNDS.lonMin &&
    lonNum <= FRANCE_BOUNDS.lonMax
  );
}

/**
 * Vérifie qu'un code postal est un code français valide (5 chiffres).
 * Exemples valides : "75001", "31000", "97400" (DOM).
 */
function validatePostalCode(cp) {
  if (typeof cp !== 'string') return false;
  return /^\d{5}$/.test(cp.trim());
}

// Export ES Module pour background.js
// (Ce fichier n'est PAS chargé dans les content scripts —
//  le content_bootstrap.js fournit les mêmes fonctions en IIFE)
export {
  sanitizeText,
  sanitizeNumber,
  sanitizeUrl,
  validateLatLon,
  validatePostalCode,
  URL_ALLOWLIST,
  FRANCE_BOUNDS
};
