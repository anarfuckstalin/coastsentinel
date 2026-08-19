# CoastSentinel — Système d'Alerte Côtière Multi-échelle (SACM)

### Note de conception scientifique et technique

**Contexte de recherche** — *Modélisation topo-bathymétrique et hydrodynamique sédimentaire*

**Auteur** — Amine Bouhadi, Université Abdelmalek Essaâdi
**Version** — 0.1 (document de conception, août 2026)
**Portée** — Système générique mondial, calibré et validé en premier lieu sur la baie d'Agadir (30,42° N ; 9,62° O)

---

## 1. Problème et positionnement scientifique

### 1.1 Le constat

Les littoraux concentrent aujourd'hui l'essentiel de l'exposition humaine aux aléas hydro-sédimentaires : submersion de tempête, érosion chronique, houle dangereuse, ensablement des ouvrages portuaires. Or les systèmes d'alerte côtière opérationnels présentent trois biais structurels :

1. **Un biais géographique.** Les systèmes matures (NOAA/CO-OPS aux États-Unis, CEMS en Europe — ECFAS n'ayant été qu'un projet de recherche H2020 achevé en 2022 —, BOM en Australie) couvrent des pays à haut revenu. La majorité des littoraux africains, sud-américains et insulaires ne dispose d'aucun service d'alerte côtière opérationnel, alors que ce sont eux qui cumulent forte exposition et faible capacité d'adaptation.
2. **Un biais d'échelle.** Les systèmes existants traitent presque exclusivement l'événementiel (l'horizon J+3 à J+5). L'érosion chronique et l'évolution bathymétrique — qui opèrent au pas saisonnier à décennal — ne déclenchent aucune alerte, alors qu'elles conditionnent la vulnérabilité de l'événement suivant : une plage qui a perdu 15 m en trois ans subit une tempête décennale comme une tempête centennale.
3. **Un biais de calibration.** Les seuils d'alerte sont presque toujours absolus (« alerte si Hs > 4 m »), donc non transposables. Un Hs de 4 m est un régime hivernal ordinaire à Agadir et un événement extrême dans le golfe de Gabès.

### 1.2 La proposition

CoastSentinel est un système d'alerte **multi-aléas**, **multi-échelles** et **mondialement transposable**, construit exclusivement sur des données ouvertes à crédibilité scientifique internationale (Copernicus, ECMWF, NASA/NOAA, UNESCO-COI, GEBCO).

Deux choix de conception fondent sa transposabilité :

> **Choix n° 1 — Seuils relatifs, pas absolus.**
> Les seuils sont dérivés de la **climatologie locale** reconstruite en tout point du globe à partir des réanalyses (ERA5, 1940–présent ; CMEMS WAV reanalysis). Un niveau d'alerte n'est pas « Hs > 4 m » mais « Hs au-delà du 99ᵉ percentile local » ou « période de retour ≥ 5 ans ». Le système s'auto-calibre partout où une réanalyse existe — c'est-à-dire partout.

> **Choix n° 2 — Le couplage des échelles est l'alerte.**
> L'état morphologique lent (position du trait de côte, pente d'estran, budget sédimentaire) n'est pas un produit annexe : il **module** le seuil événementiel. C'est ce couplage qui traduit directement la problématique « multi-approches sous différentes échelles spatio-temporelles » en objet opérationnel.

---

## 2. Architecture multi-échelles

Le système s'organise en quatre modules, chacun opérant à une échelle spatio-temporelle distincte, et un cinquième module de couplage qui les intègre.

