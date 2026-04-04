/**
 * ImmoData — Scraper Bien'ici
 *
 * Extrait les données d'une annonce ou d'une liste d'annonces
 * sur www.bienici.com en utilisant des sélecteurs CSS multi-fallback.
 */

(function () {
  'use strict';

  const log = window.__immodata.createLogger('SCRAPER:BIENICI');
  const security = window.__immodata.security;
  const ext = window.__immodata.extractors;

  const SEL = {
    prix: [
      "span[class*='mainPrice']",
      "p[class*='price']",
      "[data-testid='price']"
    ],
    surface: [
      "span[class*='surface']",
      "[data-testid='surface']"
    ],
    dpe: [
      "div[class*='dpe']",
      "[data-testid='dpe']"
    ],
    ville: [
      "span[class*='city']",
      "[itemprop='addressLocality']"
    ],
    cp: [
      "span[class*='postalCode']",
      "[itemprop='postalCode']"
    ],
    adresse: [
      "div[class*='address']",
      "[itemprop='streetAddress']"
    ],
    description: [
      "div[class*='description']",
      "[data-testid='description']"
    ],
    type_bien: [
      "span[class*='propertyType']"
    ],
    nb_pieces: [
      "span[class*='rooms']"
    ],
    annee_construction: [
      "span[class*='constructionYear']"
    ],
    page_annonce: [
      "div[class*='detailPage']",
      "main[class*='adDetail']"
    ],
    card_liste: [
      "div[class*='listCard']",
      "article[class*='propertyCard']"
    ]
  };

  function extractAnnonceData() {
    log.info('Extraction annonce Bien\'ici');

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
      site: 'bienici',
      timestamp_scrape: Date.now(),
      flags_regex: ext.extractFlags(description)
    };

    log.info('Données extraites :', data);
    return data;
  }

  function extractCardsData() {
    log.info('Extraction cartes liste Bien\'ici');

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

  window.__immodata.scrapers = window.__immodata.scrapers || {};
  window.__immodata.scrapers.bienici = { extractAnnonceData, extractCardsData };

})();
