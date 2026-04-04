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
 * Tous ces modules s'enregistrent sur self.__immodata.
 *
 * IMPORTANT : ce fichier ne fait JAMAIS de fetch() directement.
 * Toute communication réseau passe par le background via chrome.runtime.sendMessage.
 */

(function () {
  'use strict';

  // Initialiser le namespace si ce n'est pas déjà fait
  if (typeof self.__immodata === 'undefined') {
    self.__immodata = {};
  }

  const log = self.__immodata.createLogger('CONTENT');
  const detector = self.__immodata.detector;
  const scrapers = self.__immodata.scrapers;

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

    // Si on n'a ni prix ni surface, on continue quand même
    // pour afficher le dashboard en mode dégradé
    if (data.prix === null && data.surface === null) {
      log.warn('Données insuffisantes (prix et surface null) — mode dégradé');
    }

    log.info('Annonce scrapée, envoi au background pour enrichissement');

    // Tracker d'annonce : enregistrer la visite et detecter les changements de prix
    let trackerInfo = null;
    if (self.__immodata.cache && self.__immodata.cache.trackAnnonceVisit) {
      trackerInfo = await self.__immodata.cache.trackAnnonceVisit(
        data.url_annonce, data.prix, data.surface
      );
      if (trackerInfo) {
        data.jours_en_ligne = trackerInfo.jours_en_ligne;
        data.nb_baisses_prix = trackerInfo.nb_baisses_prix;
        data.delta_premier_prix = trackerInfo.delta_premier_prix;
        data.historique_prix = trackerInfo.historique;
        log.info(`Tracker: en ligne ${trackerInfo.jours_en_ligne}j, ${trackerInfo.nb_baisses_prix} baisse(s)`);
      }
    }

    // Analytics : compter l'annonce analysee
    if (self.__immodata.affiliation && self.__immodata.affiliation.analytics) {
      self.__immodata.affiliation.analytics.trackAnnonceAnalysee();
    }

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

    // Étape 2 : Appels API en parallèle (DVF + Géorisques)
    // On lance les deux en même temps pour gagner du temps
    if (data.lat && data.lon) {
      const [dvfResult, georisquesResult] = await Promise.all([
        sendToBackground('FETCH_DVF', {
          lat: data.lat,
          lon: data.lon,
          type_bien: data.type_bien,
          surface: data.surface,
          prix_annonce: data.prix,
          code_insee: data.code_insee
        }),
        sendToBackground('FETCH_GEORISQUES', {
          lat: data.lat,
          lon: data.lon
        })
      ]);

      // DVF — prix du marché
      if (dvfResult.success !== false) {
        data.dvf = dvfResult;
        log.info(`DVF: médiane ${dvfResult.mediane_m2}€/m², ${dvfResult.nb_transactions} transactions, delta ${dvfResult.delta_pct}%`);
      } else {
        log.warn('DVF échoué :', dvfResult.error);
        data.dvf = null;
      }

      // Géorisques — risques naturels et industriels
      if (georisquesResult.success !== false) {
        data.georisques = georisquesResult;
        log.info(`Géorisques: ${georisquesResult.nb_risques} risque(s), ${georisquesResult.nb_icpe} ICPE`);
      } else {
        log.warn('Géorisques échoué :', georisquesResult.error);
        data.georisques = null;
      }
    }

    // Étape 3 : Calculs locaux (frais notaire, négociation, CTP)
    // Ces calculs sont exécutés dans le background mais sans appel réseau

    // Frais de notaire
    const isNeuf = data.flags_regex && data.flags_regex.neuf_vefa;
    const notaireResult = await sendToBackground('CALC_NOTAIRE', {
      prix: data.prix,
      neuf: isNeuf
    });
    if (notaireResult.success !== false) {
      data.frais_notaire = notaireResult;
      log.info(`Notaire: ${notaireResult.frais_median}€ (${notaireResult.type_calcul})`);
    }

    // Score de négociation
    const negoResult = await sendToBackground('CALC_NEGOTIATION', {
      delta_dvf: data.dvf ? data.dvf.delta_pct : null,
      jours_en_ligne: data.jours_en_ligne || null,
      urgence_texte: data.flags_regex ? data.flags_regex.urgent : false,
      nb_photos: null,
      dpe: data.dpe
    });
    if (negoResult.success !== false) {
      data.negotiation = negoResult;
      log.info(`Négociation: score ${negoResult.score}/100 — "${negoResult.label}"`);
    }

    // Coût Total de Possession
    const ctpResult = await sendToBackground('CALC_COUT_TOTAL', {
      prix: data.prix,
      surface: data.surface,
      type_bien: data.type_bien,
      dpe: data.dpe,
      annee_constr: data.annee_constr,
      taxe_fonciere: data.flags_regex ? data.flags_regex.taxe_fonciere : null
    });
    if (ctpResult.success !== false) {
      data.cout_total = ctpResult;
      log.info(`CTP: ${ctpResult.total_mensuel}€/mois (crédit ${ctpResult.mensualite_credit}€)`);
    }

    // Étape 4 : APIs complémentaires en parallèle
    // On lance toutes les APIs qui dépendent des coordonnées GPS et/ou du code INSEE
    if (data.lat && data.lon) {
      const apiPromises = [
        sendToBackground('FETCH_EDUCATION', { lat: data.lat, lon: data.lon }),
        sendToBackground('FETCH_OVERPASS', { lat: data.lat, lon: data.lon }),
        sendToBackground('FETCH_RTE', { lat: data.lat, lon: data.lon }),
        sendToBackground('FETCH_BRUIT', { lat: data.lat, lon: data.lon }),
        sendToBackground('FETCH_MERIMEE', { lat: data.lat, lon: data.lon })
      ];

      // APIs qui utilisent le code INSEE
      if (data.code_insee) {
        apiPromises.push(
          sendToBackground('FETCH_SIRENE', { code_insee: data.code_insee }),
          sendToBackground('FETCH_ANIL', { code_insee: data.code_insee }),
          sendToBackground('FETCH_LOYERS', { code_insee: data.code_insee, type_bien: data.type_bien, surface: data.surface })
        );
      }

      // ADEME (DPE officiel)
      if (data.adresse_normalisee) {
        apiPromises.push(
          sendToBackground('FETCH_ADEME', { adresse: data.adresse_normalisee, code_insee: data.code_insee })
        );
      }

      // ORS (isochrones — optionnel, nécessite clé API)
      apiPromises.push(
        sendToBackground('FETCH_ORS', { lat: data.lat, lon: data.lon })
      );

      const [
        educationResult, overpassResult, rteResult, bruitResult, merimeeResult,
        ...extraResults
      ] = await Promise.all(apiPromises);

      // Stocker les résultats
      if (educationResult.success !== false) { data.education = educationResult; log.info(`Éducation: ${educationResult.nb_etablissements || 0} établissement(s)`); }
      if (overpassResult.success !== false) { data.overpass = overpassResult; log.info(`Overpass: ${overpassResult.nb_commerces || 0} commerces, ${overpassResult.nb_transports || 0} transports`); }
      if (rteResult.success !== false) { data.rte = rteResult; log.info(`RTE: ligne HT ${rteResult.ligne_proche ? 'oui' : 'non'}`); }
      if (bruitResult.success !== false) { data.bruit = bruitResult; log.info(`Bruit: zone PEB ${bruitResult.zone_peb ? 'oui' : 'non'}`); }
      if (merimeeResult.success !== false) { data.merimee = merimeeResult; log.info(`Mérimée: ${merimeeResult.nb_monuments || 0} monument(s)`); }

      // Résultats conditionnels (SIRENE, ANIL, Loyers, ADEME, ORS)
      let idx = 0;
      if (data.code_insee) {
        if (extraResults[idx] && extraResults[idx].success !== false) { data.sirene = extraResults[idx]; log.info(`SIRENE: ${extraResults[idx].nb_etablissements || 0} entreprises`); }
        idx++;
        if (extraResults[idx] && extraResults[idx].success !== false) { data.anil = extraResults[idx]; log.info(`ANIL: zone ${extraResults[idx].zone}`); }
        idx++;
        if (extraResults[idx] && extraResults[idx].success !== false) { data.loyers = extraResults[idx]; log.info(`Loyers: médiane ${extraResults[idx].loyer_median || '?'}€/m²`); }
        idx++;
      }
      if (data.adresse_normalisee) {
        if (extraResults[idx] && extraResults[idx].success !== false) { data.ademe = extraResults[idx]; log.info(`ADEME: DPE ${extraResults[idx].dpe || '?'}`); }
        idx++;
      }
      // ORS est toujours le dernier
      if (extraResults[idx] && extraResults[idx].success !== false) { data.ors = extraResults[idx]; log.info(`ORS: ${extraResults[idx].nb_zones || 0} isochrone(s)`); }
    }

    // Étape 5 : Calculs avancés (plus-value, liquidité, travaux, qualité de vie, rentabilité)

    // Estimation travaux
    const travauxResult = await sendToBackground('CALC_TRAVAUX', {
      dpe: data.dpe,
      surface: data.surface,
      annee_construction: data.annee_constr,
      type_bien: data.type_bien
    });
    if (travauxResult.success !== false) {
      data.travaux = travauxResult;
      log.info(`Travaux: ${travauxResult.niveau} — ${travauxResult.cout_estime}€`);
    }

    // Score plus-value
    const pvResult = await sendToBackground('CALC_PLUS_VALUE', {
      tendance_dvf: data.dvf ? data.dvf.tendance : null,
      nb_transactions: data.dvf ? data.dvf.nb_transactions : 0,
      nb_etablissements: data.sirene ? data.sirene.nb_etablissements : 0,
      score_qualite_vie: null, // sera recalculé après
      projets_urbains: false   // pas de source de données pour l'instant
    });
    if (pvResult.success !== false) {
      data.plus_value = pvResult;
      log.info(`Plus-value: score ${pvResult.score}/100 — "${pvResult.label}"`);
    }

    // Liquidité
    const liqResult = await sendToBackground('CALC_LIQUIDITE', {
      nb_transactions: data.dvf ? data.dvf.nb_transactions : 0,
      type_bien: data.type_bien,
      surface: data.surface,
      tendance_dvf: data.dvf ? data.dvf.tendance : null
    });
    if (liqResult.success !== false) {
      data.liquidite = liqResult;
      log.info(`Liquidité: ${liqResult.profil} — délai ${liqResult.delai_vente_median}j`);
    }

    // Qualité de vie (utilise les résultats des APIs complémentaires)
    const qvResult = await sendToBackground('CALC_QUALITE_VIE', {
      nb_commerces: data.overpass ? data.overpass.nb_commerces : 0,
      nb_transports: data.overpass ? data.overpass.nb_transports : 0,
      nb_ecoles: data.education ? data.education.nb_etablissements : 0,
      risques_niveau: data.georisques ? data.georisques.classification : 'FAIBLE',
      zone_bruit: data.bruit ? data.bruit.zone_peb : false,
      nb_monuments: data.merimee ? data.merimee.nb_monuments : 0,
      ligne_haute_tension: data.rte ? data.rte.ligne_proche : false
    });
    if (qvResult.success !== false) {
      data.qualite_vie = qvResult;
      log.info(`Qualité de vie: score ${qvResult.score}/100 — "${qvResult.label}"`);
    }

    // Rentabilité locative
    const rentaResult = await sendToBackground('CALC_RENTABILITE', {
      prix_achat: data.prix,
      loyer_median: data.loyers ? data.loyers.loyer_median : null,
      surface: data.surface,
      frais_notaire: data.frais_notaire ? data.frais_notaire.frais_median : null,
      cout_travaux: data.travaux ? data.travaux.cout_estime : 0,
      taxe_fonciere: null,
      charges_copro: null
    });
    if (rentaResult.success !== false) {
      data.rentabilite = rentaResult;
      log.info(`Rentabilité: meilleure stratégie "${rentaResult.meilleure}"`);
    }

    // Stocker les données enrichies pour usage ultérieur
    self.__immodata.currentData = data;

    // Étape 7 : Injection de l'interface utilisateur (Side Dashboard)
    if (self.__immodata.ui && self.__immodata.ui.sideDashboard) {
      log.info('Injection du Side Dashboard');
      self.__immodata.ui.sideDashboard.inject(data);
    }

    log.info('Traitement annonce terminé — toutes les données enrichies');
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

    // Stocker les cartes pour l'injection QuickView
    self.__immodata.currentCards = cards;

    // Étape 7 : Injection du QuickView (popup hover)
    if (self.__immodata.ui && self.__immodata.ui.quickView) {
      log.info('Initialisation du QuickView sur les cartes liste');
      self.__immodata.ui.quickView.init();
    }

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
    // Nettoyer l'UI existante avant re-injection
    if (self.__immodata.ui) {
      if (self.__immodata.ui.sideDashboard) self.__immodata.ui.sideDashboard.destroy();
      if (self.__immodata.ui.quickView) self.__immodata.ui.quickView.destroy();
    }
    // Réinitialiser pour permettre le re-traitement
    lastProcessedUrl = null;
    // Petit délai pour laisser le DOM se stabiliser
    setTimeout(processCurrentPage, 500);
  });

  // Démarrer l'observateur SPA
  detector.startSpaObserver();

  log.info('Content script chargé');

})();
