"""Interface en ligne de commande — usage hors serveur.

    coastsentinel analyse --lat 30.42 --lon -9.62 --source demo
    coastsentinel serve --port 8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

import httpx

from . import sources
from .climatology import Climatology, load_hindcast_csv
from .engine import Niveau, Site, evaluate
from .version import __version__


async def _analyse(args: argparse.Namespace) -> int:
    async with httpx.AsyncClient() as client:
        if args.source == "demo":
            forcing = sources.demo_forcing(args.days)
        else:
            forcing = await sources.fetch_openmeteo(
                client, args.lat, args.lon, days=args.days
            )

    clim = load_hindcast_csv(args.hindcast) if args.hindcast else Climatology()
    site = Site(
        nom=args.site, lat=args.lat, lon=args.lon, beta_f=args.slope,
        z_berme=args.berm, z_crete=args.crest, i_erosion=args.erosion_index,
    )
    res = evaluate(forcing, site, clim, alpha=args.alpha)
    niveau = Niveau(res.niveau_max)

    print(f"Source        : {forcing.source}")
    print(f"Climatologie  : {clim.source} ({clim.confiance.value}, "
          f"{clim.annees:.1f} ans)")
    print(f"Seuils TWL    : P95 {res.twl_p95_eff:.2f} m | "
          f"P99 {res.twl_p99_eff:.2f} m — {res.seuils_source}")
    print(f"Niveau maximal: {niveau.label.upper()}")
    print(f"Pic           : TWL {res.pic.twl:.2f} m, Hs {res.pic.hs:.2f} m, "
          f"Tp {res.pic.tp:.1f} s, régime {res.pic.regime}")
    print(f"Durée alerte  : {res.heures_alerte:.0f} h — SPI {res.spi:.0f} m²·h")
    print(f"Action        : {niveau.action}")
    if clim.annees == 0:
        print("\nATTENTION : aucun hindcast — seuils génériques, "
              "inutilisables en publication.")

    if args.json:
        payload = {
            "site": asdict(site),
            "niveau_max": res.niveau_max,
            "pic": asdict(res.pic),
            "seuils": {
                "twl_p95_eff": res.twl_p95_eff,
                "twl_p99_eff": res.twl_p99_eff,
                "source": res.seuils_source,
            },
            "serie": [asdict(s) for s in res.steps],
            "episodes": res.alertes,
            "avertissement": "Outil de recherche. Ne se substitue pas aux "
                             "alertes officielles des services nationaux.",
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON écrit : {args.json}")
    return 0


ETATS = {
    "servie": "OK      ",
    "vide": "VIDE    ",
    "absente": "ABSENTE ",
    "refusée": "REFUSÉE ",
}


async def _diag(args: argparse.Namespace) -> int:
    """Sonde le fournisseur variable par variable et affiche le verdict.

    À lancer quand une couche reste blanche : elle répond à la seule question
    qui compte — la donnée manque-t-elle à la source, ou se perd-elle en
    chemin ?
    """
    print(f"CoastSentinel {__version__} — diagnostic du fournisseur")
    print(f"Point : {args.lat:.4f}, {args.lon:.4f}\n")

    async with httpx.AsyncClient() as client:
        try:
            res = await sources.probe_variables(
                client, args.lat, args.lon, start=args.start, end=args.end
            )
        except sources.SourceError as exc:
            print(f"ÉCHEC : {exc}")
            return 2

        print("Variables ponctuelles (API marine Open-Meteo)")
        print("-" * 64)
        for nom, info in res.items():
            marque = ETATS.get(info["etat"], info["etat"])
            if info["etat"] == "servie":
                detail = (f"{info['valeurs']}/{info['total']} valeurs, "
                          f"ex. {info['exemple']}")
            else:
                detail = info.get("detail", "")
            print(f"  {marque} {nom:<28} {detail}")

        manquantes = [n for n, i in res.items() if i["etat"] != "servie"]
        print()
        if manquantes:
            print("Non servies en ce point : " + ", ".join(manquantes))
            print("Les couches correspondantes resteront vides — ce n'est pas")
            print("un défaut de l'application. Courants et température sont")
            print("modélisés à 8 km : essayez un point plus au large.")
        else:
            print("Toutes les variables sont servies en ce point.")

        # Second volet : la requête de grille, celle qu'utilise la carte.
        print("\nRequête de grille (2 × 2 nœuds autour du point)")
        print("-" * 64)
        d = 0.15
        lats = [args.lat - d, args.lat - d, args.lat + d, args.lat + d]
        lons = [args.lon - d, args.lon + d, args.lon - d, args.lon + d]
        try:
            times, cells, diag = await sources.fetch_grid(
                client, lats, lons, days=1
            )
        except sources.SourceError as exc:
            print(f"  ÉCHEC : {exc}")
            return 2
        n_mer = sum(1 for c in cells if c)
        print(f"  {n_mer}/4 nœuds en mer, {len(times)} pas de temps")
        if diag.get("erreur"):
            print(f"  Variables facultatives : {diag['erreur']}")
        for nom, servis in (diag.get("facultatives") or {}).items():
            marque = ETATS["servie"] if servis else ETATS["vide"]
            print(f"  {marque} {nom:<28} {servis}/4 nœuds")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="coastsentinel",
        description="Système d'Alerte Côtière Multi-échelle",
    )
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyse", help="Analyse d'alerte en un point")
    a.add_argument("--site", default="Agadir")
    a.add_argument("--lat", type=float, default=30.42)
    a.add_argument("--lon", type=float, default=-9.62)
    a.add_argument("--source", choices=["openmeteo", "demo"], default="demo")
    a.add_argument("--days", type=int, default=5)
    a.add_argument("--slope", type=float, default=0.045)
    a.add_argument("--berm", type=float, default=2.2)
    a.add_argument("--crest", type=float, default=4.6)
    a.add_argument("--erosion-index", type=float, default=0.0)
    a.add_argument("--alpha", type=float, default=0.2)
    a.add_argument("--hindcast", default=None)
    a.add_argument("--json", default=None)

    d = sub.add_parser(
        "diag",
        help="Quelles variables le fournisseur sert-il réellement en ce point ?",
    )
    d.add_argument("--lat", type=float, default=30.42)
    d.add_argument("--lon", type=float, default=-9.68)
    d.add_argument("--start", default=None, help="AAAA-MM-JJ")
    d.add_argument("--end", default=None, help="AAAA-MM-JJ")

    s = sub.add_parser("serve", help="Démarre l'API")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("coastsentinel.api:app", host=args.host, port=args.port,
                    reload=args.reload)
        return 0
    if args.cmd == "diag":
        return asyncio.run(_diag(args))
    return asyncio.run(_analyse(args))


if __name__ == "__main__":
    sys.exit(main())
