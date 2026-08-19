"""Cohérence physique — valeurs de référence issues des articles cités."""

import math

import pytest

from coastsentinel.physics import (
    BeachRegime,
    ImpactRegime,
    deep_water_wavelength,
    hs_to_tp,
    iribarren,
    sallenger_regime,
    stockdon_runup,
    storm_power_index,
    wave_power,
)


def test_longueur_onde():
    assert deep_water_wavelength(10.0) == pytest.approx(156.13, abs=0.01)
    assert deep_water_wavelength(20.0) / deep_water_wavelength(10.0) == pytest.approx(4.0)


def test_iribarren():
    l0 = deep_water_wavelength(10.0)
    assert iribarren(0.05, 2.0, l0) == pytest.approx(0.4418, abs=1e-3)
    assert math.isinf(iribarren(0.05, 0.0, l0))


def test_stockdon_valeurs_publiees():
    r = stockdon_runup(2.0, 10.0, 0.05)
    assert r.setup == pytest.approx(0.3092, abs=5e-4)
    assert r.swash == pytest.approx(1.2994, abs=5e-4)
    assert r.r2 == pytest.approx(1.0549, abs=5e-4)
    assert r.regime is BeachRegime.INTERMEDIAIRE


def test_stockdon_bascule_dissipative():
    r = stockdon_runup(3.0, 12.0, 0.008)
    assert r.regime is BeachRegime.DISSIPATIF
    assert r.xi0 < 0.3
    assert r.r2 == pytest.approx(0.043 * math.sqrt(3.0 * deep_water_wavelength(12.0)))


def test_stockdon_monotonie():
    assert stockdon_runup(4, 10, 0.05).r2 > stockdon_runup(2, 10, 0.05).r2
    assert stockdon_runup(2, 10, 0.10).r2 > stockdon_runup(2, 10, 0.03).r2
    assert stockdon_runup(0, 10, 0.05).r2 == 0.0
    assert stockdon_runup(0, 10, 0.05).regime is BeachRegime.CALME


def test_puissance_houle():
    # règle usuelle en génie côtier : P ≈ 0,5·Hs²·Te
    assert wave_power(2.0, 9.0) == pytest.approx(18.0, abs=1.0)
    assert wave_power(4.0, 9.0) / wave_power(2.0, 9.0) == pytest.approx(4.0)


@pytest.mark.parametrize("r_high,r_low,attendu", [
    (1.5, 0.5, ImpactRegime.SWASH),
    (3.0, 1.0, ImpactRegime.COLLISION),
    (4.5, 1.0, ImpactRegime.OVERWASH),
    (6.0, 4.5, ImpactRegime.INUNDATION),
])
def test_sallenger(r_high, r_low, attendu):
    assert sallenger_regime(r_high, r_low, 2.0, 4.0) is attendu


def test_sallenger_rangs_ordonnes():
    rangs = [sallenger_regime(*a, 2.0, 4.0).rank
             for a in [(1.5, .5), (3, 1), (4.5, 1), (6, 4.5)]]
    assert rangs == sorted(rangs) == [1, 2, 3, 4]


def test_spi_ne_compte_que_les_depassements():
    assert storm_power_index([1, 3, 4, 2], 2.5, 1.0) == pytest.approx(25.0)


def test_hs_to_tp_croissante():
    assert hs_to_tp(4) > hs_to_tp(1) > 0
