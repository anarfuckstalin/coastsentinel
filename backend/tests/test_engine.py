"""Moteur d'alerte, climatologie et couplage inter-échelles."""

import math
from dataclasses import replace

import pytest

from coastsentinel.climatology import Climatology, percentile
from coastsentinel.engine import Niveau, Site, evaluate
from coastsentinel.sources import demo_forcing


@pytest.fixture(scope="module")
def forcing():
    return demo_forcing(5)


@pytest.fixture
def site():
    return Site(nom="Test", lat=30.42, lon=-9.62, beta_f=0.045,
                z_berme=2.2, z_crete=4.6)


def test_percentile():
    s = [float(i) for i in range(101)]
    assert percentile(s, 50) == 50
    assert percentile(s, 95) == pytest.approx(95)
    assert percentile(s, 0) == 0 and percentile(s, 100) == 100
    assert math.isnan(percentile([], 50))


def test_forcage_demo_complet(forcing):
    n = len(forcing.times)
    assert n == 120
    assert len({n, len(forcing.hs), len(forcing.tp), len(forcing.sea_level)}) == 1
    assert all(h > 0 for h in forcing.hs)
    assert forcing.dt_hours == pytest.approx(1.0)


def test_chaine_complete(forcing, site):
    res = evaluate(forcing, site, Climatology())
    assert all(s.twl >= s.sea_level for s in res.steps)
    assert all(abs(s.twl - (s.sea_level + s.r2)) < 1e-9 for s in res.steps)
    assert all(0 <= s.niveau <= 3 for s in res.steps)
    assert res.niveau_max >= Niveau.ORANGE
    pic = max(res.steps, key=lambda s: s.twl)
    assert pic.niveau == res.niveau_max


def test_seuils_sans_climatologie_sont_generiques(forcing, site):
    res = evaluate(forcing, site, Climatology())
    assert "générique" in res.seuils_source


def test_couplage_erosion_abaisse_le_seuil(forcing, site):
    stable = evaluate(forcing, site, Climatology())
    erode = evaluate(forcing, replace(site, i_erosion=1.0), Climatology())
    assert erode.twl_p99_eff < stable.twl_p99_eff
    assert erode.heures_alerte >= stable.heures_alerte


def test_couplage_borne_a_50_pourcent(forcing, site):
    fort = evaluate(forcing, replace(site, i_erosion=1.0),
                    Climatology(), alpha=0.5)
    assert fort.facteur_couplage >= 0.5


def test_episodes_regroupent_les_pas_de_temps(forcing, site):
    res = evaluate(forcing, site, Climatology())
    assert res.alertes
    for ep in res.alertes:
        assert ep["duree_h"] > 0
        assert ep["debut"] <= ep["fin"]
        assert 1 <= ep["niveau"] <= 3


def test_climatologie_depuis_serie():
    import random
    rng = random.Random(7)
    serie = []
    for i in range(30 * 365 * 24 // 6):        # 30 ans au pas de 6 h
        doy = (i * 6 / 24) % 365.25
        seas = 1.55 + 0.75 * math.cos(2 * math.pi * (doy - 15) / 365.25)
        storm = abs(rng.gauss(2.4, 1.1)) if rng.random() < 1 / (4 * 45) else 0.0
        serie.append(max(0.25, seas + rng.gauss(0, 0.28) + storm))

    clim = Climatology.from_series(serie, dt_hours=6.0)
    assert clim.hs_p50 < clim.hs_p95 < clim.hs_p99 < clim.hs_p999
    assert clim.annees == pytest.approx(30, abs=1)
    assert clim.confiance.value == "élevée"
    assert clim.hs_sample

    if clim.hs_return:
        vals = [clim.hs_return[t] for t in sorted(clim.hs_return)]
        assert vals == sorted(vals), "périodes de retour non monotones"
        # garde-fou physique : pas de queue non physique
        assert vals[-1] < 3 * clim.hs_p999
        assert clim.gpd_diag["forme"] <= 0.25


def test_seuils_conjoints_avec_climatologie(forcing, site):
    clim = Climatology.from_series([1.5] * 5000 + [3.0] * 5000)
    res = evaluate(forcing, site, clim)
    assert "reconstruite" in res.seuils_source
    assert res.twl_p95 < res.twl_p99


def test_climatologie_trop_courte_reste_generique():
    clim = Climatology.from_series([1.0] * 100)
    assert clim.annees == 0
    assert clim.confiance.value == "faible"


def test_niveau_labels_et_actions():
    for n in Niveau:
        assert n.label and n.action
    assert Niveau.ROUGE.label == "Rouge"
