/**
 * ImmoData — Profil de liquidité
 *
 * Estime la facilité de revente d'un bien et le délai de vente médian,
 * basé sur le nombre de transactions DVF et le type de bien.
 */

(function () {
  'use strict';

  // Délais médians de vente par type de marché (en jours)
  const DELAIS = {
    tendu: 30,   // Paris, Lyon, etc.
    actif: 60,   // Grandes villes
    normal: 90,  // Villes moyennes
    calme: 150   // Rural, petites villes
  };

  function calculerLiquidite({ nb_transactions, type_bien, surface, tendance_dvf }) {
    let profil = 'normal';
    let delai = DELAIS.normal;

    if (nb_transactions > 50) { profil = 'tendu'; delai = DELAIS.tendu; }
    else if (nb_transactions > 20) { profil = 'actif'; delai = DELAIS.actif; }
    else if (nb_transactions < 5) { profil = 'calme'; delai = DELAIS.calme; }

    // Ajustements
    if (type_bien === 'parking') delai = Math.round(delai * 0.6);
    if (type_bien === 'terrain') delai = Math.round(delai * 1.5);
    if (surface && surface > 150) delai = Math.round(delai * 1.3);
    if (tendance_dvf === 'hausse') delai = Math.round(delai * 0.8);
    if (tendance_dvf === 'baisse') delai = Math.round(delai * 1.3);

    return {
      profil,
      delai_vente_median: delai,
      facilite: profil === 'tendu' ? 'Très facile' :
                profil === 'actif' ? 'Facile' :
                profil === 'normal' ? 'Normal' : 'Difficile'
    };
  }

  self.__immodata = self.__immodata || {};
  self.__immodata.calculs = self.__immodata.calculs || {};
  self.__immodata.calculs.liquidite = { calculerLiquidite };
})();
