# ImmoData --- Fiche Chrome Web Store

## Informations generales

- **Nom** : ImmoData
- **Version** : 1.0.0
- **Categorie** : Outils / Productivite
- **Langue** : Francais

---

## Description courte (132 caracteres max)

Enrichissez vos annonces immobilieres avec les donnees Open Data francaises : DVF, risques, quartier, DPE, investissement.

---

## Description longue

ImmoData enrichit automatiquement les annonces immobilieres sur SeLoger, LeBonCoin et Bien'ici avec des donnees publiques francaises.

### Ce que fait ImmoData

Quand vous consultez une annonce, un panneau lateral apparait avec :

**Onglet Finance**
- Prix au m2 compare a la mediane du quartier (donnees DVF)
- Score de negociation : quelle marge de negociation sur ce bien ?
- Frais de notaire estimes (neuf ou ancien)
- Cout total de possession : credit + charges + taxe fonciere + energie
- Suivi des baisses de prix sur les annonces revisitees

**Onglet Quartier**
- Transports en commun a proximite (arrets de bus, metro, tram)
- Commerces et services autour du bien
- Ecoles, colleges et lycees les plus proches avec distance
- Score de qualite de vie global

**Onglet Risques**
- Risques naturels : inondation, seisme, argile, radon
- Installations industrielles classees (ICPE) a proximite
- Lignes haute tension proches
- Zones de bruit (Plan d'Exposition au Bruit)
- Monuments historiques proteges

**Onglet Investissement**
- Estimation des travaux selon le DPE et l'annee de construction
- Simulation de plus-value a 5, 10 et 15 ans
- Score de liquidite : facilite de revente dans ce quartier
- Rentabilite locative estimee (loyers du marche vs cout total)

**Sur les pages liste**
- Survolez une annonce pour voir un apercu rapide : prix au m2, score de negociation et tendance du marche, sans quitter la liste.

### Respect de la vie privee

- Aucune donnee personnelle collectee
- Aucune information envoyee a des serveurs tiers
- Toutes les donnees restent dans votre navigateur (stockage local)
- Les statistiques d'utilisation sont 100% locales
- Cache effacable a tout moment depuis les parametres
- Seules les APIs Open Data publiques francaises sont interrogees

### Sources de donnees

- DVF (Demandes de Valeurs Foncieres) via OpenDataSoft
- Base Adresse Nationale (BAN) pour le geocodage
- Georisques.gouv.fr pour les risques naturels et industriels
- Data.education.gouv.fr pour les etablissements scolaires
- OpenStreetMap (Overpass) pour commerces et transports
- ADEME pour les diagnostics de performance energetique
- INSEE pour les donnees demographiques
- Data.culture.gouv.fr pour les monuments historiques
- RTE pour les lignes haute tension

### Parametres

- Toggle on/off pour desactiver temporairement l'extension
- Parametres de credit personnalisables (apport, duree)
- Cle API OpenRouteService optionnelle pour les isochrones
- Boutons pour vider le cache et les statistiques

---

## Captures d'ecran suggerees

1. Dashboard lateral sur une annonce SeLoger (onglet Finance)
2. QuickView au survol sur une page liste LeBonCoin
3. Onglet Risques avec carte des risques naturels
4. Popup extension avec parametres et statistiques
5. Onglet Investissement avec simulation de rentabilite

---

## Justification des permissions

| Permission | Raison |
|------------|--------|
| `storage` | Stocker le cache API, les parametres utilisateur et les statistiques locales |
| `alarms` | Nettoyer automatiquement le cache expire |
| `activeTab` | Acceder au contenu de l'onglet actif pour scraper les annonces |
| 11 host_permissions | Interroger les APIs Open Data francaises listees ci-dessus |
