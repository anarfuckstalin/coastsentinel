# Sources de données

Critère de sélection, appliqué sans exception : toute source retenue est
**(a)** libre d'accès, **(b)** produite ou validée par une institution de
référence internationale, **(c)** documentée par une publication évaluée par
les pairs ou un rapport de validation opérationnel, **(d)** mondiale ou
quasi mondiale.

Trois statuts dans les tableaux :

| Statut | Signification |
|---|---|
| **Intégrée** | branchée dans l'application, utilisée à chaque analyse |
| **Couche** | disponible en surimpression sur la carte |
| **Outil** | script fourni dans `backend/tools/`, hors application |

---

## 1. Forçage hydrodynamique

| Source | Producteur | Ce qu'elle apporte | Résolution | Clé | Statut |
|---|---|---|---|:--:|---|
| **Open-Meteo Marine API** | Open-Meteo, relais de ECMWF / GFS-Wave / MFWAM | Hs, Tp, direction, partition mer du vent / houle de fond, courant de surface, SST, niveau d'eau | horaire, J+7 | non | **Intégrée** |
| **Copernicus Marine Service** `GLOBAL_ANALYSISFORECAST_WAV_001_027` | UE / Mercator Ocean International | Vagues, qualité opérationnelle validée (QUID) | 1/12°, 3 h, J+5 | gratuite | Documentée |
| **Copernicus Marine** `GLOBAL_ANALYSISFORECAST_PHY_001_024` | idem | Niveau de mer `zos`, courants `uo`/`vo` | 1/12°, horaire | gratuite | Documentée |
| **Copernicus Marine** `GLOBAL_MULTIYEAR_WAV_001_032` | idem | Réanalyse de vagues 1980–présent | 1/5° | gratuite | Documentée |
| **ERA5** | ECMWF / Copernicus C3S | Réanalyse 1940–présent — climatologie et périodes de retour | 0,5° vagues, horaire | gratuite | **Outil** (`fetch_era5.py`) |
| **NOAA NCEP WAVEWATCH III** (NOMADS) | NOAA | Modèle de vagues mondial | 0,16°, 3 h | non | Documentée |
| **FES2022** | LEGOS / AVISO+ / CNES | Atlas de marée — prédiction en tout point | 1/16° | gratuite | Documentée |

> **Couverture inégale selon la variable.** Les vagues sont servies presque
> partout ; les **courants de surface et la température** sont modélisés à
> 0,08° (≈ 8 km) et n'ont donc pas de valeur sur les nœuds trop proches du
> rivage. C'est pourquoi ils ne sont pas cartographiés en couches : ils
> resteraient vides sur la majorité des nœuds côtiers, là où l'analyse porte.
> Ils restent disponibles dans l'analyse ponctuelle. Pour savoir ce que la
> source sert en un point précis :
>
> ```
> python -m coastsentinel.cli diag --lat 30.42 --lon -9.68
> ```
>
> Pour une couverture côtière complète des courants, passer à Copernicus
> Marine `GLOBAL_ANALYSISFORECAST_PHY_001_024` (1/12°, `uo`/`vo`).

> **Pourquoi Open-Meteo par défaut ?** Aucune clé, donc aucune friction pour
> démarrer, et le relais porte sur des modèles opérationnels reconnus. Pour une
> publication, basculer sur Copernicus Marine : le produit est versionné,
> citable et accompagné d'un rapport de validation. Les deux voies donnent le
> même moteur en aval.

---

## 2. Marégraphes et niveaux observés

| Source | Producteur | Ce qu'elle apporte | Statut |
|---|---|---|---|
| **Sea Level Station Monitoring Facility** | COI-UNESCO / VLIZ | ~950 marégraphes temps réel, pas de 1 min | Réseau intégré (positions indicatives) |
| **GLOSS** | COI-UNESCO / OMM | Réseau mondial de référence du niveau de la mer | Documentée |
| **PSMSL** | National Oceanography Centre (Royaume-Uni) | Séries mensuelles et annuelles, référence pour les tendances | Documentée |
| **UHSLC** | University of Hawai'i Sea Level Center | Séries horaires contrôlées | Documentée |
| **GESLA-3** | Consortium international | Base de niveaux extrêmes pour l'analyse fréquentielle | Documentée |

