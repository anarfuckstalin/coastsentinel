"""Moteur d'alerte : seuils climatologiques, couplage inter-échelles, niveaux."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

from .climatology import Climatology, percentile
from .physics import (
    hs_to_tp,
    sallenger_regime,
    stockdon_runup,
    storm_power_index,
    wave_power,
)

SEED = 20260817  # tirage reproductible pour la convolution houle × marée


class Niveau(IntEnum):
    VERT = 0
    JAUNE = 1
    ORANGE = 2
    ROUGE = 3

    @property
    def label(self) -> str:
        return ("Vert", "Jaune", "Orange", "Rouge")[int(self)]

    @property
    def action(self) -> str:
        return (
            "Veille — conditions dans la normale climatologique.",
            "Vigilance — information baignade et usagers du littoral.",
            "Alerte — fermeture des plages, protection des ouvrages et des accès bas.",
            "Alerte majeure — mise en sécurité des personnes, "
            "activation de la protection civile.",
        )[int(self)]


@dataclass(slots=True)
class Site:
    """Profil de plage et état morphologique d'un point d'analyse."""

    nom: str = "Site"
    lat: float = 0.0
    lon: float = 0.0
    beta_f: float = 0.05
    beta_source: str = "défaut générique"
    z_berme: float = 2.0
    z_crete: float = 4.5
    msl_trend: float = 0.0
    i_erosion: float = 0.0
    erosion_age_jours: int | None = None


@dataclass(slots=True)
class Forcing:
    """Série temporelle de forçage au large."""

    times: list[str]
    hs: list[float]
    tp: list[float]
    direction: list[float]
    sea_level: list[float]
    surge: list[float]
    source: str
    note: str = ""
    tide_estimee: bool = False
    # Grandeurs océaniques complémentaires — None si non servies pour ce point
    hs_vent: list[float] | None = None
    dir_vent: list[float] | None = None
    tp_vent: list[float] | None = None
    hs_houle: list[float] | None = None
    dir_houle: list[float] | None = None
    tp_houle: list[float] | None = None
    courant: list[float] | None = None
    courant_dir: list[float] | None = None
    sst: list[float] | None = None

    @property
    def variables_disponibles(self) -> list[str]:
        """Grandeurs complémentaires réellement servies pour ce point."""
        noms = {
            "mer du vent": self.hs_vent, "houle de fond": self.hs_houle,
            "courant de surface": self.courant,
            "température de surface": self.sst,
        }
        return [k for k, v in noms.items() if v]

    @property
    def dt_hours(self) -> float:
        if len(self.times) < 2:
            return 1.0
        a = datetime.fromisoformat(self.times[0].replace("Z", ""))
        b = datetime.fromisoformat(self.times[1].replace("Z", ""))
        return (b - a).total_seconds() / 3600.0


@dataclass(slots=True)
class Step:
    t: str
    hs: float
    tp: float
    direction: float
    sea_level: float
    surge: float
    setup: float
    swash: float
    r2: float
    xi0: float
    twl: float
    regime: str
    rank: int
    power: float
    niveau: int
    hs_vent: float | None = None
    dir_vent: float | None = None
    hs_houle: float | None = None
    dir_houle: float | None = None
    tp_houle: float | None = None
    courant: float | None = None
    courant_dir: float | None = None
    sst: float | None = None


@dataclass(slots=True)
class Result:
    steps: list[Step]
    niveau_max: int
    pic: Step
    twl_p95: float
    twl_p99: float
    twl_p95_eff: float
    twl_p99_eff: float
    facteur_couplage: float
    seuils_source: str
    spi: float
    heures_alerte: float
    dt_h: float
    regime_max: int
    climatologie: Climatology
    forcing: Forcing
    site: Site
    alertes: list[dict] = field(default_factory=list)
    rose: object | None = None


def _at(serie: list[float] | None, i: int) -> float | None:
    """Valeur facultative au pas ``i`` — ``None`` si la série est absente."""
    if not serie or i >= len(serie):
        return None
    v = serie[i]
    return None if v is None or v != v else float(v)


def twl_thresholds(
    forcing: Forcing, site: Site, clim: Climatology
) -> tuple[float, float, str]:
    """Percentiles de la **distribution conjointe** de TWL.

    Point méthodologique : additionner le P99 de houle et le P99 de marée
    supposerait leur concomitance systématique et surestimerait le seuil. On
    reconstruit la distribution de TWL en combinant chaque valeur du hindcast
    de houle à un niveau d'eau tiré de la distribution de marée observée.
    """
    tide = sorted(v for v in forcing.sea_level if v == v)
    if clim.hs_sample and len(tide) > 8:
        rng = random.Random(SEED)
        samples = [
            tide[rng.randrange(len(tide))]
            + stockdon_runup(h, hs_to_tp(h), site.beta_f).r2
            for h in clim.hs_sample
        ]
        samples.sort()
        return (
            percentile(samples, 95),
            percentile(samples, 99),
            f"distribution TWL reconstruite ({clim.annees:.1f} ans × marée)",
        )

    def pour(hs_ref: float) -> float:
        return percentile(tide, 90) + stockdon_runup(
            hs_ref, hs_to_tp(hs_ref), site.beta_f
        ).r2

    return (pour(clim.hs_p95), pour(clim.hs_p99),
            "repli générique (aucune climatologie locale)")


def evaluate(
    forcing: Forcing, site: Site, clim: Climatology, *, alpha: float = 0.2
) -> Result:
    """Applique M1 + M2 et le couplage inter-échelles M5."""
    p95, p99, seuils_source = twl_thresholds(forcing, site, clim)

    # Couplage M5 : l'état morphologique lent abaisse le seuil événementiel
    facteur = max(0.5, 1.0 - alpha * min(max(site.i_erosion, 0.0), 1.0))
    p95_eff, p99_eff = p95 * facteur, p99 * facteur

    t25 = clim.hs_return.get(25) or clim.hs_return.get(10)
    t5 = clim.hs_return.get(5)

    steps: list[Step] = []
    for i, t in enumerate(forcing.times):
        hs, tp = forcing.hs[i], forcing.tp[i]
        ru = stockdon_runup(hs, tp, site.beta_f)
        sl = forcing.sea_level[i] + site.msl_trend
        r_high, r_low = sl + ru.r2, sl + ru.setup
        regime = sallenger_regime(r_high, r_low, site.z_berme, site.z_crete)

        niveau = (2 if r_high >= p99_eff else 1 if r_high >= p95_eff else 0)
        if t25 and hs >= t25:
            niveau = max(niveau, 3)
        elif t5 and hs >= t5:
            niveau = max(niveau, 2)
        if regime.rank >= 3:
            niveau = 3
        elif regime.rank == 2:
            niveau = max(niveau, 2)

        steps.append(Step(
            t=t, hs=hs, tp=tp, direction=forcing.direction[i],
            sea_level=sl, surge=forcing.surge[i],
            setup=ru.setup, swash=ru.swash, r2=ru.r2, xi0=ru.xi0,
            twl=r_high, regime=regime.value, rank=regime.rank,
            power=wave_power(hs, 0.9 * tp), niveau=niveau,
            hs_vent=_at(forcing.hs_vent, i), dir_vent=_at(forcing.dir_vent, i),
            hs_houle=_at(forcing.hs_houle, i), dir_houle=_at(forcing.dir_houle, i),
            tp_houle=_at(forcing.tp_houle, i),
            courant=_at(forcing.courant, i), courant_dir=_at(forcing.courant_dir, i),
            sst=_at(forcing.sst, i),
        ))

    _escalade_persistance(steps, forcing.dt_hours)

    pic = max(steps, key=lambda s: s.twl)
    niveau_max = max(s.niveau for s in steps)
    dt = forcing.dt_hours

    return Result(
        steps=steps,
        niveau_max=niveau_max,
        pic=pic,
        twl_p95=p95, twl_p99=p99,
        twl_p95_eff=p95_eff, twl_p99_eff=p99_eff,
        facteur_couplage=facteur,
        seuils_source=seuils_source,
        spi=storm_power_index([s.hs for s in steps], clim.hs_p95, dt),
        heures_alerte=sum(dt for s in steps if s.niveau >= 1),
        dt_h=dt,
        regime_max=max(s.rank for s in steps),
        climatologie=clim, forcing=forcing, site=site,
        alertes=_episodes(steps, dt),
    )


def _escalade_persistance(steps: list[Step], dt: float, heures: float = 12.0) -> None:
    """12 h consécutives au même niveau font monter d'un cran.

    L'érosion est cumulative : c'est la durée qui détruit la plage, pas le pic.
    """
    if not steps:
        return
    need = max(1, int(round(heures / dt)))
    start, lvl = 0, steps[0].niveau
    for i in range(1, len(steps) + 1):
        cur = steps[i].niveau if i < len(steps) else -1
        if cur != lvl:
            if 1 <= lvl < 3 and (i - start) >= need:
                for k in range(start, i):
                    steps[k].niveau = min(3, steps[k].niveau + 1)
            start, lvl = i, cur


def _episodes(steps: Sequence[Step], dt: float, seuil: int = 1) -> list[dict]:
    """Regroupe les pas de temps en épisodes d'alerte homogènes."""
    out: list[dict] = []
    cur: dict | None = None
    for s in steps:
        if s.niveau >= seuil:
            if cur and cur["niveau"] == s.niveau:
                cur["fin"] = s.t
                cur["duree_h"] += dt
                cur["twl_max"] = max(cur["twl_max"], s.twl)
                cur["hs_max"] = max(cur["hs_max"], s.hs)
            else:
                if cur:
                    out.append(cur)
                cur = {"debut": s.t, "fin": s.t, "niveau": s.niveau,
                       "duree_h": dt, "twl_max": s.twl, "hs_max": s.hs,
                       "regime": s.regime}
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out
