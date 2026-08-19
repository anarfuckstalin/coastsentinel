# -*- coding: utf-8 -*-
"""
CoastSentinel — Phase P5 : deploiement multi-sites
==================================================

Fait tourner le meme moteur sur N littoraux de contextes morphologiques et
climatiques contrastes, et produit une page de synthese comparative.

C'est la demonstration de la transposabilite : aucun code specifique a un
site, aucune valeur de seuil codee en dur — seule change la climatologie
locale, reconstruite pour chaque point.

Usage
-----
    python multisite.py --source demo   --out synthese_mondiale.html
    python multisite.py --source openmeteo --out synthese_mondiale.html
    python multisite.py --sites mes_sites.csv --source openmeteo

CSV de sites : nom,lat,lon,slope,berm,crest,contexte,hindcast

Lecture de la sortie
--------------------
L'indicateur central est le rapport TWL_max / TWL_P99_local. Il vaut la
meme chose partout dans le monde : 1,0 = evenement au niveau du 99e
percentile local. Comparer des hauteurs d'eau brutes entre Agadir et un
atoll du Pacifique n'aurait aucun sens ; comparer leur position dans la
climatologie locale, si.

Licence : Apache-2.0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from coastsentinel import (
    Climatology, Site, evaluer, fetch_demo, fetch_openmeteo, fetch_cmems,
    NIVEAUX,
)

# ---------------------------------------------------------------------------
# Panel de sites par defaut — contextes deliberement contrastes
# ---------------------------------------------------------------------------

SITES_DEFAUT: List[Dict] = [
    dict(nom="Agadir", pays="Maroc", lat=30.42, lon=-9.62, slope=0.045,
         berm=2.2, crest=4.6,
         contexte="Baie sableuse atlantique, mesotidal, houle longue de NW"),
    dict(nom="Essaouira", pays="Maroc", lat=31.51, lon=-9.77, slope=0.035,
         berm=2.0, crest=4.2,
         contexte="Littoral atlantique expose, forte houle, systeme dunaire"),
    dict(nom="Nouakchott", pays="Mauritanie", lat=18.08, lon=-16.03,
         slope=0.025, berm=1.4, crest=2.6,
         contexte="Cordon sableux tres bas, derive litorale intense"),
    dict(nom="Dakar — Yoff", pays="Senegal", lat=14.75, lon=-17.47,
         slope=0.055, berm=2.0, crest=3.8,
         contexte="Plage urbaine tropicale, houle australe"),
    dict(nom="Cotonou", pays="Benin", lat=6.35, lon=2.42, slope=0.075,
         berm=1.8, crest=3.2,
         contexte="Cote deltaique microtidale, plage reflechissante"),
    dict(nom="Costa da Caparica", pays="Portugal", lat=38.63, lon=-9.24,
         slope=0.05, berm=2.6, crest=5.2,
         contexte="Atlantique tempere, tempetes hivernales severes"),
    dict(nom="Golfe de Gabes", pays="Tunisie", lat=34.72, lon=10.75,
         slope=0.012, berm=1.2, crest=2.2,
         contexte="Mediterranee, plage tres dissipative, fort marnage local"),
    dict(nom="Recife", pays="Bresil", lat=-8.12, lon=-34.87, slope=0.08,
         berm=2.0, crest=3.6,
         contexte="Cote tropicale a recifs, forte pression urbaine"),
    dict(nom="Funafuti", pays="Tuvalu", lat=-8.52, lon=179.20, slope=0.10,
         berm=1.5, crest=2.4,
         contexte="Atoll corallien, altitude tres faible, enjeu existentiel"),
    dict(nom="Maputo — Costa do Sol", pays="Mozambique", lat=-25.94,
         lon=32.62, slope=0.04, berm=1.8, crest=3.4,
         contexte="Ocean Indien, exposition cyclonique"),
]


def load_sites(path: str) -> List[Dict]:
    import csv
    out = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out.append(dict(
                nom=r["nom"], pays=r.get("pays", ""),
                lat=float(r["lat"]), lon=float(r["lon"]),
                slope=float(r.get("slope") or 0.05),
                berm=float(r.get("berm") or 2.0),
                crest=float(r.get("crest") or 4.5),
                contexte=r.get("contexte", ""),
                hindcast=r.get("hindcast") or None,
            ))
    return out


# ---------------------------------------------------------------------------

@dataclass
class SiteResult:
    nom: str
    pays: str
    lat: float
    lon: float
    contexte: str
    niveau: int
    twl_max: float
    twl_p99: float
    ratio: float           # TWL_max / TWL_P99_local — l'indicateur comparable
    hs_max: float
    tp: float
    regime: str
    heures_alerte: float
    clim_confiance: str
    beta_f: float
    erreur: Optional[str] = None


def run_site(s: Dict, source: str, days: int) -> SiteResult:
    site = Site(nom=s["nom"], lat=s["lat"], lon=s["lon"],
                beta_f=s.get("slope", 0.05),
                beta_source=s.get("beta_source", "panel multi-sites"),
                beta_confiance="moyenne",
                z_berme=s.get("berm", 2.0), z_crete=s.get("crest", 4.5))

    if source == "openmeteo":
        forcing = fetch_openmeteo(s["lat"], s["lon"], days)
    elif source == "cmems":
        forcing = fetch_cmems(s["lat"], s["lon"], days)
    else:
        forcing = fetch_demo(s["lat"], s["lon"], days)
        # decale la tempete synthetique selon la longitude pour eviter
        # dix sites rigoureusement identiques en mode demonstration
        k = int(abs(s["lon"])) % 7
        forcing.hs = forcing.hs[k:] + forcing.hs[:k]
        forcing.tp = forcing.tp[k:] + forcing.tp[:k]
        f = 0.75 + 0.5 * ((abs(s["lat"]) % 17) / 17.0)
        forcing.hs = [h * f for h in forcing.hs]

    clim = (Climatology.from_hindcast(s["hindcast"])
            if s.get("hindcast") else Climatology())
    steps, meta = evaluer(forcing, site, clim)
    pic = meta["pic"]
    p99 = meta["twl_p99_eff"]
    return SiteResult(
        nom=s["nom"], pays=s.get("pays", ""), lat=s["lat"], lon=s["lon"],
        contexte=s.get("contexte", ""),
        niveau=meta["niveau_max"], twl_max=pic["twl"], twl_p99=p99,
        ratio=(pic["twl"] / p99) if p99 else float("nan"),
        hs_max=pic["hs"], tp=pic["tp"], regime=pic["regime"],
        heures_alerte=meta["heures_en_alerte"],
        clim_confiance=clim.confiance, beta_f=site.beta_f,
    )


# ---------------------------------------------------------------------------
# Page de synthese
# ---------------------------------------------------------------------------

STATUS = {0: "var(--st-good)", 1: "var(--st-warning)",
          2: "var(--st-serious)", 3: "var(--st-critical)"}
ICONE = {0: "●", 1: "▲", 2: "◆", 3: "■"}


def _dotplot(res: List[SiteResult]) -> str:
    """Graphique en points : rapport TWL_max / TWL_P99 local, trie.

    Une seule serie -> pas de boite de legende (le titre nomme la mesure) ;
    chaque point est directement etiquete de sa valeur.
    """
    r = [x for x in res if x.erreur is None and x.ratio == x.ratio]
    r.sort(key=lambda x: x.ratio, reverse=True)
    if not r:
        return "<p>Aucun resultat exploitable.</p>"

    n = len(r)
    W, ROW = 960, 30
    PAD_L, PAD_R, PAD_T = 210, 66, 26
    H = PAD_T + n * ROW + 34
    vmax = max(1.35, max(x.ratio for x in r) * 1.08)
    vmin = 0.0

    def sx(v: float) -> float:
        return PAD_L + (v - vmin) * (W - PAD_L - PAD_R) / (vmax - vmin)

    out = []
    for t in (0.0, 0.5, 1.0):
        if t > vmax:
            continue
        out.append(f'<line class="grid" x1="{sx(t):.1f}" y1="{PAD_T-12}" '
                   f'x2="{sx(t):.1f}" y2="{PAD_T+n*ROW:.1f}"/>')
        out.append(f'<text class="tick" x="{sx(t):.1f}" '
                   f'y="{PAD_T+n*ROW+18:.1f}" text-anchor="middle">'
                   f'{t:.1f}</text>')
    # reference : le 99e percentile local
    out.append(f'<line x1="{sx(1.0):.1f}" y1="{PAD_T-14}" '
               f'x2="{sx(1.0):.1f}" y2="{PAD_T+n*ROW:.1f}" '
               f'stroke="var(--st-serious)" stroke-width="2" '
               f'stroke-dasharray="5 4"/>')
    out.append(f'<text class="reflab" x="{sx(1.0):.1f}" y="{PAD_T-19}" '
               f'text-anchor="middle">P99 local</text>')

    for i, x in enumerate(r):
        y = PAD_T + i * ROW + ROW / 2
        out.append(f'<text class="sitelab" x="{PAD_L-14}" y="{y+4:.1f}" '
                   f'text-anchor="end">{x.nom}</text>')
        out.append(f'<line x1="{sx(0):.1f}" y1="{y:.1f}" '
                   f'x2="{sx(x.ratio):.1f}" y2="{y:.1f}" '
                   f'stroke="var(--grid)" stroke-width="2"/>')
        out.append(f'<circle cx="{sx(x.ratio):.1f}" cy="{y:.1f}" r="7" '
                   f'fill="{STATUS[x.niveau]}" stroke="var(--surface-1)" '
                   f'stroke-width="2"/>')
        out.append(f'<text class="val" x="{sx(x.ratio)+14:.1f}" '
                   f'y="{y+4:.1f}">{x.ratio:.2f}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" '
            f'role="img" aria-label="Rapport TWL sur P99 local par site">'
            + "\n".join(out) + "</svg>")


def build_page(res: List[SiteResult], source: str) -> str:
    now = datetime.now(timezone.utc)
    okr = [x for x in res if x.erreur is None]
    n_alerte = sum(1 for x in okr if x.niveau >= 2)
    n_faible = sum(1 for x in okr if x.clim_confiance == "faible")
    pire = max(okr, key=lambda x: x.ratio) if okr else None

    lignes = "\n".join(
        f"<tr><td>{x.nom}</td><td>{x.pays}</td>"
        f"<td><span class='chip' style='--dot:{STATUS[x.niveau]}'>"
        f"<span class='dot'></span>{ICONE[x.niveau]} "
        f"{NIVEAUX[x.niveau]['label']}</span></td>"
        f"<td>{x.twl_max:.2f}</td><td>{x.twl_p99:.2f}</td>"
        f"<td><b>{x.ratio:.2f}</b></td><td>{x.hs_max:.2f}</td>"
        f"<td>{x.tp:.1f}</td><td>{x.regime}</td>"
        f"<td>{x.heures_alerte:.0f}</td><td>{x.beta_f:.3f}</td>"
        f"<td class='ctx'>{x.contexte}</td></tr>"
        for x in sorted(okr, key=lambda x: x.ratio, reverse=True))
    erreurs = "\n".join(
        f"<li><b>{x.nom}</b> — {x.erreur}</li>"
        for x in res if x.erreur)

    legende = " ".join(
        f'<span class="lg"><span class="sw" style="background:{STATUS[k]}">'
        f'</span>{ICONE[k]} {NIVEAUX[k]["label"]}</span>' for k in range(4))

    avert = ""
    if n_faible:
        avert = (f'<p class="warn"><b>{n_faible} site(s) sans hindcast '
                 f'local.</b> Leurs seuils sont génériques : les rapports '
                 f'affichés ne sont pas comparables entre eux tant qu\'une '
                 f'climatologie locale n\'a pas été fournie pour chacun '
                 f'(<code>fetch_era5.py</code>).</p>')

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CoastSentinel — synthèse multi-sites</title>
<style>
:root{{color-scheme:light}}
.viz-root{{--surface-1:#fcfcfb;--plane:#f9f9f7;--text-primary:#0b0b0b;
 --text-secondary:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
 --border:rgba(11,11,11,.10);--series-1:#2a78d6;
 --st-good:#0ca30c;--st-warning:#fab219;--st-serious:#ec835a;
 --st-critical:#d03b3b}}
@media (prefers-color-scheme:dark){{:root:where(:not([data-theme="light"]))
 .viz-root{{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;
 --text-primary:#fff;--text-secondary:#c3c2b7;--grid:#2c2c2a;--axis:#383835;
 --border:rgba(255,255,255,.10);--series-1:#3987e5}}}}
:root[data-theme="dark"] .viz-root{{color-scheme:dark;--surface-1:#1a1a19;
 --plane:#0d0d0d;--text-primary:#fff;--text-secondary:#c3c2b7;--grid:#2c2c2a;
 --axis:#383835;--border:rgba(255,255,255,.10);--series-1:#3987e5}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}}
.viz-root{{background:var(--plane);color:var(--text-primary);min-height:100vh;
 padding:22px clamp(12px,3vw,34px) 46px}}
h1{{font-size:21px;margin:0 0 3px}}
.sub{{color:var(--text-secondary);font-size:13px;margin:0 0 18px}}
.tiles{{display:grid;gap:10px;
 grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-bottom:16px}}
.tile{{background:var(--surface-1);border:1px solid var(--border);
 border-radius:12px;padding:13px 15px}}
.tl{{font-size:11.5px;color:var(--text-secondary);text-transform:uppercase;
 letter-spacing:.5px;margin-bottom:7px}}
.tv{{font-size:25px;font-weight:650;display:flex;align-items:center;gap:8px}}
.ts{{font-size:12px;color:var(--text-secondary);margin-top:6px}}
.dot{{width:11px;height:11px;border-radius:3px;background:var(--dot);
 display:inline-block;flex:none}}
.card{{background:var(--surface-1);border:1px solid var(--border);
 border-radius:12px;padding:15px 16px 12px;margin-bottom:14px}}
.card h2{{font-size:14.5px;margin:0 0 2px}}
.cap{{font-size:12.5px;color:var(--text-secondary);margin:0 0 10px}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;
 color:var(--text-secondary);margin:2px 0 10px}}
.lg{{display:inline-flex;align-items:center;gap:6px}}
.sw{{width:12px;height:12px;border-radius:3px;display:inline-block}}
svg{{width:100%;height:auto;display:block}}
.grid{{stroke:var(--grid);stroke-width:1}}
.tick{{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}}
.reflab{{fill:var(--text-secondary);font-size:11px;font-weight:600}}
.sitelab{{fill:var(--text-primary);font-size:12.5px}}
.val{{fill:var(--text-secondary);font-size:12px;font-weight:600;
 font-variant-numeric:tabular-nums}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;
 font-variant-numeric:tabular-nums}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--grid)}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),
th:nth-child(3),td:nth-child(3),th:nth-child(9),td:nth-child(9),
.ctx{{text-align:left}}
th{{color:var(--text-secondary);font-weight:600}}
.ctx{{color:var(--text-secondary);max-width:290px}}
.chip{{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}}
.warn{{border-left:3px solid var(--st-critical);padding-left:11px;
 font-size:12.5px;color:var(--text-secondary)}}
footer{{font-size:12px;color:var(--muted);margin-top:20px;line-height:1.65}}
</style></head><body><div class="viz-root">

<h1>CoastSentinel — synthèse multi-sites</h1>
<p class="sub">{len(okr)} littoraux · forçage : {source} · émis le
 {now.strftime('%d/%m/%Y %H:%M')} UTC · le même moteur, aucun paramètre
 spécifique à un site</p>

<div class="tiles">
 <div class="tile"><div class="tl">Sites évalués</div>
  <div class="tv">{len(okr)}</div>
  <div class="ts">sur {len(res)} demandés</div></div>
 <div class="tile"><div class="tl">En alerte (orange ou rouge)</div>
  <div class="tv" style="--dot:var(--st-serious)"><span class="dot"></span>
   {n_alerte}</div>
  <div class="ts">niveau ≥ 2 sur l'horizon</div></div>
 <div class="tile"><div class="tl">Site le plus exceptionnel</div>
  <div class="tv" style="--dot:{STATUS[pire.niveau] if pire else 'var(--muted)'}">
   <span class="dot"></span>{pire.nom if pire else '—'}</div>
  <div class="ts">{f'{pire.ratio:.2f} × le P99 local' if pire else ''}</div></div>
 <div class="tile"><div class="tl">Climatologie faible</div>
  <div class="tv" style="--dot:var(--st-warning)"><span class="dot"></span>
   {n_faible}</div>
  <div class="ts">sites sans hindcast local</div></div>
</div>

<div class="card">
 <h2>Position de l'événement dans la climatologie locale</h2>
 <p class="cap">Rapport TWL maximal prévu / 99ᵉ percentile local. C'est la
  seule grandeur comparable d'un littoral à l'autre : 1,00 = événement au
  niveau du P99 du site. Comparer des hauteurs d'eau brutes entre un atoll
  et une baie atlantique n'aurait aucun sens.</p>
 <div class="legend">{legende}</div>
 {_dotplot(res)}
</div>

<div class="card">
 <h2>Détail par site</h2>
 <table><thead><tr><th>Site</th><th>Pays</th><th>Niveau</th>
  <th>TWL max (m)</th><th>P99 local (m)</th><th>Rapport</th>
  <th>Hs (m)</th><th>Tp (s)</th><th>Régime</th><th>h en alerte</th>
  <th>βf</th><th>Contexte</th></tr></thead>
  <tbody>{lignes}</tbody></table>
 {avert}
 {'<p class="warn"><b>Sites en échec :</b></p><ul>' + erreurs + '</ul>'
  if erreurs else ''}
</div>

<footer>
 <b>CoastSentinel v0.1 — phase P5.</b> Le même moteur, les mêmes formules et
 les mêmes règles d'alerte sur tous les sites ; seule la climatologie locale
 change. C'est ce qui rend le système transposable à n'importe quel littoral
 du monde.<br>
 <b>Dispositif d'aide à la décision et de recherche. Ne se substitue en aucun
 cas aux alertes officielles des services nationaux compétents.</b>
</footer>
</div></body></html>"""


# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="CoastSentinel — deploiement multi-sites (phase P5)")
    p.add_argument("--sites", default=None,
                   help="CSV de sites (defaut : panel mondial integre)")
    p.add_argument("--source", choices=["openmeteo", "cmems", "demo"],
                   default="demo")
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--out", default="synthese_multisites.html")
    p.add_argument("--json", default=None)
    args = p.parse_args(argv)

    sites = load_sites(args.sites) if args.sites else SITES_DEFAUT
    res: List[SiteResult] = []
    for i, s in enumerate(sites, 1):
        print("[%d/%d] %s..." % (i, len(sites), s["nom"]), end=" ", flush=True)
        try:
            r = run_site(s, args.source, args.days)
            print("%s — TWL %.2f m (%.2f x P99)"
                  % (NIVEAUX[r.niveau]["code"], r.twl_max, r.ratio))
        except Exception as exc:
            r = SiteResult(s["nom"], s.get("pays", ""), s["lat"], s["lon"],
                           s.get("contexte", ""), 0, 0, 0, float("nan"),
                           0, 0, "-", 0, "faible", s.get("slope", 0.05),
                           erreur=str(exc))
            print("ECHEC (%s)" % exc)
        res.append(r)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(build_page(res, args.source))
    print("\nSynthese : %s" % args.out)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([r.__dict__ for r in res], fh, ensure_ascii=False,
                      indent=2)
        print("JSON     : %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
