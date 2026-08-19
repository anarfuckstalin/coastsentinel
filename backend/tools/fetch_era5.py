# -*- coding: utf-8 -*-
"""
CoastSentinel — Phase P1 : telechargement du hindcast ERA5
==========================================================

Produit le CSV de climatologie locale attendu par
`coastsentinel.py --hindcast`. C'est l'etape qui fait passer les seuils de
« generiques, confiance faible » a « derives de 30 ans de reanalyse ».

ERA5 (ECMWF / Copernicus C3S) couvre 1940 a nos jours, au pas horaire, en
tout point du globe. C'est la reference pour la climatologie de houle.

Prerequis (une seule fois)
--------------------------
1. Creer un compte gratuit sur https://cds.climate.copernicus.eu
2. Accepter les conditions du jeu "ERA5 hourly data on single levels"
3. Creer ~/.cdsapirc (Windows : C:\\Users\\<vous>\\.cdsapirc) :

       url: https://cds.climate.copernicus.eu/api
       key: <votre cle>

4. pip install cdsapi xarray netCDF4 numpy

Usage
-----
    python fetch_era5.py --lat 30.42 --lon -9.62 --debut 1996 --fin 2025 \\
                         --out era5_agadir.csv

Puis :
    python coastsentinel.py --hindcast era5_agadir.csv ...

Le telechargement est decoupe par annee et reprend ou il s'est arrete :
une coupure reseau ne fait pas tout recommencer. Comptez de quelques
minutes a quelques heures selon la file d'attente du CDS.

Note sur la resolution
----------------------
La grille de vagues d'ERA5 est a 0,5 degre (~50 km). Le point extrait est
donc au large, ce qui est exactement ce qu'attend la parametrisation de
Stockdon (conditions en eau profonde). En revanche, pres d'une cote
decoupee, le point de grille le plus proche peut tomber a terre : le script
le detecte et cherche le point marin valide le plus proche.

Licence : Apache-2.0.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List, Optional, Tuple

VARIABLES = {
    "swh": "significant_height_of_combined_wind_waves_and_swell",
    "mwp": "mean_wave_period",
    "mwd": "mean_wave_direction",
    "pp1d": "peak_wave_period",
}
DATASET = "reanalysis-era5-single-levels"


# ---------------------------------------------------------------------------

def request_year(client, year: int, lat: float, lon: float, demi: float,
                 path: str) -> str:
    """Telecharge une annee sur une petite emprise autour du point."""
    aire = [round(lat + demi, 2), round(lon - demi, 2),
            round(lat - demi, 2), round(lon + demi, 2)]   # N, O, S, E
    client.retrieve(DATASET, {
        "product_type": ["reanalysis"],
        "variable": list(VARIABLES.values()),
        "year": [str(year)],
        "month": ["%02d" % m for m in range(1, 13)],
        "day": ["%02d" % d for d in range(1, 32)],
        "time": ["%02d:00" % h for h in range(24)],
        "area": aire,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }, path)
    return path


def nearest_sea_point(ds, lat: float, lon: float,
                      var: str = "swh") -> Tuple[float, float]:
    """Trouve le point de grille marin valide le plus proche.

    Sur une cote decoupee, le plus proche voisin peut etre un point de
    terre : ERA5 y met des NaN pour les variables de vagues. On balaie
    alors l'emprise et on retient le point valide le plus proche.
    """
    import numpy as np

    da = ds[var]
    latname = "latitude" if "latitude" in da.dims else "lat"
    lonname = "longitude" if "longitude" in da.dims else "lon"
    lats = np.asarray(da[latname].values, dtype="float64")
    lons = np.asarray(da[lonname].values, dtype="float64")

    # fraction de pas de temps valides en chaque point
    valid = np.isfinite(da.values).mean(axis=0)
    best, bestd = None, 1e9
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            if valid[i, j] < 0.9:            # point de terre ou trop lacunaire
                continue
            d = (la - lat) ** 2 + (lo - lon) ** 2
            if d < bestd:
                bestd, best = d, (float(la), float(lo))
    if best is None:
        raise SystemExit(
            "Aucun point marin valide dans l'emprise. Augmenter --demi "
            "(ex. --demi 1.0) ou verifier les coordonnees du site.")
    return best


def extract_year(path: str, lat: float, lon: float) -> Tuple[List, Tuple]:
    """Lit le NetCDF et extrait la serie au point marin le plus proche."""
    import numpy as np
    import xarray as xr

    ds = xr.open_dataset(path)
    la, lo = nearest_sea_point(ds, lat, lon)
    latname = "latitude" if "latitude" in ds.dims else "lat"
    lonname = "longitude" if "longitude" in ds.dims else "lon"
    tname = "valid_time" if "valid_time" in ds.dims else "time"
    pt = ds.sel({latname: la, lonname: lo}, method="nearest")

    times = pt[tname].values
    out = []
    for k in range(len(times)):
        hs = float(pt["swh"].values[k]) if "swh" in pt else float("nan")
        if not np.isfinite(hs):
            continue
        row = {
            "time": str(np.datetime_as_string(times[k], unit="h")),
            "hs": round(hs, 3),
        }
        for short, name in (("mwp", "tm"), ("pp1d", "tp"), ("mwd", "dir")):
            if short in pt:
                v = float(pt[short].values[k])
                if np.isfinite(v):
                    row[name] = round(v, 2)
        out.append(row)
    ds.close()
    return out, (la, lo)


# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Telechargement du hindcast ERA5 pour CoastSentinel")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--debut", type=int, default=1996, help="Annee de debut")
    p.add_argument("--fin", type=int, default=2025, help="Annee de fin")
    p.add_argument("--demi", type=float, default=0.6,
                   help="Demi-emprise en degres autour du point")
    p.add_argument("--cache", default="era5_cache",
                   help="Dossier des NetCDF telecharges (reprise possible)")
    p.add_argument("--out", default="era5_hindcast.csv")
    args = p.parse_args(argv)

    if args.fin - args.debut + 1 < 10:
        print("ATTENTION : moins de 10 ans demandes. Les percentiles hauts "
              "(P99, P99.9) et les periodes de retour seront peu robustes.\n")

    try:
        import cdsapi
    except ImportError:
        raise SystemExit(
            "cdsapi absent.\n  pip install cdsapi xarray netCDF4 numpy\n"
            "Puis creer le fichier ~/.cdsapirc (voir l'en-tete de ce script).")

    os.makedirs(args.cache, exist_ok=True)
    client = cdsapi.Client()

    lignes: List[dict] = []
    point = None
    annees = list(range(args.debut, args.fin + 1))
    for k, year in enumerate(annees, 1):
        nc = os.path.join(args.cache, "era5_%d_%.2f_%.2f.nc"
                          % (year, args.lat, args.lon))
        if os.path.exists(nc) and os.path.getsize(nc) > 1024:
            print("[%d/%d] %d — deja en cache" % (k, len(annees), year))
        else:
            print("[%d/%d] %d — telechargement..." % (k, len(annees), year))
            try:
                request_year(client, year, args.lat, args.lon, args.demi, nc)
            except Exception as exc:
                print("      echec sur %d (%s) — annee ignoree" % (year, exc))
                continue
        try:
            rows, point = extract_year(nc, args.lat, args.lon)
        except Exception as exc:
            print("      lecture impossible (%s) — annee ignoree" % exc)
            continue
        lignes.extend(rows)
        print("      %d pas de temps cumules" % len(lignes))

    if not lignes:
        raise SystemExit("Aucune donnee recuperee.")

    lignes.sort(key=lambda r: r["time"])
    champs = ["time", "hs"] + [c for c in ("tp", "tm", "dir")
                               if any(c in r for r in lignes)]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)

    hs = sorted(r["hs"] for r in lignes)
    n = len(hs)

    def pc(q):
        return hs[min(n - 1, int(q / 100.0 * (n - 1)))]

    print("\n%d pas de temps ecrits dans %s" % (n, args.out))
    if point:
        print("Point de grille retenu : %.2f N, %.2f E "
              "(demande : %.2f, %.2f)" % (point[0], point[1],
                                          args.lat, args.lon))
    print("Couverture : %.1f ans" % (n / (365.25 * 24)))
    print("Hs — mediane %.2f m | P95 %.2f m | P99 %.2f m | max %.2f m"
          % (pc(50), pc(95), pc(99), hs[-1]))
    print("\nEtape suivante :")
    print("  python coastsentinel.py --lat %.4f --lon %.4f "
          "--source openmeteo --hindcast %s --out dashboard.html"
          % (args.lat, args.lon, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
