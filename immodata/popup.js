/**
 * ImmoData -- Popup Extension
 *
 * Ce script gere la popup qui s'ouvre quand on clique sur l'icone
 * ImmoData dans la barre d'outils Chrome.
 *
 * Fonctionnalites :
 * - Toggle activation/pause de l'extension
 * - Affichage des statistiques (annonces, cache)
 * - Parametres credit (apport, duree)
 * - Cle API ORS (isochrones)
 * - Boutons effacer cache et stats
 * - Version depuis manifest.json
 * - Mention RGPD
 *
 * Tout est stocke dans chrome.storage.local.
 * Aucune donnee ne quitte le navigateur.
 */

(function () {
  'use strict';

  // ============================================================
  // REFERENCES DOM
  // ============================================================

  const toggleEnabled = document.getElementById('toggle-enabled');
  const toggleLabel = document.getElementById('toggle-label');

  const statAnnonces = document.getElementById('stat-annonces');
  const statListes = document.getElementById('stat-listes');
  const statCacheKeys = document.getElementById('stat-cache-keys');
  const statCacheSize = document.getElementById('stat-cache-size');

  const paramApport = document.getElementById('param-apport');
  const paramDuree = document.getElementById('param-duree');
  const paramSaved = document.getElementById('param-saved');

  const paramOrsKey = document.getElementById('param-ors-key');
  const btnShowOrs = document.getElementById('btn-show-ors');
  const orsSaved = document.getElementById('ors-saved');

  const btnClearCache = document.getElementById('btn-clear-cache');
  const btnClearStats = document.getElementById('btn-clear-stats');

  const popupVersion = document.getElementById('popup-version');

  // ============================================================
  // VERSION — Lire depuis le manifest
  // ============================================================

  const manifest = chrome.runtime.getManifest();
  popupVersion.textContent = manifest.version;

  // ============================================================
  // TOGGLE ACTIVATION
  // ============================================================
  // La cle "enabled" dans chrome.storage.local controle
  // si le content script s'execute ou non.
  // Par defaut (cle absente) = actif.

  chrome.storage.local.get('enabled', function (result) {
    // Si la cle n'existe pas, on considere que c'est actif
    var isEnabled = result.enabled !== false;
    toggleEnabled.checked = isEnabled;
    toggleLabel.textContent = isEnabled ? 'Actif' : 'Pause';
    toggleLabel.style.color = isEnabled ? '#22C55E' : '#EF4444';
  });

  toggleEnabled.addEventListener('change', function () {
    var isEnabled = toggleEnabled.checked;
    chrome.storage.local.set({ enabled: isEnabled });
    toggleLabel.textContent = isEnabled ? 'Actif' : 'Pause';
    toggleLabel.style.color = isEnabled ? '#22C55E' : '#EF4444';
  });

  // ============================================================
  // STATISTIQUES — Lire analytics + cache stats
  // ============================================================

  function loadStats() {
    // Analytics (impressions, clics, annonces)
    chrome.storage.local.get('immodata_analytics', function (result) {
      var analytics = result.immodata_analytics || {};
      statAnnonces.textContent = (analytics.annonces_analysees || 0).toLocaleString('fr-FR');
      statListes.textContent = (analytics.pages_liste_vues || 0).toLocaleString('fr-FR');
    });

    // Cache stats : compter les cles et estimer la taille
    chrome.storage.local.get(null, function (all) {
      var keys = Object.keys(all);
      // Exclure les cles de config (pas du cache)
      var cacheKeys = keys.filter(function (k) {
        return k !== 'enabled' && k !== 'immodata_analytics' &&
               k !== 'immodata_params' && k !== 'immodata_ors_key';
      });
      statCacheKeys.textContent = cacheKeys.length.toLocaleString('fr-FR');

      // Estimer la taille en KB
      var sizeStr = JSON.stringify(all);
      var sizeKb = Math.round(sizeStr.length / 1024);
      if (sizeKb >= 1024) {
        statCacheSize.textContent = (sizeKb / 1024).toFixed(1) + ' MB';
      } else {
        statCacheSize.textContent = sizeKb + ' KB';
      }
    });
  }

  loadStats();

  // ============================================================
  // PARAMETRES CREDIT — Apport + Duree
  // ============================================================
  // Ces parametres sont utilises par le module CALC_COUT_TOTAL
  // pour calculer la mensualite de credit.

  chrome.storage.local.get('immodata_params', function (result) {
    var params = result.immodata_params || {};
    if (params.apport_pct !== undefined) paramApport.value = params.apport_pct;
    if (params.duree_ans !== undefined) paramDuree.value = params.duree_ans;
  });

  function saveParams() {
    var params = {
      apport_pct: parseInt(paramApport.value, 10) || 10,
      duree_ans: parseInt(paramDuree.value, 10) || 25
    };
    chrome.storage.local.set({ immodata_params: params });
    // Feedback visuel
    paramSaved.classList.add('visible');
    setTimeout(function () { paramSaved.classList.remove('visible'); }, 1500);
  }

  paramApport.addEventListener('change', saveParams);
  paramDuree.addEventListener('change', saveParams);

  // ============================================================
  // CLE API ORS — OpenRouteService (isochrones)
  // ============================================================

  chrome.storage.local.get('immodata_ors_key', function (result) {
    if (result.immodata_ors_key) {
      paramOrsKey.value = result.immodata_ors_key;
    }
  });

  // Sauvegarder quand on quitte le champ
  paramOrsKey.addEventListener('change', function () {
    var key = paramOrsKey.value.trim();
    chrome.storage.local.set({ immodata_ors_key: key });
    orsSaved.classList.add('visible');
    setTimeout(function () { orsSaved.classList.remove('visible'); }, 1500);
  });

  // Toggle visibilite du champ mot de passe
  btnShowOrs.addEventListener('click', function () {
    if (paramOrsKey.type === 'password') {
      paramOrsKey.type = 'text';
    } else {
      paramOrsKey.type = 'password';
    }
  });

  // ============================================================
  // ACTIONS — Vider cache, effacer stats
  // ============================================================

  btnClearCache.addEventListener('click', function () {
    // On ne supprime que les cles de cache, pas les parametres
    chrome.storage.local.get(null, function (all) {
      var keysToRemove = Object.keys(all).filter(function (k) {
        return k !== 'enabled' && k !== 'immodata_analytics' &&
               k !== 'immodata_params' && k !== 'immodata_ors_key';
      });
      if (keysToRemove.length > 0) {
        chrome.storage.local.remove(keysToRemove, function () {
          btnClearCache.textContent = '\u2713 Cache vid\u00e9';
          btnClearCache.classList.add('done');
          loadStats();
          setTimeout(function () {
            btnClearCache.textContent = '\uD83D\uDDD1 Vider le cache';
            btnClearCache.classList.remove('done');
          }, 2000);
        });
      } else {
        btnClearCache.textContent = 'D\u00e9j\u00e0 vide';
        setTimeout(function () {
          btnClearCache.textContent = '\uD83D\uDDD1 Vider le cache';
        }, 1500);
      }
    });
  });

  btnClearStats.addEventListener('click', function () {
    chrome.storage.local.set({
      immodata_analytics: {
        annonces_analysees: 0,
        pages_liste_vues: 0,
        premiere_utilisation: null,
        derniere_utilisation: null,
        cta_impressions: {},
        cta_clics: {}
      }
    }, function () {
      btnClearStats.textContent = '\u2713 Stats effac\u00e9es';
      btnClearStats.classList.add('done');
      loadStats();
      setTimeout(function () {
        btnClearStats.textContent = '\uD83D\uDCCA Effacer stats';
        btnClearStats.classList.remove('done');
      }, 2000);
    });
  });

})();
