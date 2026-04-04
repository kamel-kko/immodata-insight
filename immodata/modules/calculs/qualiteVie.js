/**
 * ImmoData — Score Qualité de Vie (SQV)
 *
 * Score composite 0-100 basé sur 6 facteurs :
 * - Proximité commerces/services (20 pts)
 * - Transports (20 pts)
 * - Éducation (15 pts)
 * - Environnement / risques (15 pts)
 * - Bruit (15 pts)
 * - Patrimoine / cadre de vie (15 pts)
 */

(function () {
  'use strict';

  const LABELS = [
    { min: 80, max: 100, label: 'Cadre de vie excellent',  couleur: 'green' },
    { min: 60, max: 79,  label: 'Cadre de vie agréable',   couleur: 'yellow' },
    { min: 40, max: 59,  label: 'Cadre de vie correct',    couleur: 'orange' },
    { min: 0,  max: 39,  label: 'Cadre de vie à améliorer', couleur: 'red' }
  ];

  function calculerQualiteVie({
    nb_commerces,        // Overpass : nombre de commerces proches
    nb_transports,       // Overpass : arrêts de transport
    nb_ecoles,           // API Éducation
    risques_niveau,      // Géorisques : 'CRITIQUE', 'MODERE', 'FAIBLE', 'AUCUN'
    zone_bruit,          // true/false (PEB aéroport)
    nb_monuments,        // Mérimée
    ligne_haute_tension  // RTE : true/false
  }) {
    let score = 0;
    const detail = {};

    // Commerces & services (20 pts)
    if (nb_commerces > 30) detail.commerces = 20;
    else if (nb_commerces > 15) detail.commerces = 14;
    else if (nb_commerces > 5) detail.commerces = 8;
    else detail.commerces = 3;
    score += detail.commerces;

    // Transports (20 pts)
    if (nb_transports > 10) detail.transports = 20;
    else if (nb_transports > 5) detail.transports = 14;
    else if (nb_transports > 2) detail.transports = 8;
    else detail.transports = 2;
    score += detail.transports;

    // Éducation (15 pts)
    if (nb_ecoles > 5) detail.education = 15;
    else if (nb_ecoles > 2) detail.education = 10;
    else if (nb_ecoles > 0) detail.education = 5;
    else detail.education = 1;
    score += detail.education;

    // Environnement / risques (15 pts)
    if (risques_niveau === 'AUCUN') detail.risques = 15;
    else if (risques_niveau === 'FAIBLE') detail.risques = 10;
    else if (risques_niveau === 'MODERE') detail.risques = 5;
    else detail.risques = 1; // CRITIQUE
    score += detail.risques;

    // Bruit (15 pts)
    detail.bruit = zone_bruit ? 3 : 15;
    if (ligne_haute_tension) detail.bruit = Math.max(1, detail.bruit - 5);
    score += detail.bruit;

    // Patrimoine / cadre (15 pts)
    if (nb_monuments > 5) detail.patrimoine = 15;
    else if (nb_monuments > 2) detail.patrimoine = 10;
    else if (nb_monuments > 0) detail.patrimoine = 6;
    else detail.patrimoine = 3;
    score += detail.patrimoine;

    score = Math.max(0, Math.min(score, 100));
    const tranche = LABELS.find(t => score >= t.min && score <= t.max) || LABELS[3];

    return {
      score,
      label: tranche.label,
      couleur: tranche.couleur,
      detail
    };
  }

  self.__immodata = self.__immodata || {};
  self.__immodata.calculs = self.__immodata.calculs || {};
  self.__immodata.calculs.qualiteVie = { calculerQualiteVie };
})();
