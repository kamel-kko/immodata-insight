/**
 * ImmoData — Score Potentiel de Plus-Value (SPV)
 *
 * Score 0-100 sur 5 ans, basé sur 5 facteurs :
 * - Tendance DVF 5 ans (35 pts)
 * - Projets urbains (25 pts) — simplifié en l'absence de données IGN
 * - Pression foncière (20 pts)
 * - Tissu économique (10 pts)
 * - Qualité de vie (10 pts)
 */

(function () {
  'use strict';

  const LABELS = [
    { min: 75, max: 100, label: 'Zone en forte mutation +',  couleur: 'green' },
    { min: 50, max: 74,  label: 'Marché porteur stable',     couleur: 'yellow' },
    { min: 25, max: 49,  label: 'Zone à surveiller',         couleur: 'orange' },
    { min: 0,  max: 24,  label: 'Signal de déclin détecté',  couleur: 'red' }
  ];

  function calculerScorePlusValue({
    tendance_dvf,       // 'hausse', 'stable', 'baisse'
    nb_transactions,    // nombre de transactions DVF
    nb_etablissements,  // SIRENE
    score_qualite_vie,  // 0-100
    projets_urbains     // boolean
  }) {
    let score = 0;
    const detail = {};

    // Tendance DVF (35 pts)
    if (tendance_dvf === 'hausse') detail.tendance = 35;
    else if (tendance_dvf === 'stable') detail.tendance = 18;
    else if (tendance_dvf === 'baisse') detail.tendance = 5;
    else detail.tendance = 15; // indéterminé
    score += detail.tendance;

    // Projets urbains (25 pts)
    detail.projets = projets_urbains ? 25 : 5;
    score += detail.projets;

    // Pression foncière (20 pts)
    if (nb_transactions > 50) detail.pression = 20;
    else if (nb_transactions > 20) detail.pression = 12;
    else if (nb_transactions > 5) detail.pression = 6;
    else detail.pression = 2;
    score += detail.pression;

    // Tissu économique (10 pts)
    if (nb_etablissements > 500) detail.economie = 10;
    else if (nb_etablissements > 100) detail.economie = 6;
    else detail.economie = 2;
    score += detail.economie;

    // Qualité de vie (10 pts)
    detail.qualite_vie = score_qualite_vie ? Math.round(score_qualite_vie / 10) : 5;
    score += detail.qualite_vie;

    score = Math.max(0, Math.min(score, 100));
    const tranche = LABELS.find(t => score >= t.min && score <= t.max) || LABELS[3];

    return { score, label: tranche.label, couleur: tranche.couleur, detail };
  }

  self.__immodata = self.__immodata || {};
  self.__immodata.calculs = self.__immodata.calculs || {};
  self.__immodata.calculs.plusValue = { calculerScorePlusValue };
})();