| Module | Aléa surveillé | Pas de temps | Horizon | Résolution spatiale | Latence | Régime |
|---|---|---|---|---|---|---|
| **M1 — SUBMERSION** | Niveau d'eau total (TWL) | horaire | J+5 | 1/12° (~8 km) → profil ponctuel | 6 h | Événementiel |
| **M2 — SÉCURITÉ** | Houle dangereuse, courants d'arrachement | horaire | J+5 | 1/12° | 6 h | Événementiel |
| **M3 — TRAIT DE CÔTE** | Érosion / accrétion | 5–10 j (image) → tendance | Diagnostic | 10 m (Sentinel-2) | 3–7 j | Chronique |
| **M4 — BATHYMÉTRIE** | Ensablement, budget sédimentaire | mensuel–saisonnier | Diagnostic | 10–100 m | 1–3 mois | Structurel |
| **M5 — COUPLAGE** | Vulnérabilité intégrée | à chaque cycle | — | profil (transect) | — | Transversal |

### 2.1 Schéma de flux

```

                    ┌──────────────────── SOURCES OUVERTES ────────────────────┐
                    │                                                          │
  CMEMS WAV/PHY ────┤  Hs, Tp, Dir, zos, courants (prévision J+5, 3 h)         │
  ERA5 / CMEMS-REA ─┤  Hindcast 1940–présent (climatologie, périodes retour)   │
  FES2022 / TPXO ───┤  Marée astronomique prédite (tout point du globe)        │
  IOC-COI / GESLA ──┤  Marégraphes temps réel (validation, surcote observée)   │
  Sentinel-2 / L8-9 ┤  Réflectance 10–30 m (trait de côte, SDB)                │
  Sentinel-1 SAR ───┤  Trait de côte tous temps (anti-nuage)                   │
  ICESat-2 ATL03 ───┤  Bathymétrie lidar photon (calibration SDB)              │
  GEBCO / EMODnet ──┤  Bathymétrie de référence                                │
  COP-DEM GLO-30 ───┤  Topographie littorale, altitude de crête                │
                    └──────────────────────────┬───────────────────────────────┘
                                               │
              ┌────────────────┬───────────────┼───────────────┬────────────────┐
              ▼                ▼               ▼               ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌───────────┐   ┌───────────┐   ┌────────────┐
        │    M1    │    │    M2    │    │    M3     │   │    M4     │   │  Climato   │
        │ TWL/     │    │ Sécurité │    │  Trait    │   │   SDB /   │   │  locale    │
        │ Runup    │    │ baignade │    │ de côte   │   │  budget   │   │ (P95…P99,  │
        │          │    │          │    │           │   │           │   │  GEV/GPD)  │
        └────┬─────┘    └────┬─────┘    └─────┬─────┘   └─────┬─────┘   └─────┬──────┘
             │               │                │               │               │
             └───────────────┴────────┬───────┴───────────────┴───────────────┘
                                      ▼
                            ┌───────────────────┐
                            │  M5 — COUPLAGE    │  pente βf, marge de plage,
                            │  Vulnérabilité    │  tendance pluriannuelle
                            └─────────┬─────────┘
                                      ▼
                            ┌───────────────────┐
                            │  MOTEUR D'ALERTE  │  Vert / Jaune / Orange / Rouge
                            └─────────┬─────────┘
                                      ▼
              ┌──────────────┬────────┴────────┬──────────────┐
              ▼              ▼                 ▼              ▼
         CAP 1.2 XML    API REST/JSON     Tableau de bord   WIS2 / MQTT
         (OASIS)        (FAIR, STAC)      HTML             (WMO)
```

---

## 3. Sources de données : justification de la crédibilité

Le critère de sélection est explicite : **toute source retenue doit être (a) libre d'accès, (b) produite ou validée par une institution de référence internationale, (c) documentée par une publication évaluée par les pairs ou un rapport de validation opérationnel, (d) mondiale ou quasi-mondiale.**

### 3.1 Forçages hydrodynamiques

