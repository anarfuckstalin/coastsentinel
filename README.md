# CoastSentinel

**Système d'Alerte Côtière Multi-échelle** — application web fondée sur des
données ouvertes à crédibilité scientifique internationale, transposable à
n'importe quel littoral du monde.

Prototype de recherche associé à la thèse *« Modélisation topo-bathymétrique et
hydrodynamique sédimentaire : étude multi-approches sous différentes échelles
spatio-temporelles ; cas du littoral d'Agadir, Maroc »*.

---

## Ce que c'est

Un **backend Python** qui porte la science — paramétrisations publiées,
climatologie locale, moteur d'alerte — exposé en API REST documentée ; et un
**frontend React** cartographique qui rend tout cela manipulable : recherche
mondiale de lieux, analyse en un point, champs cartographiques animés,
stations de référence, exports.

Deux choix de conception fondent la transposabilité mondiale :

**Les seuils sont relatifs, jamais absolus.** Le système ne dit pas « alerte si
Hs > 4 m » mais « alerte au-delà du 99ᵉ percentile local », les percentiles
étant reconstruits en tout point du globe depuis une réanalyse. Il s'auto-calibre
partout où une réanalyse existe — c'est-à-dire partout.

**Le couplage des échelles *est* l'alerte.** L'état morphologique lent
(trait de côte, budget sédimentaire) abaisse le seuil événementiel : une plage
en érosion chronique déclenche l'alerte pour un événement moins intense qu'une
plage stable.

---

## Pile technique

| Couche | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, httpx (async), uvicorn, scipy |
| **Frontend** | React 19, TypeScript 5.9, Vite 6, Tailwind CSS v4 |
| **Cartographie** | MapLibre GL 5 (vectoriel WebGL), deck.gl 9 (couches de données) |
| **État & données** | Zustand 5, TanStack Query 5 |
| **Graphiques** | Recharts 2 |
| **Déploiement** | Docker Compose (nginx + uvicorn), scripts locaux, CI GitHub Actions |

---

## Démarrage

### Docker — une seule commande

```bash
docker compose up --build
```

- Application : <http://localhost:8080>
- API et documentation interactive : <http://localhost:8000/api/docs>

### Docker — depuis les images publiées, sans compiler

Chaque commit sur `main` publie deux images sur GitHub Container Registry.
Sur n'importe quel serveur muni de Docker :

```bash
COASTSENTINEL_IMAGE=ghcr.io/<votre-compte>/coastsentinel \
docker compose -f docker-compose.ghcr.yml up -d
```

Le tag `latest` suit `main` ; `v1.0.0`, `1.0` et le sha court permettent
d'épingler une version. Les images sont privées par défaut : rendez-les
publiques dans *Packages → Package settings → Change visibility*, ou
authentifiez-vous avec `docker login ghcr.io`.

### Local — développement

Windows : double-cliquez **`DEMARRER.bat`**.
Linux / macOS : `./demarrer.sh`

Le script crée l'environnement Python, installe les dépendances du frontend au
premier lancement, démarre les deux serveurs et ouvre le navigateur.

- Application : <http://localhost:5173>
- API : <http://localhost:8000/api/docs>

### Publier sur GitHub

Double-cliquez **`PUBLIER.bat`**. Le script écrit le workflow de publication
d'images, initialise le dépôt, refuse de continuer si `node_modules`, `.venv`
ou `dist` se sont glissés dans l'index, puis pousse. Il ne demande, ne lit et
n'enregistre aucun identifiant : l'authentification reste entre vos mains et
celles de Git Credential Manager.

Créez au préalable un dépôt **vide** sur GitHub — sans README ni licence,
sinon les deux historiques divergent et le push est refusé.

### Dans un IDE (Antigravity, VS Code, Cursor)

Le dépôt embarque `.vscode/tasks.json` et `.vscode/launch.json`. Ouvrez le
dossier, puis :

- **`Ctrl+Maj+P` → « Run Task »** → *0 · Installer les dépendances* (une fois),
  puis *▶ Tout démarrer* ;
- ou **`Ctrl+Maj+B`**, qui lance directement *▶ Tout démarrer* ;
- **`F5`** → *▶ Application complète* pour déboguer l'API avec points d'arrêt.

`AGENTS.md` décrit le projet aux agents de l'IDE : lancement, commandes de
vérification et règles scientifiques à ne pas casser.

### Manuellement