> Les 90 stations embarquées portent des **positions portuaires**, précises à
> environ un kilomètre : repérage et amorce d'analyse, jamais calcul. La liste
> officielle s'importe en CSV ou GeoJSON depuis le panneau des couches.

---

## 3. Bathymétrie et topographie

| Source | Producteur | Résolution | Statut |
|---|---|---|---|
| **GEBCO 2025 Grid** | GEBCO (COI-UNESCO + OHI) | 15″ (~450 m) | **Couche** (WMS) |
| **EMODnet Bathymetry** | UE / EMODnet | 1/16′ | **Couche** (WMS) |
| **NASA Blue Marble — relief et bathymétrie** | NASA | mondiale | **Couche** |
| **Copernicus DEM GLO-30** | UE / ESA | 30 m | Documentée |
| **ICESat-2 ATL03** | NASA | ~0,7 m le long de trace | **Outil** (`m3_shoreline.py`) |

---

## 4. Observation satellitaire

| Source | Producteur | Ce qu'elle apporte | Statut |
|---|---|---|---|
| **VIIRS NOAA-20 / MODIS Terra — vraies couleurs** | NASA EOSDIS GIBS | État de la mer et panaches visibles au jour le jour | **Couche** |
| **MODIS Aqua — chlorophylle a** | NASA EOSDIS GIBS | Proxy de turbidité — suivi du panache du Souss | **Couche** |
| **GHRSST L4 MUR — température et anomalie** | NASA JPL via GIBS | SST à 1 km, et son anomalie | **Couche** |
| **Sentinel-2 MSI L2A** | UE / ESA (Copernicus Data Space) | Trait de côte, bathymétrie dérivée | **Outil** (M3/M4) |
| **Sentinel-1 SAR GRD** | UE / ESA | Trait de côte tous temps | Documentée |
| **Landsat 5-9** | USGS / NASA | Trait de côte depuis 1984 | Documentée |

---

## 5. Navigation et repères

| Source | Producteur | Statut |
|---|---|---|
| **OpenSeaMap** — balisage maritime | Communauté OpenStreetMap | **Couche** |
| **CARTO basemaps** (dark matter, positron) | CARTO / OpenStreetMap | Fond de carte |
| **Esri World Imagery** | Esri, Maxar, Earthstar | Fond satellite |

---

## 6. Jeux de référence pour la calibration

| Source | Référence | Ce qu'elle apporte |
|---|---|---|
| **Pentes de l'avant-côte mondiales** | Athanasiou et al. (2019), *ESSD* 11, 1515-1529 | βf par transects de 1 km — **le paramètre le plus sensible du modèle** |
| **Shoreline Monitor** | Luijendijk et al. (2018), *Sci. Rep.* 8, 6641 | Taux de changement du trait de côte, transects de 500 m |
| **Niveaux extrêmes mondiaux** | Vousdoukas et al. (2018), *Nat. Commun.* 9, 2360 | Niveaux extrêmes probabilistes |
| **CoastSat** | Vos et al. (2019), *Env. Model. Softw.* 122 | Chaîne d'extraction du trait de côte, RMSE ~10 m |
| **S2Shores** | Almar et al. (2024), *Coastal Engineering* 189 | Bathymétrie par inversion de cinématique |

---

## Attribution

Les données restent soumises aux licences de leurs producteurs.

- **Copernicus** (Marine, C3S, Data Space, EMODnet) — attribution obligatoire,
  mention du produit et de sa version.
- **NASA / USGS** — domaine public, attribution recommandée.
- **GEBCO** — citer *GEBCO Compilation Group (2025) GEBCO Grid*.
- **COI-UNESCO / GLOSS / PSMSL** — citer le réseau et la station utilisée.
- **OpenStreetMap / OpenSeaMap** — ODbL, attribution obligatoire.

---

## Ce qui n'est volontairement pas utilisé

Les sources fermées, celles qui exigent un abonnement commercial, et celles
sans documentation de validation publique. Un système d'alerte destiné aux
littoraux qui n'en ont pas ne peut pas dépendre d'une donnée que ces pays ne
peuvent pas se payer. C'est une contrainte de conception, pas une préférence.
