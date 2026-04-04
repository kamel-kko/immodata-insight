/**
 * ImmoData — Détecteur de site et type de page
 *
 * Ce module regarde l'URL du navigateur pour savoir sur quel site on est
 * (SeLoger, LeBonCoin ou Bien'ici) et si on est sur une page de liste
 * d'annonces ou sur la page d'une annonce en particulier.
 *
 * Il surveille aussi les navigations "SPA" (quand le site change de page
 * sans recharger complètement, comme quand on clique sur une annonce dans
 * une liste). Dans ce cas, il émet un événement personnalisé pour que le
 * reste du code puisse réagir.
 *
 * Analogie : c'est comme un détecteur de mouvement. Il surveille en
 * permanence et signale quand quelque chose a changé.
 */

(function () {
  'use strict';

  const log = globalThis.__immodata.createLogger('DETECTOR');

  // ============================================================
  // DÉTECTION DU SITE
  // ============================================================

  function detectSite() {
    const host = window.location.hostname;
    if (host.includes('seloger.com')) return 'seloger';
    if (host.includes('leboncoin.fr')) return 'leboncoin';
    if (host.includes('bienici.com')) return 'bienici';
    return null;
  }

  // ============================================================
  // DÉTECTION DU TYPE DE PAGE
  // ============================================================
  // On regarde l'URL et la structure du DOM pour déterminer
  // si c'est une page "liste" (résultats de recherche)
  // ou une page "annonce" (détail d'un bien).

  function detectPageType(site) {
    const url = window.location.href;
    const path = window.location.pathname;

    switch (site) {
      case 'seloger':
        // Page annonce : /annonces/achat/appartement/.../12345.htm
        if (/\/\d+\.htm/.test(path)) return 'annonce';
        // Page liste : /list.htm ou /recherche/
        if (path.includes('/list') || path.includes('/recherche')) return 'liste';
        // Fallback : vérifier si un conteneur d'annonce existe dans le DOM
        if (document.querySelector('[data-testid="classified-detail"]') ||
            document.querySelector('.ClassifiedDetail')) return 'annonce';
        if (document.querySelector('[data-testid="card-list"]') ||
            document.querySelector('.ListCard')) return 'liste';
        return 'inconnu';

      case 'leboncoin':
        // Page annonce : /ad/ventes_immobilieres/12345.htm
        if (/\/ad\//.test(path)) return 'annonce';
        // Page liste : /recherche
        if (path.includes('/recherche')) return 'liste';
        if (document.querySelector('[data-qa-id="adview_container"]')) return 'annonce';
        if (document.querySelector('[data-qa-id="aditem_container"]')) return 'liste';
        return 'inconnu';

      case 'bienici':
        // Page annonce : /annonce/...
        if (path.includes('/annonce/')) return 'annonce';
        // Page liste : /recherche/
        if (path.includes('/recherche/')) return 'liste';
        if (document.querySelector("div[class*='detailPage']")) return 'annonce';
        if (document.querySelector("div[class*='listCard']")) return 'liste';
        return 'inconnu';

      default:
        return 'inconnu';
    }
  }

  // ============================================================
  // OBSERVER SPA — Surveiller les navigations sans rechargement
  // ============================================================
  // Les sites modernes (comme LeBonCoin) ne rechargent pas la page
  // quand on clique sur une annonce. Le contenu change mais l'URL aussi.
  // On surveille deux choses :
  // 1. Les changements d'URL (pushState / popstate)
  // 2. Les mutations du DOM principal (ajout/suppression d'éléments)

  let lastUrl = window.location.href;
  let observer = null;

  function emitPageChanged() {
    log.info('Navigation SPA détectée');
    document.dispatchEvent(new CustomEvent('immodata:page-changed'));
  }

  function startSpaObserver() {
    // Surveiller les changements d'URL
    // On intercepte pushState et replaceState pour détecter les navigations SPA
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function () {
      originalPushState.apply(this, arguments);
      checkUrlChange();
    };

    history.replaceState = function () {
      originalReplaceState.apply(this, arguments);
      checkUrlChange();
    };

    window.addEventListener('popstate', checkUrlChange);

    function checkUrlChange() {
      const currentUrl = window.location.href;
      if (currentUrl !== lastUrl) {
        lastUrl = currentUrl;
        // Petit délai pour laisser le DOM se mettre à jour
        setTimeout(emitPageChanged, 300);
      }
    }

    // Surveiller les mutations DOM majeures
    // On observe le body pour détecter les gros changements de contenu
    observer = new MutationObserver((mutations) => {
      // On ne réagit qu'aux ajouts/suppressions d'éléments significatifs
      let significant = false;
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === 1 && node.matches &&
                (node.matches('main, article, [role="main"], #app > div'))) {
              significant = true;
              break;
            }
          }
        }
        if (significant) break;
      }
      // On ne fait rien ici pour les mutations DOM mineures.
      // Les navigations SPA sont déjà captées par l'interception de pushState.
    });

    observer.observe(document.body, {
      childList: true,
      subtree: false
    });

    log.debug('Observateur SPA démarré');
  }

  function stopSpaObserver() {
    if (observer) {
      observer.disconnect();
      observer = null;
      log.debug('Observateur SPA arrêté');
    }
  }

  // ============================================================
  // FONCTION PRINCIPALE — Analyse complète
  // ============================================================

  function detect() {
    const site = detectSite();
    const pageType = site ? detectPageType(site) : 'inconnu';
    log.info(`Détecté : site=${site}, page=${pageType}`);
    return { site, pageType };
  }

  // Exposer les fonctions via globalThis pour le content script (IIFE)
  globalThis.__immodata.detector = {
    detect,
    detectSite,
    detectPageType,
    startSpaObserver,
    stopSpaObserver
  };

})();