| Source | Produit / identifiant | Couverture | Résolution | Statut |
|---|---|---|---|---|
| **Copernicus Marine (CMEMS)** | `GLOBAL_ANALYSISFORECAST_WAV_001_027` | Mondiale | 1/12°, horaire, prévision 10 j | Opérationnel, validé QUID |
| **Copernicus Marine** | `GLOBAL_ANALYSISFORECAST_PHY_001_024` (zos, uo, vo) | Mondiale | 1/12°, horaire | Opérationnel |
| **Copernicus Marine** | `GLOBAL_MULTIYEAR_WAV_001_032` (réanalyse vagues) | Mondiale | 1/5°, 1980– | Réanalyse |
| **ECMWF / C3S** | ERA5 (`swh`, `mwp`, `mwd`, `msl`, `u10`, `v10`) | Mondiale | 0,36° (vagues, ~40 km) ; 0,28° (atmosphère), horaire, 1940– | Réanalyse de référence |
| **NOAA NCEP** | GFS-Wave / WAVEWATCH III (NOMADS) | Mondiale | 0,25°, 3 h | Opérationnel, sans clé |
| **AVISO+ / LEGOS** | FES2022 (atlas de marée) | Mondiale | 1/16° | Référence marée |
| **UNESCO-COI** | Sea Level Station Monitoring Facility | ~950 stations | 1 min | Temps réel |
| **GLOSS / PSMSL / UHSLC / GESLA-3** | Marégraphes historiques | Mondiale | horaire–mensuel | Référence validation |
| **Open-Meteo Marine API** | Vagues (relais ECMWF/GFS/Météo-France) | Mondiale | horaire, J+7 | Sans clé — utile prototypage |

> **Note pratique** — CMEMS et le service COI exigent un compte gratuit ; Open-Meteo et NOMADS n'exigent aucune clé. Le prototype fourni permet les deux voies : `--source openmeteo` (démarrage immédiat) ou `--source cmems` (qualité opérationnelle, recommandé pour la publication).

### 3.2 Observation satellitaire du trait de côte et de la bathymétrie

| Source | Usage | Résolution | Accès |
|---|---|---|---|
| **Sentinel-2 MSI L2A** (Copernicus Data Space) | Trait de côte, SDB | 10 m, 5 j | STAC, libre |
| **Landsat 5/7/8/9** (USGS) | Trait de côte 1984–présent | 30 m, 16 j | STAC / GEE, libre |
| **Sentinel-1 SAR GRD** | Trait de côte tous temps | 10 m, 6–12 j | STAC, libre |
| **ICESat-2 ATL03** | Bathymétrie lidar photon (calibration SDB sans levé) | ~0,7 m le long de trace | NSIDC, libre |
| **GEBCO 2025 Grid** | Bathymétrie de référence mondiale | 15″ (~450 m) | libre |
| **EMODnet Bathymetry** | Bathymétrie régionale haute résolution | 1/16′ | libre (Europe + Med.) |
| **Copernicus DEM GLO-30** | Topographie, altitude de crête de plage | 30 m | libre |
| **Athanasiou et al. (2019), ESSD** | Pentes de l'avant-côte mondiales | transects 1 km | libre — **clé pour la transposabilité** |
| **Luijendijk et al. (2018), Sci. Rep.** | Taux de changement du trait de côte mondiaux | transects 500 m | libre |

### 3.3 Chaînes de traitement ouvertes réutilisables

- **CoastSat** (Vos et al., 2019, *Env. Model. Softw.*) — extraction du trait de côte sub-pixel depuis Sentinel-2/Landsat via Google Earth Engine ; précision publiée ~10 m (RMSE). Base du module M3.
- **S2Shores** (CNES) — bathymétrie par inversion de la cinématique des vagues sur Sentinel-2 ; produit mondial 1 km publié dans *Scientific Data* (2025). Base du module M4, voie « inversion ».
- **XBeach**, **SWAN**, **SCHISM**, **TELEMAC**, **Delft3D-FM** — modèles morphodynamiques et de propagation open source pour la descente d'échelle nearshore (voir § 7).
- **pyTMD / pyfes** — prédiction de marée depuis FES2022/TPXO en Python.
- **pyextremes** — ajustement GEV/GPD pour les périodes de retour.

---

## 4. Formulation physique du moteur d'alerte

### 4.1 Module M1 — Niveau d'eau total et submersion

Le niveau d'eau total instantané au rivage se décompose en :

