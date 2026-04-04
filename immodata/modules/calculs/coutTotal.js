/**
 * ImmoData — Coût Total de Possession (CTP)
 *
 * Calcule combien un bien coûte RÉELLEMENT chaque mois, au-delà de la
 * simple mensualité de crédit. On additionne tous les postes de dépense :
 * crédit, taxe foncière, charges de copro, énergie, provision travaux.
 *
 * C'est la réponse à la question : "Si j'achète ce bien, combien
 * ça me coûte vraiment par mois, tout compris ?"
 *
 * On compare aussi avec un loyer équivalent pour savoir au bout de
 * combien d'années l'achat devient plus rentable que la location.
 */

(function () {
  'use strict';

  // Consommation énergétique moyenne par lettre DPE (en kWh/m²/an)
  // Source : barème officiel DPE
  const DPE_KWH = {
    A: 50,    // < 70 kWh
    B: 110,   // 70-110
    C: 180,   // 110-180
    D: 250,   // 180-250
    E: 330,   // 250-330
    F: 420,   // 330-420
    G: 500    // > 420
  };

  const TARIF_KWH = 0.2516; // Tarif EDF réglementé (€/kWh, 2024-2025)

  /**
   * Calcule la mensualité d'un crédit immobilier (formule d'amortissement).
   *
   * C'est la formule classique de crédit :
   * M = C × (t / 12) / (1 - (1 + t/12)^(-n×12))
   * où C = capital emprunté, t = taux annuel, n = durée en années
   *
   * @param {number} capital - Montant emprunté (prix - apport)
   * @param {number} tauxAnnuel - Taux d'intérêt annuel (ex: 0.035 pour 3,5%)
   * @param {number} dureeAnnees - Durée du prêt en années
   * @returns {number} Mensualité en euros
   */
  function calcMensualiteCredit(capital, tauxAnnuel, dureeAnnees) {
    if (capital <= 0) return 0;
    if (tauxAnnuel <= 0) return capital / (dureeAnnees * 12);
    const tauxMensuel = tauxAnnuel / 12;
    const nbMois = dureeAnnees * 12;
    return capital * tauxMensuel / (1 - Math.pow(1 + tauxMensuel, -nbMois));
  }

  /**
   * Calcule le Coût Total de Possession mensuel.
   *
   * @param {Object} params
   * @param {number} params.prix - Prix du bien
   * @param {number} params.surface - Surface en m²
   * @param {string} params.type_bien - 'appartement', 'maison', etc.
   * @param {string|null} params.dpe - Lettre DPE (A-G)
   * @param {number|null} params.annee_constr - Année de construction
   * @param {number|null} params.taxe_fonciere - Montant annuel si connu
   * @param {number} [params.apport_pct=20] - % d'apport (ex: 20 = 20%)
   * @param {number} [params.duree_credit=20] - Durée du crédit en années
   * @param {number} [params.taux_credit=0.035] - Taux annuel (ex: 0.035 = 3,5%)
   * @param {number|null} [params.loyer_equivalent] - Loyer marché pour comparaison
   * @returns {{ mensualite_credit, total_mensuel, detail_postes, loyer_equivalent, rentabilite_annees }}
   */
  function calculerCoutTotal({
    prix,
    surface,
    type_bien,
    dpe,
    annee_constr,
    taxe_fonciere,
    apport_pct = 20,
    duree_credit = 20,
    taux_credit = 0.035,
    loyer_equivalent = null
  }) {
    if (!prix || prix <= 0 || !surface || surface <= 0) {
      return {
        mensualite_credit: 0,
        total_mensuel: 0,
        detail_postes: {},
        loyer_equivalent: null,
        rentabilite_annees: null
      };
    }

    const anneeActuelle = new Date().getFullYear();

    // 1. Mensualité de crédit
    const apport = prix * (apport_pct / 100);
    const capitalEmprunte = prix - apport;
    const mensualiteCredit = Math.round(calcMensualiteCredit(capitalEmprunte, taux_credit, duree_credit));

    // 2. Taxe foncière mensuelle
    // Si connue (extraite de l'annonce), on l'utilise
    // Sinon, estimation à 1,2% de la valeur du bien par an
    let taxeFonciereMensuelle;
    if (taxe_fonciere && taxe_fonciere > 0) {
      taxeFonciereMensuelle = Math.round(taxe_fonciere / 12);
    } else {
      taxeFonciereMensuelle = Math.round((prix * 0.012) / 12);
    }

    // 3. Charges de copropriété (uniquement pour les appartements)
    // Estimation : 3€/m²/mois si avant 1980, 1,5€/m²/mois si récent
    let chargesCopro = 0;
    if (type_bien === 'appartement') {
      const ancien = annee_constr && annee_constr < 1980;
      chargesCopro = Math.round(surface * (ancien ? 3 : 1.5));
    }

    // 4. Coûts énergétiques mensuels
    // DPE → kWh/m²/an × surface × tarif EDF ÷ 12 mois
    const kwhM2 = (dpe && DPE_KWH[dpe]) ? DPE_KWH[dpe] : DPE_KWH.D; // D par défaut
    const coutsEnergie = Math.round((kwhM2 * surface * TARIF_KWH) / 12);

    // 5. Provision travaux mensuelle
    // Si DPE mauvais (D, E, F, G) OU bien ancien (> 40 ans) : 15€/m²/an
    // Sinon : 5€/m²/an
    const ageBien = annee_constr ? (anneeActuelle - annee_constr) : 30;
    const dpeMauvais = dpe && ['D', 'E', 'F', 'G'].includes(dpe);
    const tauxTravaux = (dpeMauvais || ageBien > 40) ? 15 : 5;
    const provisionTravaux = Math.round((surface * tauxTravaux) / 12);

    // Total mensuel
    const totalMensuel = mensualiteCredit + taxeFonciereMensuelle + chargesCopro + coutsEnergie + provisionTravaux;

    // Comparatif achat vs location
    // Si on a un loyer équivalent, on calcule le "seuil de rentabilité" :
    // au bout de combien d'années l'achat revient moins cher que la location
    let rentabiliteAnnees = null;
    if (loyer_equivalent && loyer_equivalent > 0 && totalMensuel > loyer_equivalent) {
      // Coût supplémentaire mensuel de l'achat vs location
      const deltaMensuel = totalMensuel - loyer_equivalent;
      // Valeur récupérée : on rembourse du capital chaque mois
      // Approximation : le capital remboursé dans le crédit est la mensualité - les intérêts
      // En début de crédit, les intérêts sont élevés, donc le capital remboursé est faible
      // On utilise une approximation simplifiée
      const interetsMensuels = capitalEmprunte * (taux_credit / 12);
      const capitalRembMensuel = mensualiteCredit - interetsMensuels;

      if (capitalRembMensuel > deltaMensuel) {
        // L'achat est rentable dès le premier mois (rare)
        rentabiliteAnnees = 0;
      } else {
        // Nombre d'années avant que le patrimoine constitué compense le surcoût
        // Formule simplifiée : apport + années × capitalRemb × 12 > années × delta × 12
        rentabiliteAnnees = Math.round(apport / ((capitalRembMensuel - deltaMensuel) * -12));
        if (rentabiliteAnnees < 0 || rentabiliteAnnees > 50) rentabiliteAnnees = null;
      }
    } else if (loyer_equivalent && loyer_equivalent > 0 && totalMensuel <= loyer_equivalent) {
      rentabiliteAnnees = 0; // L'achat est moins cher que le loyer dès le départ
    }

    return {
      mensualite_credit: mensualiteCredit,
      total_mensuel: totalMensuel,
      loyer_equivalent: loyer_equivalent,
      rentabilite_annees: rentabiliteAnnees,
      detail_postes: {
        credit: mensualiteCredit,
        taxe_fonciere: taxeFonciereMensuelle,
        charges_copro: chargesCopro,
        energie: coutsEnergie,
        provision_travaux: provisionTravaux,
        apport,
        capital_emprunte: capitalEmprunte,
        taux_credit: taux_credit,
        duree_credit: duree_credit
      }
    };
  }

  // Exposer via globalThis
  if (typeof globalThis.__immodata === 'undefined') {
    globalThis.__immodata = {};
  }
  globalThis.__immodata.calculs = globalThis.__immodata.calculs || {};
  globalThis.__immodata.calculs.coutTotal = { calculerCoutTotal, calcMensualiteCredit, DPE_KWH };

})();
