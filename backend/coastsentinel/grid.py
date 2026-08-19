"""Évaluation du moteur sur une grille régulière — champs cartographiques."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .engine import Site
from .physics import sallenger_regime, stockdon_runup, wave_power

CHAMPS = ("alerte", "twl", "hs", "anom", "tp", "power", "r2", "sl")


def build_axes(
    sud: float, nord: float, ouest: float, est: float, nx: int, ny: int
) -> tuple[list[float], list[float]]:
    lats = [sud + (nord - sud) * (i / (ny - 1)) for i in range(ny)]
    lons = [ouest + (est - ouest) * (j / (nx - 1)) for j in range(nx)]
    return lats, lons


def flatten(lats: Sequence[float], lons: Sequence[float]
            ) -> tuple[list[float], list[float]]:
    """Produit les deux vecteurs plats attendus par la requête multi-points."""
    fl_lat, fl_lon = [], []
    for la in lats:
        for lo in lons:
            fl_lat.append(la)
            fl_lon.append(((lo + 540.0) % 360.0) - 180.0)
    return fl_lat, fl_lon


def compute(
    lats: Sequence[float], lons: Sequence[float], times: Sequence[str],
    cells: Sequence[dict[str, Any] | None], site: Site,
    p95_eff: float, p99_eff: float, ref_p95: float,
) -> dict[str, Any]:
    """Évalue le moteur en chaque nœud et retourne les champs par pas de temps.

    Les nœuds à terre valent ``None`` : le masque terre/mer reste net, on
    n'extrapole jamais une valeur de houle par-dessus la côte.
    """
    ny, nx, nt = len(lats), len(lons), len(times)
    champs: dict[str, list[list[list[float | None]]]] = {
        k: [[[None] * nx for _ in range(ny)] for _ in range(nt)]
        for k in CHAMPS
    }
    directions: list[list[list[float | None]]] = [
        [[None] * nx for _ in range(ny)] for _ in range(nt)
    ]
    stats = {k: {"min": math.inf, "max": -math.inf} for k in CHAMPS}
    # Couverture : combien de valeurs le champ porte réellement. Un champ à
    # zéro n'est pas un champ nul, c'est un champ que le fournisseur n'a pas
    # servi — et l'interface doit le dire au lieu d'afficher une carte vide.
    couverture = dict.fromkeys(CHAMPS, 0)
    couverture_dir = {"direction": 0}
    n_mer = 0

    for idx, cell in enumerate(cells):
        i, j = divmod(idx, nx)
        if cell is None:
            continue
        n_mer += 1
        for t in range(nt):
            hs = cell["hs"][t]
            if hs is None or hs != hs:
                continue
            tp = cell["tp"][t] or 8.0
            sl = cell["sl"][t]
            if sl is None or sl != sl:
                sl = 0.0
            ru = stockdon_runup(hs, tp, site.beta_f)
            r_high, r_low = sl + ru.r2, sl + ru.setup
            regime = sallenger_regime(r_high, r_low, site.z_berme, site.z_crete)

            niveau = 2 if r_high >= p99_eff else 1 if r_high >= p95_eff else 0
            if regime.rank >= 3:
                niveau = 3
            elif regime.rank == 2:
                niveau = max(niveau, 2)

            values = {
                "alerte": float(niveau),
                "twl": r_high,
                "hs": hs,
                "anom": hs / ref_p95 if ref_p95 > 0 else None,
                "tp": tp,
                "power": wave_power(hs, 0.9 * tp),
                "r2": ru.r2,
                "sl": sl,
            }
            for k, v in values.items():
                if v is None or v != v:
                    continue
                champs[k][t][i][j] = round(v, 4)
                couverture[k] += 1
                stats[k]["min"] = min(stats[k]["min"], v)
                stats[k]["max"] = max(stats[k]["max"], v)

            d = cell["dir"][t]
            if d is not None and d == d:
                directions[t][i][j] = round(float(d), 1)
                couverture_dir["direction"] += 1

    for s in stats.values():
        if not math.isfinite(s["min"]):
            s["min"], s["max"] = 0.0, 1.0
        s["min"], s["max"] = round(s["min"], 4), round(s["max"], 4)

    return {
        "champs": champs, "directions": directions, "stats": stats,
        "n_mer": n_mer, "n_total": nx * ny,
        "couverture": couverture | couverture_dir,
        "champs_disponibles": [k for k in CHAMPS if couverture[k] > 0],
    }
