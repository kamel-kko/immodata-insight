/**
 * ImmoData — QuickView (popup hover sur page liste)
 *
 * Ce fichier gere le mini-popup qui apparait au survol des cartes
 * d'annonces sur les pages LISTE (SeLoger, LeBonCoin, Bien'ici).
 *
 * Fonctionnement :
 * 1. Un MutationObserver detecte les cartes d'annonces sur la page
 * 2. Au mouseenter (800ms de delai), on affiche un popup au-dessus
 * 3. Le popup montre 4 infos cles : delta DVF, prix/m2, DPE, duree en ligne
 * 4. Un bouton "Analyse complete" ouvre l'annonce dans un nouvel onglet
 * 5. Au mouseleave, le popup disparait immediatement
 *
 * Le QuickView est injecte HORS du Shadow DOM (directement dans le DOM
 * de la page) car il doit se positionner relativement aux cartes du site.
 * Les styles sont donc en inline pour eviter les conflits CSS.
 *
 * Enregistre : self.__immodata.ui.quickView
 */

(function () {
  'use strict';

  if (!self.__immodata) self.__immodata = {};
  if (!self.__immodata.ui) self.__immodata.ui = {};

  const log = self.__immodata.createLogger
    ? self.__immodata.createLogger('QUICKVIEW')
    : { info: console.log, warn: console.warn, error: console.error, debug: console.debug };

  // ============================================================
  // CONFIG
  // ============================================================

  const HOVER_DELAY = 800;       // ms avant affichage
  const MAX_POPUPS = 3;          // max popups en memoire
  const QV_WIDTH = 360;          // largeur du popup en px

  // Cache des donnees QV deja recuperees
  const qvCache = new Map();

  // Pool de popups actifs (pour garbage collect)
  const activePopups = [];

  // ============================================================
  // STYLES INLINE — Pas de Shadow DOM, donc tout en inline
  // ============================================================

  const COLORS = {
    bg: '#0F0F11',
    surface: '#1A1A1F',
    surface2: '#242429',
    surface3: '#2E2E36',
    border: 'rgba(255,255,255,0.07)',
    text1: '#F2F2F7',
    text2: '#A0A0B0',
    text3: '#5C5C6E',
    accent: '#6C63FF',
    green: '#00D4AA',
    warn: '#F59E0B',
    danger: '#EF4444',
    success: '#22C55E'
  };

  const DPE_COLORS = {
    A: '#22C55E', B: '#84CC16', C: '#EAB308',
    D: '#F59E0B', E: '#F97316', F: '#EF4444', G: '#DC2626'
  };

  // Partenaires pub (contextuel DPE)
  const SPONSORS = [
    { id: 'pretto', icon: 'P', bg: 'linear-gradient(135deg,#6C63FF,#8B5CF6)', name: 'Pretto', msg: 'Taux d\u00e8s 3,2% \u2014 Simulation gratuite' },
    { id: 'habitissimo', icon: 'H', bg: 'linear-gradient(135deg,#F59E0B,#F97316)', name: 'Habitissimo', msg: '3 devis travaux gratuits en 24h' },
    { id: 'luko', icon: 'L', bg: 'linear-gradient(135deg,#00D4AA,#059669)', name: 'Luko', msg: 'Assurance d\u00e8s 3,30 \u20ac/mois' }
  ];

  function sponsorOrder(dpe) {
    if (dpe && 'DEFG'.includes(dpe)) return [1, 0, 2];
    if (dpe && 'ABC'.includes(dpe))  return [0, 1, 2];
    return [2, 0, 1];
  }

  // ============================================================
  // HELPERS
  // ============================================================

  function fmt(n) {
    if (n === null || n === undefined) return '\u2014';
    return Math.round(n).toLocaleString('fr-FR');
  }

  function scoreColor(score) {
    if (score >= 70) return COLORS.green;
    if (score >= 40) return COLORS.accent;
    if (score >= 25) return COLORS.warn;
    return COLORS.danger;
  }

  // ============================================================
  // CONSTRUCTION DU POPUP HTML
  // ============================================================

  function buildScoreBar(label, value, color) {
    return `
      <div style="min-width:0;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;">
          <span style="font-size:9px;font-weight:600;color:${COLORS.text2};text-transform:uppercase;letter-spacing:0.06em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${label}</span>
          <span style="font-family:monospace;font-size:12px;font-weight:700;color:${COLORS.text1};flex-shrink:0;margin-left:4px;">${value}</span>
        </div>
        <div style="width:100%;height:5px;background:${COLORS.surface3};border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${value}%;background:${color};border-radius:3px;"></div>
        </div>
      </div>`;
  }

  function buildPopupHtml(qvData) {
    const d = qvData;
    const dpe = d.dpe || '?';
    const dpeCol = DPE_COLORS[dpe] || COLORS.text3;

    // Delta DVF
    const delta = d.delta_pct;
    const sign = delta !== null && delta <= 0 ? '' : '+';
    const badgeBg = delta !== null && delta <= 0 ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)';
    const badgeColor = delta !== null && delta <= 0 ? COLORS.success : COLORS.danger;
    const deltaLabel = delta !== null
      ? (delta <= 0 ? 'sous le march\u00e9' : 'au-dessus march\u00e9')
      : 'march\u00e9 inconnu';
    const deltaDisplay = delta !== null ? `${sign}${delta}%` : '?';

    // Prix au m2
    const prixM2 = d.prix_m2 ? fmt(d.prix_m2) : '\u2014';
    const mediane = d.mediane_m2 ? fmt(d.mediane_m2) : '?';

    // Scores
    const negoScore = d.nego_score !== undefined ? d.nego_score : null;
    const pvScore = d.pv_score !== undefined ? d.pv_score : null;
    const qvScore = d.qv_score !== undefined ? d.qv_score : null;
    const riskScore = d.risk_score !== undefined ? d.risk_score : null;

    // Titre
    const title = d.title || 'Annonce';

    // Jours en ligne
    const jours = d.jours_en_ligne;

    // URL annonce
    const url = d.url || '#';

    // Sponsor contextuel
    const order = sponsorOrder(dpe);
    const sp = SPONSORS[order[0]];

    return `
      <div style="background:${COLORS.bg};border:1px solid ${COLORS.border};border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.5);overflow:hidden;font-family:'Inter','Segoe UI',system-ui,sans-serif;">
        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid ${COLORS.border};background:${COLORS.surface};">
          <span style="font-size:13px;font-weight:600;color:${COLORS.text1};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:240px;">\ud83c\udfe0 ${title}</span>
          <span style="font-family:monospace;font-size:12px;font-weight:700;padding:1px 7px;border-radius:4px;background:${dpeCol}20;color:${dpeCol}">DPE ${dpe}</span>
        </div>

        <!-- Grille 2 colonnes : delta + prix/m2 -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;background:${COLORS.border};">
          <div style="background:${COLORS.surface};padding:10px 14px;">
            <div><span style="font-size:15px;font-weight:700;padding:2px 10px;border-radius:20px;background:${badgeBg};color:${badgeColor}">${deltaDisplay}</span></div>
            <div style="font-size:10px;color:${COLORS.text3};margin-top:4px;text-transform:uppercase;letter-spacing:0.06em">${deltaLabel}</div>
          </div>
          <div style="background:${COLORS.surface};padding:10px 14px;">
            <div style="font-family:monospace;font-size:18px;font-weight:700;color:${COLORS.text1};">${prixM2} \u20ac</div>
            <div style="font-size:10px;color:${COLORS.text3};margin-top:2px;text-transform:uppercase;letter-spacing:0.06em">prix/m\u00b2 \u00b7 m\u00e9d. ${mediane}</div>
          </div>
        </div>

        <!-- 4 score bars sur 2 colonnes -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 14px;padding:10px 14px;border-top:1px solid ${COLORS.border};background:${COLORS.surface};">
          ${negoScore !== null ? buildScoreBar('N\u00e9gociation', negoScore, scoreColor(negoScore)) : buildScoreBar('N\u00e9gociation', '\u2014', COLORS.text3)}
          ${pvScore !== null ? buildScoreBar('Plus-value 5a', pvScore, scoreColor(pvScore)) : buildScoreBar('Plus-value', '\u2014', COLORS.text3)}
          ${qvScore !== null ? buildScoreBar('Qualit\u00e9 vie', qvScore, scoreColor(qvScore)) : buildScoreBar('Qualit\u00e9 vie', '\u2014', COLORS.text3)}
          ${riskScore !== null ? buildScoreBar('Risques', riskScore, scoreColor(riskScore)) : buildScoreBar('Risques', '\u2014', COLORS.text3)}
        </div>

        <!-- Sponsor pub compacte -->
        <div style="border-top:1px solid ${COLORS.border};background:${COLORS.surface2};">
          <div style="display:flex;align-items:center;gap:8px;padding:6px 14px;height:32px;cursor:pointer;">
            <span style="width:16px;height:16px;border-radius:3px;background:${sp.bg};display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:#fff;flex-shrink:0;">${sp.icon}</span>
            <span style="font-size:11px;font-weight:700;color:${COLORS.text1};white-space:nowrap;">${sp.name}</span>
            <span style="font-size:10px;color:${COLORS.text2};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${sp.msg}</span>
            <span style="margin-left:auto;color:${COLORS.text3};font-size:12px;flex-shrink:0;">\u203a</span>
          </div>
          <div style="font-size:9px;color:${COLORS.text3};text-align:center;padding:0 0 4px;letter-spacing:0.02em;">\u2726 pub</div>
        </div>

        <!-- Footer -->
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 14px;border-top:1px solid ${COLORS.border};background:${COLORS.bg};">
          <span style="font-size:11px;color:${COLORS.text3};">${jours !== null && jours !== undefined ? '\u23f1 En ligne : ' + jours + ' jours' : ''}</span>
          <a href="${url}" target="_blank" rel="noopener" style="font-size:11px;font-weight:700;color:${COLORS.accent};text-decoration:none;cursor:pointer;display:flex;align-items:center;gap:4px;">Analyse compl\u00e8te <span>\u2192</span></a>
        </div>
      </div>`;
  }

  // ============================================================
  // CHARGEMENT DONNEES — Appel BAN + DVF (cache only si dispo)
  // ============================================================

  function sendToBackground(action, payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action, payload }, (response) => {
        if (chrome.runtime.lastError) {
          resolve({ success: false, error: 'COMM_ERROR' });
          return;
        }
        resolve(response || { success: false, error: 'NO_RESPONSE' });
      });
    });
  }

  async function fetchQvData(cardData) {
    // Verifier le cache
    const cacheKey = cardData.url || cardData.adresse_brute || JSON.stringify(cardData);
    if (qvCache.has(cacheKey)) {
      return qvCache.get(cacheKey);
    }

    const result = {
      title: cardData.titre || cardData.type_bien || 'Annonce',
      dpe: cardData.dpe || null,
      prix_m2: null,
      mediane_m2: null,
      delta_pct: null,
      nego_score: null,
      pv_score: null,
      qv_score: null,
      risk_score: null,
      jours_en_ligne: null,
      url: cardData.url || '#'
    };

    // Calculer prix au m2 si possible
    if (cardData.prix && cardData.surface) {
      result.prix_m2 = Math.round(cardData.prix / cardData.surface);
    }

    // Geocoder via BAN
    if (cardData.adresse_brute || cardData.cp || cardData.ville) {
      const ban = await sendToBackground('FETCH_BAN', {
        adresse: cardData.adresse_brute,
        cp: cardData.cp,
        ville: cardData.ville
      });

      if (ban.success !== false && ban.lat && ban.lon) {
        // Appeler DVF
        const dvf = await sendToBackground('FETCH_DVF', {
          lat: ban.lat,
          lon: ban.lon,
          type_bien: cardData.type_bien,
          surface: cardData.surface,
          prix_annonce: cardData.prix,
          code_insee: ban.code_insee
        });

        if (dvf.success !== false) {
          result.mediane_m2 = dvf.mediane_m2;
          result.delta_pct = dvf.delta_pct;
        }

        // Score negociation rapide
        const nego = await sendToBackground('CALC_NEGOTIATION', {
          delta_dvf: dvf.success !== false ? dvf.delta_pct : null,
          jours_en_ligne: null,
          urgence_texte: false,
          nb_photos: null,
          dpe: cardData.dpe
        });
        if (nego.success !== false) {
          result.nego_score = nego.score;
        }
      }
    }

    // Stocker en cache
    qvCache.set(cacheKey, result);

    // Garbage collect si trop de cles
    if (qvCache.size > 50) {
      const firstKey = qvCache.keys().next().value;
      qvCache.delete(firstKey);
    }

    return result;
  }

  // ============================================================
  // CREATION / POSITIONNEMENT DU POPUP
  // ============================================================

  const QV_HEIGHT_ESTIMATE = 280; // hauteur estimee du popup complet

  function createPopup() {
    const popup = document.createElement('div');
    popup.className = 'immodata-qv-popup';
    popup.style.cssText = `
      position:fixed;
      width:${QV_WIDTH}px;
      z-index:2147483647;
      opacity:0;
      pointer-events:none;
      transition:opacity 150ms ease, transform 150ms ease;
    `;
    // On l'ajoute au body (pas dans la card) pour eviter overflow:hidden
    document.body.appendChild(popup);
    return popup;
  }

  /**
   * Positionne le popup intelligemment par rapport a la card :
   * - Au-dessus si assez de place, sinon en dessous
   * - Horizontal : centre sur la card, cale dans le viewport
   */
  function positionPopup(popup, card) {
    const rect = card.getBoundingClientRect();
    const qvH = QV_HEIGHT_ESTIMATE;

    // Vertical : au-dessus par defaut, en dessous si pas assez de place
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    let top;
    if (spaceAbove >= qvH + 8) {
      // Au-dessus
      top = rect.top - qvH - 8;
    } else if (spaceBelow >= qvH + 8) {
      // En dessous
      top = rect.bottom + 8;
    } else {
      // Pas assez de place ni au-dessus ni en dessous : coller en haut
      top = 8;
    }

    // Horizontal : centre sur la card, cale dans l'ecran
    let left = rect.left + (rect.width / 2) - (QV_WIDTH / 2);
    left = Math.min(left, window.innerWidth - QV_WIDTH - 16);
    left = Math.max(left, 16);

    popup.style.top = Math.round(top) + 'px';
    popup.style.left = Math.round(left) + 'px';
  }

  function showPopup(popup, card) {
    positionPopup(popup, card);
    popup.style.opacity = '1';
    popup.style.pointerEvents = 'auto';
    popup.style.transform = 'translateY(0)';
  }

  function hidePopup(popup) {
    popup.style.opacity = '0';
    popup.style.pointerEvents = 'none';
    popup.style.transform = 'translateY(6px)';
  }

  // ============================================================
  // ATTACHEMENT AUX CARTES — Via MutationObserver
  // ============================================================

  /** Selecteurs CSS pour les cartes d'annonces par site */
  const CARD_SELECTORS = {
    seloger: '[data-testid="sl.explore.card-container"], .CardContainer, a[class*="ClassifiedCard"]',
    leboncoin: '[data-qa-id="aditem_container"], [data-test-id="ad"], a[data-qa-id="aditem_container"], li[data-qa-id="aditem_container"], div[class*="aditem"], article[class*="ad"]',
    bienici: '.searchResults__item, .resultsListContainer__resultItem, div[class*="ResultItem"]'
  };

  function getCardSelector() {
    const host = window.location.hostname;
    if (host.includes('seloger'))   return CARD_SELECTORS.seloger;
    if (host.includes('leboncoin')) return CARD_SELECTORS.leboncoin;
    if (host.includes('bienici'))   return CARD_SELECTORS.bienici;
    return null;
  }

  function attachToCard(card, cardData) {
    // Eviter double attachement
    if (card.hasAttribute('data-immodata-qv')) return;
    card.setAttribute('data-immodata-qv', 'true');
    log.debug('attachToCard : prix=' + cardData.prix + ' surface=' + cardData.surface + ' url=' + (cardData.url || '').slice(0, 60));

    // Creer le popup (sur le body, pas dans la card)
    const popup = createPopup();

    let hoverTimeout = null;
    let loaded = false;

    card.addEventListener('mouseenter', () => {
      hoverTimeout = setTimeout(async () => {
        log.info('Survol card — popup affiche (prix=' + cardData.prix + ')');
        // Charger les donnees si pas encore fait
        if (!loaded) {
          popup.innerHTML = `
            <div style="background:${COLORS.bg};border:1px solid ${COLORS.border};border-radius:12px;padding:20px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.5);font-family:'Inter','Segoe UI',system-ui,sans-serif;">
              <div style="font-size:12px;color:${COLORS.text2};">Chargement...</div>
            </div>`;
          showPopup(popup, card);

          const qvData = await fetchQvData(cardData);
          popup.innerHTML = buildPopupHtml(qvData);
          loaded = true;
        }
        showPopup(popup, card);

        // Garbage collect : garder max N popups
        activePopups.push(popup);
        while (activePopups.length > MAX_POPUPS) {
          const old = activePopups.shift();
          if (old !== popup) old.innerHTML = '';
        }
      }, HOVER_DELAY);
    });

    card.addEventListener('mouseleave', () => {
      clearTimeout(hoverTimeout);
      hidePopup(popup);
    });

    // Masquer aussi quand la card quitte le viewport (scroll)
    // pour eviter un popup orphelin
    let scrollTimeout = null;
    window.addEventListener('scroll', () => {
      if (popup.style.opacity === '1') {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
          positionPopup(popup, card);
        }, 16);
      }
    }, { passive: true });
  }

  // ============================================================
  // INITIALISATION — Observer les cartes
  // ============================================================

  function init() {
    log.info('init() appele');

    const selector = getCardSelector();
    if (!selector) {
      log.warn('Aucun selecteur de carte pour ce site (' + window.location.hostname + ')');
      return;
    }
    log.info('Selecteur utilise : ' + selector);

    const cards = self.__immodata.currentCards || [];
    log.info('currentCards disponibles : ' + cards.length);

    // Attacher aux cartes deja presentes
    const cardElements = document.querySelectorAll(selector);
    log.info('Cards DOM trouvees : ' + cardElements.length);

    cardElements.forEach((el, i) => {
      const cardData = cards[i] || extractMinimalData(el);
      attachToCard(el, cardData);
    });

    // Si aucune carte trouvee, on essaie les selecteurs un par un pour debug
    if (cardElements.length === 0) {
      const host = window.location.hostname;
      const key = host.includes('seloger') ? 'seloger' : host.includes('leboncoin') ? 'leboncoin' : host.includes('bienici') ? 'bienici' : null;
      if (key) {
        CARD_SELECTORS[key].split(', ').forEach(sel => {
          const found = document.querySelectorAll(sel);
          log.debug('  selecteur "' + sel + '" → ' + found.length + ' element(s)');
        });
      }
    }

    // Observer les nouvelles cartes (scroll infini, SPA)
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.matches && node.matches(selector)) {
            log.debug('MutationObserver : nouvelle carte detectee');
            attachToCard(node, extractMinimalData(node));
          }
          const inner = node.querySelectorAll ? node.querySelectorAll(selector) : [];
          if (inner.length > 0) log.debug('MutationObserver : ' + inner.length + ' carte(s) ajoutee(s)');
          inner.forEach(el => attachToCard(el, extractMinimalData(el)));
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    log.info('MutationObserver demarre');
  }

  /**
   * Extraire un minimum de donnees depuis l'element DOM
   * (fallback si currentCards n'est pas disponible)
   */
  function extractMinimalData(el) {
    const text = el.textContent || '';
    // Tenter d'extraire le prix
    const prixMatch = text.match(/([\d\s]+)\s*\u20ac/);
    const prix = prixMatch ? parseInt(prixMatch[1].replace(/\s/g, ''), 10) : null;
    // Tenter d'extraire la surface
    const surfMatch = text.match(/([\d,]+)\s*m[²2]/);
    const surface = surfMatch ? parseFloat(surfMatch[1].replace(',', '.')) : null;
    // URL
    const link = el.querySelector('a[href]');
    const url = link ? link.href : '#';

    return {
      prix: prix,
      surface: surface,
      url: url,
      titre: null,
      dpe: null,
      type_bien: null,
      adresse_brute: null,
      cp: null,
      ville: null
    };
  }

  // ============================================================
  // DESTRUCTION — Nettoyer (navigation SPA)
  // ============================================================

  function destroy() {
    document.querySelectorAll('.immodata-qv-popup').forEach(p => p.remove());
    document.querySelectorAll('[data-immodata-qv]').forEach(el => {
      el.removeAttribute('data-immodata-qv');
    });
    qvCache.clear();
    activePopups.length = 0;
  }

  // ============================================================
  // EXPORT
  // ============================================================

  self.__immodata.ui.quickView = {
    init: init,
    destroy: destroy
  };

})();
