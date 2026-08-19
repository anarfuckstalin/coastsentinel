"""Climatologie locale — ce qui rend le système transposable partout.

Les seuils d'alerte ne sont jamais des valeurs absolues codées en dur mais
des percentiles de la distribution locale, reconstruits en tout point du
globe depuis une réanalyse. C'est le choix de conception central.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

log = logging.getLogger(__name__)


class Confiance(StrEnum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    ELEVEE = "élevée"


def percentile(sorted_values: Sequence[float], p: float) -> float:
    """Percentile par interpolation linéaire (``p`` en 0-100)."""
    if not sorted_values:
        return math.nan
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    k = (n - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_values[int(k)]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


@dataclass(slots=True)
class Climatology:
    """Seuils climatologiques locaux dérivés d'un hindcast."""

    source: str = "générique"
    confiance: Confiance = Confiance.FAIBLE
    annees: float = 0.0
    hs_p50: float = 1.2
    hs_p95: float = 2.8
    hs_p99: float = 3.6
    hs_p999: float = 4.6
    hs_return: dict[int, float] = field(default_factory=dict)
    gpd_diag: dict[str, object] = field(default_factory=dict)
    hs_sample: list[float] = field(default_factory=list)

    @classmethod
    def from_series(
        cls, hs: Sequence[float], source: str = "hindcast", *,
        dt_hours: float = 1.0, max_sample: int = 60_000,
    ) -> Climatology:
        """Construit la climatologie depuis une série de hauteurs significatives."""
        clean = [v for v in hs if v is not None and v == v and v >= 0]
        if len(clean) < 1000:
            log.warning("Hindcast trop court (%d pas) — seuils génériques",
                        len(clean))
            return cls()

        ordered = sorted(clean)
        annees = len(clean) * dt_hours / (365.25 * 24.0)
        conf = (Confiance.ELEVEE if annees >= 20
                else Confiance.MOYENNE if annees >= 10
                else Confiance.FAIBLE)

        clim = cls(
            source=source,
            confiance=conf,
            annees=round(annees, 1),
            hs_p50=percentile(ordered, 50),
            hs_p95=percentile(ordered, 95),
            hs_p99=percentile(ordered, 99),
            hs_p999=percentile(ordered, 99.9),
        )
        clim.hs_return, clim.gpd_diag = gpd_return_levels(
            clean, clim.hs_p99, annees, clim.hs_p999, dt_hours=dt_hours
        )
        step = max(1, len(clean) // max_sample)
        clim.hs_sample = clean[::step]
        return clim


def gpd_return_levels(
    hs: Sequence[float], threshold: float, annees: float, p999: float, *,
    dt_hours: float = 1.0,
) -> tuple[dict[int, float], dict[str, object]]:
    """Niveaux de période de retour par POT/GPD avec déclustering 72 h.

    Garde-fou physique : pour la hauteur significative, le paramètre de forme
    de la GPD est normalement ≤ 0 (queue bornée ou exponentielle). Une forme
    fortement positive produit des niveaux non physiques — on rebascule alors
    sur un ajustement à forme nulle, pratique usuelle en climatologie de houle,
    et le diagnostic est conservé.
    """
    try:
        from scipy.stats import genpareto
    except ImportError:  # pragma: no cover - dépendance optionnelle
        return {}, {"methode": "indisponible (scipy absent)"}

    window = max(1, int(round(72.0 / dt_hours)))
    peaks: list[float] = []
    i, n = 0, len(hs)
    while i < n:
        if hs[i] > threshold:
            j = i
            local: list[float] = []
            while j < n and hs[j] > threshold:
                local.append(hs[j])
                j += 1
            peaks.append(max(local))
            i = j + window
        else:
            i += 1

    if len(peaks) < 20 or annees <= 0:
        return {}, {"methode": f"échantillon de pics insuffisant ({len(peaks)})"}

    excess = [p - threshold for p in peaks]
    try:
        shape, _loc, scale = genpareto.fit(excess, floc=0.0)
    except Exception as exc:  # pragma: no cover
        return {}, {"methode": f"échec de l'ajustement GPD ({exc})"}

    lam = len(peaks) / annees
    methode = "GPD/POT (seuil P99, déclustering 72 h)"

    def levels(sh: float, sc: float) -> dict[int, float]:
        out: dict[int, float] = {}
        for t in (1, 2, 5, 10, 25, 50, 100):
            p = 1.0 - 1.0 / (lam * t)
            if not 0.0 < p < 1.0:
                continue
            out[t] = float(threshold + genpareto.ppf(p, sh, loc=0.0, scale=sc))
        return out

    out = levels(shape, scale)
    top = out.get(100) or (max(out.values()) if out else 0.0)
    if shape > 0.25 or (p999 > 0 and top > 3.0 * p999):
        mean_excess = sum(excess) / len(excess)
        out = levels(0.0, mean_excess)
        methode = (
            "GPD/POT à forme contrainte à 0 (queue exponentielle) — "
            f"l'ajustement libre donnait une queue non physique (forme = {shape:.2f})"
        )
        shape, scale = 0.0, mean_excess

    diag = {
        "methode": methode,
        "forme": round(float(shape), 3),
        "echelle": round(float(scale), 3),
        "n_pics": len(peaks),
        "pics_par_an": round(lam, 2),
        "seuil": round(threshold, 3),
    }
    return out, diag


def load_hindcast_csv(path: str, hs_col: str = "hs") -> Climatology:
    """Charge un hindcast depuis un CSV (export ERA5 ou CMEMS-reanalysis)."""
    import csv
    import os

    hs: list[float] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
        col = (cols.get(hs_col) or cols.get("swh") or cols.get("hs")
               or cols.get("wave_height") or cols.get("vhm0"))
        if col is None:
            raise ValueError(
                f"Colonne de hauteur significative introuvable dans {path} "
                "(attendu : hs / swh / VHM0 / wave_height)"
            )
        for row in reader:
            try:
                hs.append(float(row[col]))
            except (TypeError, ValueError):
                continue
    return Climatology.from_series(hs, source=os.path.basename(path))
