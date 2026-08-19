# Outils scientifiques hors application

Scripts autonomes, complémentaires de l'API. Ils gardent leur interface en
ligne de commande d'origine et ne dépendent pas du serveur.

| Script | Rôle | Phase |
|---|---|---|
| `fetch_era5.py` | Télécharge le hindcast ERA5 (30 ans) en un point | P1 |
| `validation.py` | POD / FAR / CSI, ROC, Brier, calibration de α | P4 |
| `multisite.py` | Déploiement comparatif sur N littoraux | P5 |
| `m3_shoreline.py` | Trait de côte par satellite (M3) et amorce SDB (M4) | P2-P3 |
| `make_demo_hindcast.py` | Hindcast synthétique pour tester la chaîne des seuils | — |

```bash
python tools/validation.py          # 31 tests du module de validation
python tools/m3_shoreline.py        # auto-test du module trait de côte
python tools/fetch_era5.py --lat 30.42 --lon -9.62 --debut 1996 --fin 2025 \
       --out era5_agadir.csv
```

`validation.py` est l'étape qui transforme le système en résultat publiable :
il confronte les alertes émises aux impacts réellement observés. Voir la note
de conception (`docs/NOTE_CONCEPTION_CoastSentinel.md`), section 6.
