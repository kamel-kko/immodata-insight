/**
 * ImmoData — Content Script (orchestrateur principal)
 *
 * Ce fichier est le "chef d'orchestre" côté page web. Il :
 * 1. Détecte sur quel site on est et quel type de page (liste/annonce)
 * 2. Lance le bon scraper pour extraire les données
 * 3. Envoie les données au background (Service Worker) pour enrichissement
 * 4. Déclenchera l'injection de l'interface utilisateur (Étapes 6-7)
 *
 * Il est chargé en dernier dans la liste des content scripts du manifest,
 * après security.js, logger.js, extractors.js, detector.js et les scrapers.
 * Tous ces modules s'enregistrent sur globalThis.__immodata.
 *
 * IMPORTANT : ce fichier ne fait JAMAIS de fetch() directement.
 * Toute communication réseau passe par le background via chrome.runtime.sendMessage.
 */

(function () {
  'use strict';

  // Initialiser le namespace si ce n'est pas déjà fait
  if (typeof globalThis.__immodata === 'undefined') {
    globalThis.__immodata = {};
  }

  const log = globalThis.__immodata.createLogger('CONTENT');
  const detector = globalThis.__immodata.detector;
  const scrapers = globalThis.__immodata.scrapers;

  // Flag pour éviter de traiter la même page deux fois d'affilée
  let lastProcessedUrl = null;

  // ============================================================
  // VÉRIFICATION ACTIVATION — L'extension est-elle en pause ?
  // ============================================================

  async function isEnabled() {
    return new Promise((resolve) => {
      chrome.storage.local.get('enabled', (result) => {
        // Par défaut, l'extension est active (si la clé n'existe pas)
        resolve(result.enabled !== false);
      });
    });
  }

  // ============================================================
  // ENVOI AU BACKGROUND — Communication avec le Service Worker
  // ============================================================

  function sendToBackground(action, payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action, payload }, (response) => {
        if (chrome.runtime.lastError) {
          log.error('Erreur communication background:', chrome.runtime.lastError.message);
          resolve({ success: false, error: 'COMM_ERROR', message: chrome.runtime.lastError.message });
          return;
        }
        resolve(response || { success: false, error: 'NO_RESPONSE' });
      });
    });
  }

  // ============================================================
  // TRAITEMENT PAGE ANNONCE
  // ============================================================

  async function processAnnonce(site) {
    const scraper = scrapers[site];
    if (!scraper) {
      log.error(`Pas de scraper pour le site "${site}"`);
      return;
    }

    const data = scraper.extractAnnonceData();

    // Ne rien envoyer si on n'a ni prix ni surface
    if (data.prix === null && data.surface === null) {
      log.warn('Données insuffisantes (prix et surface null) — abandon');
      return;
    }

    log.info('Annonce scrapée, envoi au background pour enrichissement');

    // Étape 1 : Géocodage BAN (nécessaire pour toutes les APIs suivantes)
    if (data.adresse_brute || data.cp || data.ville) {
      const banResult = await sendToBackground('FETCH_BAN', {
        adresse: data.adresse_brute,
        cp: data.cp,
        ville: data.ville
      });

      if (banResult.success !== false) {
        data.lat = banResult.lat;
        data.lon = banResult.lon;
        data.adresse_normalisee = banResult.adresse_normalisee;
        data.code_insee = banResult.code_insee;
        data.fiabilite_geo = banResult.fiabilite_score;
        log.info(`Géocodage OK : ${banResult.adresse_normalisee} (${banResult.lat}, ${banResult.lon})`);
      } else {
        log.warn('Géocodage BAN échoué :', banResult.error);
      }
    }

    // Les appels DVF, Géorisques, etc. seront ajoutés aux Étapes 4-5.
    // L'injection UI sera ajoutée aux Étapes 6-7.

    // Stocker les données scrapées pour usage ultérieur (UI, etc.)
    globalThis.__immodata.currentData = data;

    log.info('Traitement annonce terminé');
    return data;
  }

  // ============================================================
  // TRAITEMENT PAGE LISTE
  // ============================================================

  async function processListe(site) {
    const scraper = scrapers[site];
    if (!scraper) {
      log.error(`Pas de scraper pour le site "${site}"`);
      return;
    }

    const cards = scraper.extractCardsData();
    if (cards.length === 0) {
      log.warn('Aucune carte d\'annonce trouvée sur la page liste');
      return;
    }

    // Stocker les cartes pour l'injection QuickView (Étape 7)
    globalThis.__immodata.currentCards = cards;

    log.info(`${cards.length} carte(s) détectée(s) sur la page liste`);
    return cards;
  }

  // ============================================================
  // FONCTION PRINCIPALE — Analyse de la page courante
  // ============================================================

  async function processCurrentPage() {
    // Vérifier que l'extension est active
    const enabled = await isEnabled();
    if (!enabled) {
      log.info('Extension en pause — aucune action');
      return;
    }

    // Éviter de traiter la même URL deux fois
    const currentUrl = window.location.href;
    if (currentUrl === lastProcessedUrl) {
      log.debug('Page déjà traitée, ignorée');
      return;
    }
    lastProcessedUrl = currentUrl;

    // Détecter site et type de page
    const { site, pageType } = detector.detect();

    if (!site) {
      log.debug('Site non reconnu — aucune action');
      return;
    }

    log.info(`Traitement : ${site} / ${pageType}`);

    switch (pageType) {
      case 'annonce':
        await processAnnonce(site);
        break;
      case 'liste':
        await processListe(site);
        break;
      default:
        log.debug('Type de page inconnu — aucune action');
    }
  }

  // ============================================================
  // DÉMARRAGE
  // ============================================================

  // Lancer le traitement initial
  processCurrentPage();

  // Écouter les navigations SPA (détectées par detector.js)
  document.addEventListener('immodata:page-changed', () => {
    log.info('Événement page-changed reçu — re-traitement');
    // Réinitialiser pour permettre le re-traitement
    lastProcessedUrl = null;
    // Petit délai pour laisser le DOM se stabiliser
    setTimeout(processCurrentPage, 500);
  });

  // Démarrer l'observateur SPA
  detector.startSpaObserver();

  log.info('Content script chargé');

})();
