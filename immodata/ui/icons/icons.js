/**
 * ImmoData — Icônes SVG inline
 *
 * Toutes les icônes sont des chaînes SVG prêtes à être injectées
 * directement dans le HTML via innerHTML. Pas de fichiers externes,
 * pas de requêtes réseau — tout est dans ce fichier.
 *
 * Chaque icône fait 18x18px et utilise currentColor pour hériter
 * de la couleur du parent (var(--idi-text-2) par défaut).
 *
 * Utilisation dans le code :
 *   element.innerHTML = ICONS.euro;
 *
 * Comme c'est un content script (IIFE), on enregistre sur self.__immodata.
 */

(function () {
  'use strict';

  const s = 'xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';

  const ICONS = {
    // Finance
    euro: `<svg ${s}><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    trending_up: `<svg ${s}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
    trending_down: `<svg ${s}><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>`,
    calculator: `<svg ${s}><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="8" y2="10.01"/><line x1="12" y1="10" x2="12" y2="10.01"/><line x1="16" y1="10" x2="16" y2="10.01"/><line x1="8" y1="14" x2="8" y2="14.01"/><line x1="12" y1="14" x2="12" y2="14.01"/><line x1="16" y1="14" x2="16" y2="14.01"/><line x1="8" y1="18" x2="16" y2="18"/></svg>`,
    credit_card: `<svg ${s}><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>`,
    bar_chart: `<svg ${s}><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>`,
    percent: `<svg ${s}><line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></svg>`,

    // Quartier & proximité
    map_pin: `<svg ${s}><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
    school: `<svg ${s}><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 1 2 3 6 3s6-2 6-3v-5"/></svg>`,
    shopping_bag: `<svg ${s}><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>`,
    bus: `<svg ${s}><rect x="3" y="3" width="18" height="14" rx="2"/><line x1="3" y1="11" x2="21" y2="11"/><line x1="12" y1="3" x2="12" y2="11"/><circle cx="7.5" cy="20" r="1.5"/><circle cx="16.5" cy="20" r="1.5"/></svg>`,
    tree: `<svg ${s}><path d="M12 22v-7"/><path d="M9 9V5l3-3 3 3v4"/><path d="M5 15l7-7 7 7"/><path d="M3 19l9-9 9 9"/></svg>`,
    building: `<svg ${s}><rect x="4" y="2" width="16" height="20"/><line x1="9" y1="6" x2="9" y2="6.01"/><line x1="15" y1="6" x2="15" y2="6.01"/><line x1="9" y1="10" x2="9" y2="10.01"/><line x1="15" y1="10" x2="15" y2="10.01"/><line x1="9" y1="14" x2="9" y2="14.01"/><line x1="15" y1="14" x2="15" y2="14.01"/><path d="M9 22v-4h6v4"/></svg>`,

    // Risques
    alert_triangle: `<svg ${s}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    shield: `<svg ${s}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    zap: `<svg ${s}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
    volume: `<svg ${s}><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
    droplet: `<svg ${s}><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>`,

    // Investissement
    home: `<svg ${s}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    key: `<svg ${s}><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>`,
    tool: `<svg ${s}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
    clock: `<svg ${s}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    award: `<svg ${s}><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>`,

    // Énergie / DPE
    thermometer: `<svg ${s}><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>`,
    leaf: `<svg ${s}><path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 17 3.5s1.5 2.5-.5 6.5c3 0 4.5 1.5 4.5 1.5S19.4 18 11 20z"/><path d="M2 21c0-3 1.85-5.36 5.08-6"/></svg>`,
    monument: `<svg ${s}><path d="M2 20h20"/><path d="M5 20v-8l7-4 7 4v8"/><path d="M9 20v-4h6v4"/><path d="M12 4v4"/></svg>`,

    // UI
    chevron_right: `<svg ${s}><polyline points="9 18 15 12 9 6"/></svg>`,
    chevron_left: `<svg ${s}><polyline points="15 18 9 12 15 6"/></svg>`,
    x: `<svg ${s}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    minimize: `<svg ${s}><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`,
    maximize: `<svg ${s}><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`,
    info: `<svg ${s}><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    external_link: `<svg ${s}><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
    refresh: `<svg ${s}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`,
    star: `<svg ${s}><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`
  };

  self.__immodata = self.__immodata || {};
  self.__immodata.icons = ICONS;
})();
