/**
 * ImmoData — Rentabilité Locative (4 stratégies)
 *
 * Compare 4 stratégies d'investissement :
 * - Location nue (classique)
 * - LMNP (meublé, abattement 50%)
 * - Colocation (meublé, chambres multiples)
 * - Airbnb / courte durée (saisonnier)
 *
 * Retourne rendement brut, net, et cashflow mensuel pour chaque.
 */

(function () {
  'use strict';

  // Hypothèses par défaut
  const DEFAULTS = {
    taux_vacance_nu: 0.05,        // 5% de vacance locative (nu)
    taux_vacance_meuble: 0.08,    // 8% (meublé, plus de rotation)
    taux_vacance_airbnb: 0.25,    // 25% (saisonnier)
    charges_copro_m2: 25,         // €/m²/an moyen
    taxe_fonciere_pct: 0.01,     // ~1% du prix
    assurance_pno_an: 150,        // Assurance propriétaire non-occupant
    gestion_pct: 0.07,           // 7% frais de gestion agence
    abattement_lmnp: 0.50,       // 50% micro-BIC
    abattement_nu: 0.30,         // 30% micro-foncier
    majoration_meuble: 1.15,     // +15% loyer meublé vs nu
    majoration_coloc: 1.40,      // +40% en colocation
    majoration_airbnb: 2.00      // x2 en courte durée (avant vacance)
  };

  function calculerRentabilite({
    prix_achat,
    loyer_median,        // loyer nu mensuel estimé (API loyers ou estimation)
    surface,
    frais_notaire,       // déjà calculé par notaire.js
    cout_travaux,        // estimé par travaux.js (0 si pas de travaux)
    taxe_fonciere,       // annuelle, ou null (on estime)
    charges_copro        // mensuelles, ou null (on estime)
  }) {
    if (!prix_achat || prix_achat <= 0) {
      return { success: false, error: 'Prix d\'achat manquant' };
    }

    const loyerBase = loyer_median || Math.round(surface * 12); // fallback 12€/m²
    const notaire = frais_notaire || Math.round(prix_achat * 0.08);
    const travaux = cout_travaux || 0;
    const investissement = prix_achat + notaire + travaux;

    const taxeFonciere = taxe_fonciere || Math.round(prix_achat * DEFAULTS.taxe_fonciere_pct);
    const chargesCoproAn = charges_copro
      ? charges_copro * 12
      : Math.round((surface || 70) * DEFAULTS.charges_copro_m2);

    const chargesAnnuelles = taxeFonciere + chargesCoproAn + DEFAULTS.assurance_pno_an;

    function calculerStrategie(nom, loyerMensuel, tauxVacance, abattement) {
      const loyerAnnuelBrut = loyerMensuel * 12;
      const loyerEffectif = loyerAnnuelBrut * (1 - tauxVacance);
      const fraisGestion = loyerEffectif * DEFAULTS.gestion_pct;

      const rendementBrut = (loyerAnnuelBrut / investissement) * 100;
      const revenuNet = loyerEffectif - chargesAnnuelles - fraisGestion;
      const rendementNet = (revenuNet / investissement) * 100;

      const impotEstime = revenuNet > 0 ? revenuNet * (1 - abattement) * 0.30 : 0;
      const cashflowAnnuel = revenuNet - impotEstime;

      return {
        nom,
        loyer_mensuel: Math.round(loyerMensuel),
        rendement_brut: Math.round(rendementBrut * 100) / 100,
        rendement_net: Math.round(rendementNet * 100) / 100,
        cashflow_mensuel: Math.round(cashflowAnnuel / 12),
        revenu_net_annuel: Math.round(revenuNet),
        charges_annuelles: Math.round(chargesAnnuelles)
      };
    }

    const strategies = [
      calculerStrategie(
        'Location nue',
        loyerBase,
        DEFAULTS.taux_vacance_nu,
        DEFAULTS.abattement_nu
      ),
      calculerStrategie(
        'LMNP meublé',
        Math.round(loyerBase * DEFAULTS.majoration_meuble),
        DEFAULTS.taux_vacance_meuble,
        DEFAULTS.abattement_lmnp
      ),
      calculerStrategie(
        'Colocation',
        Math.round(loyerBase * DEFAULTS.majoration_coloc),
        DEFAULTS.taux_vacance_meuble,
        DEFAULTS.abattement_lmnp
      ),
      calculerStrategie(
        'Airbnb',
        Math.round(loyerBase * DEFAULTS.majoration_airbnb),
        DEFAULTS.taux_vacance_airbnb,
        DEFAULTS.abattement_lmnp
      )
    ];

    // Trier par rendement net décroissant
    strategies.sort((a, b) => b.rendement_net - a.rendement_net);

    return {
      investissement_total: investissement,
      strategies,
      meilleure: strategies[0].nom
    };
  }

  self.__immodata = self.__immodata || {};
  self.__immodata.calculs = self.__immodata.calculs || {};
  self.__immodata.calculs.rentabilite = { calculerRentabilite };
})();
