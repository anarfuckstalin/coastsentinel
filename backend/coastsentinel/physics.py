"""Paramétrisations physiques publiées.

Chaque fonction implémente une formulation issue de la littérature évaluée
par les pairs, citée dans sa docstring. Aucune constante d'ajustement
maison : ce module doit rester auditable ligne à ligne face aux articles.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

G: Final[float] = 9.81       # accélération de la pesanteur, m/s²
RHO: Final[float] = 1025.0   # masse volumique de l'eau de mer, kg/m³


class BeachRegime(StrEnum):
    """Régime de plage au sens du nombre d'Iribarren."""

    CALME = "calme"
    DISSIPATIF = "dissipatif"
    INTERMEDIAIRE = "intermédiaire"
    REFLECHISSANT = "réfléchissant"


class ImpactRegime(StrEnum):
    """Échelle d'impact de tempête — Sallenger (2000)."""

    SWASH = "swash"
    COLLISION = "collision"
    OVERWASH = "overwash"
    INUNDATION = "inundation"

    @property
    def rank(self) -> int:
        return {"swash": 1, "collision": 2, "overwash": 3, "inundation": 4}[
            self.value
        ]


@dataclass(frozen=True, slots=True)
class Runup:
    """Décomposition du jet de rive."""

    setup: float
    swash: float
    r2: float
    xi0: float
    regime: BeachRegime


def deep_water_wavelength(tp: float) -> float:
    """Longueur d'onde en eau profonde ``L0 = g·Tp²/2π`` [m]."""
    return G * tp * tp / (2.0 * math.pi)


def iribarren(beta: float, h0: float, l0: float) -> float:
    """Nombre d'Iribarren au large ``ξ0 = β / √(H0/L0)`` [-]."""
    if h0 <= 0 or l0 <= 0:
        return math.inf
    return beta / math.sqrt(h0 / l0)


def stockdon_runup(h0: float, tp: float, beta: float) -> Runup:
    """Jet de rive ``R2%`` — Stockdon, Holman, Howd & Sallenger (2006),
    *Coastal Engineering* 53(7), 573-588.

    Domaine de validité : plages sableuses ouvertes à pente modérée.
    L'écart-type publié sur R2% est de l'ordre de ±20 %.
    """
    if h0 <= 0 or tp <= 0:
        return Runup(0.0, 0.0, 0.0, 0.0, BeachRegime.CALME)

    l0 = deep_water_wavelength(tp)
    xi0 = iribarren(beta, h0, l0)
    root = math.sqrt(h0 * l0)

    if xi0 < 0.3:
        # Régime dissipatif : setup et swash saturent
        return Runup(0.016 * root, 0.046 * root, 0.043 * root, xi0,
                     BeachRegime.DISSIPATIF)

    setup = 0.35 * beta * root
    swash = math.sqrt(h0 * l0 * (0.563 * beta * beta + 0.004))
    regime = (BeachRegime.REFLECHISSANT if xi0 > 1.25
              else BeachRegime.INTERMEDIAIRE)
    return Runup(setup, swash, 1.1 * (setup + swash / 2.0), xi0, regime)


def wave_power(hs: float, te: float) -> float:
    """Flux d'énergie de la houle en eau profonde [kW/m de crête].

    ``P = ρg²Hs²Te / 64π``. Règle usuelle en génie côtier : ``P ≈ 0,5·Hs²·Te``.
    """
    return RHO * G * G / (64.0 * math.pi) * hs * hs * te / 1000.0


def sallenger_regime(
    r_high: float, r_low: float, d_low: float, d_high: float
) -> ImpactRegime:
    """Régime d'impact morphologique — Sallenger (2000), *J. Coastal Res.* 16(3).

    ``r_high`` = niveau statique + R2% ; ``r_low`` = niveau statique + setup ;
    ``d_low`` = pied de dune ou berme ; ``d_high`` = crête.
    """
    if r_low >= d_high:
        return ImpactRegime.INUNDATION
    if r_high >= d_high:
        return ImpactRegime.OVERWASH
    if r_high >= d_low:
        return ImpactRegime.COLLISION
    return ImpactRegime.SWASH


def storm_power_index(
    hs_series: Sequence[float], threshold: float, dt_hours: float
) -> float:
    """Indice de puissance de tempête ``SPI = Σ Hs²·dt`` au-dessus du seuil.

    Dolan & Davis (1992), *J. Coastal Res.* 8(4), 840-853. Unité : m²·h.
    """
    return sum(h * h * dt_hours for h in hs_series if h >= threshold)


def hs_to_tp(hs: float) -> float:
    """Relation empirique Hs–Tp utilisée quand la période n'est pas fournie.

    ``Tp ≈ 4,5·√Hs`` — approximation usuelle pour une mer développée, à ne
    utiliser que faute de mieux (la période observée est toujours préférable).
    """
    return 4.5 * math.sqrt(max(hs, 0.1))