```math
\mathrm{TWL}(t) = \underbrace{\eta_{\text{marée}}(t)}_{\text{astronomique}} + \underbrace{\eta_{\text{surcote}}(t)}_{\text{météorologique}} + \underbrace{R_{2\%}(t)}_{\text{jet de rive}} + \underbrace{\eta_{\text{MSL}}}_{\text{tendance eustatique}}
```

**Jet de rive — paramétrisation de Stockdon et al. (2006)**, référence la plus largement validée pour les plages sableuses ouvertes :

Longueur d'onde au large : $`L_0 = \dfrac{g T_p^2}{2\pi}`$

Nombre d'Iribarren : $`\xi_0 = \dfrac{\beta_f}{\sqrt{H_0/L_0}}`$

Régime intermédiaire à réfléchissant ($`\xi_0 \geq 0{,}3`$) :

```math
R_{2\%} = 1{,}1 \left[ 0{,}35\,\beta_f \sqrt{H_0 L_0} \;+\; \frac{\sqrt{H_0 L_0 \left(0{,}563\,\beta_f^2 + 0{,}004\right)}}{2} \right]
```

où le premier terme est le *setup* $`\langle\eta\rangle`$ et le second la demi-amplitude du *swash* $`S/2`$.

Régime dissipatif ($`\xi_0 < 0{,}3`$) :

```math
R_{2\%} = 0{,}043 \sqrt{H_0 L_0}
```

**Paramètre critique : $`\beta_f`$**, la pente de l'estran. C'est la principale source d'incertitude en déploiement mondial. Stratégie en cascade :
1. Mesure locale (levé DGPS/drone) — cas d'Agadir ;
2. Extraction depuis Copernicus DEM GLO-30 + SDB ;
3. Défaut mondial : Athanasiou et al. (2019) ;
4. Valeur générique 0,05 si rien d'autre — signalée explicitement dans les métadonnées de l'alerte.

**Régimes d'impact de tempête — Sallenger (2000)**, qui structure la sévérité :

| Régime | Condition | Signification |
|---|---|---|
| *Swash* | $`R_{high} < D_{low}`$ | Jet de rive confiné à l'estran |
| *Collision* | $`D_{low} \le R_{high} < D_{high}`$ | Attaque du pied de dune / berme → érosion |
| *Overwash* | $`R_{high} \ge D_{high}`$ | Franchissement, transport vers l'arrière-plage |
| *Inundation* | $`R_{low} \ge D_{high}`$ | Submersion continue |

avec $`R_{high} = \eta_{\text{marée}} + \eta_{\text{surcote}} + R_{2\%}`$ le niveau atteint par le jet de rive, $`R_{low} = \eta_{\text{marée}} + \eta_{\text{surcote}}`$ le niveau d'eau statique (sans jet de rive), $`D_{low}`$ le pied de dune/berme et $`D_{high}`$ la crête (extraits du MNT).

### 4.2 Module M2 — Houle dangereuse

Flux d'énergie de la houle (puissance par mètre de crête, eau profonde) :

```math
P = \frac{\rho g^2}{64\pi} H_s^2 T_e \quad [\mathrm{W\,m^{-1}}]
```

où $`T_e`$ est la période énergétique. Les produits de vagues (ERA5 `mwp`, CMEMS) fournissant la période pic $`T_p`$, on applique la conversion usuelle $`T_e \approx 0{,}9\,T_p`$ (spectre JONSWAP) ; l'omettre surestime $`P`$ d'environ 11 %.

Indice de puissance de tempête (Dolan & Davis, 1992) : $`\;SPI = H_s^2 \cdot D\;`$ avec $`D`$ la durée en heures au-dessus du seuil, permettant de classer les tempêtes en cinq classes.

Proxy de courants d'arrachement : combinaison d'un Hs modéré-fort, d'une incidence quasi-normale et d'une morphologie à barre/baïne — indicateur qualitatif tant qu'aucune donnée morphologique haute résolution n'est disponible ; **à ne pas présenter comme une prévision déterministe**.

