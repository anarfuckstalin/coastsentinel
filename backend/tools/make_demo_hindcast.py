# -*- coding: utf-8 -*-
"""Genere un hindcast SYNTHETIQUE de 30 ans pour tester la chaine de seuils.

    python3 make_demo_hindcast.py era5_demo.csv

ATTENTION : ce fichier ne contient AUCUNE donnee reelle. Il sert uniquement
a verifier que le calcul des percentiles et des periodes de retour fonctionne.
Pour un usage scientifique, remplacer par un vrai hindcast :

  * ERA5 (Climate Data Store, 1940-present) :
      variable "significant_height_of_combined_wind_waves_and_swell"
  * CMEMS GLOBAL_MULTIYEAR_WAV_001_032 (1980-present, meilleure resolution) :
      variable VHM0

Le CSV attendu par coastsentinel.py a deux colonnes : time, hs.
"""

import csv
import math
import random
import sys
from datetime import datetime, timedelta


def generate(path: str, annees: int = 30, seed: int = 7) -> int:
    rng = random.Random(seed)
    t = datetime(2026 - annees, 1, 1)
    n = annees * 365 * 24
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "hs"])
        for i in range(n):
            doy = t.timetuple().tm_yday
            # cycle saisonnier : hiver atlantique nettement plus energique
            seas = 1.55 + 0.75 * math.cos(2 * math.pi * (doy - 15) / 365.25)
            # variabilite synoptique (passages de depressions)
            synop = (0.9 * math.sin(2 * math.pi * i / (24 * 6.3))
                     + 0.5 * math.sin(2 * math.pi * i / (24 * 2.7)))
            storm = 0.0
            if rng.random() < 1 / (24 * 45):        # ~8 tempetes par an
                storm = abs(rng.gauss(2.4, 1.1))
            hs = max(0.25, seas + 0.55 * synop + rng.gauss(0, 0.28) + storm)
            w.writerow([t.isoformat(), round(hs, 3)])
            t += timedelta(hours=1)
    return n


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "era5_demo.csv"
    n = generate(out)
    print("%d pas de temps horaires ecrits dans %s" % (n, out))
    print("ATTENTION : donnees synthetiques, aucune valeur scientifique.")
