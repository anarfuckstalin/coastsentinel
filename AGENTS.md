# Contexte pour les agents de développement

Fichier lu par les IDE agentiques (Antigravity, Cursor, Claude Code…) avant
d'intervenir sur ce dépôt. Il décrit ce que le projet est, comment le lancer,
et surtout **ce qu'il ne faut pas casser**.

## Le projet

CoastSentinel — système d'alerte côtière multi-échelle. Backend Python
(FastAPI) qui porte la science, frontend React/deck.gl qui la rend
manipulable. Contexte : thèse sur la modélisation topo-bathymétrique et
hydrodynamique sédimentaire du littoral d'Agadir, Maroc.

```
backend/coastsentinel/   moteur scientifique + API      (Python 3.11+)
backend/tools/           scripts autonomes hérités       (style d'origine, hors lint)
frontend/src/            application web                 (React 19 + TypeScript)
docs/                    note de conception scientifique
```

## Lancer

```bash
pip install -e "backend[science,dev]"
uvicorn coastsentinel.api:app --app-dir backend --reload   # http://localhost:8000/api/docs
cd frontend && npm install && npm run dev                   # http://localhost:5173
```

Dans l'IDE : tâche **« ▶ Tout démarrer »** (`.vscode/tasks.json`).

## Vérifier avant de proposer un changement

```bash
pytest backend -q                 # 35 tests
ruff check backend                # doit passer
cd frontend && npx tsc -b && npm run build
```

## Règles à respecter

**La physique est adossée à la littérature.** `backend/coastsentinel/physics.py`
implémente Stockdon et al. (2006), Sallenger (2000), Dolan & Davis (1992).
Aucune constante d'ajustement maison. Les tests confrontent le code aux valeurs
publiées dans les articles, pas à ses propres sorties : ne les « corrigez »
jamais pour faire passer une modification — c'est le code qui a tort.

**Les seuils sont relatifs, jamais absolus.** Ne codez aucun seuil en dur du
type `hs > 4`. Tout seuil se dérive des percentiles de la climatologie locale.
C'est ce qui rend le système applicable à n'importe quel littoral.

**Les seuils TWL viennent de la distribution conjointe** (houle × marée),
pas de la somme des percentiles marginaux — celle-ci supposerait une
concomitance systématique et surestimerait le seuil. Voir
`engine.twl_thresholds`.

**Le masque terre/mer est strict.** Une maille dont un seul nœud est à terre
n'est pas rendue. N'introduisez pas d'extrapolation ou de remplissage par
plus proche voisin par-dessus la côte.

**Les couleurs suivent une règle unique**, définie dans
`frontend/src/lib/palette.ts` : séquentielle une teinte pour les magnitudes,
divergente deux teintes + gris neutre pour les anomalies, palette de statut
réservée aux niveaux d'alerte. Pas d'arc-en-ciel, et la palette de statut ne
sert jamais de couleur de série.

**L'incertitude s'affiche, elle ne se masque pas.** Origine de la pente βf,
âge de la donnée morphologique, confiance de la climatologie, marée substituée :
tout cela remonte dans `avertissements` et doit rester visible à l'écran.

**Le disclaimer est non négociable.** L'outil est une aide à la décision et de
recherche ; il ne se substitue pas aux alertes officielles des services
nationaux. Cette mention figure dans l'API, l'interface et les exports.

## Langue

Interface, messages d'erreur, commentaires et docstrings en **français**.
Les identifiants de code restent en anglais quand c'est l'usage du domaine
(`stockdon_runup`, `wave_power`, `setup`, `swash`).
