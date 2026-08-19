"""Fournisseurs de données ouvertes.

Toutes les sources retenues sont libres d'accès et adossées à une institution
de référence. Open-Meteo relaie les modèles de vagues ECMWF / GFS-Wave /
MFWAM et ne demande aucune clé, ce qui en fait la source par défaut.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .engine import Forcing

log = logging.getLogger(__name__)

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
# Variables horaires demandées pour l'analyse ponctuelle. Toutes ne sont pas
# disponibles partout : `_column` remplace proprement les valeurs manquantes et
# l'interface signale ce qui a été substitué.
HOURLY = ",".join((
    "wave_height", "wave_period", "wave_direction",
    "wind_wave_height", "wind_wave_direction", "wind_wave_period",
    "swell_wave_height", "swell_wave_direction", "swell_wave_period",
    "ocean_current_velocity", "ocean_current_direction",
    "sea_surface_temperature", "sea_level_height_msl",
))

# Sous-ensemble pour la grille : chaque variable multiplie le volume transféré
# par le nombre de nœuds, on ne demande que ce qui est cartographié. Les
# grandeurs facultatives (houle de fond, courant, température) restent
# disponibles pour l'analyse ponctuelle, où elles ne coûtent qu'une requête.
HOURLY_GRILLE = ",".join((
    "wave_height", "wave_period", "wave_direction", "sea_level_height_msl",
))
TIMEOUT = httpx.Timeout(45.0, connect=15.0)


class SourceError(RuntimeError):
    """Erreur remontée telle quelle à l'utilisateur, en français."""


