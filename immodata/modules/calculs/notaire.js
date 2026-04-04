/**
 * ImmoData — Calcul des frais de notaire
 *
 * Calcule les frais de notaire selon le barème officiel français
 * (article A444-91 du Code de commerce).
 *
 * Les frais de notaire se composent de :
 * 1. Émoluments du notaire (ses honoraires, calculés par tranches)
 * 2. Droits d'enregistrement (taxe pour l'État et le département)
 * 3. Débours (frais administratifs divers, environ 1 200€)
 *
 * Pour un bien ANCIEN : les droits sont d'environ 5,8% → total ~7-8%
 * Pour un bien NEUF (< 5 ans) : droits réduits à 0,715% → total ~2-3%
 *
 * On affiche une fourchette min/max car les droits d'enregistrement
 * varient légèrement selon les départements.
 */

(function () {
  'use strict';

  // Barème des émoluments notaire par tranches
  // C'est comme l'impôt sur le revenu : chaque tranche a son propre taux
  const TRANCHES = [
    { min: 0,      max: 6500,   taux: 0.03870 },   // 3,870%
    { min: 6500,   max: 17000,  taux: 0.01596 },   // 1,596%
    { min: 17000,  max: 60000,  taux: 0.01064 },   // 1,064%
    { min: 60000,  max: Infinity, taux: 0.00799 }   // 0,799%
  ];

  const TVA_TAUX = 0.20; // 20% de TVA sur les émoluments

  // Droits d'enregistrement : varient selon les départements
  // La plupart sont à 5,80665% mais quelques-uns sont plus bas
  const DROITS_ANCIEN = {
    min: 5.09006,   // Départements à taux réduit (Indre, Morbihan, etc.)
    max: 5.80665,   // Majorité des départements
    base: 5.80665   // Taux de base utilisé pour le calcul médian
  };

  const DROITS_NEUF = 0.715; // Taux réduit pour le neuf (en %)

  const DEBOURS = 1200; // Frais administratifs forfaitaires (estimation moyenne)

  /**
   * Calcule les émoluments du notaire selon le barème par tranches.
   * Fonctionne comme l'impôt : chaque "morceau" du prix est taxé
   * à un taux différent.
   *
   * Exemple pour 200 000€ :
   * - 0 à 6 500€ → 6500 × 3,870% = 251,55€
   * - 6 500 à 17 000€ → 10500 × 1,596% = 167,58€
   * - 17 000 à 60 000€ → 43000 × 1,064% = 457,52€
   * - 60 000 à 200 000€ → 140000 × 0,799% = 1 118,60€
   * Total émoluments = 1 995,25€ HT
   */
  function calcEmoluments(prix) {
    let emoluments = 0;
    for (const tranche of TRANCHES) {
      if (prix <= tranche.min) break;
      const montantDansTranche = Math.min(prix, tranche.max) - tranche.min;
      emoluments += montantDansTranche * tranche.taux;
    }
    return emoluments;
  }

  /**
   * Calcule les frais de notaire complets.
   *
   * @param {Object} params
   * @param {number} params.prix - Prix du bien en euros
   * @param {boolean} [params.neuf=false] - true si bien neuf/VEFA (< 5 ans)
   * @returns {{ frais_min, frais_max, frais_median, type_calcul, detail }}
   */
  function calculerFraisNotaire({ prix, neuf }) {
    if (!prix || prix <= 0) {
      return { frais_min: 0, frais_max: 0, frais_median: 0, type_calcul: 'erreur', detail: null };
    }

    const isNeuf = neuf === true;
    const emolumentsHT = calcEmoluments(prix);
    const emolumentsTTC = emolumentsHT * (1 + TVA_TAUX);

    let fraisMin, fraisMax, fraisMedian;

    if (isNeuf) {
      // Neuf : droits réduits à 0,715%
      const droits = prix * (DROITS_NEUF / 100);
      fraisMin = Math.round(emolumentsTTC + droits + DEBOURS * 0.8);
      fraisMax = Math.round(emolumentsTTC + droits + DEBOURS * 1.2);
      fraisMedian = Math.round(emolumentsTTC + droits + DEBOURS);
    } else {
      // Ancien : droits entre 5,09% et 5,81% selon département
      const droitsMin = prix * (DROITS_ANCIEN.min / 100);
      const droitsMax = prix * (DROITS_ANCIEN.max / 100);
      const droitsBase = prix * (DROITS_ANCIEN.base / 100);
      fraisMin = Math.round(emolumentsTTC + droitsMin + DEBOURS * 0.8);
      fraisMax = Math.round(emolumentsTTC + droitsMax + DEBOURS * 1.2);
      fraisMedian = Math.round(emolumentsTTC + droitsBase + DEBOURS);
    }

    return {
      frais_min: fraisMin,
      frais_max: fraisMax,
      frais_median: fraisMedian,
      type_calcul: isNeuf ? 'neuf' : 'ancien',
      detail: {
        emoluments_ht: Math.round(emolumentsHT),
        emoluments_ttc: Math.round(emolumentsTTC),
        tva: Math.round(emolumentsHT * TVA_TAUX),
        debours: DEBOURS,
        droits_pct: isNeuf ? DROITS_NEUF : DROITS_ANCIEN.base
      }
    };
  }

  // Exposer via globalThis (IIFE) et export (ES Module)
  if (typeof window.__immodata === 'undefined') {
    window.__immodata = {};
  }
  window.__immodata.calculs = window.__immodata.calculs || {};
  window.__immodata.calculs.notaire = { calculerFraisNotaire };

})();
