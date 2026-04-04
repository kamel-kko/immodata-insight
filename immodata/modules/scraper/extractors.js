/**
 * ImmoData — Fonctions d'extraction partagées
 *
 * Ce fichier contient les fonctions utilisées par les 3 scrapers
 * (SeLoger, LeBonCoin, Bien'ici) pour extraire et valider les données.
 *
 * Le principe du "multi-fallback" :
 * Pour chaque donnée (prix, surface, etc.), on a une liste de sélecteurs CSS
 * à essayer dans l'ordre. Si le premier ne trouve rien, on essaie le deuxième,
 * etc. C'est comme avoir plusieurs clés pour la même porte — si une ne marche
 * pas, on essaie la suivante.
 */

(function () {
  'use strict';

  const log = self.__immodata.createLogger('EXTRACTOR');
  const security = self.__immodata.security;

  // ============================================================
  // EXTRACTION PAR SÉLECTEURS MULTI-FALLBACK
  // ============================================================

  /**
   * Essaie une liste de sélecteurs CSS et retourne le texte du premier
   * élément trouvé. Si aucun ne fonctionne, retourne null.
   *
   * @param {string[]} selectors - Liste de sélecteurs CSS à essayer
   * @param {string} fieldName - Nom du champ (pour les logs)
   * @param {Element} [root=document] - Élément racine pour la recherche
   * @returns {string|null}
   */
  function extractText(selectors, fieldName, root) {
    root = root || document;
    for (const selector of selectors) {
      try {
        const el = root.querySelector(selector);
        if (el) {
          // Cas spécial : balise meta → lire l'attribut content
          if (el.tagName === 'META') {
            const content = el.getAttribute('content');
            if (content) return content.trim();
          }
          const text = el.textContent;
          if (text && text.trim()) return text.trim();
        }
      } catch {
        // Sélecteur invalide, on passe au suivant
      }
    }
    log.warn(`Aucun sélecteur n'a fonctionné pour "${fieldName}"`);
    return null;
  }

  // ============================================================
  // PARSERS — Nettoyage et conversion des données brutes
  // ============================================================

  /**
   * Extrait un prix en euros depuis un texte.
   * "350 000 €" → 350000, "199.500€" → 199500
   */
  function parsePrice(text) {
    if (!text) return null;
    // Retirer tout sauf chiffres, points, virgules, espaces
    const cleaned = text.replace(/[^\d.,\s]/g, '').trim();
    // Retirer les espaces et remplacer virgule par point
    const normalized = cleaned.replace(/\s/g, '').replace(',', '.');
    const num = security.sanitizeNumber(parseFloat(normalized));
    // Un prix immobilier est au moins 1000€
    if (num !== null && num >= 1000) return Math.round(num);
    return null;
  }

  /**
   * Extrait une surface en m² depuis un texte.
   * "65 m²" → 65, "120,5m2" → 121
   */
  function parseSurface(text) {
    if (!text) return null;
    const match = text.match(/([\d.,\s]+)\s*m/i);
    if (!match) return null;
    const cleaned = match[1].replace(/\s/g, '').replace(',', '.');
    const num = security.sanitizeNumber(parseFloat(cleaned));
    if (num !== null && num > 0 && num < 10000) return Math.round(num);
    return null;
  }

  /**
   * Extrait une lettre DPE (A-G) depuis un texte.
   * "Classe énergie : D" → "D"
   */
  function parseDpe(text) {
    if (!text) return null;
    const match = text.match(/\b([A-Ga-g])\b/);
    return match ? match[1].toUpperCase() : null;
  }

  /**
   * Extrait un code postal français depuis un texte.
   * "Paris 75011" → "75011"
   */
  function parsePostalCode(text) {
    if (!text) return null;
    const match = text.match(/\b(\d{5})\b/);
    if (match && security.validatePostalCode(match[1])) return match[1];
    return null;
  }

  /**
   * Extrait un nombre de pièces depuis un texte.
   * "3 pièces" → 3, "T4" → 4, "5p" → 5
   */
  function parseRooms(text) {
    if (!text) return null;
    // Formats courants : "3 pièces", "T4", "F3", "5p"
    const match = text.match(/(\d+)\s*(?:pi[eè]ces?|p\b)/i) ||
                  text.match(/[TF](\d+)/i) ||
                  text.match(/(\d+)/);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num > 0 && num < 30) return num;
    }
    return null;
  }

  /**
   * Extrait une année de construction depuis un texte.
   * "Construit en 1965" → 1965
   */
  function parseYear(text) {
    if (!text) return null;
    const match = text.match(/\b(1[89]\d{2}|20[0-2]\d)\b/);
    return match ? parseInt(match[1], 10) : null;
  }

  /**
   * Déduit le type de bien depuis un texte.
   * Retourne l'un des types normalisés : appartement, maison, terrain, parking, autre.
   */
  function parsePropertyType(text) {
    if (!text) return 'autre';
    const lower = text.toLowerCase();
    if (lower.includes('appartement') || lower.includes('studio') || lower.includes('loft')) return 'appartement';
    if (lower.includes('maison') || lower.includes('villa') || lower.includes('pavillon')) return 'maison';
    if (lower.includes('terrain')) return 'terrain';
    if (lower.includes('parking') || lower.includes('garage') || lower.includes('box')) return 'parking';
    return 'autre';
  }

  // ============================================================
  // FLAGS REGEX — Détecter des caractéristiques dans la description
  // ============================================================
  // On applique des expressions régulières sur le texte de la description
  // pour détecter des mots-clés (jardin, travaux, urgent, etc.)

  // Les regex du fichier selectors.json utilisent (?i) pour l'insensibilité
  // à la casse, mais en JS on utilise le flag "i" directement.
  const REGEX_FLAGS = {
    jardin: /\b(jardin|terrain\s+privatif|extérieur\s+privatif)\b/i,
    balcon: /\b(balcon|terrasse|loggia)\b/i,
    neuf_vefa: /\b(neuf|vefa|programme\s+neuf|livraison|promoteur|RT2020|RE2020)\b/i,
    travaux: /\b(travaux|à\s+rénover|à\s+rafraîchir|rénovation|remise\s+en\s+état|gros\s+travaux)\b/i,
    cave: /\b(cave|cellier|sous-sol\s+privatif)\b/i,
    parking: /\b(parking|garage|stationnement|box\s+fermé|place\s+de\s+parking)\b/i,
    ascenseur: /\b(ascenseur|élévateur)\b/i,
    gardien: /\b(gardien|concierge|interphone\s+vidéo)\b/i,
    piscine: /\b(piscine|jacuzzi|spa)\b/i,
    urgent: /\b(urgent|mutation|cause\s+départ|à\s+saisir|opportunité)\b/i,
    copropriete: /\b(copropriété|syndic|charges\s+de\s+copro)\b/i
  };

  const REGEX_TAXE_FONCIERE = /taxe\s+foncière[^\d]{0,20}(\d[\s\d]*\d?)\s*€?/i;

  /**
   * Applique toutes les regex sur une description pour détecter les flags.
   *
   * @param {string} description - Texte de la description
   * @returns {Object} Objet avec chaque flag à true/false + taxe_fonciere
   */
  function extractFlags(description) {
    if (!description) {
      return {
        jardin: false, balcon: false, neuf_vefa: false, travaux: false,
        cave: false, parking: false, ascenseur: false, gardien: false,
        piscine: false, urgent: false, copropriete: false, taxe_fonciere: null
      };
    }

    const flags = {};
    for (const [name, regex] of Object.entries(REGEX_FLAGS)) {
      flags[name] = regex.test(description);
    }

    // Cas spécial : taxe foncière → extraire le montant
    const taxeMatch = description.match(REGEX_TAXE_FONCIERE);
    if (taxeMatch) {
      const montant = parseInt(taxeMatch[1].replace(/\s/g, ''), 10);
      flags.taxe_fonciere = Number.isFinite(montant) ? montant : null;
    } else {
      flags.taxe_fonciere = null;
    }

    return flags;
  }

  // Exposer via globalThis
  self.__immodata.extractors = {
    extractText,
    parsePrice,
    parseSurface,
    parseDpe,
    parsePostalCode,
    parseRooms,
    parseYear,
    parsePropertyType,
    extractFlags
  };

})();