### 4.3 Module M3 — Érosion et trait de côte

Chaîne : Sentinel-2/Landsat → indice d'eau (MNDWI/AWEI) → seuillage Otsu → contour sub-pixel → correction de marée (projection sur $`\beta_f`$ à un datum commun) → position le long de transects perpendiculaires.

Indicateurs par transect :
- **EPR** (End Point Rate) : $`(P_{t_2} - P_{t_1})/(t_2 - t_1)`$ ;
- **LRR** (Linear Regression Rate) avec intervalle de confiance à 95 % ;
- **Position résiduelle** $`\Delta P`$ = écart à la tendance saisonnière ajustée → détecte l'événement érosif ;
- **Marge de sécurité** $`M = P_{\text{actuel}} - P_{\text{seuil enjeu}}`$ → temps avant atteinte de l'enjeu = $`M / |LRR|`$.

Une alerte M3 est émise si $`\Delta P`$ dépasse 2 écarts-types de la variabilité saisonnière, ou si le temps avant atteinte de l'enjeu passe sous 10 ans.

### 4.4 Module M4 — Bathymétrie et budget sédimentaire

Deux voies complémentaires, cohérentes avec l'approche « multi-approches » de la thèse :

**Voie ratio log (Stumpf et al., 2003)** — pour les eaux claires :

```math
Z = m_1 \frac{\ln(n\,R_w(\lambda_i))}{\ln(n\,R_w(\lambda_j))} - m_0
```

calibrée sur les points ICESat-2 ATL03 (bathymétrie photonique), ce qui **supprime le besoin d'un levé bathymétrique in situ** — condition sine qua non d'un déploiement mondial.

**Voie inversion de cinématique** (S2Shores, CNES) — pour les eaux turbides où la voie optique échoue : la profondeur est déduite de la relation de dispersion à partir de la célérité des crêtes détectée sur les bandes Sentinel-2 acquises avec un léger décalage temporel. **Le littoral d'Agadir, à forte turbidité saisonnière liée aux apports du Souss, est un site d'intérêt pour comparer les deux voies** — c'est un résultat publiable en soi.

Budget sédimentaire : $`\;\Delta V = \int (Z_{t_2} - Z_{t_1})\,dA\;`$ par cellule, avec propagation de l'incertitude verticale (LoD à 95 %) — seul un $`\Delta V`$ supérieur au LoD est déclaré significatif.

### 4.5 Module M5 — Couplage inter-échelles

C'est l'apport scientifique central. Le seuil d'alerte événementiel est modulé par l'état morphologique lent :

```math
\mathrm{TWL}_{\text{seuil,eff}} = \mathrm{TWL}_{\text{seuil,0}} \cdot \left(1 - \alpha \cdot I_{\text{érosion}}\right)
```

avec $`I_{\text{érosion}} \in [0,1]`$ un indice normalisé combinant le taux LRR, la perte de largeur de plage sur 5 ans et le déficit du budget sédimentaire, et $`\alpha \approx 0{,}2`$ un coefficient à calibrer sur les événements d'impact documentés.

Interprétation : *une plage en érosion chronique déclenche l'alerte pour un événement moins intense qu'une plage stable.* Cette relation est falsifiable — elle se teste sur une base d'événements d'impact observés (§ 6).

---

## 5. Seuils et niveaux d'alerte

### 5.1 Principe : percentiles locaux et périodes de retour

Pour chaque point de grille, le système précalcule à partir d'un hindcast de 30 ans minimum :
- les percentiles P50, P90, P95, P98, P99, P99,9 de Hs, TWL, P ;
- les niveaux de période de retour 1, 2, 5, 10, 25, 50, 100 ans par ajustement **GPD sur dépassements de seuil (POT)** avec déclustering (indépendance des tempêtes ≥ 72 h), et **GEV sur maxima annuels** en contrôle croisé.

### 5.2 Grille d'alerte

