"""API CoastSentinel — FastAPI.

Documentation interactive : http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import grid as gridmod
from . import sources
from .climatology import Climatology
from .engine import Niveau, Site, evaluate
from .rose import rose as calcule_rose
from .schemas import (
    AnalyseRequest,
    AnalyseResponse,
    ClimatologieOut,
    GrilleRequest,
    GrilleResponse,
    LieuOut,
    PasDeTemps,
    RoseOut,
    SeuilsOut,
)
from .stations import STATIONS
from .version import __version__

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("coastsentinel")

CACHE_TTL = float(os.getenv("CACHE_TTL", "900"))   # 15 min
_cache: dict[str, tuple[float, Any]] = {}


def cache_get(key: str) -> Any | None:
    hit = _cache.get(key)
    if not hit:
        return None
    ts, value = hit
    if time.monotonic() - ts > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return value


def cache_put(key: str, value: Any) -> Any:
    if len(_cache) > 512:
        _cache.clear()
    _cache[key] = (time.monotonic(), value)
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        headers={"User-Agent": f"CoastSentinel/{__version__}"},
        follow_redirects=True,
    )
    log.info("CoastSentinel %s — API prête", __version__)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="CoastSentinel API",
    version=__version__,
    summary="Système d'alerte côtière multi-échelle, transposable à tout littoral",
    description=(
        "Moteur d'alerte fondé sur des données ouvertes à crédibilité "
        "scientifique internationale. Les seuils sont **relatifs** — "
        "percentiles de la climatologie locale — jamais des valeurs absolues, "
        "ce qui rend le système applicable partout dans le monde.\n\n"
        "**Avertissement** : dispositif d'aide à la décision et de recherche. "
        "Ne se substitue en aucun cas aux alertes officielles des services "
        "nationaux compétents."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _site(req: AnalyseRequest | GrilleRequest, nom: str = "Site",
          lat: float = 0.0, lon: float = 0.0) -> Site:
    p = req.profil
    return Site(
        nom=nom, lat=lat, lon=lon,
        beta_f=p.beta_f, z_berme=p.z_berme, z_crete=p.z_crete,
        msl_trend=p.msl_trend, i_erosion=p.i_erosion,
    )


def _avertissements(clim: Climatology, forcing) -> list[str]:
    out: list[str] = []
    if clim.annees == 0:
        out.append(
            "Aucune climatologie locale : les seuils sont génériques et ne "
            "doivent être utilisés ni en opérationnel ni en publication."
        )
    elif clim.annees < 10:
        out.append(
            f"Climatologie courte ({clim.annees:.1f} ans) : les percentiles "
            "hauts et les périodes de retour sont peu robustes."
        )
    if forcing.tide_estimee:
        out.append(
            "Niveau d'eau non fourni pour ce point : une marée semi-diurne "
            "générique a été substituée. Coupler un atlas de marée (FES2022) "
            "ou un marégraphe proche pour un résultat exploitable."
        )
    return out


@app.get("/api/sante", tags=["système"], summary="État du service")
async def sante() -> dict[str, Any]:
    return {
        "statut": "ok",
        "version": __version__,
        "cache": len(_cache),
        # Permet à l'interface de reconnaître un backend resté sur une
        # version antérieure : c'est la cause n°1 des couches vides après
        # une mise à jour, le front se recharge tout seul, pas uvicorn.
        "champs": list(gridmod.CHAMPS),
    }


@app.get("/api/lieux", response_model=list[LieuOut], tags=["recherche"],
         summary="Recherche de villes et de ports")
async def lieux(q: str = Query(..., min_length=2, max_length=80)) -> list[LieuOut]:
    key = f"geo:{q.lower()}"
    if (hit := cache_get(key)) is not None:
        return hit
    try:
        res = await sources.geocode(app.state.http, q)
    except sources.SourceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    out = [
        LieuOut(
            nom=r["name"], lat=r["latitude"], lon=r["longitude"],
            pays=r.get("country"), region=r.get("admin1"),
            population=r.get("population"),
        )
        for r in res
    ]
    return cache_put(key, out)


@app.get("/api/stations", tags=["recherche"],
         summary="Réseau de stations de référence")
async def stations(q: str | None = None) -> dict[str, Any]:
    items = STATIONS
    if q:
        needle = q.lower()
        items = [
            s for s in STATIONS
            if needle in f"{s['nom']} {s['pays']} {s['region']}".lower()
        ]
    return {
        "total": len(STATIONS),
        "retournees": len(items),
        "stations": items,
        "note": (
            "Positions portuaires, précises à environ un kilomètre. Elles "
            "servent au repérage et à amorcer une analyse, jamais au calcul. "
            "Pour des positions officielles, importez la liste de "
            "l'IOC-UNESCO ou de votre réseau national."
        ),
    }


@app.post("/api/analyse", response_model=AnalyseResponse, tags=["analyse"],
          summary="Analyse d'alerte en un point")
async def analyse(req: AnalyseRequest) -> AnalyseResponse:
    key = f"an:{req.model_dump_json()}"
    if (hit := cache_get(key)) is not None:
        return hit

    client = app.state.http
    rose_obj = None
    try:
        if req.source == "demo":
            forcing = sources.demo_forcing(req.days)
            clim = Climatology()
        else:
            forcing = await sources.fetch_openmeteo(
                client, req.lat, req.lon,
                days=req.days, start=req.start, end=req.end,
            )
            clim = Climatology()
            if req.climatologie_annees > 0:
                try:
                    serie, dirs, dt = await sources.fetch_climatology_series(
                        client, req.lat, req.lon, req.climatologie_annees
                    )
                    clim = Climatology.from_series(
                        serie, source="Open-Meteo (réanalyse au point)",
                        dt_hours=dt,
                    )
                    if serie and dirs:
                        rose_obj = calcule_rose(
                            serie, dirs,
                            source=f"climatologie locale, {clim.annees:.1f} ans",
                        )
                except sources.SourceError as exc:
                    log.warning("Climatologie indisponible : %s", exc)
    except sources.SourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    site = _site(req, req.nom, req.lat, req.lon)
    res = evaluate(forcing, site, clim, alpha=req.profil.alpha)
    niveau = Niveau(res.niveau_max)

    if rose_obj is None:
        # Repli : rose sur la seule période analysée. Elle décrit un épisode,
        # pas un régime — la source le dit explicitement.
        rose_obj = calcule_rose(
            forcing.hs, forcing.direction,
            source="période analysée seulement — non climatologique",
        )

    out = AnalyseResponse(
        site=asdict(site),
        niveau_max=res.niveau_max,
        niveau_label=niveau.label,
        action=niveau.action,
        pic=PasDeTemps.model_validate(res.pic),
        seuils=SeuilsOut(
            twl_p95=res.twl_p95, twl_p99=res.twl_p99,
            twl_p95_eff=res.twl_p95_eff, twl_p99_eff=res.twl_p99_eff,
            facteur_couplage=res.facteur_couplage, source=res.seuils_source,
        ),
        climatologie=ClimatologieOut(
            source=clim.source, confiance=clim.confiance.value,
            annees=clim.annees, hs_p50=clim.hs_p50, hs_p95=clim.hs_p95,
            hs_p99=clim.hs_p99, hs_p999=clim.hs_p999,
            hs_return=clim.hs_return, gpd_diag=clim.gpd_diag,
        ),
        spi=res.spi, heures_alerte=res.heures_alerte, dt_h=res.dt_h,
        regime_max=res.regime_max,
        serie=[PasDeTemps.model_validate(s) for s in res.steps],
        episodes=res.alertes,
        source=forcing.source, note=forcing.note,
        tide_estimee=forcing.tide_estimee,
        variables_disponibles=forcing.variables_disponibles,
        rose=RoseOut.model_validate(rose_obj) if rose_obj.n else None,
        avertissements=_avertissements(clim, forcing),
    )
    return cache_put(key, out)


@app.post("/api/grille", response_model=GrilleResponse, tags=["cartographie"],
          summary="Champs cartographiques sur une emprise")
async def grille(req: GrilleRequest) -> GrilleResponse:
    key = f"gr:{req.model_dump_json()}"
    if (hit := cache_get(key)) is not None:
        return hit

    lats, lons = gridmod.build_axes(
        req.sud, req.nord, req.ouest, req.est, req.nx, req.ny
    )
    fl_lat, fl_lon = gridmod.flatten(lats, lons)

    try:
        if req.source == "demo":
            times, cells = _grille_demo(lats, lons, req.days)
        else:
            times, cells = await sources.fetch_grid(
                app.state.http, fl_lat, fl_lon,
                days=req.days, start=req.start, end=req.end,
            )
    except sources.SourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    site = _site(req)
    facteur = max(0.5, 1.0 - req.profil.alpha * req.profil.i_erosion)
    p95 = (req.seuil_p95 if req.seuil_p95 is not None else 2.5) * facteur
    p99 = (req.seuil_p99 if req.seuil_p99 is not None else 3.2) * facteur

    res = gridmod.compute(lats, lons, times, cells, site, p95, p99, req.ref_p95)

    avert = [
        "La couche d'alerte applique le profil de plage du panneau à TOUS les "
        "nœuds : c'est une projection spatiale du forçage, pas une carte de "
        "vulnérabilité. Les couches Hs, Tp, direction et niveau d'eau sont des "
        "grandeurs de modèle sans hypothèse ajoutée."
    ]
    if req.seuil_p95 is None:
        avert.append(
            "Seuils génériques : lancez d'abord une analyse ponctuelle pour "
            "caler les seuils sur la climatologie locale."
        )

    out = GrilleResponse(
        lats=lats, lons=lons, times=times,
        champs=res["champs"], directions=res["directions"],
        stats=res["stats"],
        n_mer=res["n_mer"], n_total=res["n_total"],
        seuils={"p95_eff": round(p95, 3), "p99_eff": round(p99, 3)},
        couverture=res["couverture"],
        champs_disponibles=res["champs_disponibles"],
        avertissements=avert,
    )
    return cache_put(key, out)


def _grille_demo(lats, lons, days: int):
    """Grille synthétique : gradient spatial appliqué au jeu de démonstration."""
    base = sources.demo_forcing(days)
    times = base.times
    cells: list[dict[str, Any] | None] = []
    ny, nx = len(lats), len(lons)
    for i in range(ny):
        for j in range(nx):
            if i >= ny - 1 and j >= nx - 1:
                cells.append(None)          # un nœud « à terre » pour le masque
                continue
            f = 0.75 + 0.5 * (i / max(ny - 1, 1)) + 0.15 * (j / max(nx - 1, 1))
            cells.append({
                "hs": [h * f for h in base.hs],
                "tp": list(base.tp),
                "dir": list(base.direction),
                "sl": list(base.sea_level),
            })
    return times, cells