```bash
# backend
pip install -e "backend[science]"
uvicorn coastsentinel.api:app --app-dir backend --reload

# frontend, dans un autre terminal
cd frontend && npm install && npm run dev
```

---

## L'application

**Barre de recherche mondiale** — ville, port, ou coordonnées collées telles
quelles (`30.42, -9.62`), avec navigation au clavier.

**Analyse en un point** — cliquez n'importe où sur la carte. Le système
télécharge le forçage, reconstruit la climatologie locale sur 3, 10 ou 20 ans,
calcule le niveau d'alerte et affiche le détail : tuiles de synthèse, frise
horaire des niveaux, TWL comparé aux seuils, décomposition marée / setup /
swash, houle comparée aux percentiles locaux, table de données, exports CSV et
JSON.

**Couches cartographiques animées** — le moteur est évalué sur une grille
couvrant la zone visible (une seule requête multi-points), puis interpolé et
rendu en raster WebGL. La **résolution de la grille est réglable** : cinq
préréglages de 4 × 3 à 14 × 11, ou saisie directe du nombre de colonnes et de
lignes, plus l'horizon temporel des couches. Huit champs : niveau d'alerte,
TWL, Hs, anomalie Hs/P95 local, période, puissance de houle, jet de rive,
niveau d'eau — plus les vecteurs de direction de houle. Un curseur temporel
anime la séquence.

Ces huit champs dérivent tous du socle vagues + niveau d'eau, servi par le
modèle presque partout. Les grandeurs à couverture inégale — houle de fond,
courant de surface, température — restent au niveau de **l'analyse
ponctuelle**, où elles ne coûtent qu'une requête : sur une grille, elles
multiplient le volume transféré par le nombre de nœuds pour un résultat vide
sur la plupart des nœuds côtiers.

**Roses de direction** — histogramme polaire de la distribution conjointe
intensité × direction de provenance, sur 16 secteurs. Calculée sur la
climatologie locale quand elle est disponible ; sinon sur la seule période
analysée, et l'application le dit explicitement — une rose de cinq jours décrit
un épisode, pas un régime.

**Autres grandeurs océaniques au point analysé** — partition mer du vent /
houle de fond, courant de surface (vitesse et direction), température de
surface. Servies quand le modèle les couvre pour le point choisi, signalées
sinon.

**Couches de référence ouvertes** — bathymétrie GEBCO 2025, EMODnet Bathymetry,
NASA Blue Marble, balisage OpenSeaMap ; imagerie VIIRS NOAA-20 et MODIS Terra,
chlorophylle a (proxy de turbidité, utile pour le panache du Souss),
température de surface MUR et son anomalie — avec sélecteur de date.
Le détail des sources, de leurs producteurs et de leurs licences est dans
[`docs/SOURCES.md`](docs/SOURCES.md).

**Exports** — série ponctuelle en CSV et JSON ; **grille en GeoJSON**
(instantané du pas affiché, prêt pour QGIS) et **en CSV long** (toute la
séquence, un enregistrement par nœud et par pas — le format qu'attendent
pandas et R). Les nœuds à terre sont omis, jamais exportés à zéro : un zéro se
confondrait avec une mesure.

**Stations mondiales** — 90 marégraphes et ports de référence, dont 13 sur la
côte marocaine. Chaque station est **cliquable** : une infobulle donne son nom,
sa région, ses coordonnées et un bouton *Analyser ce point* qui lance
directement le calcul.

---

## Règles de représentation

Les couleurs suivent une règle stricte, appliquée du raster cartographique aux
graphiques : rampe **séquentielle** à une seule teinte pour les magnitudes,
rampe **divergente** à deux teintes avec gris neutre au centre pour les
anomalies, **palette de statut réservée** pour les niveaux d'alerte — jamais
réutilisée comme couleur de série. Pas d'arc-en-ciel : une rampe arc-en-ciel
invente des frontières qui n'existent pas dans la donnée.

Le masquage terre/mer est strict : une maille dont un seul nœud est à terre
n'est pas rendue, plutôt que d'extrapoler une valeur de houle par-dessus la côte.

---

## Science

| Grandeur | Référence |
|---|---|
| Jet de rive R2%, setup, swash | Stockdon, Holman, Howd & Sallenger (2006), *Coastal Engineering* 53(7) |
| Régime d'impact morphologique | Sallenger (2000), *J. Coastal Research* 16(3) |
| Indice de puissance de tempête | Dolan & Davis (1992), *J. Coastal Research* 8(4) |
| Périodes de retour | GPD/POT avec déclustering 72 h, garde-fou de forme |