| Niveau | Code | Déclencheur hydrodynamique | Régime Sallenger | Action |
|---|---|---|---|---|
| **Vert** | 0 | TWL < P95 local | Swash | Veille |
| **Jaune** | 1 | P95 ≤ TWL < P99 **ou** T ≥ 1 an | Swash / Collision | Vigilance, information baignade |
| **Orange** | 2 | TWL ≥ P99 **ou** T ≥ 5 ans | Collision | Alerte : fermeture plages, ouvrages sensibles |
| **Rouge** | 3 | T ≥ 25 ans **ou** régime Overwash/Inundation | Overwash / Inundation | Alerte majeure : évacuation, protection civile |

Règles complémentaires :
- **Escalade par persistance** : ≥ 12 h consécutives à un niveau *n* ≥ 1 (Jaune ou au-dessus) fait passer au niveau *n+1* (l'érosion est cumulative — c'est la durée qui détruit la plage, pas le pic). La règle ne s'applique pas au niveau Vert.
- **Escalade par couplage M5** : si $`I_{\text{érosion}} > 0{,}6`$, remontée d'un niveau.
- **Concomitance marée** : pic de houle dans un créneau de ±2 h autour d'une pleine mer de vive-eau, définie comme un marnage au-delà du 90ᵉ percentile local — et non par le coefficient de marée, convention française (SHOM) sans équivalent mondial, incompatible avec le Choix n° 1.

### 5.3 Communication de l'incertitude

Chaque alerte porte obligatoirement :
- la probabilité de dépassement issue de l'ensemble (si le forçage ensembliste est disponible) ;
- l'intervalle de confiance sur $`R_{2\%}`$ (l'écart-type publié de Stockdon et al. est de l'ordre de ±20 %) ;
- le niveau de confiance sur $`\beta_f`$ (mesuré / dérivé MNT / mondial par défaut / générique) ;
- l'âge de la donnée morphologique M3-M4.

**Une alerte sans son incertitude n'est pas un produit scientifique.**

---

## 6. Validation — ce qui fait la crédibilité

### 6.1 Validation des forçages

Comparaison des séries CMEMS/ERA5 aux bouées et marégraphes : biais, RMSE, indice d'agrément de Willmott, coefficient de dispersion. Pour Agadir : marégraphes COI/GLOSS de la façade atlantique marocaine et données du port d'Agadir (ANP) si accessibles.

### 6.2 Validation du trait de côte (M3)

Comparaison des traits de côte satellitaires aux levés DGPS/drone de terrain sur la baie d'Agadir. Métrique : RMSE de la position cross-shore. Cible : < 10 m (référence CoastSat).

### 6.3 Validation de la bathymétrie (M4)

Comparaison aux sondages monofaisceau/multifaisceau disponibles et aux points ICESat-2 retenus hors calibration. Métriques conformes aux **standards OHI S-44** (ordre 1a/1b), avec analyse de l'erreur en fonction de la profondeur et de la turbidité.

### 6.4 Validation du système d'alerte lui-même

C'est l'étape que la plupart des travaux omettent. Construction d'une base d'**événements d'impact observés** (dégâts sur front de mer, submersion, recul brutal) à partir de la presse locale, des rapports de protection civile, des images satellitaires post-tempête et de la littérature. Puis, sur la table de contingence :

| | Impact observé | Pas d'impact |
|---|---|---|
| **Alerte émise** | VP | FP |
| **Pas d'alerte** | FN | VN |

Scores : **POD** = VP/(VP+FN), **FAR** = FP/(VP+FP), **CSI** = VP/(VP+FP+FN), **score de Peirce**, **score de Brier** et courbe **ROC** pour la version probabiliste. Le calibrage de $`\alpha`$ (§ 4.5) se fait par maximisation du CSI.

> Objectif d'un système opérationnel : POD > 0,8 avec FAR < 0,4. Un système à FAR élevé perd la confiance des utilisateurs et cesse d'être utilisé — c'est le mode d'échec dominant des systèmes d'alerte.

---

## 7. Limites, hypothèses et honnêteté scientifique

