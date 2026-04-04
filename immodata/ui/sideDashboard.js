/**
 * ImmoData — Side Dashboard (panneau lateral complet)
 *
 * Ce fichier injecte le panneau lateral droit sur les pages ANNONCE.
 * Il cree un Shadow DOM sur le <body>, y charge tous les CSS du
 * design system, puis construit la grille Bento avec les vraies
 * donnees scrapees et calculees par le content_script.
 *
 * Fonctionnement :
 * 1. On cree un <div id="immodata-host"> sur le body
 * 2. On y attache un Shadow DOM ferme (isolation CSS totale)
 * 3. On affiche d'abord des skeleton loaders (chargement)
 * 4. On remplit les cartes au fur et a mesure que les donnees arrivent
 *
 * Enregistre : self.__immodata.ui.sideDashboard
 */

(function () {
  'use strict';

  if (!self.__immodata) self.__immodata = {};
  if (!self.__immodata.ui) self.__immodata.ui = {};

  const log = self.__immodata.createLogger
    ? self.__immodata.createLogger('SIDE_DASHBOARD')
    : { info: console.log, warn: console.warn, error: console.error, debug: console.debug };

  const ICONS = self.__immodata.icons || {};

  // ============================================================
  // HELPERS — Fonctions utilitaires pour construire le HTML
  // ============================================================

  /** Formater un nombre avec separateur de milliers */
  function fmt(n) {
    if (n === null || n === undefined) return '—';
    return Math.round(n).toLocaleString('fr-FR');
  }

  /** Formater un prix en euros */
  function fmtEur(n) {
    if (n === null || n === undefined) return '—';
    return fmt(n) + ' \u20ac';
  }

  /** Choisir la classe de badge selon un score 0-100 */
  function scoreBadgeClass(score) {
    if (score >= 70) return 'idi-badge-success';
    if (score >= 40) return 'idi-badge-warn';
    return 'idi-badge-danger';
  }

  /** Choisir la couleur de barre selon un score 0-100 */
  function scoreBarColor(score) {
    if (score >= 70) return 'var(--idi-green)';
    if (score >= 40) return 'var(--idi-accent)';
    if (score >= 25) return 'var(--idi-warn)';
    return 'var(--idi-danger)';
  }

  /** Choisir le label textuel selon un score 0-100 */
  function scoreLabel(score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Bon';
    if (score >= 40) return 'Moyen';
    if (score >= 20) return 'Faible';
    return 'Critique';
  }

  /** Couleur DPE standard */
  function dpeColor(dpe) {
    const colors = { A: '#22C55E', B: '#84CC16', C: '#EAB308', D: '#F59E0B', E: '#F97316', F: '#EF4444', G: '#DC2626' };
    return colors[dpe] || 'var(--idi-neutral)';
  }

  /** Carte skeleton (chargement) */
  function skeleton(size, lines) {
    const cls = size === 'xl' ? 'idi-card-xl' : size === 'm' ? 'idi-card-m' : '';
    let content = '<div class="skeleton skeleton-label" style="width:100px;margin-bottom:8px"></div>';
    content += '<div class="skeleton skeleton-value"></div>';
    for (let i = 0; i < (lines || 0); i++) {
      content += `<div class="skeleton skeleton-line" style="margin-top:8px;width:${70 + i * 10}%"></div>`;
    }
    return `<div class="bento-card ${cls}">${content}</div>`;
  }

  /** Carte en etat degrade (API echouee) */
  function degraded(icon, label, message) {
    return `
      <div class="bento-header">
        <span class="bento-icon">${icon}</span>
        <span class="bento-label">${label}</span>
      </div>
      <div style="font-size:12px;color:var(--idi-text-3)">${message}</div>`;
  }

  // ============================================================
  // ONGLET FINANCE
  // ============================================================

  function renderFinance(data) {
    const nego = data.negotiation;
    const dvf = data.dvf;
    const ctp = data.cout_total;
    const notaire = data.frais_notaire;
    const dpe = data.dpe || (data.ademe ? data.ademe.dpe : null);

    // Score de negociation
    const negoScore = nego ? nego.score : null;
    const negoLabel = nego ? nego.label : 'Chargement...';
    const negoBadge = dvf && dvf.delta_pct !== null
      ? `<span class="idi-badge ${dvf.delta_pct <= 0 ? 'idi-badge-success' : 'idi-badge-danger'} idi-badge-float idi-badge-enter">${dvf.delta_pct <= 0 ? '' : '+'}${dvf.delta_pct}% vs march\u00e9</span>`
      : '';

    // Prix au m2
    const prixM2 = data.prix && data.surface ? Math.round(data.prix / data.surface) : null;
    const medianeM2 = dvf ? dvf.mediane_m2 : null;
    const prixM2Badge = prixM2 && medianeM2
      ? (() => {
          const diff = Math.round(((prixM2 - medianeM2) / medianeM2) * 100);
          const cls = diff <= 0 ? 'idi-badge-success' : diff <= 10 ? 'idi-badge-warn' : 'idi-badge-danger';
          return `<span class="idi-badge ${cls}" style="margin-top:6px">${diff <= 0 ? '' : '+'}${diff}% vs m\u00e9diane</span>`;
        })()
      : '';

    // CTP details
    const credit = ctp ? fmtEur(ctp.mensualite_credit) : '—';
    const taxeF = ctp ? fmtEur(Math.round(ctp.taxe_fonciere / 12)) : '—';
    const copro = ctp ? fmtEur(ctp.charges_copro) : '—';
    const energie = ctp ? fmtEur(ctp.cout_energie) : '—';

    // Frais notaire
    const notaireVal = notaire ? fmtEur(notaire.frais_median) : '—';
    const notaireType = notaire ? notaire.type_calcul : '';

    // CTA dynamiques via le systeme d'affiliation
    // triggers.js decide quels CTA afficher, ctaRenderer.js genere le HTML
    let ctaHtml = '';
    if (self.__immodata.affiliation && self.__immodata.affiliation.ctaRenderer) {
      ctaHtml = self.__immodata.affiliation.ctaRenderer.renderAllCtas(data);
    }

    // Tracker : info "en ligne depuis X jours" et baisses de prix
    const trackerHtml = data.jours_en_ligne != null && data.jours_en_ligne > 0
      ? `<div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.bar_chart || ''}</span>
            <span class="bento-label">Historique annonce</span>
          </div>
          <div style="font-size:13px;font-weight:600;color:var(--idi-text-1);">\u23f1 En ligne depuis ${data.jours_en_ligne} jour${data.jours_en_ligne > 1 ? 's' : ''}</div>
          ${data.nb_baisses_prix > 0
            ? `<div style="font-size:11px;color:var(--idi-success);margin-top:4px;">\u2193 ${data.nb_baisses_prix} baisse(s) de prix d\u00e9tect\u00e9e(s)${data.delta_premier_prix ? ' (' + fmtEur(data.delta_premier_prix) + ')' : ''}</div>`
            : `<div style="font-size:11px;color:var(--idi-text-3);margin-top:4px;">Aucune baisse de prix d\u00e9tect\u00e9e</div>`
          }
        </div>`
      : '';

    return `
      <div class="idi-grid idi-stagger">
        <!-- Score negociation -->
        <div class="bento-card idi-card-xl">
          ${negoBadge}
          <div class="bento-header">
            <span class="bento-icon">${ICONS.percent || ''}</span>
            <span class="bento-label">Score de n\u00e9gociation</span>
          </div>
          <div class="bento-value bento-value-lg">${negoScore !== null ? negoScore : '—'}<span style="font-size:16px;color:var(--idi-text-2)">/100</span></div>
          <div style="font-size:11px;color:var(--idi-text-2);margin-top:4px;">${negoLabel}</div>
          ${negoScore !== null ? `<div class="idi-score-bar"><div class="idi-score-bar-fill animate" style="width:${negoScore}%;background:${scoreBarColor(negoScore)}"></div></div>` : ''}
        </div>

        <!-- Cout total + Prix/m2 -->
        <div class="idi-row-split">
          <div class="bento-card">
            <div class="bento-header">
              <span class="bento-icon">${ICONS.credit_card || ''}</span>
              <span class="bento-label">Co\u00fbt total mensuel</span>
            </div>
            <div class="bento-value">${ctp ? fmtEur(ctp.total_mensuel) : '—'}</div>
            <div style="font-size:10px;color:var(--idi-text-3);margin-top:4px;">Cr\u00e9dit + Taxe + Copro + \u00c9nergie</div>
          </div>
          <div class="bento-card">
            <div class="bento-header">
              <span class="bento-icon">${ICONS.euro || ''}</span>
              <span class="bento-label">Prix / m\u00b2</span>
            </div>
            <div class="bento-value">${prixM2 !== null ? fmtEur(prixM2) : '—'}</div>
            ${prixM2Badge}
          </div>
        </div>

        <!-- 3x S : Taxe + Copro + Energie -->
        <div class="idi-row-triple">
          <div class="bento-card idi-card-s">
            <div class="bento-label">Taxe fonci\u00e8re</div>
            <div class="bento-value" style="font-size:18px;">${taxeF}/mois</div>
          </div>
          <div class="bento-card idi-card-s">
            <div class="bento-label">Charges copro</div>
            <div class="bento-value" style="font-size:18px;">${copro}</div>
          </div>
          <div class="bento-card idi-card-s">
            <div class="bento-label">Co\u00fbt \u00e9nergie</div>
            <div class="bento-value" style="font-size:18px;">${energie}</div>
          </div>
        </div>

        <!-- Frais notaire + DPE -->
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.bar_chart || ''}</span>
            <span class="bento-label">Frais de notaire</span>
          </div>
          <div class="bento-value">${notaireVal}</div>
          <div style="font-size:10px;color:var(--idi-text-3);margin-top:2px;">${notaireType}</div>
        </div>
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.thermometer || ''}</span>
            <span class="bento-label">DPE officiel</span>
          </div>
          <div class="bento-value" style="color:${dpeColor(dpe)}">${dpe || '?'}</div>
          <div style="font-size:10px;color:var(--idi-text-3);margin-top:2px;">${dpe && 'FG'.includes(dpe) ? 'Passoire thermique' : dpe && 'DE'.includes(dpe) ? 'Travaux recommand\u00e9s' : dpe ? 'Correct' : 'Non communiqu\u00e9'}</div>
        </div>

        <!-- Tracker historique annonce -->
        ${trackerHtml}

        <!-- CTA Affiliation dynamiques -->
        ${ctaHtml}
      </div>`;
  }

  // ============================================================
  // ONGLET QUARTIER
  // ============================================================

  function renderQuartier(data) {
    const ov = data.overpass;
    const edu = data.education;
    const qv = data.qualite_vie;

    // Transports
    const transports = ov && ov.transports
      ? ov.transports.slice(0, 5).map(t =>
          `<div style="display:flex;justify-content:space-between;padding:3px 0;">
            <span style="font-size:12px;color:var(--idi-text-1)">${t.name || t.type}</span>
            <span style="font-size:11px;color:var(--idi-text-3)">${t.distance ? t.distance + 'm' : ''}</span>
          </div>`
        ).join('')
      : '<div style="font-size:12px;color:var(--idi-text-3)">Aucune donn\u00e9e</div>';

    // Commerces
    const nbCommerces = ov ? (ov.nb_commerces || 0) : '—';
    const nbTransports = ov ? (ov.nb_transports || 0) : '—';

    // Ecoles
    const ecoles = edu && edu.etablissements
      ? edu.etablissements.slice(0, 4).map(e =>
          `<div style="display:flex;justify-content:space-between;padding:3px 0;">
            <span style="font-size:12px;color:var(--idi-text-1);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px">${e.nom || e.type}</span>
            <span style="font-size:11px;color:var(--idi-text-3)">${e.distance ? e.distance + 'm' : ''}</span>
          </div>`
        ).join('')
      : '<div style="font-size:12px;color:var(--idi-text-3)">Aucune donn\u00e9e</div>';

    // Score qualite de vie
    const qvScore = qv ? qv.score : null;

    return `
      <div class="idi-grid idi-stagger">
        <!-- Transports proches -->
        <div class="bento-card idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.bus || ''}</span>
            <span class="bento-label">Transports proches</span>
          </div>
          ${transports}
        </div>

        <!-- Ecoles -->
        <div class="bento-card idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.school || ''}</span>
            <span class="bento-label">\u00c9coles &amp; \u00e9tablissements</span>
          </div>
          ${ecoles}
        </div>

        <!-- Commerces + Transports count -->
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.shopping_bag || ''}</span>
            <span class="bento-label">Commerces</span>
          </div>
          <div class="bento-value">${nbCommerces}</div>
          <div style="font-size:10px;color:var(--idi-text-3);margin-top:2px;">dans un rayon de 500m</div>
        </div>
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.bus || ''}</span>
            <span class="bento-label">Arr\u00eats transports</span>
          </div>
          <div class="bento-value">${nbTransports}</div>
          <div style="font-size:10px;color:var(--idi-text-3);margin-top:2px;">dans un rayon de 500m</div>
        </div>

        <!-- Score Qualite de vie -->
        <div class="bento-card idi-card-xl">
          ${qvScore !== null ? `
            <div class="bento-header">
              <span class="bento-icon">${ICONS.star || ''}</span>
              <span class="bento-label">Score qualit\u00e9 de vie</span>
            </div>
            <div class="bento-value bento-value-lg">${qvScore}<span style="font-size:16px;color:var(--idi-text-2)">/100</span></div>
            <div style="font-size:11px;color:var(--idi-text-2);margin-top:4px;">${scoreLabel(qvScore)}</div>
            <div class="idi-score-bar"><div class="idi-score-bar-fill animate" style="width:${qvScore}%;background:${scoreBarColor(qvScore)}"></div></div>
          ` : degraded(ICONS.star || '', 'Qualit\u00e9 de vie', 'Donn\u00e9es insuffisantes')}
        </div>
      </div>`;
  }

  // ============================================================
  // ONGLET RISQUES
  // ============================================================

  function renderRisques(data) {
    const geo = data.georisques;
    const rte = data.rte;
    const bruit = data.bruit;
    const merimee = data.merimee;

    // Risques naturels
    const nbRisques = geo ? geo.nb_risques : '—';
    const classification = geo ? geo.classification : 'INCONNU';
    const riskBadgeClass = classification === 'FORT' || classification === 'TRES_FORT'
      ? 'idi-badge-danger'
      : classification === 'MOYEN' ? 'idi-badge-warn' : 'idi-badge-success';

    // Risques caches
    const ligneHT = rte ? rte.ligne_proche : false;
    const zonePEB = bruit ? bruit.zone_peb : false;
    const nbIcpe = geo ? geo.nb_icpe : 0;
    const nbMonuments = merimee ? merimee.nb_monuments : 0;

    // Liste risques
    const risquesList = geo && geo.risques
      ? geo.risques.slice(0, 5).map(r =>
          `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">
            <span style="color:var(--idi-danger);font-size:14px;flex-shrink:0;">\u26a0</span>
            <span style="font-size:12px;color:var(--idi-text-1)">${r.libelle || r.type || r}</span>
          </div>`
        ).join('')
      : '';

    return `
      <div class="idi-grid idi-stagger">
        <!-- Risques naturels -->
        <div class="bento-card idi-card-xl">
          <span class="idi-badge ${riskBadgeClass} idi-badge-float idi-badge-enter">${classification}</span>
          <div class="bento-header">
            <span class="bento-icon" style="color:var(--idi-danger)">${ICONS.alert_triangle || ''}</span>
            <span class="bento-label">Risques naturels (G\u00e9orisques)</span>
          </div>
          <div class="bento-value bento-value-lg">${nbRisques}</div>
          <div style="font-size:11px;color:var(--idi-text-2);margin-top:4px;">risque(s) identifi\u00e9(s)</div>
          ${risquesList}
        </div>

        <!-- Risques caches -->
        <div class="bento-card idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.shield || ''}</span>
            <span class="bento-label">Risques cach\u00e9s</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div style="padding:8px;border-radius:8px;background:${ligneHT ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)'}">
              <div style="font-size:11px;font-weight:600;color:${ligneHT ? 'var(--idi-danger)' : 'var(--idi-success)'}">Ligne HT</div>
              <div style="font-size:10px;color:var(--idi-text-3)">${ligneHT ? 'Proche !' : 'Aucune'}</div>
            </div>
            <div style="padding:8px;border-radius:8px;background:${zonePEB ? 'rgba(245,158,11,0.1)' : 'rgba(34,197,94,0.1)'}">
              <div style="font-size:11px;font-weight:600;color:${zonePEB ? 'var(--idi-warn)' : 'var(--idi-success)'}">Plan bruit</div>
              <div style="font-size:10px;color:var(--idi-text-3)">${zonePEB ? 'Zone PEB' : 'Hors zone'}</div>
            </div>
            <div style="padding:8px;border-radius:8px;background:${nbIcpe > 0 ? 'rgba(245,158,11,0.1)' : 'rgba(34,197,94,0.1)'}">
              <div style="font-size:11px;font-weight:600;color:${nbIcpe > 0 ? 'var(--idi-warn)' : 'var(--idi-success)'}">ICPE</div>
              <div style="font-size:10px;color:var(--idi-text-3)">${nbIcpe > 0 ? nbIcpe + ' site(s)' : 'Aucun'}</div>
            </div>
            <div style="padding:8px;border-radius:8px;background:${nbMonuments > 0 ? 'rgba(108,99,255,0.1)' : 'rgba(100,116,139,0.1)'}">
              <div style="font-size:11px;font-weight:600;color:${nbMonuments > 0 ? 'var(--idi-accent)' : 'var(--idi-neutral)'}">Monuments</div>
              <div style="font-size:10px;color:var(--idi-text-3)">${nbMonuments > 0 ? nbMonuments + ' proche(s)' : 'Aucun'}</div>
            </div>
          </div>
        </div>
      </div>`;
  }

  // ============================================================
  // ONGLET INVESTIR
  // ============================================================

  function renderInvestir(data) {
    const renta = data.rentabilite;
    const liq = data.liquidite;
    const anil = data.anil;

    // Tableau comparatif 4 strategies
    const strategies = renta && renta.strategies
      ? renta.strategies.map(s => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--idi-border);">
            <div>
              <div style="font-size:12px;font-weight:600;color:var(--idi-text-1)">${s.nom}</div>
              <div style="font-size:10px;color:var(--idi-text-3)">Cashflow ${s.cashflow_mensuel >= 0 ? '+' : ''}${fmt(s.cashflow_mensuel)} \u20ac/mois</div>
            </div>
            <div style="text-align:right">
              <div style="font-family:var(--idi-font-mono);font-size:16px;font-weight:700;color:${s.rendement_net >= 5 ? 'var(--idi-green)' : s.rendement_net >= 3 ? 'var(--idi-accent)' : 'var(--idi-text-2)'}">${s.rendement_net.toFixed(1)}%</div>
              <div style="font-size:10px;color:var(--idi-text-3)">net</div>
            </div>
          </div>`
        ).join('')
      : '<div style="font-size:12px;color:var(--idi-text-3)">Donn\u00e9es insuffisantes</div>';

    const meilleure = renta ? renta.meilleure : '—';

    // Liquidite
    const liqProfil = liq ? liq.profil : '—';
    const delaiVente = liq ? liq.delai_vente_median : '—';

    // Zone
    const zone = anil ? anil.zone : '—';

    return `
      <div class="idi-grid idi-stagger">
        <!-- Comparatif 4 strategies -->
        <div class="bento-card idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.bar_chart || ''}</span>
            <span class="bento-label">Comparatif strat\u00e9gies locatives</span>
          </div>
          ${strategies}
          ${renta ? `<div style="font-size:11px;color:var(--idi-accent);margin-top:8px;font-weight:600;">Recommandation : ${meilleure}</div>` : ''}
        </div>

        <!-- Liquidite + Delai -->
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.trending_up || ''}</span>
            <span class="bento-label">Liquidit\u00e9</span>
          </div>
          <div class="bento-value" style="font-size:18px;text-transform:capitalize">${liqProfil}</div>
        </div>
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.clock || ''}</span>
            <span class="bento-label">D\u00e9lai vente m\u00e9dian</span>
          </div>
          <div class="bento-value" style="font-size:18px;">${delaiVente} j</div>
        </div>

        <!-- Zones -->
        <div class="idi-row-triple">
          <div class="bento-card idi-card-s">
            <div class="bento-label">Zone ANIL</div>
            <div class="bento-value" style="font-size:18px;">${zone}</div>
          </div>
          <div class="bento-card idi-card-s">
            <div class="bento-label">LMNP</div>
            <div class="bento-value" style="font-size:18px;color:var(--idi-success)">\u2713</div>
          </div>
          <div class="bento-card idi-card-s">
            <div class="bento-label">Airbnb</div>
            <div class="bento-value" style="font-size:18px;color:var(--idi-text-3)">?</div>
          </div>
        </div>
      </div>`;
  }

  // ============================================================
  // ONGLET AVENIR
  // ============================================================

  function renderAvenir(data) {
    const pv = data.plus_value;
    const qv = data.qualite_vie;
    const sirene = data.sirene;
    const rte = data.rte;
    const bruit = data.bruit;

    const pvScore = pv ? pv.score : null;
    const pvLabel = pv ? pv.label : '—';

    const nbEntreprises = sirene ? sirene.nb_etablissements : '—';

    return `
      <div class="idi-grid idi-stagger">
        <!-- Score Plus-Value -->
        <div class="bento-card idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.trending_up || ''}</span>
            <span class="bento-label">Score potentiel plus-value</span>
          </div>
          <div class="bento-value bento-value-lg">${pvScore !== null ? pvScore : '—'}<span style="font-size:16px;color:var(--idi-text-2)">/100</span></div>
          <div style="font-size:11px;color:var(--idi-text-2);margin-top:4px;">${pvLabel}</div>
          ${pvScore !== null ? `<div class="idi-score-bar"><div class="idi-score-bar-fill animate" style="width:${pvScore}%;background:${scoreBarColor(pvScore)}"></div></div>` : ''}
        </div>

        <!-- Tissu economique -->
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.building || ''}</span>
            <span class="bento-label">Tissu \u00e9conomique</span>
          </div>
          <div class="bento-value" style="font-size:18px;">${nbEntreprises}</div>
          <div style="font-size:10px;color:var(--idi-text-3);margin-top:2px;">\u00e9tablissements actifs</div>
        </div>

        <!-- Score environnemental -->
        <div class="bento-card idi-card-m">
          <div class="bento-header">
            <span class="bento-icon">${ICONS.tree || ''}</span>
            <span class="bento-label">Environnement</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <div style="font-size:11px;color:${rte && rte.ligne_proche ? 'var(--idi-danger)' : 'var(--idi-success)'}">Ligne HT : ${rte && rte.ligne_proche ? '\u26a0 Proche' : '\u2713 OK'}</div>
            <div style="font-size:11px;color:${bruit && bruit.zone_peb ? 'var(--idi-warn)' : 'var(--idi-success)'}">Bruit : ${bruit && bruit.zone_peb ? '\u26a0 PEB' : '\u2713 Calme'}</div>
          </div>
        </div>
      </div>`;
  }

  // ============================================================
  // FOOTER COMMUN — CTA Rapport PDF
  // ============================================================

  function renderFooter() {
    return `
      <div style="padding:var(--idi-gap);">
        <div class="cta-rapport idi-card-xl">
          <div class="bento-header">
            <span class="bento-icon" style="color:var(--idi-accent)">${ICONS.star || ''}</span>
            <span class="bento-label">Rapport complet ImmoData</span>
          </div>
          <div class="cta-rapport-price">
            <span class="current">4,90 \u20ac</span>
            <span class="old">valeur 49 \u20ac</span>
          </div>
          <ul class="cta-rapport-list">
            <li><span class="check">\u2713</span> Analyse compl\u00e8te prix vs march\u00e9 DVF</li>
            <li><span class="check">\u2713</span> Carte des risques et nuisances</li>
            <li><span class="check">\u2713</span> Simulation rentabilit\u00e9 4 strat\u00e9gies</li>
            <li><span class="check">\u2713</span> Score qualit\u00e9 de vie du quartier</li>
            <li><span class="check">\u2713</span> Estimation travaux + aides MaPrimeR\u00e9nov'</li>
          </ul>
          <button class="cta-btn-rapport">T\u00e9l\u00e9charger le rapport PDF <span class="arrow">\u2192</span></button>
        </div>
        <div style="font-size:9px;color:var(--idi-text-3);text-align:center;padding:8px 0;letter-spacing:0.02em;">
          ImmoData \u00b7 Donn\u00e9es Open Data \u00b7 RGPD conforme
        </div>
      </div>`;
  }

  // ============================================================
  // SKELETON — Affichage initial pendant le chargement
  // ============================================================

  function renderSkeleton() {
    return `
      <div class="idi-grid">
        ${skeleton('xl', 2)}
        ${skeleton('m', 0)}
        ${skeleton('m', 0)}
        ${skeleton('xl', 1)}
      </div>`;
  }

  // ============================================================
  // SPONSOR BANNER — Bande pub rotative
  // ============================================================

  function renderSponsorBanner() {
    return `
      <div class="idi-sponsor-wrap">
        <div class="idi-sponsor-band" id="idi-sponsor-band">
          <div class="idi-sponsor-slide active" data-url="#">
            <div class="idi-sponsor-logo" style="background:linear-gradient(135deg,#6C63FF,#8B5CF6)">P</div>
            <span class="idi-sponsor-name">Pretto</span>
            <span class="idi-sponsor-msg">Taux d\u00e8s 3,2% \u2014 Simulation gratuite</span>
            <span class="idi-sponsor-arrow">\u203a</span>
          </div>
          <div class="idi-sponsor-slide" data-url="#">
            <div class="idi-sponsor-logo" style="background:linear-gradient(135deg,#F59E0B,#F97316)">H</div>
            <span class="idi-sponsor-name">Habitissimo</span>
            <span class="idi-sponsor-msg">3 devis travaux gratuits en 24h</span>
            <span class="idi-sponsor-arrow">\u203a</span>
          </div>
          <div class="idi-sponsor-slide" data-url="#">
            <div class="idi-sponsor-logo" style="background:linear-gradient(135deg,#00D4AA,#059669)">L</div>
            <span class="idi-sponsor-name">Luko</span>
            <span class="idi-sponsor-msg">Assurance d\u00e8s 3,30 \u20ac/mois</span>
            <span class="idi-sponsor-arrow">\u203a</span>
          </div>
        </div>
        <div class="idi-sponsor-dots" id="idi-sponsor-dots">
          <div class="idi-sponsor-dot active"></div>
          <div class="idi-sponsor-dot"></div>
          <div class="idi-sponsor-dot"></div>
        </div>
        <div class="idi-sponsor-mention">\u2726 Publicit\u00e9 \u2014 permet de garder ImmoData gratuit</div>
      </div>`;
  }

  // ============================================================
  // INJECTION PRINCIPALE
  // ============================================================

  function inject(data) {
    log.info('inject() appele — prix=' + data.prix + ' surface=' + data.surface + ' ville=' + data.ville);

    // Eviter double injection
    if (document.getElementById('immodata-host')) {
      log.info('Panel deja present — update');
      update(data);
      return;
    }

    // Creer le host element
    const host = document.createElement('div');
    host.id = 'immodata-host';
    host.style.cssText = 'position:fixed;right:0;top:50%;transform:translateY(-50%);width:380px;max-height:90vh;z-index:2147483647;';
    document.body.appendChild(host);

    // Creer le Shadow DOM
    const shadow = host.attachShadow({ mode: 'open' });

    // Charger les CSS via fetch (les fichiers sont dans l'extension)
    const cssFiles = ['ui/design-tokens.css', 'ui/bento-grid.css', 'ui/components.css', 'ui/animations.css'];
    const style = document.createElement('style');

    // Charger les CSS depuis les fichiers de l'extension
    Promise.all(
      cssFiles.map(f => fetch(chrome.runtime.getURL(f)).then(r => r.text()))
    ).then(sheets => {
      style.textContent = sheets.join('\n');
      shadow.appendChild(style);
      buildPanel(shadow, data);
    }).catch(() => {
      // Fallback : on continue sans CSS (ne devrait pas arriver)
      shadow.appendChild(style);
      buildPanel(shadow, data);
    });
  }

  function buildPanel(shadow, data) {
    const adresse = data.adresse_normalisee || data.adresse_brute || 'Adresse inconnue';
    const surface = data.surface ? data.surface + 'm\u00b2' : '';
    const pieces = data.nb_pieces ? data.nb_pieces + ' p' : '';
    const subtitle = [pieces, surface, data.ville || ''].filter(Boolean).join(' \u00b7 ');

    const panel = document.createElement('div');
    panel.className = 'idi-panel idi-panel-enter';
    panel.innerHTML = `
      <div class="idi-panel-fixed">
        <div class="idi-panel-header">
          <div>
            <div class="idi-panel-title">${ICONS.home || ''} ImmoData</div>
            <div class="idi-panel-subtitle">${subtitle}</div>
          </div>
          <div style="display:flex;gap:4px;">
            <button class="idi-btn-icon" id="idi-collapse">${ICONS.chevron_right || '\u203a'}</button>
            <button class="idi-btn-icon" id="idi-close">${ICONS.x || '\u00d7'}</button>
          </div>
        </div>
        ${renderSponsorBanner()}
        <div class="idi-tabs" id="idi-tabs">
          <button class="idi-tab active" data-tab="finance">Finance</button>
          <button class="idi-tab" data-tab="quartier">Quartier</button>
          <button class="idi-tab" data-tab="risques">Risques</button>
          <button class="idi-tab" data-tab="investir">Investir</button>
          <button class="idi-tab" data-tab="avenir">Avenir</button>
        </div>
      </div>
      <div class="idi-panel-body" id="idi-body">
        ${renderSkeleton()}
      </div>`;

    shadow.appendChild(panel);

    // Stocker la ref shadow pour les updates
    self.__immodata.ui._shadow = shadow;
    self.__immodata.ui._panel = panel;

    // Initialiser l'interactivite
    initInteractivity(shadow, data);

    // Remplir les donnees (remplace les skeletons)
    renderTab(shadow, 'finance', data);
  }

  // ============================================================
  // INTERACTIVITE — Onglets, boutons, sponsor
  // ============================================================

  function initInteractivity(shadow, data) {
    // Onglets
    shadow.querySelectorAll('.idi-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        shadow.querySelectorAll('.idi-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const tabName = tab.getAttribute('data-tab');
        renderTab(shadow, tabName, data);
        // Sauvegarder l'onglet actif
        if (chrome.storage && chrome.storage.session) {
          chrome.storage.session.set({ activeTab: tabName });
        }
      });
    });

    // Bouton fermer
    const closeBtn = shadow.getElementById('idi-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        const host = document.getElementById('immodata-host');
        if (host) host.remove();
      });
    }

    // Bouton replier
    const collapseBtn = shadow.getElementById('idi-collapse');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => {
        const host = document.getElementById('immodata-host');
        if (!host) return;
        const collapsed = host.style.width === '40px';
        host.style.width = collapsed ? '380px' : '40px';
        host.style.overflow = collapsed ? '' : 'hidden';
      });
    }

    // Rotation sponsor (8s)
    const slides = shadow.querySelectorAll('.idi-sponsor-slide');
    const dots = shadow.querySelectorAll('.idi-sponsor-dot');
    if (slides.length > 1) {
      let current = 0;
      setInterval(() => {
        slides[current].classList.remove('active');
        dots[current].classList.remove('active');
        current = (current + 1) % slides.length;
        slides[current].classList.add('active');
        dots[current].classList.add('active');
      }, 8000);

      dots.forEach((dot, i) => {
        dot.style.cursor = 'pointer';
        dot.addEventListener('click', () => {
          slides[current].classList.remove('active');
          dots[current].classList.remove('active');
          current = i;
          slides[current].classList.add('active');
          dots[current].classList.add('active');
        });
      });
    }
  }

  // ============================================================
  // RENDU ONGLET — Remplit le body selon l'onglet actif
  // ============================================================

  function renderTab(shadow, tabName, data) {
    const body = shadow.getElementById('idi-body');
    if (!body) return;

    let content = '';
    switch (tabName) {
      case 'finance':  content = renderFinance(data); break;
      case 'quartier': content = renderQuartier(data); break;
      case 'risques':  content = renderRisques(data); break;
      case 'investir': content = renderInvestir(data); break;
      case 'avenir':   content = renderAvenir(data); break;
      default:         content = renderFinance(data);
    }

    body.innerHTML = content + renderFooter();
    body.scrollTop = 0;

    // Brancher les clics CTA affiliation sur le contenu fraichement rendu
    if (self.__immodata.affiliation && self.__immodata.affiliation.ctaRenderer) {
      self.__immodata.affiliation.ctaRenderer.bindCtaClicks(shadow);
    }
  }

  // ============================================================
  // MISE A JOUR — Re-rendre quand les donnees changent
  // ============================================================

  function update(data) {
    const shadow = self.__immodata.ui._shadow;
    if (!shadow) return;

    // Trouver l'onglet actif
    const activeTab = shadow.querySelector('.idi-tab.active');
    const tabName = activeTab ? activeTab.getAttribute('data-tab') : 'finance';

    renderTab(shadow, tabName, data);
  }

  // ============================================================
  // DESTRUCTION — Retirer le panel (navigation SPA)
  // ============================================================

  function destroy() {
    const host = document.getElementById('immodata-host');
    if (host) host.remove();
    self.__immodata.ui._shadow = null;
    self.__immodata.ui._panel = null;
  }

  // ============================================================
  // EXPORT
  // ============================================================

  self.__immodata.ui.sideDashboard = {
    inject: inject,
    update: update,
    destroy: destroy
  };

})();