**Seuils TWL.** Ils sont les percentiles de la **distribution conjointe**
reconstruite (hindcast de houle × distribution de marée), et non la somme
« P99 houle + P99 marée » — cette dernière suppose une concomitance
systématique et surestime le seuil.

**Périodes de retour.** Pour la hauteur significative, le paramètre de forme de
la GPD est normalement ≤ 0. Un ajustement libre donnant une forme fortement
positive produit des niveaux non physiques ; le code rebascule alors sur une
queue exponentielle et conserve le diagnostic.

---

## Limites assumées

Le système transpose au rivage un forçage calculé au large par une formule
empirique. Il ne simule **pas** la propagation nearshore : ni la réfraction sur
la bathymétrie de la baie d'Agadir, ni la diffraction derrière le cap Ghir, ni
l'effet des ouvrages portuaires. La descente d'échelle (SWAN / XBeach) est la
suite logique.

La paramétrisation de Stockdon et al. (2006) est établie sur des plages
sableuses ouvertes. Sur côtes rocheuses, galets, récifs ou ouvrages verticaux,
utiliser Poate et al. (2016) ou EurOtop.

**La couche d'alerte cartographique applique le profil de plage du panneau à
tous les nœuds** : c'est une projection spatiale du forçage, pas une carte de
vulnérabilité. Les couches Hs, Tp, direction et niveau d'eau sont des grandeurs
de modèle sans hypothèse ajoutée.

La pente d'estran βf domine l'incertitude sur le jet de rive. Un levé DGPS
local vaut mieux que n'importe quel raffinement du code.

**Toutes les variables ne sont pas servies partout.** Les vagues le sont
presque universellement ; le courant de surface et la température viennent d'un
modèle à 8 km et manquent souvent près du rivage. C'est la raison pour laquelle
elles ne sont pas cartographiées. Pour savoir ce que la source sert en un point
donné :

```bash
python -m coastsentinel.cli diag --lat 30.42 --lon -9.68
```

La commande interroge la source **une variable à la fois** et affiche, pour
chacune, servie / vide / absente / refusée. Groupées, les variables se
masquent l'une l'autre et l'on conclut à tort que tout manque.

> **CoastSentinel est un dispositif d'aide à la décision et de recherche. Il ne
> se substitue en aucun cas aux alertes officielles émises par les services
> nationaux compétents** (au Maroc : DMN, Protection Civile, ANP).

---

## Tests

```bash
pytest backend -q        # 63 tests : physique, moteur, climatologie, roses, grille, API
cd frontend && npx tsc -b && npm run build
```

Les tests de physique confrontent le code aux **valeurs publiées** dans les
articles cités, pas à ses propres sorties.

---

## Structure

```
backend/
  coastsentinel/
    physics.py       paramétrisations publiées
    climatology.py   percentiles locaux, GPD/POT
    engine.py        seuils, couplage M5, niveaux, épisodes
    grid.py          évaluation sur grille
    sources.py       Open-Meteo, géocodage, jeu de démonstration
    schemas.py       contrats d'API (Pydantic v2)
    api.py           routes FastAPI
    stations.py      réseau de référence
    cli.py           usage hors serveur
  tests/
frontend/
  src/
    api/client.ts    client typé
    lib/palette.ts   rampes et règles de couleur
    lib/field.ts     interpolation et rendu raster
    components/      carte, panneau, recherche, résultats, curseur temporel
    store.ts         état global (Zustand)
docker-compose.yml · docker-compose.ghcr.yml · DEMARRER.bat · demarrer.sh · PUBLIER.bat
.github/workflows/ci.yml · .github/workflows/docker.yml · LICENSE · CITATION.cff
```

---

## Licence

**MIT** pour le code — voir [`LICENSE`](LICENSE). Les données restent soumises
aux licences de leurs producteurs (Copernicus : attribution obligatoire ;
NASA/USGS : domaine public ; GEBCO, OpenStreetMap : citation requise). Le
détail figure dans [`docs/SOURCES.md`](docs/SOURCES.md).

Pour citer ce travail, un fichier [`CITATION.cff`](CITATION.cff) est fourni :
GitHub en dérive automatiquement une notice « Cite this repository ».

Auteur : Amine Bouhadi — Université Abdelmalek Essaâdi, Maroc.
