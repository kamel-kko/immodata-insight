/**
 * ImmoData -- Generateur HTML des cartes CTA (Call To Action)
 *
 * Ce fichier transforme les regles CTA evaluees par triggers.js
 * en HTML pret a injecter dans le Side Dashboard.
 *
 * Chaque carte CTA a :
 * - Le logo du partenaire (lettre + gradient)
 * - Un titre et un sous-titre contextuels
 * - Un bouton d'action qui ouvre l'URL via le background
 * - Un badge "pub" discret
 *
 * IMPORTANT : le clic sur un CTA envoie un message OPEN_AFFILIATE_URL
 * au background.js qui ouvre l'URL dans un nouvel onglet.
 * On ne fait JAMAIS window.open() depuis le content script.
 *
 * Enregistre : self.__immodata.affiliation.ctaRenderer
 */

(function () {
  'use strict';

  if (!self.__immodata) self.__immodata = {};
  if (!self.__immodata.affiliation) self.__immodata.affiliation = {};

  var log = self.__immodata.createLogger
    ? self.__immodata.createLogger('CTA_RENDERER')
    : { info: console.log, warn: console.warn, error: console.error, debug: console.debug };

  // Icones SVG simples pour les categories
  var CATEGORY_ICONS = {
    credit: '\u{1F3E6}',       // banque
    travaux: '\u{1F528}',      // marteau
    diagnostics: '\u{1F50D}',  // loupe
    assurance: '\u{1F6E1}',    // bouclier
    demenagement: '\u{1F69A}'  // camion
  };

  /**
   * Genere le HTML d'une seule carte CTA.
   * Le HTML utilise les classes du design system Bento
   * (idi-card-m, bento-header, etc.).
   */
  function renderCtaCard(cta) {
    var icon = CATEGORY_ICONS[cta.category] || '';
    var p = cta.partner;

    return '<div class="bento-card idi-card-m cta-card" data-cta-id="' + cta.id + '" data-cta-url="' + cta.url + '">' +
      '<span class="idi-badge idi-badge-float" style="background:rgba(108,99,255,0.15);color:#8B5CF6;font-size:9px;">pub</span>' +
      '<div class="bento-header">' +
        '<div style="width:24px;height:24px;border-radius:6px;background:' + p.bg + ';display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;flex-shrink:0;">' + p.icon + '</div>' +
        '<span class="bento-label">' + p.name + '</span>' +
      '</div>' +
      '<div style="font-size:13px;font-weight:600;color:var(--idi-text-1,#F2F2F7);margin-top:6px;">' + icon + ' ' + cta.label + '</div>' +
      '<div style="font-size:11px;color:var(--idi-text-2,#A0A0B0);margin-top:2px;">' + cta.sublabel + '</div>' +
      '<button class="cta-btn-affiliate" style="margin-top:8px;width:100%;padding:8px 0;border:none;border-radius:8px;background:var(--idi-accent,#6C63FF);color:#fff;font-size:12px;font-weight:700;cursor:pointer;transition:opacity 150ms;">En profiter <span style="margin-left:4px;">\u2192</span></button>' +
    '</div>';
  }

  /**
   * Genere le HTML de toutes les cartes CTA pour une annonce.
   *
   * @param {Object} data - Donnees de l'annonce
   * @returns {string} HTML des cartes CTA (ou vide si aucun CTA ne matche)
   */
  function renderAllCtas(data) {
    var triggers = self.__immodata.affiliation.triggers;
    if (!triggers) {
      log.warn('triggers.js non charge — pas de CTA');
      return '';
    }

    var ctas = triggers.evaluateRules(data);
    if (ctas.length === 0) return '';

    log.info(ctas.length + ' CTA(s) genere(s) : ' + ctas.map(function (c) { return c.id; }).join(', '));

    var html = '<!-- CTA Affiliation -->';
    for (var i = 0; i < ctas.length; i++) {
      html += renderCtaCard(ctas[i]);
    }
    return html;
  }

  /**
   * Attache les event listeners sur les boutons CTA.
   * Doit etre appele APRES que le HTML a ete injecte dans le DOM (ou Shadow DOM).
   *
   * @param {ShadowRoot|HTMLElement} root - L'element racine ou chercher les boutons
   */
  function bindCtaClicks(root) {
    var cards = root.querySelectorAll('.cta-card[data-cta-url]');
    log.debug('Binding CTA clicks sur ' + cards.length + ' carte(s)');

    cards.forEach(function (card) {
      var url = card.getAttribute('data-cta-url');
      var ctaId = card.getAttribute('data-cta-id');
      var btn = card.querySelector('.cta-btn-affiliate');

      if (!btn || btn.hasAttribute('data-cta-bound')) return;
      btn.setAttribute('data-cta-bound', 'true');

      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        log.info('CTA clic : ' + ctaId + ' -> ' + url.slice(0, 80));

        // Tracker le clic (analytics)
        if (self.__immodata.affiliation.analytics) {
          self.__immodata.affiliation.analytics.trackClick(ctaId);
        }

        // Ouvrir via le background (securise)
        chrome.runtime.sendMessage({
          action: 'OPEN_AFFILIATE_URL',
          payload: { url: url }
        });
      });

      // Tracker l'impression (la carte est visible)
      if (self.__immodata.affiliation.analytics) {
        self.__immodata.affiliation.analytics.trackImpression(ctaId);
      }
    });
  }

  // Export
  self.__immodata.affiliation.ctaRenderer = {
    renderCtaCard: renderCtaCard,
    renderAllCtas: renderAllCtas,
    bindCtaClicks: bindCtaClicks
  };

})();
