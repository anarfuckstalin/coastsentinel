"""Champs de grille : couverture réellement servie, masque terre/mer.

La grille ne porte que des grandeurs dérivées du socle vagues + niveau d'eau.
Les grandeurs facultatives (houle de fond, courant, température) restent au
niveau de l'analyse ponctuelle : sur une grille, elles multiplient le volume
transféré par le nombre de nœuds pour une couverture très inégale.
"""

from __future__ import annotations

import math

import pytest

from coastsentinel import grid as gridmod
from coastsentinel.engine import Site

SITE = Site(nom="test", lat=30.4, lon=-9.7, beta_f=0.045,
            z_berme=2.2, z_crete=4.6)

RETIRES = ("houle", "courant", "sst", "courant_dir")


def _cellule(n: int) -> dict:
    return {
        "hs": [2.0] * n,
        "tp": [11.0] * n,
        "dir": [305.0] * n,
        "sl": [0.4] * n,
    }


def _grille(nt: int = 3, terre: int = 0):
    lats = [30.2, 30.4, 30.6]
    lons = [-9.9, -9.7, -9.5]
    times = [f"2026-08-19T{h:02d}:00" for h in range(nt)]
    cells: list[dict | None] = [_cellule(nt) for _ in range(len(lats) * len(lons))]
    for i in range(terre):
        cells[i] = None
    return gridmod.compute(lats, lons, times, cells, SITE, 2.5, 3.2, 2.0)


def test_couverture_complete():
    res = _grille()
    attendu = 3 * 9                       # trois pas de temps, neuf nœuds
    for champ in gridmod.CHAMPS:
        assert res["couverture"][champ] == attendu, champ
    assert set(res["champs_disponibles"]) == set(gridmod.CHAMPS)
    assert res["couverture"]["direction"] == attendu


def test_les_champs_facultatifs_ne_sont_plus_calcules():
    """Garde-fou : ces champs ont été retirés de la grille, pas déplacés."""
    res = _grille()
    for champ in RETIRES:
        assert champ not in res["champs"]
        assert champ not in res["couverture"]
        assert champ not in gridmod.CHAMPS
    assert "directions_courant" not in res


def test_les_noeuds_a_terre_restent_vides():
    """Aucune extrapolation par-dessus la côte : le masque est strict."""
    res = _grille(terre=2)
    assert res["n_mer"] == 7
    assert res["n_total"] == 9
    assert res["champs"]["hs"][0][0][0] is None
    assert res["champs"]["hs"][0][0][1] is None
    assert res["couverture"]["hs"] == 3 * 7


def test_stats_degradees_sur_grille_entierement_a_terre():
    """Sans un seul nœud servi, l'échelle reste finie — jamais des infinis."""
    lats, lons = [30.2, 30.4], [-9.9, -9.7]
    times = ["2026-08-19T00:00"]
    res = gridmod.compute(lats, lons, times, [None] * 4, SITE, 2.5, 3.2, 2.0)
    assert res["n_mer"] == 0
    assert res["champs_disponibles"] == []
    for champ in gridmod.CHAMPS:
        s = res["stats"][champ]
        assert math.isfinite(s["min"]) and math.isfinite(s["max"])
        assert (s["min"], s["max"]) == (0.0, 1.0)


def test_anomalie_relative_au_percentile_de_reference():
    """L'anomalie est un rapport à P95 local, pas une valeur absolue."""
    res = gridmod.compute(
        [30.2, 30.4], [-9.9, -9.7], ["2026-08-19T00:00"],
        [_cellule(1)] * 4, SITE, 2.5, 3.2, ref_p95=4.0,
    )
    assert res["champs"]["anom"][0][0][0] == pytest.approx(0.5)


@pytest.mark.parametrize("champ", gridmod.CHAMPS)
def test_tous_les_champs_declares_sont_comptes(champ):
    res = _grille()
    assert champ in res["couverture"]
    assert champ in res["champs"]
