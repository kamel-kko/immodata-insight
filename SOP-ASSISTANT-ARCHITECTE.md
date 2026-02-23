# SOP — Assistant Architecte SaaS

## Procédure Opérationnelle Standard (Standard Operating Procedure)

*Version : 1.0 — Date : 2026-02-23*

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Stack technologique](#2-stack-technologique)
3. [Architecture globale](#3-architecture-globale)
4. [Module 0 : Projets (socle commun)](#4-module-0--projets-socle-commun)
5. [Module 1 : Assistant ERP (sécurité + accessibilité)](#5-module-1--assistant-erp-sécurité--accessibilité)
6. [Module 2 : Assistant Urbanisme](#6-module-2--assistant-urbanisme)
7. [Base de données réglementaire](#7-base-de-données-réglementaire)
8. [Agent IA : fonctionnement](#8-agent-ia--fonctionnement)
9. [Communication inter-modules](#9-communication-inter-modules)
10. [Structure des dossiers du code](#10-structure-des-dossiers-du-code)
11. [Schéma de la base de données](#11-schéma-de-la-base-de-données)
12. [Plan de développement phase par phase](#12-plan-de-développement-phase-par-phase)
13. [Comptes et services à créer avant de coder](#13-comptes-et-services-à-créer-avant-de-coder)

---

## 1. Vue d'ensemble du projet

### Quoi ?
Une application web SaaS (Software as a Service) destinée aux architectes. L'application fonctionne comme un assistant intelligent qui aide les architectes dans leur travail quotidien : réglementation, calculs, notices, urbanisme.

### Pour qui ?
- Architectes indépendants
- Cabinets d'architecture
- Bureaux d'études

### Comment ?
L'application est organisée en **modules indépendants** qui partagent une base de données commune (les projets). Chaque module est spécialisé dans un domaine. Les modules peuvent s'enrichir mutuellement : par exemple, le module Urbanisme fournit l'adresse et le zonage, que le module ERP peut ensuite utiliser.

### Analogie
Imagine une boîte à outils d'architecte numérique. Chaque tiroir contient un outil différent (ERP, urbanisme, calculs...), mais tous les tiroirs partagent le même plan de travail (le projet en cours).

---

## 2. Stack technologique

| Couche | Technologie | Rôle | Coût |
|--------|-------------|------|------|
| **Frontend** (ce que l'utilisateur voit) | Next.js 14 (React inclus) | Interface web, pages, navigation | Gratuit |
| **Backend** (le moteur caché) | Next.js API Routes | Logique serveur dans le même projet | Gratuit |
| **Base de données + Auth + Fichiers** | Supabase | Tout-en-un : comptes utilisateurs, données, stockage PDF/plans | Gratuit jusqu'à 500 MB |
| **IA** | Kimi K2.5 (Moonshot AI) via Vercel AI SDK | Assistant intelligent, génération de notices, analyse | ~$0.60/M tokens input, ~$3.00/M tokens output |
| **Interface UI** | shadcn/ui + Tailwind CSS | Composants visuels (boutons, formulaires, tableaux) | Gratuit |
| **Paiements** (plus tard) | Stripe | Abonnements, facturation | Commission sur paiements |
| **Hébergement** (plus tard) | Vercel | Mise en ligne de l'application | Gratuit pour commencer |

### Pourquoi cette stack ?

- **Un seul langage** (JavaScript/TypeScript) pour tout le projet = moins de choses à apprendre.
- **Supabase tout-en-un** = un seul tableau de bord pour la base de données, l'authentification, et le stockage de fichiers. Pas besoin de jongler entre 3 services différents.
- **Kimi K2.5** = 4 à 5x moins cher que GPT-4o pour des performances comparables. Supporte le "function calling" (l'IA peut appeler des outils) et le mode "Agent" (l'IA peut enchaîner des actions).
- **Next.js** = React est inclus dedans. C'est React + le backend + la gestion des pages automatique. Pour un SaaS, c'est le standard en 2026.

---

## 3. Architecture globale

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NAVIGATEUR DE L'ARCHITECTE                       │
│                                                                     │
│  ┌────────────┐  ┌──────────────────────────────────────────────┐  │
│  │  SIDEBAR    │  │              MODULE ACTIF                    │  │
│  │             │  │                                              │  │
│  │  Projets    │  │  ┌──────────────┐  ┌─────────────────────┐ │  │
│  │  ERP        │  │  │  Formulaire  │  │   Chat IA / Résultat│ │  │
│  │  Urbanisme  │  │  │  + Outils    │  │                     │ │  │
│  │  (futurs    │  │  │              │  │  "L'ERP est de      │ │  │
│  │   modules)  │  │  │              │  │   type M, 3ème      │ │  │
│  │             │  │  │              │  │   catégorie..."     │ │  │
│  └────────────┘  │  └──────────────┘  └─────────────────────┘ │  │
│                   └──────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Requêtes HTTP (API)
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      NEXT.JS API ROUTES (backend)                   │
│                                                                     │
│  /api/projets      → CRUD projets                                  │
│  /api/erp/chat     → Chat IA sécurité/accessibilité                │
│  /api/erp/calcul   → Calculs effectif, UP, issues de secours      │
│  /api/erp/notice   → Génération notice sécurité/accessibilité      │
│  /api/urbanisme    → Chat IA urbanisme                             │
│  /api/urbanisme/gpu → Appels API Géoportail Urbanisme              │
│  /api/documents    → Upload/téléchargement de fichiers             │
└──────┬──────────────────┬──────────────────┬───────────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────────────────────┐
│  KIMI K2.5  │   │  SUPABASE   │   │  API GÉOPORTAIL URBANISME  │
│  (Moonshot) │   │             │   │  (IGN - api.gouv.fr)       │
│             │   │  - Auth     │   │                             │
│  Via Vercel │   │  - PostgreSQL│  │  - Zonage PLU/PLUi         │
│  AI SDK     │   │  - Storage  │   │  - Prescriptions           │
│             │   │             │   │  - Servitudes              │
│  Modes :    │   │  Tables :   │   │                             │
│  - Chat     │   │  - users    │   │  Endpoints :               │
│  - Agent    │   │  - projets  │   │  /api/gpu/zone-urba        │
│  - Function │   │  - reglements│  │  /api/gpu/prescription-*   │
│    calling  │   │  - documents │   │  /api/gpu/document         │
└─────────────┘   └─────────────┘   └─────────────────────────────┘
```

---

## 4. Module 0 : Projets (socle commun)

### Pourquoi "Module 0" ?
C'est le socle sur lequel tous les autres modules s'appuient. Chaque projet contient les informations de base (adresse, type, client) que les modules ERP et Urbanisme vont utiliser.

### Fonctionnalités
- Créer / modifier / supprimer un projet
- Informations de base : nom, adresse, type de bâtiment, maître d'ouvrage
- Upload de documents : plans, cahier des charges, devis d'entreprise
- Chaque module se rattache à un projet (référence)
- Tableau de bord : liste de tous les projets avec statut

### Données du projet
```
Projet :
  - id
  - nom               → "Rénovation Boulangerie Martin"
  - adresse            → "12 rue des Lilas, 75011 Paris"
  - code_postal
  - commune
  - code_insee         → utile pour l'API Géoportail
  - type_batiment      → "commerce", "habitation", "bureau", "ERP"
  - maitre_ouvrage     → nom du client
  - surface_totale     → m²
  - statut             → "en cours", "terminé", "en attente"
  - created_at
  - updated_at
```

---

## 5. Module 1 : Assistant ERP (sécurité + accessibilité)

Ce module est divisé en **deux sous-modules** qui partagent le même contexte projet.

---

### 5A. Sous-module Sécurité incendie

#### Sources réglementaires à intégrer dans la base de données

| Texte | Contenu | Usage |
|-------|---------|-------|
| Arrêté du 25 juin 1980 (modifié 2022) | Règlement de sécurité ERP catégories 1 à 4 | Règles générales, types, calcul effectif |
| Livre III (Articles PE 1 à PX 1) | Règlement ERP 5ème catégorie | Petits établissements |
| Code de la construction (Articles R143-2 à R143-17) | Définition et classement des ERP | Classification officielle |
| Arrêté du 7 février 2022 | Modifications récentes | Mises à jour |

#### Les 22 types d'ERP à stocker

| Lettre | Activité | Exemple |
|--------|----------|---------|
| J | Structures d'accueil pour personnes âgées/handicapées | EHPAD, foyer |
| L | Salles de spectacles, conférences, réunions | Cinéma, théâtre |
| M | Magasins de vente, centres commerciaux | Supermarché |
| N | Restaurants et débits de boissons | Restaurant, bar |
| O | Hôtels et pensions de famille | Hôtel |
| P | Salles de danse et salles de jeux | Discothèque |
| R | Établissements d'enseignement, colonies de vacances | École, université |
| S | Bibliothèques, centres de documentation | Bibliothèque |
| T | Salles d'expositions | Musée, galerie |
| U | Établissements sanitaires | Hôpital, clinique |
| V | Établissements de culte | Église, mosquée |
| W | Administrations, banques, bureaux | Mairie, banque |
| X | Établissements sportifs couverts | Gymnase, piscine |
| Y | Musées | Musée |
| PA | Établissements de plein air | Stade |
| CTS | Chapiteaux, tentes, structures | Cirque |
| SG | Structures gonflables | Structure gonflable |
| PS | Parcs de stationnement couverts | Parking |
| OA | Hôtels-restaurants d'altitude | Refuge |
| GA | Gares accessibles au public | Gare |
| EF | Établissements flottants | Péniche-restaurant |
| REF | Refuges de montagne | Refuge |

#### Les 5 catégories d'ERP

| Catégorie | Seuil d'effectif (public + personnel) | Groupe |
|-----------|---------------------------------------|--------|
| 1ère | Plus de 1 500 personnes | 1er groupe |
| 2ème | De 701 à 1 500 personnes | 1er groupe |
| 3ème | De 301 à 700 personnes | 1er groupe |
| 4ème | Jusqu'à 300 personnes (sauf 5ème cat.) | 1er groupe |
| 5ème | En dessous des seuils fixés par type | 2ème groupe |

*Note : le seuil de la 5ème catégorie varie selon le type d'ERP.*

#### Micro-modules de calcul (sécurité)

**Micro-module 1 : Calcul de l'effectif**
```
Entrées utilisateur :
  - Type d'ERP (lettre)
  - Surfaces des différentes zones (m²)
  - Nombre de places assises (si applicable)
  - Effectif du personnel

Logique :
  - Appliquer la densité réglementaire par type
    (ex: Type N restaurant = 1 pers/m² assis, 2 pers/m² debout)
  - Additionner les effectifs par zone
  - Ajouter le personnel pour l'effectif total

Sortie :
  - Effectif public
  - Effectif total (public + personnel)
  - Catégorie ERP déduite
```

**Micro-module 2 : Détermination du type et de la catégorie**
```
Entrées :
  - Activité principale (description libre ou choix dans liste)
  - Effectif calculé (depuis micro-module 1)

Logique :
  - Correspondance activité → type (lettre)
  - Effectif total → catégorie (1 à 5)
  - Si multi-activités → type principal + types secondaires

Sortie :
  - Type ERP (ex: "Type M — 3ème catégorie")
  - Réglementation applicable (1er ou 2ème groupe)
```

**Micro-module 3 : Calcul des dégagements (issues de secours et unités de passage)**
```
Entrées :
  - Effectif total
  - Catégorie ERP
  - Nombre de niveaux

Logique (règles issues de l'arrêté du 25 juin 1980) :
  - Nombre d'issues de secours :
    → Jusqu'à 19 personnes : 1 sortie
    → De 20 à 50 : 2 sorties
    → De 51 à 100 : 2 sorties (dont 1 de 2 UP)
    → Au-delà : calcul proportionnel

  - Unité de Passage (UP) :
    → 1 UP = 0,60 m de large
    → 2 UP = 1,40 m (pas 1,20 m — règle spéciale)
    → 3 UP et plus = n × 0,60 m

  - Nombre d'UP :
    → Effectif ÷ 100 = nombre d'UP (arrondi au supérieur)
    → Minimum 2 UP pour les ERP du 1er groupe

Sortie :
  - Nombre minimum d'issues de secours
  - Largeur minimale par issue
  - Nombre total d'UP
  - Largeur totale de dégagement requise
```

**Micro-module 4 : Génération de notice de sécurité**
```
Entrées :
  - Données du projet (depuis Module 0)
  - Résultats des micro-modules 1, 2, 3
  - Modèle de notice (fourni par l'utilisateur, stocké dans Supabase Storage)

Logique :
  - L'IA Kimi K2.5 reçoit toutes les données + le modèle
  - Elle génère une notice de sécurité complète
  - L'utilisateur peut affiner via le chat

Sortie :
  - Notice de sécurité au format PDF/Word
  - Possibilité de modifier et regénérer
```

---

### 5B. Sous-module Accessibilité

#### Sources réglementaires à intégrer

| Texte | Contenu |
|-------|---------|
| Loi du 11 février 2005 | Égalité des droits et des chances, accessibilité généralisée |
| Ordonnance du 26 septembre 2014 | Agendas d'Accessibilité Programmée (Ad'AP) |
| Décret du 28 mars 2017 | Accessibilité des ERP |
| Arrêté du 20 avril 2017 | Dispositions techniques accessibilité |
| Loi du 15 juillet 2024 | Accélération de l'accessibilité numérique et physique |
| Décret n°2024-217 du 8 mars 2024 | Renforcement des sanctions (jusqu'à 75 000€) |
| Normes NF EN 17210 | Bandes podotactiles, contrastes lumineux, acoustique |

#### Fonctionnalités

- **Chat IA réglementaire** : poser des questions sur l'accessibilité, obtenir des réponses sourcées
- **Checklist interactive** : vérifier point par point la conformité d'un ERP
  - Cheminement extérieur (pente max 5%, palier de repos tous les 10m)
  - Stationnement PMR (1 place par tranche de 50, largeur 3,30m)
  - Entrée du bâtiment (seuil max 2cm, espace de manoeuvre)
  - Circulations intérieures (largeur min 1,40m, 1,20m ponctuellement)
  - Sanitaires accessibles (espace de retournement 1,50m)
  - Escaliers (contremarches, nez de marche, main courante)
  - Signalétique (contraste 70%, hauteur, pictogrammes)
- **Génération de notice d'accessibilité** : pour autorisation de travaux / permis de construire
- **Registre Public d'Accessibilité** : génération du RPA (obligatoire depuis 2025)

---

## 6. Module 2 : Assistant Urbanisme

### Source de données : API Géoportail de l'Urbanisme (GPU)

L'API est fournie gratuitement par l'IGN (Institut Géographique National). Elle permet de récupérer toutes les données d'urbanisme à partir d'une localisation.

#### Endpoints disponibles

| Endpoint | Données retournées |
|----------|--------------------|
| `/api/gpu/municipality` | Infos commune (statut RNU, document applicable) |
| `/api/gpu/document` | Emprise du document d'urbanisme (PLU, PLUi, POS, carte communale) |
| `/api/gpu/zone-urba` | Zonage : zone U, AU, A, N avec règlement associé |
| `/api/gpu/secteur-cc` | Secteurs de carte communale |
| `/api/gpu/prescription-surf` | Prescriptions surfaciques (emplacements réservés, etc.) |
| `/api/gpu/prescription-lin` | Prescriptions linéaires (alignements, etc.) |
| `/api/gpu/prescription-pct` | Prescriptions ponctuelles |
| `/api/gpu/info-surf` | Informations surfaciques |
| `/api/gpu/info-lin` | Informations linéaires |
| `/api/gpu/info-pct` | Informations ponctuelles |
| `/api/gpu/acte-sup` | Servitudes d'Utilité Publique — actes |
| `/api/gpu/assiette-sup-s` | Servitudes — assiettes surfaciques |
| `/api/gpu/assiette-sup-l` | Servitudes — assiettes linéaires |
| `/api/gpu/assiette-sup-p` | Servitudes — assiettes ponctuelles |

**Paramètres principaux :**
- `geom` : Géométrie GeoJSON (Point, Polygon) en EPSG:4326 (coordonnées GPS)
- `partition` : Identifiant du document au format `DU_<INSEE>`

**Format de réponse :** GeoJSON FeatureCollection

### Flux de fonctionnement du module Urbanisme

```
L'architecte entre une adresse
        │
        ▼
[Géocodage : adresse → coordonnées GPS]
  (via API adresse.data.gouv.fr)
        │
        ▼
[Appel API GPU avec les coordonnées]
        │
        ├─→ /zone-urba        → Zone du PLU (U, AU, A, N)
        ├─→ /prescription-*   → Prescriptions applicables
        ├─→ /info-*           → Informations complémentaires
        └─→ /assiette-sup-*   → Servitudes
        │
        ▼
[Stockage des résultats en base de données]
  (lié au projet en cours)
        │
        ▼
[L'IA Kimi K2.5 reçoit toutes les données]
        │
        ▼
[Génération d'une note de synthèse urbanistique]
  - Zone applicable et règles
  - Hauteur max, emprise au sol, COS
  - Prescriptions et servitudes
  - Contraintes spéciales
        │
        ▼
[Chat IA disponible pour questions complémentaires]
  "Quelle est la hauteur max autorisée ?"
  "Puis-je construire un R+2 dans cette zone ?"
```

### Fonctionnalités détaillées

1. **Recherche par adresse** : l'utilisateur tape une adresse, le système récupère automatiquement toutes les données d'urbanisme
2. **Fiche de synthèse** : résumé clair de toute la réglementation applicable
3. **Chat IA** : questions/réponses sur le PLU avec sources réglementaires
4. **Note urbanistique** : document formel résumant la réglementation (exportable PDF)
5. **Historique** : chaque recherche est sauvegardée dans le projet

---

## 7. Base de données réglementaire

### Stratégie de constitution

La base de données réglementaire est le coeur du système. Elle alimente l'IA pour qu'elle puisse répondre avec des sources fiables.

#### Méthode de collecte

```
PHASE 1 — Collecte manuelle initiale (nous)
  │
  │  Sources officielles :
  │  - Légifrance (textes de loi)
  │  - Service-public.fr
  │  - ecologie.gouv.fr
  │  - Arrêtés du 25 juin 1980 (sécurité)
  │  - Loi du 11 février 2005 (accessibilité)
  │
  ▼
PHASE 2 — Structuration en base de données
  │
  │  Chaque article/règle est découpé en :
  │  - Domaine (sécurité, accessibilité, urbanisme)
  │  - Thème (effectif, dégagements, PMR, zonage...)
  │  - Texte de la règle
  │  - Source (référence du texte officiel)
  │  - Date de dernière mise à jour
  │
  ▼
PHASE 3 — Enrichissement par l'IA (agent)
  │
  │  L'agent IA peut :
  │  - Rechercher sur internet des mises à jour
  │  - Proposer des ajouts (validés par un humain)
  │  - Croiser les sources
  │
  ▼
PHASE 4 — Utilisation par les modules
  │
  │  Quand l'utilisateur pose une question :
  │  1. Recherche dans la base réglementaire locale
  │  2. L'IA formule une réponse basée sur ces données
  │  3. La source est toujours citée
```

#### Structure de la table `reglementations`

```
reglementations :
  - id
  - domaine          → "securite" | "accessibilite" | "urbanisme"
  - theme            → "effectif" | "degagements" | "pmr_cheminement" | "zonage"
  - sous_theme       → "type_M" | "categorie_3" | "pente_max"
  - titre            → "Calcul de l'effectif pour les magasins (Type M)"
  - contenu          → Le texte de la règle
  - source_reference → "Arrêté du 25 juin 1980, Article M2"
  - source_url       → "https://www.legifrance.gouv.fr/..."
  - date_texte       → Date du texte officiel
  - date_maj         → Dernière vérification
  - tags             → ["effectif", "type_M", "magasin", "surface"]
  - embedding        → Vecteur pour la recherche sémantique (pgvector)
```

### Recherche sémantique (RAG)

Pour que l'IA trouve les bonnes règles, on utilise une technique appelée **RAG** (Retrieval-Augmented Generation) :

```
Question de l'utilisateur :
"Combien de sorties de secours pour un restaurant de 150 places ?"
        │
        ▼
[1. Recherche sémantique dans la base réglementaire]
  → Trouve les règles sur les dégagements Type N
  → Trouve les règles sur le calcul d'effectif Type N
  → Trouve les règles sur les UP
        │
        ▼
[2. L'IA reçoit la question + les règles trouvées]
        │
        ▼
[3. L'IA formule une réponse avec les sources]
  → "Pour un restaurant de 150 places (Type N),
     l'effectif est de 150 personnes assises (1 pers/m²).
     Il faut 2 issues de secours minimum avec 2 UP soit 1,40m.
     Source : Arrêté du 25 juin 1980, Art. CO 38"
```

> **Analogie RAG :** C'est comme un avocat qui, avant de répondre à ta question, va d'abord consulter ses classeurs de jurisprudence pour trouver les articles pertinents, puis te fait une réponse en citant les textes.

---

## 8. Agent IA : fonctionnement

### Kimi K2.5 — Modes d'utilisation

| Mode | Usage dans l'application |
|------|--------------------------|
| **Chat** | Questions/réponses simples avec l'architecte |
| **Function Calling** | L'IA appelle les micro-modules de calcul automatiquement |
| **Agent** | L'IA enchaîne plusieurs actions (recherche + calcul + notice) |

### Exemple concret : flux Agent

```
Utilisateur : "Je dois ouvrir un restaurant de 200m² au 15 rue de la Paix, Paris.
               Dis-moi tout ce que je dois savoir."

L'agent IA va automatiquement :

  Étape 1 → Appeler l'API Géoportail avec l'adresse
           → Récupérer le zonage PLU, prescriptions, servitudes

  Étape 2 → Calculer l'effectif (200m² × densité Type N)
           → Déterminer la catégorie ERP

  Étape 3 → Calculer les dégagements nécessaires
           → Nombre d'issues, largeur, UP

  Étape 4 → Chercher les règles d'accessibilité applicables

  Étape 5 → Générer une synthèse complète :
           "Votre restaurant est en zone U du PLU de Paris.
            Type N, 3ème catégorie (200 personnes public + 15 personnel).
            Vous devez prévoir 2 issues de secours de 1,40m minimum.
            3 UP requises. Sanitaire PMR obligatoire.
            Hauteur max autorisée : R+5.
            Sources : [liens vers les textes]"
```

### Function Calling : les fonctions que l'IA peut appeler

```javascript
// L'IA peut appeler ces fonctions automatiquement :

calculerEffectif({ type: "N", surfaces: { assis: 150, debout: 50 } })
// → { effectif_public: 250, categorie: 3 }

determinerTypeERP({ activite: "restaurant" })
// → { type: "N", libelle: "Restaurants et débits de boissons" }

calculerDegagements({ effectif: 250, categorie: 3 })
// → { issues: 2, up_total: 3, largeur_min: "1,80m" }

rechercherReglementation({ domaine: "securite", theme: "degagements", type: "N" })
// → [{ titre: "...", contenu: "...", source: "..." }]

rechercherUrbanisme({ adresse: "15 rue de la Paix, 75002 Paris" })
// → { zone: "U", hauteur_max: "25m", prescriptions: [...] }
```

---

## 9. Communication inter-modules

### Principe : le projet comme hub central

Les modules ne communiquent pas directement entre eux. Ils lisent et écrivent tous dans le **même projet** en base de données. C'est la base de données qui fait le lien.

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   MODULE     │     │   BASE DE DONNÉES    │     │   MODULE     │
│   URBANISME  │────▶│                      │◀────│   ERP        │
│              │     │   Table PROJETS      │     │              │
│ Écrit :      │     │                      │     │ Lit :        │
│ - zonage     │     │  zonage_plu: "Ua"    │     │ - zonage     │
│ - hauteur    │     │  hauteur_max: "18m"  │     │ - adresse    │
│ - prescriptions    │  categorie_erp: "3"  │     │              │
│              │     │  effectif: 250       │     │ Écrit :      │
│              │     │  nb_issues: 2        │     │ - catégorie  │
│              │     │  type_erp: "N"       │     │ - effectif   │
└──────────────┘     └──────────────────────┘     └──────────────┘
                              │
                     ┌────────▼────────┐
                     │  FUTURS MODULES │
                     │                 │
                     │  Lisent les     │
                     │  données des    │
                     │  modules        │
                     │  précédents     │
                     └─────────────────┘
```

### Contexte IA partagé

Quand un module appelle l'IA, il lui fournit automatiquement le contexte des autres modules :

```
"Tu es un assistant ERP. Voici le contexte du projet en cours :
 - Adresse : 15 rue de la Paix, 75002 Paris
 - Zone PLU : Ua (fourni par le module Urbanisme)
 - Type de bâtiment : commerce
 - Surface : 200 m²
 Réponds à la question suivante en tenant compte de ce contexte."
```

---

## 10. Structure des dossiers du code

```
P:/PROJETS CODAGE/01-application-archi/
│
├── app/
│   ├── (auth)/                          ← Pages connexion/inscription
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   │
│   ├── (dashboard)/                     ← Interface principale (protégée)
│   │   ├── layout.tsx                   ← Sidebar + header communs
│   │   ├── page.tsx                     ← Tableau de bord d'accueil
│   │   │
│   │   ├── projets/                     ← MODULE 0 : Gestion projets
│   │   │   ├── page.tsx                 ← Liste des projets
│   │   │   ├── nouveau/page.tsx         ← Créer un projet
│   │   │   └── [id]/                    ← Projet spécifique
│   │   │       ├── page.tsx             ← Détails du projet
│   │   │       └── documents/page.tsx   ← Documents du projet
│   │   │
│   │   ├── erp/                         ← MODULE 1 : ERP
│   │   │   ├── page.tsx                 ← Accueil module ERP
│   │   │   ├── securite/
│   │   │   │   ├── page.tsx             ← Chat IA sécurité
│   │   │   │   ├── calcul/page.tsx      ← Calculateur effectif/UP
│   │   │   │   └── notice/page.tsx      ← Génération notice sécurité
│   │   │   └── accessibilite/
│   │   │       ├── page.tsx             ← Chat IA accessibilité
│   │   │       ├── checklist/page.tsx   ← Checklist conformité
│   │   │       └── notice/page.tsx      ← Génération notice accessibilité
│   │   │
│   │   └── urbanisme/                   ← MODULE 2 : Urbanisme
│   │       ├── page.tsx                 ← Recherche par adresse
│   │       ├── synthese/page.tsx        ← Fiche de synthèse
│   │       └── chat/page.tsx            ← Chat IA urbanisme
│   │
│   ├── api/                             ← Routes API (backend)
│   │   ├── auth/
│   │   │   └── callback/route.ts        ← Callback Supabase Auth
│   │   ├── projets/
│   │   │   ├── route.ts                 ← GET (liste), POST (créer)
│   │   │   └── [id]/route.ts            ← GET, PUT, DELETE un projet
│   │   ├── erp/
│   │   │   ├── chat/route.ts            ← Chat IA sécurité/accessibilité
│   │   │   ├── calcul/route.ts          ← API calcul effectif, UP, issues
│   │   │   └── notice/route.ts          ← API génération notice
│   │   ├── urbanisme/
│   │   │   ├── chat/route.ts            ← Chat IA urbanisme
│   │   │   ├── gpu/route.ts             ← Proxy API Géoportail
│   │   │   └── synthese/route.ts        ← Génération synthèse
│   │   ├── documents/
│   │   │   └── route.ts                 ← Upload/download fichiers
│   │   └── reglementations/
│   │       └── route.ts                 ← Recherche dans la base réglementaire
│   │
│   ├── layout.tsx                       ← Layout racine
│   └── page.tsx                         ← Landing page (page d'accueil publique)
│
├── components/
│   ├── ui/                              ← shadcn/ui (boutons, inputs, etc.)
│   ├── layout/
│   │   ├── Sidebar.tsx                  ← Navigation latérale
│   │   ├── Header.tsx                   ← En-tête avec profil utilisateur
│   │   └── ProjectSelector.tsx          ← Sélecteur de projet actif
│   ├── chat/
│   │   ├── ChatWindow.tsx               ← Fenêtre de chat IA réutilisable
│   │   ├── MessageList.tsx              ← Liste des messages
│   │   └── MessageInput.tsx             ← Champ de saisie
│   ├── erp/
│   │   ├── EffectifCalculator.tsx       ← Formulaire calcul effectif
│   │   ├── DegagementCalculator.tsx     ← Formulaire calcul UP/issues
│   │   ├── TypeSelector.tsx             ← Sélecteur type ERP
│   │   ├── AccessibiliteChecklist.tsx   ← Checklist interactive
│   │   └── NoticeGenerator.tsx          ← Interface génération notice
│   ├── urbanisme/
│   │   ├── AddressSearch.tsx            ← Barre de recherche adresse
│   │   ├── ZonageSummary.tsx            ← Affichage du zonage
│   │   └── SyntheseCard.tsx             ← Carte de synthèse
│   └── projets/
│       ├── ProjectCard.tsx              ← Carte projet dans la liste
│       ├── ProjectForm.tsx              ← Formulaire création/édition
│       └── DocumentUpload.tsx           ← Upload de documents
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts                    ← Client Supabase (navigateur)
│   │   ├── server.ts                    ← Client Supabase (serveur)
│   │   └── middleware.ts                ← Protection des routes
│   ├── ai/
│   │   ├── client.ts                    ← Config Kimi K2.5 via Vercel AI SDK
│   │   ├── tools.ts                     ← Fonctions que l'IA peut appeler
│   │   └── prompts/
│   │       ├── erp-securite.ts          ← Prompt système sécurité
│   │       ├── erp-accessibilite.ts     ← Prompt système accessibilité
│   │       └── urbanisme.ts             ← Prompt système urbanisme
│   ├── erp/
│   │   ├── calcul-effectif.ts           ← Logique calcul effectif
│   │   ├── calcul-degagements.ts        ← Logique calcul UP/issues
│   │   ├── types-erp.ts                 ← Données des 22 types
│   │   └── categories.ts               ← Seuils de catégories
│   ├── urbanisme/
│   │   ├── geocodage.ts                 ← Adresse → coordonnées GPS
│   │   └── gpu-client.ts               ← Client API Géoportail
│   └── utils/
│       └── pdf-export.ts               ← Export en PDF
│
├── supabase/
│   └── migrations/                      ← Scripts de création des tables
│       ├── 001_create_profiles.sql
│       ├── 002_create_projets.sql
│       ├── 003_create_reglementations.sql
│       ├── 004_create_conversations.sql
│       └── 005_create_documents.sql
│
├── public/                              ← Images, icônes
├── .env.local                           ← Variables d'environnement (JAMAIS sur GitHub)
├── next.config.js
├── tailwind.config.js
├── package.json
└── tsconfig.json
```

---

## 11. Schéma de la base de données

### Tables principales

```
┌──────────────────┐     ┌──────────────────────────┐
│     profiles      │     │        projets            │
├──────────────────┤     ├──────────────────────────┤
│ id (= auth.uid)  │──┐  │ id                        │
│ email             │  │  │ user_id ──────────────────│──┐
│ nom               │  │  │ nom                       │  │
│ prenom            │  │  │ adresse                   │  │
│ cabinet           │  │  │ code_postal               │  │
│ role              │  │  │ commune                   │  │
│ plan_abonnement   │  │  │ code_insee                │  │
│ created_at        │  │  │ coordonnees_gps (json)    │  │
└──────────────────┘  │  │ type_batiment              │  │
                      │  │ maitre_ouvrage             │  │
                      │  │ surface_totale             │  │
                      │  │                            │  │
                      │  │ -- Données module ERP --   │  │
                      │  │ type_erp                   │  │
                      │  │ categorie_erp              │  │
                      │  │ effectif_public             │  │
                      │  │ effectif_total              │  │
                      │  │ nb_issues_secours           │  │
                      │  │ nb_up                       │  │
                      │  │                            │  │
                      │  │ -- Données module Urba --  │  │
                      │  │ zonage_plu                 │  │
                      │  │ zone_libelle               │  │
                      │  │ hauteur_max                │  │
                      │  │ prescriptions (json)       │  │
                      │  │ servitudes (json)          │  │
                      │  │                            │  │
                      │  │ statut                     │  │
                      │  │ created_at                 │  │
                      │  │ updated_at                 │  │
                      │  └──────────────────────────┘  │
                      │                                 │
┌─────────────────────▼────────────────────┐            │
│          reglementations                  │            │
├──────────────────────────────────────────┤            │
│ id                                        │            │
│ domaine  ("securite"|"accessibilite"|    │            │
│           "urbanisme")                    │            │
│ theme                                     │            │
│ sous_theme                                │            │
│ titre                                     │            │
│ contenu                                   │            │
│ source_reference                          │            │
│ source_url                                │            │
│ date_texte                                │            │
│ date_maj                                  │            │
│ tags (text[])                             │            │
│ embedding (vector)  ← pour recherche IA  │            │
│ created_at                                │            │
└──────────────────────────────────────────┘            │
                                                         │
┌────────────────────────────────────────────────────────▼─┐
│                    conversations                          │
├──────────────────────────────────────────────────────────┤
│ id                                                        │
│ user_id                                                   │
│ projet_id (optionnel)                                    │
│ module     ("erp_securite"|"erp_accessibilite"|"urbanisme")│
│ messages (json)   ← historique du chat                   │
│ created_at                                                │
│ updated_at                                                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                     documents                             │
├──────────────────────────────────────────────────────────┤
│ id                                                        │
│ projet_id                                                │
│ user_id                                                   │
│ nom_fichier                                               │
│ type_fichier    ("plan"|"devis"|"notice"|"photo"|"autre")│
│ url_storage     ← lien Supabase Storage                  │
│ taille_octets                                             │
│ texte_extrait   ← si PDF, texte pour l'IA               │
│ created_at                                                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  notices_generees                          │
├──────────────────────────────────────────────────────────┤
│ id                                                        │
│ projet_id                                                │
│ user_id                                                   │
│ type_notice  ("securite"|"accessibilite"|"urbanisme")    │
│ contenu_html                                              │
│ contenu_pdf_url  ← lien Supabase Storage                 │
│ modele_utilise   ← quel template                         │
│ version                                                   │
│ created_at                                                │
│ updated_at                                                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  modeles_notices                           │
├──────────────────────────────────────────────────────────┤
│ id                                                        │
│ user_id                                                   │
│ nom            → "Notice sécurité AT standard"           │
│ type_notice    → "securite" | "accessibilite"            │
│ contenu        → Le modèle (HTML/texte)                  │
│ url_fichier    → ou fichier Word/PDF sur Storage         │
│ created_at                                                │
└──────────────────────────────────────────────────────────┘
```

---

## 12. Plan de développement phase par phase

### PHASE 1 — Fondations (semaines 1-2)

```
Objectif : avoir un squelette d'application fonctionnel

  1.1  Initialiser le projet Next.js
       → npx create-next-app@latest

  1.2  Configurer Supabase
       → Créer le projet sur supabase.com
       → Configurer l'authentification (email + mot de passe)
       → Créer les tables : profiles, projets

  1.3  Configurer Supabase Auth dans Next.js
       → Package @supabase/ssr
       → Middleware de protection des routes
       → Pages login / register

  1.4  Créer le layout du dashboard
       → Sidebar avec navigation
       → Header avec sélecteur de projet
       → Protection des pages (rediriger si non connecté)

  1.5  Module Projets (CRUD basique)
       → Page liste des projets
       → Formulaire de création
       → Page détail d'un projet

  LIVRABLE : Application avec connexion, création de projets, navigation
```

### PHASE 2 — Base réglementaire (semaines 3-4)

```
Objectif : constituer la base de connaissances ERP

  2.1  Créer la table reglementations avec extension pgvector
       → Migration SQL dans Supabase

  2.2  Collecter et saisir les réglementations sécurité
       → Types d'ERP (22 types avec règles de calcul)
       → Catégories (seuils)
       → Dégagements (UP, issues de secours)
       → Règles par type (articles spécifiques)

  2.3  Collecter et saisir les réglementations accessibilité
       → Cheminement, stationnement, entrée
       → Circulations, sanitaires, escaliers
       → Signalétique, éclairage

  2.4  Générer les embeddings (vecteurs) pour chaque règle
       → Permet la recherche sémantique par l'IA

  2.5  Créer l'API /api/reglementations
       → Recherche par domaine/thème
       → Recherche sémantique (par vecteur)

  LIVRABLE : Base réglementaire consultable et prête pour l'IA
```

### PHASE 3 — Module ERP Sécurité (semaines 5-7)

```
Objectif : module ERP sécurité fonctionnel

  3.1  Configurer Kimi K2.5 via Vercel AI SDK
       → lib/ai/client.ts
       → Premier prompt système sécurité

  3.2  Micro-module calcul effectif
       → Interface formulaire (type, surfaces)
       → Logique de calcul (lib/erp/calcul-effectif.ts)
       → Affichage résultat + catégorie déduite

  3.3  Micro-module calcul dégagements
       → Interface (effectif, catégorie, niveaux)
       → Logique (lib/erp/calcul-degagements.ts)
       → Résultat : issues, UP, largeurs

  3.4  Chat IA sécurité
       → Composant ChatWindow connecté à Kimi K2.5
       → Prompt système avec contexte du projet
       → RAG : recherche dans la base réglementaire avant de répondre
       → Sources citées dans les réponses

  3.5  Function calling
       → L'IA peut appeler les micro-modules automatiquement
       → L'IA peut chercher dans la base réglementaire

  LIVRABLE : Module ERP sécurité complet avec calculs et chat IA
```

### PHASE 4 — Notices sécurité + Accessibilité (semaines 8-10)

```
Objectif : génération de notices et module accessibilité

  4.1  Upload de modèles de notices
       → Table modeles_notices
       → Interface upload (Word/PDF)
       → Stockage Supabase Storage

  4.2  Génération de notice sécurité
       → L'IA reçoit : modèle + données projet + calculs
       → Génère une notice personnalisée
       → Export PDF

  4.3  Module accessibilité — Chat IA
       → Prompt système accessibilité
       → RAG sur la base réglementaire accessibilité
       → Contexte projet partagé

  4.4  Checklist interactive accessibilité
       → Liste des points de conformité
       → Cocher/décocher avec commentaires
       → Sauvegarde par projet

  4.5  Génération de notice accessibilité
       → Pour autorisation de travaux / permis de construire
       → Export PDF

  LIVRABLE : Module ERP complet (sécurité + accessibilité + notices)
```

### PHASE 5 — Module Urbanisme (semaines 11-14)

```
Objectif : module urbanisme fonctionnel

  5.1  Géocodage
       → API adresse.data.gouv.fr (adresse → GPS)
       → Composant AddressSearch avec autocomplétion

  5.2  Client API Géoportail
       → lib/urbanisme/gpu-client.ts
       → Appels zone-urba, prescriptions, servitudes
       → Proxy via /api/urbanisme/gpu

  5.3  Collecte automatique des données urbanistiques
       → L'utilisateur entre une adresse
       → Le système récupère toutes les données GPU
       → Stockage dans le projet

  5.4  Fiche de synthèse urbanistique
       → Affichage structuré des données
       → Zone, prescriptions, servitudes
       → Généré par l'IA à partir des données brutes

  5.5  Chat IA urbanisme
       → Prompt système urbanisme
       → Contexte : données GPU + réglementations
       → Questions/réponses avec sources

  5.6  Export note urbanistique PDF

  LIVRABLE : Module urbanisme complet avec recherche par adresse et chat IA
```

### PHASE 6 — Interconnexion et polissage (semaines 15-16)

```
Objectif : tout connecter et finaliser

  6.1  Contexte partagé entre modules
       → Le chat ERP connaît les données urbanisme
       → Le chat urbanisme connaît les données ERP
       → L'agent peut enchaîner les deux

  6.2  Upload de documents projet
       → Plans, devis, cahier des charges
       → Extraction de texte pour les PDF
       → L'IA peut interroger les documents

  6.3  Tableau de bord amélioré
       → Résumé du projet avec données de tous les modules
       → Accès rapide aux dernières conversations

  6.4  Tests et corrections
       → Vérifier tous les calculs ERP
       → Vérifier les réponses IA (sources, précision)
       → Corriger les bugs

  LIVRABLE : Application complète et fonctionnelle
```

---

## 13. Comptes et services à créer avant de coder

| Service | URL | Ce qu'il faut | Coût |
|---------|-----|---------------|------|
| **Supabase** | supabase.com | Email | Gratuit (plan Free : 500 MB) |
| **Moonshot AI** (Kimi K2.5) | platform.moonshot.ai | Email + carte bancaire | Pay-per-use (~$0.60/M tokens input) |
| **Vercel** (hébergement) | vercel.com | Compte GitHub | Gratuit (plan Hobby) |
| **Node.js** | nodejs.org | Installation locale | Gratuit |

### Variables d'environnement nécessaires (.env.local)

```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...

# Kimi K2.5 (Moonshot)
MOONSHOT_API_KEY=sk-...

# API Géoportail (pas de clé nécessaire — API publique)
# Les appels se font directement à https://apicarto.ign.fr/
```

---

## Résumé visuel du projet

```
┌─────────────────────────────────────────────────────────────┐
│                   ASSISTANT ARCHITECTE SaaS                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               MODULE 0 : PROJETS                     │    │
│  │  Nom | Adresse | Type | Documents | Statut          │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │ (données partagées)                 │
│           ┌────────────┼────────────┐                       │
│           │            │            │                        │
│  ┌────────▼───────┐   │   ┌────────▼───────┐               │
│  │  MODULE 1: ERP │   │   │ MODULE 2: URBA │               │
│  │                │   │   │                │               │
│  │ ┌──────────┐   │   │   │ Recherche      │               │
│  │ │ Sécurité │   │   │   │ adresse        │               │
│  │ │ -Effectif│   │   │   │     │          │               │
│  │ │ -Type    │   │   │   │     ▼          │               │
│  │ │ -UP      │   │   │   │ API Géoportail │               │
│  │ │ -Issues  │   │   │   │     │          │               │
│  │ │ -Notice  │   │   │   │     ▼          │               │
│  │ └──────────┘   │   │   │ Synthèse PLU   │               │
│  │ ┌──────────┐   │   │   │ Chat IA        │               │
│  │ │ Accessi. │   │   │   │ Note PDF       │               │
│  │ │ -Checklist│  │   │   └────────────────┘               │
│  │ │ -Chat IA │   │   │                                     │
│  │ │ -Notice  │   │   │   ┌────────────────┐               │
│  │ └──────────┘   │   │   │ FUTURS MODULES │               │
│  └────────────────┘   │   │ Métrés, Plans, │               │
│                        │   │ Matériaux...   │               │
│                        │   └────────────────┘               │
│                        │                                     │
│              ┌─────────▼──────────┐                         │
│              │   BASE SUPABASE    │                         │
│              │  + Réglementations │                         │
│              │  + Documents       │                         │
│              │  + Kimi K2.5 (IA)  │                         │
│              └────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

*Ce SOP sera mis à jour au fur et à mesure de l'avancement du projet.*
