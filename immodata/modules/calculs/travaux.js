/**
 * ImmoData — Estimation Travaux + MaPrimeRénov'
 *
 * Estime le coût de rénovation selon le DPE actuel et la surface,
 * et indique l'éligibilité MaPrimeRénov' selon la zone climatique.
 */

(function () {
  'use strict';

  // Coût moyen au m² selon le type de rénovation
  const COUT_M2 = {
    leger: 200,    // Peinture, sols, petites réparations
    moyen: 500,    // Cuisine, salle de bain, isolation partielle
    lourd: 900,    // Rénovation complète, toiture, isolation totale
    tres_lourd: 1400 // Restructuration, mise aux normes, extension
  };

  // Estimation du niveau de travaux selon le DPE
  const DPE_TRAVAUX = {
    A: 'aucun',
    B: 'aucun',
    C: 'leger',
    D: 'moyen',
    E: 'moyen',
    F: 'lourd',
    G: 'tres_lourd'
  };

  // Plafonds MaPrimeRénov' simplifiés (barème 2024)
  const MAPRIMERENOV = {
    tres_modeste: { isolation: 75, chauffage: 10000, global: 35000 },
    modeste:      { isolation: 60, chauffage: 8000,  global: 25000 },
    intermediaire:{ isolation: 40, chauffage: 4000,  global: 15000 },
    superieur:    { isolation: 15, chauffage: 2000,  global: 7000 }
  };

  function estimerTravaux({ dpe, surface, annee_construction, type_bien }) {
    // Déterminer le niveau de travaux
    let niveau = DPE_TRAVAUX[dpe] || 'moyen';

    // Ajustement selon l'année de construction
    if (annee_construction && annee_construction < 1975) {
      if (niveau === 'leger') niveau = 'moyen';
      else if (niveau === 'moyen') niveau = 'lourd';
    }

    if (niveau === 'aucun') {
      return {
        niveau: 'aucun',
        cout_estime: 0,
        cout_m2: 0,
        maprimerenov_eligible: false,
        detail: 'Bien récent ou en bon état, pas de travaux nécessaires'
      };
    }

    const coutM2 = COUT_M2[niveau] || COUT_M2.moyen;
    const surfaceEstimee = surface || 70; // surface par défaut
    let coutTotal = Math.round(coutM2 * surfaceEstimee);

    // Majoration pour les maisons (plus de surface à traiter)
    if (type_bien === 'maison') {
      coutTotal = Math.round(coutTotal * 1.3);
    }

    // Fourchette : -20% / +30%
    const fourchette = {
      bas: Math.round(coutTotal * 0.8),
      haut: Math.round(coutTotal * 1.3)
    };

    // Éligibilité MaPrimeRénov' (simplifiée)
    const mprEligible = dpe && ['D', 'E', 'F', 'G'].includes(dpe);
    const mprAide = mprEligible ? MAPRIMERENOV.modeste : null;

    return {
      niveau,
      cout_estime: coutTotal,
      cout_m2: coutM2,
      fourchette,
      maprimerenov_eligible: mprEligible,
      maprimerenov_plafond: mprAide ? mprAide.global : 0,
      detail: `Rénovation ${niveau} estimée à ${coutM2}€/m²`
    };
  }

  self.__immodata = self.__immodata || {};
  self.__immodata.calculs = self.__immodata.calculs || {};
  self.__immodata.calculs.travaux = { estimerTravaux };
})();
