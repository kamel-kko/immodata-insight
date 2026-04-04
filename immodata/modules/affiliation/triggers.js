/**
 * ImmoData -- Regles de declenchement CTA (Call To Action)
 *
 * Ce fichier definit QUAND et QUEL CTA afficher en fonction
 * des donnees de l'annonce. Chaque regle a :
 * - un id unique (ex: "credit")
 * - une fonction `match(data)` qui retourne true/false
 * - un partenaire (ou plusieurs pour rotation A/B)
 * - un message contextuel
 *
 * Analogie : c'est un aiguilleur. Selon les donnees du bien,
 * il decide quel panneau publicitaire afficher. Un bien DPE F
 * verra "devis travaux", un bien a 300 000 EUR verra "simulation credit".
 *
 * Enregistre : self.__immodata.affiliation.triggers
 */

(function () {
  'use strict';

  if (!self.__immodata) self.__immodata = {};
  if (!self.__immodata.affiliation) self.__immodata.affiliation = {};

  // ==============================================================
  // PARTENAIRES — Infos fixes de chaque partenaire
  // ==============================================================

  const PARTNERS = {
    pretto: {
      id: 'pretto',
      name: 'Pretto',
      icon: 'P',
      bg: 'linear-gradient(135deg,#6C63FF,#8B5CF6)',
      base_url: 'https://www.pretto.fr/simulation/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=credit'
    },
    meilleurtaux: {
      id: 'meilleurtaux',
      name: 'Meilleurtaux',
      icon: 'M',
      bg: 'linear-gradient(135deg,#3B82F6,#1D4ED8)',
      base_url: 'https://www.meilleurtaux.com/credit-immobilier/simulation-de-pret-immobilier/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=credit'
    },
    habitissimo: {
      id: 'habitissimo',
      name: 'Habitissimo',
      icon: 'H',
      bg: 'linear-gradient(135deg,#F59E0B,#F97316)',
      base_url: 'https://www.habitissimo.fr/devis/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=travaux'
    },
    luko: {
      id: 'luko',
      name: 'Luko',
      icon: 'L',
      bg: 'linear-gradient(135deg,#00D4AA,#059669)',
      base_url: 'https://www.luko.eu/fr/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=assurance'
    },
    diagamter: {
      id: 'diagamter',
      name: 'Diagamter',
      icon: 'D',
      bg: 'linear-gradient(135deg,#EF4444,#DC2626)',
      base_url: 'https://www.diagamter.com/devis/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=diagnostics'
    },
    moveezy: {
      id: 'moveezy',
      name: 'Moveezy',
      icon: 'V',
      bg: 'linear-gradient(135deg,#8B5CF6,#7C3AED)',
      base_url: 'https://www.moveezy.fr/',
      utm: 'utm_source=immodata&utm_medium=extension&utm_campaign=demenagement'
    }
  };

  // ==============================================================
  // REGLES CTA — Chaque regle decide quand un CTA s'affiche
  // ==============================================================
  // Priorite : plus le nombre est bas, plus le CTA est affiche en premier.
  // On n'affiche pas plus de 3 CTA dans le dashboard pour ne pas surcharger.

  const CTA_RULES = [
    {
      id: 'credit',
      priority: 1,
      // Affiche si le prix est > 80 000 EUR (achat immobilier classique)
      match: function (data) {
        return data.prix && data.prix > 80000;
      },
      // Rotation A/B : alterne entre Pretto et Meilleurtaux
      // selon le timestamp de la visite (pair = Pretto, impair = Meilleurtaux)
      getPartner: function () {
        var second = Math.floor(Date.now() / 1000);
        return second % 2 === 0 ? PARTNERS.pretto : PARTNERS.meilleurtaux;
      },
      label: 'Simuler votre cr\u00e9dit',
      sublabel: 'Sans engagement \u2014 R\u00e9ponse en 5 min',
      category: 'credit'
    },
    {
      id: 'travaux',
      priority: 2,
      // Affiche si DPE D, E, F ou G (travaux de renovation recommandes)
      match: function (data) {
        return data.dpe && 'DEFG'.includes(data.dpe);
      },
      getPartner: function () {
        return PARTNERS.habitissimo;
      },
      label: '3 devis travaux gratuits',
      sublabel: function (data) {
        if (data.travaux && data.travaux.prime_estimee) {
          return 'MaPrimeR\u00e9nov\u0027 estim\u00e9e : ' + Math.round(data.travaux.prime_estimee).toLocaleString('fr-FR') + ' \u20ac';
        }
        return 'Comparez les artisans de votre ville';
      },
      category: 'travaux'
    },
    {
      id: 'diagnostics',
      priority: 3,
      // Affiche si le bien a ete construit avant 1997
      // (risque amiante, plomb, diagnostics obligatoires)
      match: function (data) {
        return data.annee_constr && data.annee_constr < 1997;
      },
      getPartner: function () {
        return PARTNERS.diagamter;
      },
      label: 'Devis diagnostics obligatoires',
      sublabel: 'Amiante, plomb, DPE, gaz, \u00e9lectricit\u00e9',
      category: 'diagnostics'
    },
    {
      id: 'assurance',
      priority: 4,
      // Toujours affiche (assurance habitation = universel)
      match: function () {
        return true;
      },
      getPartner: function () {
        return PARTNERS.luko;
      },
      label: 'Assurance d\u00e8s 3,30 \u20ac/mois',
      sublabel: 'Protection compl\u00e8te, r\u00e9siliation facile',
      category: 'assurance'
    },
    {
      id: 'demenagement',
      priority: 5,
      // Toujours affiche mais basse priorite
      match: function () {
        return true;
      },
      getPartner: function () {
        return PARTNERS.moveezy;
      },
      label: 'Comparer les d\u00e9m\u00e9nageurs',
      sublabel: 'Devis gratuits en 2 min',
      category: 'demenagement'
    }
  ];

  // Maximum de CTA affiches simultanement
  var MAX_CTA = 3;

  /**
   * Evalue toutes les regles et retourne les CTA a afficher.
   * Les regles sont triees par priorite, et on garde les N premiers qui matchent.
   *
   * @param {Object} data - Donnees de l'annonce (prix, dpe, annee_constr, etc.)
   * @returns {Array<{ id, partner, label, sublabel, url, category }>}
   */
  function evaluateRules(data) {
    var sorted = CTA_RULES.slice().sort(function (a, b) { return a.priority - b.priority; });
    var results = [];

    for (var i = 0; i < sorted.length && results.length < MAX_CTA; i++) {
      var rule = sorted[i];
      if (rule.match(data)) {
        var partner = rule.getPartner();
        var sublabel = typeof rule.sublabel === 'function' ? rule.sublabel(data) : rule.sublabel;

        // Construire l'URL avec UTM
        var url = partner.base_url;
        if (url.includes('?')) {
          url += '&' + partner.utm;
        } else {
          url += '?' + partner.utm;
        }

        results.push({
          id: rule.id,
          partner: partner,
          label: rule.label,
          sublabel: sublabel,
          url: url,
          category: rule.category
        });
      }
    }

    return results;
  }

  // Export
  self.__immodata.affiliation.triggers = {
    evaluateRules: evaluateRules,
    PARTNERS: PARTNERS,
    CTA_RULES: CTA_RULES,
    MAX_CTA: MAX_CTA
  };

})();
