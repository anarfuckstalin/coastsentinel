"""Roses de direction — centrage des secteurs et conservation des fréquences."""

import math

import pytest

from coastsentinel.rose import BORNES_HS, SECTEURS_16, rose


def test_secteurs_centres_sur_les_caps():
    """« N » couvre [-11,25° ; +11,25°[ et non [0° ; 22,5°[.

    Oublier ce demi-secteur décale toute la rose : c'est l'erreur classique.
    """
    assert rose([1.0], [0.0], source="t").secteur_dominant == "N"
    assert rose([1.0], [355.0], source="t").secteur_dominant == "N"
    assert rose([1.0], [11.0], source="t").secteur_dominant == "N"
    assert rose([1.0], [12.0], source="t").secteur_dominant == "NNE"
    assert rose([1.0], [45.0], source="t").secteur_dominant == "NE"
    assert rose([1.0], [180.0], source="t").secteur_dominant == "S"
    assert rose([1.0], [270.0], source="t").secteur_dominant == "O"


def test_frequences_somment_a_un():
    import random
    rng = random.Random(11)
    vals = [max(0.1, rng.gauss(2.0, 0.8)) for _ in range(3000)]
    dirs = [rng.uniform(0, 360) for _ in range(3000)]
    r = rose(vals, dirs, source="t")
    total = sum(sum(ligne) for ligne in r.frequences)
    assert total + r.calme == pytest.approx(1.0, abs=1e-9)
    assert r.n == 3000


def test_classes_et_bornes():
    r = rose([0.2, 0.8, 1.2, 2.5, 5.0], [0] * 5, source="t")
    assert len(r.classes) == len(BORNES_HS) + 1
    # une valeur au-delà de la dernière borne tombe dans la classe ouverte
    assert r.frequences[0][-1] == pytest.approx(0.2)
    assert r.frequences[0][0] == pytest.approx(0.2)   # < 0,5 m


def test_valeurs_invalides_ignorees():
    r = rose([1.0, float("nan"), -1.0, 2.0], [10, 20, 30, 40], source="t")
    assert r.n == 2


def test_huit_secteurs():
    r = rose([1.0] * 10, [90.0] * 10, source="t", n_secteurs=8)
    assert len(r.secteurs) == 8
    assert r.secteur_dominant == "E"


def test_secteurs_refuses_hors_8_ou_16():
    with pytest.raises(ValueError):
        rose([1.0], [0.0], source="t", n_secteurs=12)


def test_seuil_de_calme():
    r = rose([0.1, 0.1, 3.0, 3.0], [0] * 4, source="t", seuil_calme=0.5)
    assert r.calme == pytest.approx(0.5)
    assert sum(sum(x) for x in r.frequences) == pytest.approx(0.5)


def test_serie_vide():
    r = rose([], [], source="t")
    assert r.n == 0 and not r.frequences


def test_statistiques_sur_les_valeurs_retenues():
    r = rose([1.0, 2.0, 3.0, 4.0], [0] * 4, source="t")
    assert r.moyenne == pytest.approx(2.5)
    assert r.p95 >= 3.0
    assert not math.isnan(r.p95)


def test_noms_de_secteurs_uniques():
    assert len(set(SECTEURS_16)) == 16
