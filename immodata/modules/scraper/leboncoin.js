/**
 * ImmoData — Scraper LeBonCoin
 *
 * Extrait les données d'une annonce ou d'une liste d'annonces
 * sur www.leboncoin.fr en utilisant des sélecteurs CSS multi-fallback.
 */

(function () {
  'use strict';

  const log = self.__immodata.createLogger('SCRAPER:LEBONCOIN');
  const security = self.__immodata.security;
  const ext = self.__immodata.extractors;

  // Selecteurs pour la PAGE ANNONCE (fiche detail)
  const SEL = {
    prix: [
      "[data-qa-id='adview_price']",
      "span[class*='rice']",
      "[itemprop='price']",
      "p[class*='rice']",
      "div[class*='rice'] span"
    ],
    surface: [
      "[data-qa-id='criteria_item_square']",
      "div[class*='surface']",
      "span[class*='surface']"
    ],
    dpe: [
      "[data-qa-id='criteria_item_energy_rate']",
      "div[class*='energy']",
      "span[class*='energy']"
    ],
    ville: [
      "[data-qa-id='adview_location_informations']",
      "[itemprop='addressLocality']",
      "div[data-test-id='ad_location'] span",
      "span[class*='location']",
      "div[class*='Location'] span",
      "a[href*='/recherche/'] span"
    ],
    cp: [
      "[itemprop='postalCode']",
      "[data-qa-id='adview_location_informations'] span:last-child",
      "div[data-test-id='ad_location']",
      "span[class*='location']",
      "div[class*='Location']"
    ],
    adresse: [
      "[itemprop='streetAddress']",
      "[data-qa-id='adview_location_informations']",
      "div[data-test-id='ad_location']",
      "div[class*='Location']",
      "span[class*='address']"
    ],
    description: [
      "[data-qa-id='adview_description_container']",
      "div[class*='description']"
    ],
    type_bien: [
      "[data-qa-id='criteria_item_real_estate_type']"
    ],
    nb_pieces: [
      "[data-qa-id='criteria_item_rooms']"
    ],
    annee_construction: [
      "[data-qa-id='criteria_item_square_land_surface']"
    ],
    page_annonce: [
      "[data-qa-id='adview_container']",
      "div[class*='adview']"
    ],
    card_liste: [
      "[data-qa-id='aditem_container']",
      "a[data-qa-id='aditem_container']",
      "li[data-qa-id='aditem_container']",
      "div[class*='aditem']",
      "article[class*='ad']"
    ]
  };

  // Selecteurs specifiques aux CARDS LISTE (plus souples)
  const SEL_CARD = {
    prix: [
      "[data-qa-id='price']",
      "span[class*='rice']",
      "p[class*='rice']",
      "[class*='Price']",
      "span[aria-label*='rix']"
    ],
    surface: [
      "span[class*='surface']",
      "[class*='Surface']",
      "span[class*='square']"
    ],
    dpe: [
      "span[class*='energy']",
      "[class*='Energy']",
      "[class*='dpe']"
    ],
    titre: [
      "[data-qa-id='title']",
      "p[class*='title']",
      "span[class*='title']",
      "h2",
      "h3"
    ]
  };

  function extractAnnonceData() {
    log.info('Extraction annonce LeBonCoin');

    const prixBrut = ext.extractText(SEL.prix, 'prix');
    const surfaceBrut = ext.extractText(SEL.surface, 'surface');
    const dpeBrut = ext.extractText(SEL.dpe, 'dpe');
    const villeBrut = ext.extractText(SEL.ville, 'ville');
    const cpBrut = ext.extractText(SEL.cp, 'cp');
    const adresseBrut = ext.extractText(SEL.adresse, 'adresse');
    const descriptionBrut = ext.extractText(SEL.description, 'description');
    const typeBienBrut = ext.extractText(SEL.type_bien, 'type_bien');
    const nbPiecesBrut = ext.extractText(SEL.nb_pieces, 'nb_pieces');
    const anneeBrut = ext.extractText(SEL.annee_construction, 'annee_construction');

    const prix = ext.parsePrice(prixBrut);
    const surface = ext.parseSurface(surfaceBrut);
    const description = descriptionBrut
      ? security.sanitizeText(descriptionBrut).slice(0, 2000)
      : null;

    const cp = ext.parsePostalCode(cpBrut) || ext.parsePostalCode(villeBrut);

    const data = {
      prix,
      surface,
      prix_m2: (prix && surface) ? Math.round(prix / surface) : null,
      dpe: ext.parseDpe(dpeBrut),
      ges: null,
      ville: villeBrut ? security.sanitizeText(villeBrut) : null,
      cp,
      adresse_brute: adresseBrut ? security.sanitizeText(adresseBrut) : null,
      type_bien: ext.parsePropertyType(typeBienBrut),
      nb_pieces: ext.parseRooms(nbPiecesBrut),
      annee_constr: ext.parseYear(anneeBrut),
      description,
      url_annonce: window.location.href,
      site: 'leboncoin',
      timestamp_scrape: Date.now(),
      flags_regex: ext.extractFlags(description)
    };

    log.info('Données extraites :', data);
    return data;
  }

  function extractCardsData() {
    log.info('Extraction cartes liste LeBonCoin');

    const cards = [];

    // Strategie 1 : selecteurs classiques data-qa-id
    for (const selector of SEL.card_liste) {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        log.info('Selecteur card OK : "' + selector + '" → ' + elements.length + ' card(s)');
        elements.forEach((el) => {
          // Essayer les selecteurs specifiques carte d'abord, puis fallback texte
          const prixBrut = ext.extractText(SEL_CARD.prix, 'prix-card', el);
          const surfaceBrut = ext.extractText(SEL_CARD.surface, 'surface-card', el);
          let prix = ext.parsePrice(prixBrut);
          let surface = ext.parseSurface(surfaceBrut);

          // Fallback regex sur le texte entier de la card
          if (prix === null) {
            prix = extractPrixFromText(el.textContent);
          }
          if (surface === null) {
            surface = extractSurfaceFromText(el.textContent);
          }

          if (prix === null && surface === null) return;

          const link = el.tagName === 'A' ? el : el.querySelector('a[href]');
          const dpeBrut = ext.extractText(SEL_CARD.dpe, 'dpe-card', el);
          const titreBrut = ext.extractText(SEL_CARD.titre, 'titre-card', el);

          cards.push({
            element: el,
            prix,
            surface,
            dpe: ext.parseDpe(dpeBrut),
            titre: titreBrut,
            url: link ? link.href : null
          });
        });
        break;
      }
    }

    // Strategie 2 : fallback robuste par liens d'annonces
    // Independant des classes CSS — fonctionne meme si LeBonCoin change son design
    if (cards.length === 0) {
      log.info('Selecteurs classiques echoues — fallback par liens annonces');
      const allLinks = document.querySelectorAll('a[href*="/ad/ventes_immobilieres/"], a[href*="/ad/locations/"], a[href*="/ad/colocations/"]');
      log.info('Liens annonces trouves : ' + allLinks.length);

      allLinks.forEach((link) => {
        // Eviter les doublons (meme href)
        if (cards.some(c => c.url === link.href)) return;

        const text = link.textContent || '';
        const prix = extractPrixFromText(text);
        const surface = extractSurfaceFromText(text);

        if (prix === null && surface === null) return;

        // Remonter au parent le plus proche qui ressemble a une card
        // (le lien lui-meme ou un parent avec du contenu)
        const cardEl = link.closest('article, li, div[class*="item"], div[class*="card"]') || link;

        cards.push({
          element: cardEl,
          prix,
          surface,
          dpe: null,
          titre: null,
          url: link.href
        });
      });
    }

    log.info(cards.length + ' carte(s) extraite(s)');
    return cards;
  }

  /**
   * Extrait un prix depuis le texte brut avec regex.
   * "299 000 €" → 299000
   */
  function extractPrixFromText(text) {
    if (!text) return null;
    const match = text.match(/(\d[\d\s.]*)\s*\u20ac/);
    if (!match) return null;
    const cleaned = match[1].replace(/[\s.]/g, '');
    const num = parseInt(cleaned, 10);
    return (num >= 1000 && num < 100000000) ? num : null;
  }

  /**
   * Extrait une surface depuis le texte brut avec regex.
   * "157m²" → 157, "65 m2" → 65
   */
  function extractSurfaceFromText(text) {
    if (!text) return null;
    const match = text.match(/(\d[\d,]*)\s*m[²2]/i);
    if (!match) return null;
    const num = parseFloat(match[1].replace(',', '.'));
    return (num > 0 && num < 10000) ? Math.round(num) : null;
  }

  self.__immodata.scrapers = self.__immodata.scrapers || {};
  self.__immodata.scrapers.leboncoin = { extractAnnonceData, extractCardsData };

})();
