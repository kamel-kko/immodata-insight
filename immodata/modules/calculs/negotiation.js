/**
 * ImmoData — Score de négociation (0-100)
 *
 * Ce module calcule un score qui indique le potentiel de négociation
 * sur le prix d'un bien immobilier. Plus le score est élevé, plus
 * il y a de chances que le vendeur accepte une offre en dessous du prix affiché.
 *
 * Le score est basé sur 5 facteurs :
 * 1. Delta DVF (40 pts) : le prix est-il au-dessus du marché ?
 * 2. Durée en ligne (20 pts) : depuis combien de temps l'annonce est publiée ?
 * 3. Urgence texte (15 pts) : y a-t-il des mots comme "urgent", "mutation" ?
 * 4. Nombre de photos (10 pts) : peu de photos = vendeur moins motivé ?
 * 5. DPE mauvais (15 pts) : un DPE F ou G rend le bien moins attractif
 *
 * Analogie : c'est comme un détecteur de "bonnes affaires potentielles".
 * Plus le score est haut, plus tu as de marge pour négocier.
 */

(function () {
  'use strict';

  // Messages associés à chaque tranche de score
  const SCORE_LABELS = [
    { min: 0,  max: 25,  label: 'Prix dans la norme marché',         couleur: 'yellow' },
    { min: 26, max: 50,  label: 'Légère marge de négociation',       couleur: 'orange' },
    { min: 51, max: 75,  label: '+8-12% vs marché — négociable',     couleur: 'red' },
    { min: 76, max: 100, label: 'Surévalué — marge estimée 12-20%',  couleur: 'red-double' }
  ];

  /**
   * Calcule le score de négociation.
   *
   * @param {Object} params
   * @param {number|null} params.delta_dvf - Écart en % par rapport à la médiane DVF
   *   (positif = plus cher que le marché, négatif = moins cher)
   * @param {number|null} params.jours_en_ligne - Nombre de jours depuis la publication
   * @param {boolean} params.urgence_texte - Mots-clés "urgent/mutation" détectés
   * @param {number|null} params.nb_photos - Nombre de photos dans l'annonce
   * @param {string|null} params.dpe - Lettre DPE (A-G)
   * @returns {{ score, label, couleur, detail }}
   */
  function calculerScoreNegociation({ delta_dvf, jours_en_ligne, urgence_texte, nb_photos, dpe }) {
    let score = 0;
    const detail = {};

    // --- Facteur 1 : Delta DVF (40 pts max) ---
    // Si le prix est 20% au-dessus du marché → 40 pts
    // Si le prix est pile au marché → 0 pts
    // Si le prix est en dessous → 0 pts (pas de négociation à faire)
    if (delta_dvf !== null && delta_dvf !== undefined) {
      if (delta_dvf > 0) {
        // Proportionnel : +20% = 40pts, +10% = 20pts, +5% = 10pts
        detail.delta_dvf = Math.min(Math.round(delta_dvf * 2), 40);
      } else {
        detail.delta_dvf = 0;
      }
    } else {
      detail.delta_dvf = 0;
    }
    score += detail.delta_dvf;

    // --- Facteur 2 : Durée en ligne (20 pts max) ---
    // Plus une annonce reste longtemps, plus le vendeur est pressé
    // 90+ jours = 20 pts, 60 jours = 13 pts, 30 jours = 7 pts
    if (jours_en_ligne !== null && jours_en_ligne !== undefined && jours_en_ligne > 0) {
      detail.duree_ligne = Math.min(Math.round((jours_en_ligne / 90) * 20), 20);
    } else {
      detail.duree_ligne = 0;
    }
    score += detail.duree_ligne;

    // --- Facteur 3 : Urgence dans le texte (15 pts max) ---
    // "urgent", "mutation", "cause départ" = le vendeur veut vendre vite
    detail.urgence_texte = urgence_texte ? 15 : 0;
    score += detail.urgence_texte;

    // --- Facteur 4 : Peu de photos (10 pts max) ---
    // Moins de 5 photos = annonce peu soignée = vendeur moins engagé
    if (nb_photos !== null && nb_photos !== undefined) {
      if (nb_photos < 3) detail.nb_photos = 10;
      else if (nb_photos < 5) detail.nb_photos = 5;
      else detail.nb_photos = 0;
    } else {
      detail.nb_photos = 0;
    }
    score += detail.nb_photos;

    // --- Facteur 5 : DPE mauvais (15 pts max) ---
    // DPE F ou G = passoire thermique = coûts de rénovation
    // = argument de négociation fort
    if (dpe === 'F') detail.dpe_mauvais = 10;
    else if (dpe === 'G') detail.dpe_mauvais = 15;
    else detail.dpe_mauvais = 0;
    score += detail.dpe_mauvais;

    // Borner entre 0 et 100
    score = Math.max(0, Math.min(score, 100));

    // Trouver le label et la couleur
    const tranche = SCORE_LABELS.find(t => score >= t.min && score <= t.max) || SCORE_LABELS[0];

    return {
      score,
      label: tranche.label,
      couleur: tranche.couleur,
      detail
    };
  }

  // Exposer via globalThis
  if (typeof globalThis.__immodata === 'undefined') {
    globalThis.__immodata = {};
  }
  globalThis.__immodata.calculs = globalThis.__immodata.calculs || {};
  globalThis.__immodata.calculs.negotiation = { calculerScoreNegociation, SCORE_LABELS };

})();

export function calculerScoreNegociation(params) {
  return globalThis.__immodata.calculs.negotiation.calculerScoreNegociation(params);
}