def _lowpass(values: Sequence[float], window: int) -> list[float]:
    """Moyenne glissante centrée — retrait grossier du signal de marée."""
    n = len(values)
    half = max(1, window // 2)
    out = []
    for i in range(n):
        a, b = max(0, i - half), min(n, i + half + 1)
        seg = values[a:b]
        out.append(sum(seg) / len(seg))
    return out


def _column(hourly: dict[str, Any], name: str, default: float,
            n: int) -> list[float]:
    vals = hourly.get(name)
    if not vals:
        return [default] * n
    return [default if v is None else float(v) for v in vals]


def _optionnel(hourly: dict[str, Any], name: str, n: int) -> list[float] | None:
    """Colonne facultative : ``None`` si la variable n'est pas servie ici."""
    vals = hourly.get(name)
    if not vals or all(v is None for v in vals):
        return None
    dernier = 0.0
    out: list[float] = []
    for v in vals:
        if v is None:
            out.append(dernier)
        else:
            dernier = float(v)
            out.append(dernier)
    return out[:n] + [dernier] * max(0, n - len(out))


def _to_forcing(hourly: dict[str, Any], source: str, note: str) -> Forcing:
    times = list(hourly["time"])
    n = len(times)
    hs = _column(hourly, "wave_height", 0.0, n)
    tp = _column(hourly, "wave_period", 8.0, n)
    dr = _column(hourly, "wave_direction", 0.0, n)

    raw_sl = hourly.get("sea_level_height_msl")
    tide_estimee = not raw_sl or all(v is None for v in raw_sl)
    if tide_estimee:
        # Aucune donnée de niveau d'eau en ce point : marée semi-diurne
        # générique, explicitement signalée à l'utilisateur.
        sl = [1.0 * math.cos(2 * math.pi * i / 12.42)
              + 0.35 * math.cos(2 * math.pi * i / 12.0) for i in range(n)]
    else:
        sl = [0.0 if v is None else float(v) for v in raw_sl]

    return Forcing(
        times=times, hs=hs, tp=tp, direction=dr,
        sea_level=sl, surge=_lowpass(sl, 25),
        source=source, note=note, tide_estimee=tide_estimee,
        hs_vent=_optionnel(hourly, "wind_wave_height", n),
        dir_vent=_optionnel(hourly, "wind_wave_direction", n),
        tp_vent=_optionnel(hourly, "wind_wave_period", n),
        hs_houle=_optionnel(hourly, "swell_wave_height", n),
        dir_houle=_optionnel(hourly, "swell_wave_direction", n),
        tp_houle=_optionnel(hourly, "swell_wave_period", n),
        courant=_optionnel(hourly, "ocean_current_velocity", n),
        courant_dir=_optionnel(hourly, "ocean_current_direction", n),
        sst=_optionnel(hourly, "sea_surface_temperature", n),
    )


async def _get(client: httpx.AsyncClient, url: str,
               params: dict[str, Any]) -> Any:
    try:
        r = await client.get(url, params=params, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise SourceError(
            f"Service de données injoignable ({exc.__class__.__name__}). "
            "Vérifiez votre connexion."
        ) from exc
    if r.status_code != 200:
        detail = ""
        try:
            detail = r.json().get("reason", "")
        except Exception:
            detail = r.text[:200]
        raise SourceError(f"Service de données : {r.status_code} {detail}".strip())
    return r.json()


async def fetch_openmeteo(
    client: httpx.AsyncClient, lat: float, lon: float, *,
    days: int = 5, start: str | None = None, end: str | None = None,
) -> Forcing:
    """Prévision ou rétrospective de vagues en un point (mondial, sans clé)."""
    params: dict[str, Any] = {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "hourly": HOURLY, "timezone": "UTC",
    }
    if start and end:
        params |= {"start_date": start, "end_date": end}
        note = "Période choisie par l'utilisateur."
    else:
        params["forecast_days"] = days
        note = f"Prévision à {days} jours."

    data = await _get(client, MARINE_URL, params)
    hourly = data.get("hourly") or {}
    if not hourly.get("time"):
        raise SourceError(
            "Aucune donnée pour ce point : il est probablement à terre. "
            "Choisissez un point en mer, près du rivage."
        )
    return _to_forcing(
        hourly, "Open-Meteo Marine API (ECMWF / GFS-Wave / MFWAM)", note
    )


async def fetch_climatology_series(
    client: httpx.AsyncClient, lat: float, lon: float, annees: int
) -> tuple[list[float], list[float], float]:
    """Série historique de Hs **et de direction** au point.

    La direction est indispensable à la rose : une rose calculée sur cinq jours
    de prévision décrit un épisode, pas un régime.
    """
    fin = datetime.now(UTC) - timedelta(days=3)
    debut = fin.replace(year=fin.year - annees)
    data = await _get(client, MARINE_URL, {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "hourly": "wave_height,wave_direction", "timezone": "UTC",
        "start_date": debut.date().isoformat(),
        "end_date": fin.date().isoformat(),
    })
    hourly = data.get("hourly") or {}
    bruts_hs = hourly.get("wave_height") or []
    bruts_dir = hourly.get("wave_direction") or []
    hs: list[float] = []
    dirs: list[float] = []
    for i, v in enumerate(bruts_hs):
        if v is None:
            continue
        hs.append(float(v))
        d = bruts_dir[i] if i < len(bruts_dir) else None
        dirs.append(float(d) if d is not None else float("nan"))

    n_total = len(hourly.get("time") or [])
    dt = 1.0
    if n_total > 1:
        a = datetime.fromisoformat(hourly["time"][0])
        b = datetime.fromisoformat(hourly["time"][1])
        dt = max((b - a).total_seconds() / 3600.0, 0.5)
    return hs, dirs, dt


async def fetch_grid(
    client: httpx.AsyncClient,
    lats: Sequence[float], lons: Sequence[float], *,
    days: int = 3, start: str | None = None, end: str | None = None,
) -> tuple[list[str], list[dict[str, Any] | None]]:
    """Grille de points en **une seule requête** multi-coordonnées."""
    params: dict[str, Any] = {
        "latitude": ",".join(f"{v:.4f}" for v in lats),
        "longitude": ",".join(f"{v:.4f}" for v in lons),
        "hourly": HOURLY_GRILLE,
        "timezone": "UTC",
    }
    if start and end:
        params |= {"start_date": start, "end_date": end}
    else:
        params["forecast_days"] = days

    data = await _get(client, MARINE_URL, params)
    locs = data if isinstance(data, list) else [data]
    if len(locs) != len(lats):
        raise SourceError(
            f"Réponse incomplète : {len(locs)} points reçus sur {len(lats)}."
        )

    times: list[str] = []
    for loc in locs:
        h = loc.get("hourly") or {}
        if h.get("time"):
            times = list(h["time"])
            break
    if not times:
        raise SourceError(
            "Aucun nœud marin dans cette zone. Recadrez la carte sur un littoral."
        )

    cells: list[dict[str, Any] | None] = []
    for loc in locs:
        h = loc.get("hourly") or {}
        hs = h.get("wave_height")
        if not hs or all(v is None for v in hs):
            cells.append(None)          # nœud à terre
            continue
        n = len(times)
        cells.append({
            "hs": _column(h, "wave_height", math.nan, n),
            "tp": _column(h, "wave_period", 8.0, n),
            "dir": _column(h, "wave_direction", math.nan, n),
            "sl": _column(h, "sea_level_height_msl", 0.0, n),
        })
    if not any(cells):
        raise SourceError("Tous les nœuds sont à terre. Recadrez la carte.")
    return times, cells


async def probe_variables(
    client: httpx.AsyncClient, lat: float, lon: float, *,
    start: str | None = None, end: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Sonde le fournisseur variable par variable, **une requête chacune**.

    Groupées, les variables se masquent l'une l'autre : une seule refusée fait
    échouer la requête entière et l'on conclut à tort que toutes manquent.
    Isolées, chaque réponse est un verdict propre.
    """
    variables = HOURLY.split(",")
    resultat: dict[str, dict[str, Any]] = {}
    for nom in variables:
        params: dict[str, Any] = {
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "hourly": nom, "timezone": "UTC",
        }
        if start and end:
            params |= {"start_date": start, "end_date": end}
        else:
            params["forecast_days"] = 1
        try:
            data = await _get(client, MARINE_URL, params)
        except SourceError as exc:
            resultat[nom] = {"etat": "refusée", "detail": str(exc)}
            continue
        vals = (data.get("hourly") or {}).get(nom)
        if not vals:
            resultat[nom] = {"etat": "absente", "detail": "colonne non renvoyée"}
            continue
        servis = sum(1 for v in vals if v is not None)
        resultat[nom] = {
            "etat": "servie" if servis else "vide",
            "valeurs": servis, "total": len(vals),
            "exemple": next((v for v in vals if v is not None), None),
        }
    return resultat


async def geocode(client: httpx.AsyncClient, nom: str,
                  count: int = 8) -> list[dict[str, Any]]:
    """Recherche de lieux (villes, ports) — géocodage Open-Meteo."""
    data = await _get(client, GEOCODE_URL, {
        "name": nom, "count": count, "language": "fr", "format": "json",
    })
    return data.get("results") or []


def demo_forcing(days: int = 5) -> Forcing:
    """Jeu synthétique : dépression atlantique concomitante d'une vive-eau.

    Permet d'auditer toute la chaîne hors ligne. Aucune donnée réelle.
    """
    t0 = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    n = days * 24
    peak, width = n * 0.45, n * 0.13
    times, hs, tp, dr, sl, sg = [], [], [], [], [], []

    for i in range(n):
        times.append((t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M"))
        base = 1.4 + 0.25 * math.sin(2 * math.pi * i / 60.0)
        storm = 3.4 * math.exp(-((i - peak) ** 2) / (2 * width ** 2))
        hs.append(round(base + storm, 3))
        tp.append(round(9.0 + 6.5 * (storm / 3.4)
                        + 0.6 * math.sin(2 * math.pi * i / 47.0), 2))
        dr.append(round((315.0 - 30.0 * (storm / 3.4)) % 360.0, 1))
        spring = 1.0 + 0.22 * math.cos(2 * math.pi * (i - peak) / 354.0)
        tide = (1.15 * math.cos(2 * math.pi * i / 12.42)
                + 0.42 * math.cos(2 * math.pi * i / 12.0)) * spring
        surge = 0.55 * (storm / 3.4) + 0.05
        sg.append(round(surge, 3))
        sl.append(round(tide + surge, 3))

    return Forcing(
        times=times, hs=hs, tp=tp, direction=dr, sea_level=sl, surge=sg,
        hs_houle=[round(0.72 * v, 3) for v in hs],
        dir_houle=list(dr),
        tp_houle=[round(1.15 * v, 2) for v in tp],
        hs_vent=[round(0.45 * v, 3) for v in hs],
        dir_vent=[round((d + 22.0) % 360.0, 1) for d in dr],
        tp_vent=[round(0.55 * v, 2) for v in tp],
        courant=[round(0.12 + 0.22 * (h / max(hs)), 3) for h in hs],
        courant_dir=[round((d + 250.0) % 360.0, 1) for d in dr],
        sst=[round(19.5 + 1.6 * math.sin(2 * math.pi * i / 24.0), 2)
             for i in range(len(times))],
        source="DÉMO — jeu synthétique (aucune donnée réelle)",
        note="Mode démonstration hors ligne : dépression atlantique "
             "synthétique concomitante d'une vive-eau.",
        tide_estimee=True,
    )
