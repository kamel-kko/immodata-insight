/**
 * ImmoData -- Analytics local (chrome.storage uniquement)
 *
 * Ce fichier gere le tracking 100% local des statistiques d'usage :
 * - Nombre d'annonces analysees
 * - Impressions et clics sur les CTA partenaires
 * - Taux de clic par partenaire
 *
 * AUCUNE donnee ne quitte le navigateur. Tout est stocke dans
 * chrome.storage.local sous la cle "immodata_analytics".
 *
 * Analogie : c'est un compteur personnel. Comme un podometre
 * qui compte tes pas sans envoyer les donnees a personne.
 *
 * Enregistre : self.__immodata.affiliation.analytics
 */

(function () {
  'use strict';

  if (!self.__immodata) self.__immodata = {};
  if (!self.__immodata.affiliation) self.__immodata.affiliation = {};

  var log = self.__immodata.createLogger
    ? self.__immodata.createLogger('ANALYTICS')
    : { info: console.log, warn: console.warn, error: console.error, debug: console.debug };

  // Cle de stockage dans chrome.storage.local
  var STORAGE_KEY = 'immodata_analytics';

  // Structure par defaut des analytics
  var DEFAULT_STATS = {
    annonces_analysees: 0,
    pages_liste_vues: 0,
    premiere_utilisation: null,
    derniere_utilisation: null,
    cta_impressions: {},
    cta_clics: {}
  };

  // Cache en memoire pour eviter de lire chrome.storage a chaque appel
  var statsCache = null;

  /**
   * Charge les stats depuis chrome.storage.local.
   * Si rien n'existe, retourne la structure par defaut.
   */
  async function loadStats() {
    if (statsCache) return statsCache;
    try {
      var result = await chrome.storage.local.get(STORAGE_KEY);
      statsCache = result[STORAGE_KEY] || JSON.parse(JSON.stringify(DEFAULT_STATS));
      return statsCache;
    } catch (err) {
      log.error('Erreur lecture analytics :', err);
      return JSON.parse(JSON.stringify(DEFAULT_STATS));
    }
  }

  /**
   * Sauvegarde les stats dans chrome.storage.local.
   */
  async function saveStats(stats) {
    statsCache = stats;
    try {
      await chrome.storage.local.set({ [STORAGE_KEY]: stats });
    } catch (err) {
      log.error('Erreur ecriture analytics :', err);
    }
  }

  /**
   * Incremente le compteur d'annonces analysees.
   * Appele par content_script.js a chaque page annonce traitee.
   */
  async function trackAnnonceAnalysee() {
    var stats = await loadStats();
    stats.annonces_analysees++;
    stats.derniere_utilisation = Date.now();
    if (!stats.premiere_utilisation) stats.premiere_utilisation = Date.now();
    await saveStats(stats);
    log.debug('Annonce analysee — total : ' + stats.annonces_analysees);
  }

  /**
   * Incremente le compteur de pages liste vues.
   */
  async function trackPageListeVue() {
    var stats = await loadStats();
    stats.pages_liste_vues++;
    stats.derniere_utilisation = Date.now();
    if (!stats.premiere_utilisation) stats.premiere_utilisation = Date.now();
    await saveStats(stats);
    log.debug('Page liste vue — total : ' + stats.pages_liste_vues);
  }

  /**
   * Enregistre une impression CTA (le CTA a ete affiche a l'ecran).
   * @param {string} ctaId - Identifiant du CTA (ex: "credit", "travaux")
   */
  async function trackImpression(ctaId) {
    var stats = await loadStats();
    if (!stats.cta_impressions[ctaId]) stats.cta_impressions[ctaId] = 0;
    stats.cta_impressions[ctaId]++;
    await saveStats(stats);
    log.debug('Impression CTA : ' + ctaId + ' (total ' + stats.cta_impressions[ctaId] + ')');
  }

  /**
   * Enregistre un clic sur un CTA.
   * @param {string} ctaId - Identifiant du CTA
   */
  async function trackClick(ctaId) {
    var stats = await loadStats();
    if (!stats.cta_clics[ctaId]) stats.cta_clics[ctaId] = 0;
    stats.cta_clics[ctaId]++;
    await saveStats(stats);
    log.info('Clic CTA : ' + ctaId + ' (total ' + stats.cta_clics[ctaId] + ')');
  }

  /**
   * Retourne toutes les stats pour affichage dans la popup.
   */
  async function getStats() {
    return await loadStats();
  }

  /**
   * Remet toutes les stats a zero.
   * Appele par le bouton "Effacer statistiques" dans la popup.
   */
  async function resetStats() {
    statsCache = JSON.parse(JSON.stringify(DEFAULT_STATS));
    await saveStats(statsCache);
    log.info('Analytics remis a zero');
  }

  // Export
  self.__immodata.affiliation.analytics = {
    trackAnnonceAnalysee: trackAnnonceAnalysee,
    trackPageListeVue: trackPageListeVue,
    trackImpression: trackImpression,
    trackClick: trackClick,
    getStats: getStats,
    resetStats: resetStats
  };

})();
