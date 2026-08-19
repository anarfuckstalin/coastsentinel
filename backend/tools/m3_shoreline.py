# -*- coding: utf-8 -*-
"""
CoastSentinel — Module M3 (trait de cote) et amorce du module M4 (SDB)
======================================================================

M3 : extraction du trait de cote depuis Sentinel-2 L2A (Copernicus Data
Space Ecosystem, catalogue STAC ouvert, sans cle pour la recherche), calcul
des taux EPR / LRR le long de transects, et derivation de l'indice
d'erosion I_erosion consomme par le couplage M5 de `coastsentinel.py`.

M4 : fonction de bathymetrie derivee du satellite par ratio logarithmique
(Stumpf et al., 2003), calibrable sur des points ICESat-2 ATL03 — ce qui
supprime le besoin d'un leve bathymetrique in situ et rend l'approche
deployable partout dans le monde.

Dependances (installation sur votre machine, pas requises pour lire le code) :
    pip install pystac-client odc-stac rioxarray xarray numpy scikit-image \
                shapely geopandas scipy

Chaine M3 (identique dans son principe a CoastSat, Vos et al. 2019) :
    1. recherche STAC Sentinel-2 L2A sur l'emprise et la periode
    2. filtrage nuages (SCL) et selection des scenes exploitables
    3. calcul de l'indice d'eau MNDWI = (Green - SWIR1)/(Green + SWIR1)
    4. seuillage Otsu -> masque terre/mer
    5. contour sub-pixel (marching squares)
    6. correction de maree : projection horizontale du contour sur la pente
       beta_f pour ramener toutes les dates a un meme datum
    7. intersection avec les transects -> position cross-shore
    8. EPR, LRR + IC 95 %, residu saisonnier, indice d'erosion

Licence : Apache-2.0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

STAC_CDSE = "https://catalogue.dataspace.copernicus.eu/stac"
STAC_EARTHSEARCH = "https://earth-search.aws.element84.com/v1"  # miroir S2 L2A


# ---------------------------------------------------------------------------
# 1. Recherche et lecture des scenes
# ---------------------------------------------------------------------------

def search_sentinel2(bbox: Tuple[float, float, float, float],
                     start: str, end: str,
                     max_cloud: float = 20.0,
                     stac_url: str = STAC_EARTHSEARCH) -> List[dict]:
    """Recherche STAC des scenes Sentinel-2 L2A. Retourne la liste d'items.

    bbox = (lon_min, lat_min, lon_max, lat_max)
    """
    from pystac_client import Client  # type: ignore

    client = Client.open(stac_url)
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=list(bbox),
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )
    items = list(search.items())
    items.sort(key=lambda it: it.datetime)
    return items


def load_bands(item, bbox, bands=("green", "swir16", "scl"), res: int = 10):
    """Charge les bandes necessaires en xarray via odc-stac (COG, lecture
    partielle : seule l'emprise demandee est telechargee)."""
    import odc.stac  # type: ignore

    ds = odc.stac.load([item], bands=list(bands), bbox=list(bbox),
                       resolution=res, chunks={})
    return ds.isel(time=0)


# ---------------------------------------------------------------------------
# 2. Indice d'eau, seuillage et contour sub-pixel
# ---------------------------------------------------------------------------

def mndwi(green, swir):
    """Modified Normalized Difference Water Index (Xu, 2006).
    Plus robuste que le NDWI en milieu cotier construit."""
    import numpy as np  # type: ignore
    g = green.astype("float32")
    s = swir.astype("float32")
    denom = g + s
    return np.where(denom == 0, 0.0, (g - s) / denom)


def cloud_mask_from_scl(scl):
    """Masque a partir de la Scene Classification Layer Sentinel-2.
    Classes rejetees : 3 ombre nuage, 8 nuage moyen, 9 nuage haut,
    10 cirrus, 11 neige/glace, 0 no-data, 1 sature."""
    import numpy as np  # type: ignore
    bad = {0, 1, 3, 8, 9, 10, 11}
    return np.isin(scl, list(bad))


def water_threshold(index_array) -> float:
    """Seuil terre/mer par la methode d'Otsu, calcule sur l'histogramme
    de l'indice d'eau. Otsu maximise la variance inter-classes : il
    s'adapte automatiquement a chaque scene (turbidite, eclairement)."""
    from skimage.filters import threshold_otsu  # type: ignore
    import numpy as np  # type: ignore
    vals = index_array[np.isfinite(index_array)]
    if vals.size < 1000:
        raise ValueError("Trop peu de pixels valides pour le seuillage Otsu")
    return float(threshold_otsu(vals))


def extract_contour(index_array, threshold: float, transform=None):
    """Contour sub-pixel du trait de cote (marching squares).
    Retourne une liste de polylignes en coordonnees carte si `transform`
    (affine rasterio) est fourni, sinon en indices pixel.
    """
    from skimage import measure  # type: ignore
    contours = measure.find_contours(index_array, level=threshold)
    if transform is None:
        return contours
    out = []
    for c in contours:
        pts = [transform * (float(col), float(row)) for row, col in c]
        out.append(pts)
    return out


# ---------------------------------------------------------------------------
# 3. Correction de maree
# ---------------------------------------------------------------------------

def tidal_correction(position_cross_shore: float, tide_level: float,
                     beta_f: float, datum: float = 0.0) -> float:
    """Ramene une position de trait de cote a un datum vertical commun.

    Le trait de cote instantane observe a un niveau d'eau `tide_level`
    est decale horizontalement de (tide_level - datum)/beta_f par rapport
    a sa position au datum. Sans cette correction, une variation de maree
    de 1 m sur une plage a beta_f = 0,05 produit un faux deplacement de
    20 m — soit plus que la plupart des signaux d'erosion recherches.
    """
    if beta_f <= 0:
        raise ValueError("beta_f doit etre strictement positif")
    return position_cross_shore + (tide_level - datum) / beta_f


# ---------------------------------------------------------------------------
# 4. Statistiques de changement le long des transects
# ---------------------------------------------------------------------------

@dataclass
class TransectSeries:
    """Serie temporelle de position cross-shore sur un transect."""
    nom: str
    dates: List[datetime]
    positions: List[float]        # m, positif vers le large
    incertitude: float = 10.0     # m, RMSE typique CoastSat sur Sentinel-2


@dataclass
class TransectStats:
    nom: str
    epr: float                    # m/an
    lrr: float                    # m/an
    lrr_ic95: float               # +/- m/an
    r2: float
    n: int
    residu_dernier: float         # ecart a la tendance, m
    sigma_residu: float           # m
    significatif: bool


def _decimal_years(dates: Sequence[datetime]) -> List[float]:
    return [d.year + (d.timetuple().tm_yday - 1) / 365.25 for d in dates]


def transect_stats(ts: TransectSeries) -> TransectStats:
    """EPR, LRR avec intervalle de confiance a 95 %, et residu courant."""
    n = len(ts.positions)
    if n < 3:
        raise ValueError("Au moins 3 observations sont necessaires")
    x = _decimal_years(ts.dates)
    y = list(ts.positions)

    epr = (y[-1] - y[0]) / (x[-1] - x[0]) if x[-1] != x[0] else 0.0

    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx

    resid = [y[i] - (intercept + slope * x[i]) for i in range(n)]
    sse = sum(r * r for r in resid)
    sst = sum((yi - my) ** 2 for yi in y)
    r2 = 1.0 - sse / sst if sst else 0.0
    se_slope = math.sqrt(sse / (n - 2) / sxx) if sxx and n > 2 else float("nan")
    # t de Student a 95 % ; 1.96 pour n grand, majore pour petits echantillons
    tcrit = 1.96 if n > 30 else 2.31 if n > 8 else 3.18
    ic95 = tcrit * se_slope

    sigma = math.sqrt(sse / (n - 1)) if n > 1 else 0.0
    residu_dernier = resid[-1]
    significatif = abs(slope) > ic95 and abs(slope) * 10 > ts.incertitude

    return TransectStats(ts.nom, epr, slope, ic95, r2, n,
                         residu_dernier, sigma, significatif)


def erosion_index(stats: Sequence[TransectStats],
                  largeur_perdue_5ans: Optional[float] = None,
                  deficit_sedimentaire: Optional[float] = None,
                  lrr_ref: float = -2.0) -> float:
    """Indice d'erosion normalise I in [0,1] consomme par le couplage M5.

    Combine trois signaux, chacun normalise puis moyenne sur ceux qui sont
    disponibles (le systeme reste utilisable avec un seul) :
      - taux LRR median (rapporte a `lrr_ref`, taux de reference en m/an) ;
      - largeur de plage perdue sur 5 ans (rapportee a 20 m) ;
      - deficit du budget sedimentaire (rapporte a 1, deja normalise).

    I = 0 : littoral stable ou en accretion. I = 1 : erosion severe.
    """
    comps: List[float] = []
    sig = [s.lrr for s in stats if s.significatif]
    if sig:
        med = sorted(sig)[len(sig) // 2]
        comps.append(max(0.0, min(1.0, med / lrr_ref)) if lrr_ref < 0 else 0.0)
    if largeur_perdue_5ans is not None:
        comps.append(max(0.0, min(1.0, largeur_perdue_5ans / 20.0)))
    if deficit_sedimentaire is not None:
        comps.append(max(0.0, min(1.0, deficit_sedimentaire)))
    if not comps:
        return 0.0
    return round(sum(comps) / len(comps), 3)


def alerte_m3(stats: TransectStats, distance_enjeu: float,
              horizon_alerte_ans: float = 10.0) -> Dict[str, object]:
    """Regle d'alerte chronique : temps restant avant que le trait de cote
    n'atteigne l'enjeu (route, front de mer, ouvrage)."""
    if stats.lrr >= 0:
        return {"alerte": False, "motif": "pas de recul significatif",
                "annees_restantes": None}
    annees = distance_enjeu / abs(stats.lrr)
    evt = abs(stats.residu_dernier) > 2.0 * stats.sigma_residu
    return {
        "alerte": bool(annees < horizon_alerte_ans or evt),
        "annees_restantes": round(annees, 1),
        "evenement_erosif_detecte": evt,
        "motif": ("enjeu atteint dans moins de %.0f ans"
                  % horizon_alerte_ans if annees < horizon_alerte_ans
                  else "residu > 2 sigma (evenement erosif)" if evt
                  else "-"),
    }


# ---------------------------------------------------------------------------
# 5. Module M4 — bathymetrie derivee du satellite (ratio log)
# ---------------------------------------------------------------------------

def stumpf_ratio(blue, green, n: float = 1000.0):
    """Ratio logarithmique de Stumpf et al. (2003), Limnol. Oceanogr. 48(1).

        pSDB = ln(n * Rw_blue) / ln(n * Rw_green)

    La constante n (typiquement 1000) assure que les logarithmes restent
    positifs et que le ratio varie lineairement avec la profondeur.
    Le ratio est ensuite calibre lineairement : Z = m1 * pSDB - m0.
    """
    import numpy as np  # type: ignore
    b = np.clip(blue.astype("float32"), 1e-6, None)
    g = np.clip(green.astype("float32"), 1e-6, None)
    return np.log(n * b) / np.log(n * g)


def calibrate_sdb(psdb_values: Sequence[float],
                  depths: Sequence[float]) -> Dict[str, float]:
    """Calibre Z = m1 * pSDB - m0 sur des profondeurs de reference
    (points ICESat-2 ATL03, sondages, EMODnet). Retourne m1, m0, R2 et RMSE.
    """
    n = len(psdb_values)
    if n < 20 or n != len(depths):
        raise ValueError("Au moins 20 couples (pSDB, profondeur) apparies")
    mx = sum(psdb_values) / n
    my = sum(depths) / n
    sxx = sum((v - mx) ** 2 for v in psdb_values)
    sxy = sum((psdb_values[i] - mx) * (depths[i] - my) for i in range(n))
    m1 = sxy / sxx if sxx else 0.0
    m0 = -(my - m1 * mx)
    pred = [m1 * v - m0 for v in psdb_values]
    sse = sum((depths[i] - pred[i]) ** 2 for i in range(n))
    sst = sum((d - my) ** 2 for d in depths)
    return {"m1": m1, "m0": m0,
            "r2": 1.0 - sse / sst if sst else 0.0,
            "rmse": math.sqrt(sse / n),
            "n": n}


def volume_change(z1, z2, cell_area: float,
                  sigma_z1: float, sigma_z2: float,
                  confiance: float = 1.96) -> Dict[str, float]:
    """Budget sedimentaire entre deux surfaces bathymetriques.

    Le seuil de detection (LoD, Limit of Detection) est propage depuis
    les incertitudes verticales des deux MNT : seule une difference
    superieure au LoD est declaree significative. Sans ce test, tout
    calcul de budget sedimentaire est indefendable.
    """
    import numpy as np  # type: ignore
    lod = confiance * math.sqrt(sigma_z1 ** 2 + sigma_z2 ** 2)
    dz = np.asarray(z2, dtype="float64") - np.asarray(z1, dtype="float64")
    signif = np.abs(dz) > lod
    return {
        "lod_m": lod,
        "volume_net_m3": float(np.nansum(dz[signif]) * cell_area),
        "erosion_m3": float(np.nansum(dz[signif & (dz < 0)]) * cell_area),
        "accretion_m3": float(np.nansum(dz[signif & (dz > 0)]) * cell_area),
        "fraction_significative": float(np.nanmean(signif)),
    }


# ---------------------------------------------------------------------------
# Auto-test des parties independantes du reseau
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from datetime import datetime as _dt

    # Transect fictif : recul de 2,5 m/an avec bruit et un evenement final
    dates = [_dt(y, 6, 15) for y in range(2010, 2026)]
    pos = [100.0 - 2.5 * i + ((-1) ** i) * 1.8 for i in range(len(dates))]
    pos[-1] -= 9.0   # evenement erosif
    ts = TransectSeries("T-Agadir-04", dates, pos)
    st = transect_stats(ts)
    print("LRR   = %.2f +/- %.2f m/an   (R2 = %.3f, n = %d)"
          % (st.lrr, st.lrr_ic95, st.r2, st.n))
    print("EPR   = %.2f m/an" % st.epr)
    print("residu dernier = %.2f m (sigma = %.2f)"
          % (st.residu_dernier, st.sigma_residu))
    print("alerte M3 :", alerte_m3(st, distance_enjeu=45.0))
    print("I_erosion =", erosion_index([st], largeur_perdue_5ans=12.0))

    # Correction de maree : 1 m de maree sur une pente 0,05 = 20 m
    print("correction de maree :",
          round(tidal_correction(0.0, 1.0, 0.05), 1), "m")

    # Calibration SDB synthetique
    psdb = [1.0 + 0.02 * i for i in range(40)]
    depth = [-(1.5 + 0.62 * (v - 1.0) / 0.02 * 0.02 * 10) for v in psdb]
    print("calibration SDB :", {k: round(v, 3)
                                for k, v in calibrate_sdb(psdb, depth).items()})