Il est essentiel de les énoncer explicitement, dans le système comme dans la publication.

1. **Résolution des modèles globaux.** Les grilles CMEMS/ERA5 (~8–50 km) ne résolvent ni la réfraction sur la bathymétrie de la baie d'Agadir, ni la diffraction derrière le cap Ghir, ni les ouvrages portuaires. Le TWL calculé est un **niveau d'eau au large transposé au rivage par formule empirique**, non une simulation nearshore. Palier suivant : descente d'échelle SWAN/XBeach sur la bathymétrie SDB+GEBCO+levés locaux — c'est précisément le cœur de la thèse.
2. **Domaine de validité de Stockdon et al. (2006).** Établie sur des plages sableuses ouvertes à pente modérée. Elle est mal adaptée aux côtes rocheuses, aux plages à galets, aux récifs coralliens et aux ouvrages verticaux. Sur ces morphologies : signaler la dégradation de confiance, ou basculer sur d'autres paramétrisations (Poate et al. 2016 pour les galets, EurOtop pour les ouvrages).
3. **Incertitude sur $`\beta_f`$.** À l'échelle mondiale, elle domine l'erreur sur $`R_{2\%}`$. C'est le point faible assumé du système.
4. **Absence de surcote haute résolution.** Le `zos` global CMEMS ne résout pas la surcote en baie fermée ou en estuaire. Un couplage SCHISM/Delft3D-FM régional serait nécessaire pour un service opérationnel certifié.
5. **SDB limitée par la turbidité et la profondeur.** La voie optique décroche typiquement au-delà de 1,5 × la profondeur de Secchi. À Agadir, les panaches turbides du Souss limiteront la voie optique en période de crue — d'où la voie inversion en secours.
6. **Latence de M3-M4.** L'état morphologique alimentant M5 peut avoir plusieurs semaines. Le système doit afficher cet âge, jamais le masquer.
7. **CoastSentinel est un système d'aide à la décision, pas une autorité d'alerte.** La responsabilité de l'alerte officielle appartient aux services nationaux (au Maroc : DMN, protection civile, ANP). Le positionnement correct est celui d'un **complément ouvert et transposable**, en particulier là où aucun service n'existe. Ce point doit figurer dans la clause de non-responsabilité de toute diffusion.

---

## 8. Interopérabilité et diffusion mondiale

Pour qu'un système « pour le monde entier » soit réellement utilisable, il doit parler les standards du monde :

- **CAP 1.2 (Common Alerting Protocol, OASIS/ITU-T X.1303)** — format d'alerte universel, adopté par l'OMM et les services d'alerte nationaux. Chaque alerte CoastSentinel est sérialisée en CAP.
- **WIS 2.0 (OMM)** — publication des notifications par MQTT sur le système d'information de l'OMM.
- **OGC STAC / API-Features / EDR** — exposition des données et des couches.
- **FAIR + DOI Zenodo** — code, seuils précalculés et jeux de validation versionnés et citables.
- **Licences** — code sous licence permissive (Apache-2.0 ou MIT) ; produits dérivés sous CC-BY-4.0, en respectant les conditions Copernicus (attribution) et NASA/USGS (domaine public).

Ce positionnement rattache directement le travail à l'initiative onusienne **« Early Warnings for All »** (alerte précoce pour tous à l'horizon 2027), ce qui constitue un argument fort pour le financement et la publication.

---

## 9. Feuille de route

