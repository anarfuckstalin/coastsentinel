"""API : contrats, validation d'entrée, dégradation propre."""

import pytest
from fastapi.testclient import TestClient

from coastsentinel.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    assert r.json()["statut"] == "ok"


def test_openapi_documente(client):
    # le schéma vit sous /api pour passer par le proxy du frontend
    spec = client.get("/api/openapi.json").json()
    assert spec["info"]["title"] == "CoastSentinel API"
    for route in ("/api/analyse", "/api/grille", "/api/stations", "/api/lieux"):
        assert route in spec["paths"]
    assert client.get("/api/docs").status_code == 200


def test_stations(client):
    r = client.get("/api/stations")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 90
    assert all(-90 <= s["lat"] <= 90 for s in d["stations"])
    assert all(-180 <= s["lon"] <= 180 for s in d["stations"])
    assert len({s["nom"] for s in d["stations"]}) == d["total"]
    assert "jamais au calcul" in d["note"]


def test_stations_filtre(client):
    d = client.get("/api/stations", params={"q": "maroc"}).json()
    assert 10 <= d["retournees"] < d["total"]
    assert any(s["nom"] == "Agadir" for s in d["stations"])


def test_analyse_demo(client):
    r = client.post("/api/analyse", json={
        "nom": "Agadir", "lat": 30.42, "lon": -9.62, "source": "demo",
        "profil": {"beta_f": 0.045, "z_berme": 2.2, "z_crete": 4.6},
    })
    assert r.status_code == 200
    d = r.json()
    assert d["niveau_max"] == 3
    assert d["niveau_label"] == "Rouge"
    assert d["pic"]["twl"] == pytest.approx(4.62, abs=0.02)
    assert d["pic"]["regime"] == "overwash"
    assert len(d["serie"]) == 120
    assert d["episodes"]
    assert any("générique" in a for a in d["avertissements"])


def test_analyse_refuse_une_crete_sous_la_berme(client):
    r = client.post("/api/analyse", json={
        "lat": 30.42, "lon": -9.62, "source": "demo",
        "profil": {"z_berme": 5.0, "z_crete": 2.0},
    })
    assert r.status_code == 422
    assert "crête" in r.text


def test_analyse_refuse_des_coordonnees_hors_bornes(client):
    r = client.post("/api/analyse",
                    json={"lat": 120, "lon": 0, "source": "demo"})
    assert r.status_code == 422


def test_analyse_refuse_une_seule_date(client):
    r = client.post("/api/analyse", json={
        "lat": 30.42, "lon": -9.62, "source": "demo", "start": "2026-01-01",
    })
    assert r.status_code == 422


def test_grille_demo(client):
    r = client.post("/api/grille", json={
        "sud": 29.8, "nord": 31.0, "ouest": -10.4, "est": -9.2,
        "nx": 5, "ny": 4, "source": "demo", "days": 2,
    })
    assert r.status_code == 200
    d = r.json()
    assert len(d["lats"]) == 4 and len(d["lons"]) == 5
    assert d["n_total"] == 20
    assert d["n_mer"] == 19            # un nœud à terre pour le masque
    for champ in ("alerte", "twl", "hs", "anom", "tp", "power", "r2", "sl"):
        assert champ in d["champs"]
        assert len(d["champs"][champ]) == len(d["times"])
    # le nœud à terre reste vide : pas d'extrapolation par-dessus la côte
    assert d["champs"]["hs"][0][-1][-1] is None
    assert d["stats"]["hs"]["max"] > d["stats"]["hs"]["min"]
    assert any("projection spatiale" in a for a in d["avertissements"])


def test_grille_expose_la_couverture(client):
    d = client.post("/api/grille", json={
        "sud": 29.8, "nord": 31.0, "ouest": -10.4, "est": -9.2,
        "nx": 5, "ny": 4, "source": "demo", "days": 1,
    }).json()
    assert set(d["champs_disponibles"]) == {
        "alerte", "twl", "hs", "anom", "tp", "power", "r2", "sl",
    }
    for champ in d["champs_disponibles"]:
        assert d["couverture"][champ] > 0
    assert d["couverture"]["direction"] > 0


def test_grille_couverture_partielle(client, monkeypatch):
    """Nœuds à terre : la couverture le reflète, sans faire échouer la carte."""
    from coastsentinel import sources

    async def _moitie_a_terre(_client, lats, _lons, **_kw):
        times = ["2026-08-19T00:00", "2026-08-19T01:00"]
        cells = [
            None if i % 2 else {
                "hs": [2.0, 2.2], "tp": [11.0, 11.0],
                "dir": [305.0, 300.0], "sl": [0.4, 0.5],
            }
            for i in range(len(lats))
        ]
        return times, cells

    monkeypatch.setattr(sources, "fetch_grid", _moitie_a_terre)
    d = client.post("/api/grille", json={
        "sud": 29.8, "nord": 31.0, "ouest": -10.4, "est": -9.2,
        "nx": 4, "ny": 3, "days": 1,
    }).json()

    assert d["n_mer"] == 6 and d["n_total"] == 12
    assert d["couverture"]["hs"] == 12          # 6 nœuds × 2 pas
    assert "hs" in d["champs_disponibles"]


def test_grille_refuse_une_emprise_trop_vaste(client):
    r = client.post("/api/grille", json={
        "sud": -40, "nord": 40, "ouest": -40, "est": 40, "source": "demo",
    })
    assert r.status_code == 422
    assert "trop vaste" in r.text


def test_grille_refuse_une_emprise_inversee(client):
    r = client.post("/api/grille", json={
        "sud": 31, "nord": 30, "ouest": -10, "est": -9, "source": "demo",
    })
    assert r.status_code == 422


def test_analyse_expose_les_grandeurs_oceaniques(client):
    d = client.post("/api/analyse", json={
        "lat": 30.42, "lon": -9.62, "source": "demo",
    }).json()
    pas = d["serie"][40]
    for champ in ("hs_houle", "dir_houle", "hs_vent", "courant", "sst"):
        assert pas[champ] is not None, champ
    assert set(d["variables_disponibles"]) >= {"houle de fond", "mer du vent"}


def test_analyse_fournit_une_rose(client):
    d = client.post("/api/analyse", json={
        "lat": 30.42, "lon": -9.62, "source": "demo",
    }).json()
    r = d["rose"]
    assert r is not None
    assert len(r["secteurs"]) == 16
    assert len(r["frequences"]) == 16
    assert all(len(ligne) == len(r["classes"]) for ligne in r["frequences"])
    total = sum(sum(ligne) for ligne in r["frequences"])
    assert total + r["calme"] == pytest.approx(1.0, abs=1e-6)
    # houle de démonstration venant du NO
    assert r["secteur_dominant"] in {"NO", "NNO", "ONO"}
    assert "non climatologique" in r["source"]


def test_grille_ne_porte_pas_les_champs_facultatifs(client):
    """Retirés de la carte : ils restent au niveau de l'analyse ponctuelle."""
    d = client.post("/api/grille", json={
        "sud": 29.8, "nord": 31.0, "ouest": -10.4, "est": -9.2,
        "nx": 4, "ny": 3, "source": "demo", "days": 1,
    }).json()
    for champ in ("houle", "courant", "sst"):
        assert champ not in d["champs"]
        assert champ not in d["couverture"]
    assert "directions_courant" not in d
