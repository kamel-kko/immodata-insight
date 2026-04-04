/**
 * ImmoData — Scraper SeLoger
 *
 * Extrait les données d'une annonce ou d'une liste d'annonces
 * sur www.seloger.com en utilisant des sélecteurs CSS multi-fallback.
 */

(function () {
  'use strict';

  const log = globalThis.__immodata.createLogger('SCRAPER:SELOGER');
  const security = globalThis.__immodata.security;
  const ext = globalThis.__immodata.extractors;

  // Sélecteurs multi-fallback pour SeLoger
  // Si le site change son HTML, on peut mettre à jour ces listes
  // sans toucher au code d'extraction.
  const SEL = {
    prix: [
      "[data-testid='price']",
      ".Price__price",
      "span[class*='Price']",
      "meta[property='product:price:amount'][content]"
    ],
    surface: [
      "[data-testid='surface']",
      "span[class*='Surface']",
      "div[class*='surface']"
    ],
    dpe: [
      "[data-testid='dpe-letter']",
      "span[class*='Dpe']",
      ".energy-diagnostic span"
    ],
    ville: [
      "[data-testid='city']",
      "span[class*='City']",
      "meta[property='og:locality']"
    ],
    cp: [
      "[data-testid='postalcode']",
      "span[class*='PostalCode']"
    ],
    adresse: [
      "[data-testid='address']",
      "span[class*='Address']"
    ],
    description: [
      "[data-testid='description']",
      ".Description__content",
      "div[class*='Description']"
    ],
    type_bien: [
      "[data-testid='property-type']",
      "span[class*='PropertyType']"
    ],
    nb_pieces: [
      "[data-testid='rooms']",
      "span[class*='Rooms']"
    ],
    annee_construction: [
      "[data-testid='construction-year']",
      "span[class*='ConstructionYear']"
    ],
    page_annonce: [
      "[data-testid='classified-detail']",
      ".ClassifiedDetail",
      "div[class*='AdDetail']"
    ],
    card_liste: [
      "[data-testid='card-list']",
      ".ListCard",
      "div[class*='Card']"
    ]
  };

  /**
   * Extrait toutes les données d'une page annonce SeLoger.
   * Retourne un objet normalisé avec toutes les infos du bien.
   */
  function extractAnnonceData() {
    log.info('Extraction annonce SeLoger');

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

    // Extraire le CP depuis le champ CP ou depuis le champ ville
    const cp = ext.parsePostalCode(cpBrut) || ext.parsePostalCode(villeBrut);

    const data = {
      prix,
      surface,
      prix_m2: (prix && surface) ? Math.round(prix / surface) : null,
      dpe: ext.parseDpe(dpeBrut),
      ges: null, // SeLoger ne sépare pas toujours DPE et GES
      ville: villeBrut ? security.sanitizeText(villeBrut) : null,
      cp,
      adresse_brute: adresseBrut ? security.sanitizeText(adresseBrut) : null,
      type_bien: ext.parsePropertyType(typeBienBrut),
      nb_pieces: ext.parseRooms(nbPiecesBrut),
      annee_constr: ext.parseYear(anneeBrut),
      description,
      url_annonce: window.location.href,
      site: 'seloger',
      timestamp_scrape: Date.now(),
      flags_regex: ext.extractFlags(description)
    };

    log.info('Données extraites :', data);
    return data;
  }

  /**
   * Extrait les données minimales de chaque carte d'annonce sur une page liste.
   * Retourne un tableau d'objets { element, prix, surface, dpe, url }.
   */
  function extractCardsData() {
    log.info('Extraction cartes liste SeLoger');

    const cards = [];
    for (const selector of SEL.card_liste) {
      const elements = document.querySelectorAll(selector);
      if (elements.length > 0) {
        elements.forEach((el) => {
          const prixBrut = ext.extractText(SEL.prix, 'prix-card', el);
          const surfaceBrut = ext.extractText(SEL.surface, 'surface-card', el);
          const prix = ext.parsePrice(prixBrut);
          const surface = ext.parseSurface(surfaceBrut);

          // On ignore les cartes sans prix NI surface
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
        break; // On a trouvé des cartes, pas besoin d'essayer les autres sélecteurs
      }
    }

    log.info(`${cards.length} carte(s) extraite(s)`);
    return cards;
  }

  globalThis.__immodata.scrapers = globalThis.__immodata.scrapers || {};
  globalThis.__immodata.scrapers.seloger = { extractAnnonceData, extractCardsData };

})();