| Phase | Contenu | Durée indicative | Sortie |
|---|---|---|---|
| **P0 — Prototype** | M1+M2 sur Agadir, seuils percentiles, tableau de bord | 1–2 mois | Code + démonstrateur (*fourni avec cette note*) |
| **P1 — Climatologie** | Hindcast ERA5/CMEMS 30 ans, GEV/GPD, seuils Agadir | 2–3 mois | Atlas de seuils, chapitre méthodologique |
| **P2 — M3 trait de côte** | CoastSat sur la baie d'Agadir 1984–2026, validation DGPS | 3–4 mois | Article n° 1 : évolution du trait de côte |
| **P3 — M4 bathymétrie** | SDB double voie (Stumpf + S2Shores) calibrée ICESat-2 | 4–6 mois | Article n° 2 : SDB en eaux turbides |
| **P4 — Couplage M5** | Calibration de α, validation POD/FAR sur base d'événements | 3–4 mois | Article n° 3 : **le cœur original de la thèse** |
| **P5 — Généralisation** | Déploiement sur 10 sites tests de contextes contrastés | 3–4 mois | Article n° 4 : transposabilité mondiale |
| **P6 — Opérationnel** | CAP/WIS2, API publique, hébergement, gouvernance | 3–6 mois | Service en ligne + note technique |

---

## 10. Références principales

**Hydrodynamique et runup**
- Stockdon, H.F., Holman, R.A., Howd, P.A., Sallenger, A.H. (2006). Empirical parameterization of setup, swash, and runup. *Coastal Engineering*, 53(7), 573–588.
- Sallenger, A.H. (2000). Storm impact scale for barrier islands. *Journal of Coastal Research*, 16(3), 890–895.
- Dolan, R., Davis, R.E. (1992). An intensity scale for Atlantic coast northeast storms. *Journal of Coastal Research*, 8(4), 840–853.
- Poate, T.G., McCall, R.T., Masselink, G. (2016). A new parameterisation for runup on gravel beaches. *Coastal Engineering*, 117, 176–190.

**Niveaux extrêmes et exposition mondiale**
- Vousdoukas, M.I. et al. (2018). Global probabilistic projections of extreme sea levels. *Nature Communications*, 9, 2360.
- Vousdoukas, M.I. et al. (2020). Sandy coastlines under threat of erosion. *Nature Climate Change*, 10, 260–263.
- Kirezci, E. et al. (2020). Projections of global-scale extreme sea levels and resulting episodic coastal flooding. *Scientific Reports*, 10, 11629.

**Trait de côte et pentes**
- Vos, K., Splinter, K.D., Harley, M.D., Simmons, J.A., Turner, I.L. (2019). CoastSat: A Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling & Software*, 122, 104528.
- Luijendijk, A. et al. (2018). The state of the world's beaches. *Scientific Reports*, 8, 6641.
- Athanasiou, P. et al. (2019). Global distribution of nearshore slopes with implications for coastal retreat. *Earth System Science Data*, 11, 1515–1529.

**Bathymétrie dérivée du satellite**
- Stumpf, R.P., Holderied, K., Sinclair, M. (2003). Determination of water depth with high-resolution satellite imagery over variable bottom types. *Limnology and Oceanography*, 48(1part2), 547–556.
- Almar, R. et al. (2024). Satellite-derived bathymetry from correlation of Sentinel-2 spectral bands to derive wave kinematics: qualification of S2Shores estimates with hydrographic standards. *Coastal Engineering*, 189, 104458.
- Parrish, C.E. et al. (2019). Validation of ICESat-2 ATLAS bathymetry. *Remote Sensing*, 11(14), 1634.

**Systèmes d'alerte**
- Ferreira, O. (2026). A review of early warning systems for storm-induced coastal flooding and erosion on wave-dominated open coasts. *Cambridge Prisms: Coastal Futures*, 4, e7. https://doi.org/10.1017/cft.2026.10026
- OASIS (2010). *Common Alerting Protocol Version 1.2*.

**Données**
- Copernicus Marine Service — https://marine.copernicus.eu
- Copernicus Data Space Ecosystem — https://dataspace.copernicus.eu
- UNESCO-COI Sea Level Station Monitoring Facility — https://www.ioc-sealevelmonitoring.org
- GEBCO — https://www.gebco.net
- NOAA NOMADS — https://nomads.ncep.noaa.gov

---

*Document de conception, version 0.1. Le prototype logiciel associé (`coastsentinel.py`) implémente les modules M1, M2 et le moteur d'alerte de la phase P0.*
