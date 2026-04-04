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
    for (const selector of SEL.card_liste) {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        elements.forEach((el) => {
          const prixBrut = ext.extractText(SEL.prix, 'prix-card', el);
          const surfaceBrut = ext.extractText(SEL.surface, 'surface-card', el);
          const prix = ext.parsePrice(prixBrut);
          const surface = ext.parseSurface(surfaceBrut);

          if (prix === null && surface === null) return;

          const link = el.querySelector('a[href]');
          const dpeBrut = ext.extractText(SEL.dpe, 'dpe-card', el);

          cards.push({
            element: el,
            prix,
            surface,
            dpe: ext.parseDpe(dpeBrut),
            url: link ? link.href : null
          });
        });
        break;
      }
    }

    log.info(`${cards.length} carte(s) extraite(s)`);
    return cards;
  }

  self.__immodata.scrapers = self.__immodata.scrapers || {};
  self.__immodata.scrapers.leboncoin = { extractAnnonceData, extractCardsData };

})();
