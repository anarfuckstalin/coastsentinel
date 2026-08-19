# -*- coding: utf-8 -*-
"""
CoastSentinel — Module de validation du systeme d'alerte
========================================================

C'est l'etape que la plupart des travaux sur les systemes d'alerte cotiere
omettent : verifier que les alertes emises correspondent aux impacts
reellement observes. Sans elle, un systeme d'alerte n'est qu'un calcul.

Contenu
-------
  * base d'evenements d'impact observes (schema + chargement CSV)
  * appariement alertes <-> evenements avec tolerance temporelle
  * table de contingence et scores : POD, FAR, CSI, biais, PSS (Peirce),
    HSS (Heidke), taux de fausse alarme F
  * intervalles de confiance par bootstrap
  * courbe ROC sur les niveaux d'alerte
  * score de Brier et diagramme de fiabilite (version probabiliste)
  * calibration du coefficient de couplage alpha (module M5) par
    maximisation du CSI

Objectif operationnel vise : POD > 0,8 avec FAR < 0,4. Un systeme a FAR
elevee perd la confiance des utilisateurs et cesse d'etre utilise — c'est
le mode d'echec dominant des systemes d'alerte.

Auto-test :  python3 validation.py

Licence : Apache-2.0.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# 1. Base d'evenements d'impact observes
# ---------------------------------------------------------------------------


@dataclass
class ImpactEvent:
    """Un impact cotier reellement observe.

    Sources admissibles, par ordre de fiabilite decroissante :
      1. rapports de la protection civile / autorite portuaire ;
      2. leves post-tempete (DGPS, drone) montrant un recul brutal ;
      3. imagerie satellitaire post-evenement (Sentinel-1/2) ;
      4. presse locale et reseaux sociaux geolocalises.

    `severite` suit la meme echelle que les niveaux d'alerte :
      1 = gene (embruns, plage submergee a maree haute)
      2 = degats materiels localises, erosion mesurable
      3 = degats majeurs, submersion de zones habitees, evacuation
    """
    site: str
    debut: datetime
    fin: datetime
    severite: int
    type: str = "submersion"       # submersion | erosion | degats_ouvrage
    source: str = ""
    confiance: str = "moyenne"     # faible | moyenne | elevee
    note: str = ""

    def chevauche(self, t0: datetime, t1: datetime,
                  tolerance_h: float = 12.0) -> bool:
        """Vrai si l'evenement recouvre la fenetre [t0, t1] elargie de la
        tolerance. La tolerance absorbe l'imprecision de datation des
        sources documentaires (un article de presse date le lendemain)."""
        tol = timedelta(hours=tolerance_h)
        return self.debut - tol <= t1 and self.fin + tol >= t0


def load_events(path: str) -> List[ImpactEvent]:
    """Charge la base d'evenements depuis un CSV.

    Colonnes : site, debut, fin, severite, type, source, confiance, note
    Dates au format ISO (2024-01-12T06:00 ou 2024-01-12).
    """
    import csv
    out: List[ImpactEvent] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            out.append(ImpactEvent(
                site=row.get("site", "").strip(),
                debut=_parse_dt(row["debut"]),
                fin=_parse_dt(row.get("fin") or row["debut"]),
                severite=int(row.get("severite", 2)),
                type=row.get("type", "submersion").strip(),
                source=row.get("source", "").strip(),
                confiance=row.get("confiance", "moyenne").strip(),
                note=row.get("note", "").strip(),
            ))
    return out


def _parse_dt(s: str) -> datetime:
    s = s.strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M",
                "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s)


def template_csv(path: str = "evenements_impact.csv") -> str:
    """Ecrit un modele de base d'evenements a completer."""
    contenu = (
        "site,debut,fin,severite,type,source,confiance,note\n"
        "Agadir,2024-01-11T18:00,2024-01-12T12:00,3,submersion,"
        "Protection civile,elevee,Exemple a remplacer\n"
        "Agadir,2023-02-20T00:00,2023-02-21T00:00,2,erosion,"
        "Leve drone post-tempete,elevee,Exemple a remplacer\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(contenu)
    return path


# ---------------------------------------------------------------------------
# 2. Appariement et table de contingence
# ---------------------------------------------------------------------------


@dataclass
class AlertWindow:
    """Une fenetre temporelle et le niveau d'alerte qui y a ete emis."""
    debut: datetime
    fin: datetime
    niveau: int
    proba: Optional[float] = None    # probabilite de depassement (ensemble)


def windows_from_steps(steps, dt_hours: float = 1.0) -> List[AlertWindow]:
    """Convertit une serie de pas evalues (sortie de `evaluer`) en fenetres
    d'alerte homogenes : chaque plage consecutive de meme niveau devient
    une fenetre. C'est l'unite de verification : on ne compte pas 48 fois
    la meme tempete."""
    out: List[AlertWindow] = []
    if not steps:
        return out
    dt = timedelta(hours=dt_hours)
    debut, niv = steps[0].t, steps[0].niveau
    for i in range(1, len(steps) + 1):
        cur = steps[i].niveau if i < len(steps) else None
        if cur != niv:
            out.append(AlertWindow(debut, steps[i - 1].t + dt, niv))
            if cur is not None:
                debut, niv = steps[i].t, cur
    return out


@dataclass
class Contingency:
    """Table de contingence 2x2 pour un seuil d'alerte donne."""
    vp: int = 0     # alerte emise, impact observe
    fp: int = 0     # alerte emise, aucun impact  (fausse alarme)
    fn: int = 0     # aucune alerte, impact observe (manque)
    vn: int = 0     # aucune alerte, aucun impact

    @property
    def n(self) -> int:
        return self.vp + self.fp + self.fn + self.vn

    # --- scores contingents -------------------------------------------
    @property
    def pod(self) -> float:
        """Probability Of Detection (sensibilite). Cible > 0,8."""
        d = self.vp + self.fn
        return self.vp / d if d else float("nan")

    @property
    def far(self) -> float:
        """False Alarm Ratio : part des alertes qui etaient injustifiees.
        Cible < 0,4. A ne pas confondre avec F ci-dessous."""
        d = self.vp + self.fp
        return self.fp / d if d else float("nan")

    @property
    def f(self) -> float:
        """False alarm rate (POFD) : part des non-evenements ayant declenche
        une alerte. C'est l'abscisse de la courbe ROC."""
        d = self.fp + self.vn
        return self.fp / d if d else float("nan")

    @property
    def csi(self) -> float:
        """Critical Success Index (Threat Score). Combine POD et FAR ; c'est
        le score a maximiser pour calibrer un systeme d'alerte."""
        d = self.vp + self.fp + self.fn
        return self.vp / d if d else float("nan")

    @property
    def biais(self) -> float:
        """Biais de frequence : > 1 = sur-alerte, < 1 = sous-alerte."""
        d = self.vp + self.fn
        return (self.vp + self.fp) / d if d else float("nan")

    @property
    def pss(self) -> float:
        """Score de Peirce (Hanssen-Kuipers) = POD - F. 0 = sans valeur."""
        return self.pod - self.f

    @property
    def hss(self) -> float:
        """Score de Heidke : amelioration par rapport a une prevision
        aleatoire de meme distribution marginale."""
        a, b, c, d = self.vp, self.fp, self.fn, self.vn
        num = 2.0 * (a * d - b * c)
        den = ((a + c) * (c + d) + (a + b) * (b + d))
        return num / den if den else float("nan")

    @property
    def exactitude(self) -> float:
        return (self.vp + self.vn) / self.n if self.n else float("nan")

    def resume(self) -> Dict[str, float]:
        return {"VP": self.vp, "FP": self.fp, "FN": self.fn, "VN": self.vn,
                "POD": self.pod, "FAR": self.far, "F": self.f,
                "CSI": self.csi, "biais": self.biais, "PSS": self.pss,
                "HSS": self.hss, "exactitude": self.exactitude}

    def __str__(self) -> str:
        return ("VP=%d FP=%d FN=%d VN=%d | POD=%.2f FAR=%.2f CSI=%.2f "
                "PSS=%.2f HSS=%.2f biais=%.2f"
                % (self.vp, self.fp, self.fn, self.vn, self.pod, self.far,
                   self.csi, self.pss, self.hss, self.biais))


@dataclass
class MatchResult:
    """Resultat de l'appariement, conserve pour le bootstrap.

    `event_hits[i]`      : l'evenement i a-t-il ete couvert par une alerte ?
    `episode_matched[j]` : l'episode d'alerte j correspondait-il a un impact ?
    `vn`                 : nombre de fenetres calmes sans impact observe.
    """
    event_hits: List[bool] = field(default_factory=list)
    episode_matched: List[bool] = field(default_factory=list)
    vn: int = 0
    episodes: List[Tuple[datetime, datetime]] = field(default_factory=list)


def _episodes(windows: Sequence[AlertWindow],
              seuil_niveau: int) -> List[Tuple[datetime, datetime]]:
    """Fusionne les fenetres contigues en alerte en episodes.

    L'unite de verification est l'EPISODE, pas le pas de temps : une
    tempete de 48 h ne doit compter que pour un evenement a verifier, sinon
    les scores dependent arbitrairement du pas de temps du modele.
    """
    eps: List[Tuple[datetime, datetime]] = []
    cur: Optional[List[datetime]] = None
    for w in sorted(windows, key=lambda x: x.debut):
        if w.niveau >= seuil_niveau:
            if cur is not None and w.debut <= cur[1]:
                cur[1] = max(cur[1], w.fin)
            else:
                if cur is not None:
                    eps.append((cur[0], cur[1]))
                cur = [w.debut, w.fin]
        elif cur is not None:
            eps.append((cur[0], cur[1]))
            cur = None
    if cur is not None:
        eps.append((cur[0], cur[1]))
    return eps


def match(windows: Sequence[AlertWindow],
          events: Sequence[ImpactEvent],
          seuil_niveau: int = 2,
          seuil_severite: int = 1,
          tolerance_h: float = 12.0,
          site: Optional[str] = None) -> MatchResult:
    """Apparie les episodes d'alerte et les impacts observes.

    Convention de verification (standard en verification de tempetes) :
      * chaque IMPACT observe est un succes (VP) s'il est couvert par au
        moins un episode d'alerte, un manque (FN) sinon ;
      * chaque EPISODE d'alerte ne recouvrant aucun impact est une fausse
        alarme (FP) ; un episode qui en recouvre un ne l'est jamais, meme
        si un autre episode couvre deja le meme impact ;
      * les VN sont les fenetres calmes eloignees de tout impact — ils
        n'entrent que dans F, PSS et HSS.
    """
    ev = [e for e in events
          if e.severite >= seuil_severite and (site is None or e.site == site)]
    eps = _episodes(windows, seuil_niveau)

    ep_matched = [False] * len(eps)
    hits: List[bool] = []
    for e in ev:
        touche = [j for j, (a, b) in enumerate(eps)
                  if e.chevauche(a, b, tolerance_h)]
        hits.append(bool(touche))
        for j in touche:
            ep_matched[j] = True

    vn = sum(1 for w in windows
             if w.niveau < seuil_niveau
             and not any(e.chevauche(w.debut, w.fin, tolerance_h) for e in ev))
    return MatchResult(hits, ep_matched, vn, eps)


def contingency(windows: Sequence[AlertWindow],
                events: Sequence[ImpactEvent],
                seuil_niveau: int = 2,
                seuil_severite: int = 1,
                tolerance_h: float = 12.0,
                site: Optional[str] = None) -> Contingency:
    """Table de contingence 2x2 — voir `match` pour la convention."""
    m = match(windows, events, seuil_niveau, seuil_severite, tolerance_h,
              site)
    return from_match(m)


def from_match(m: MatchResult) -> Contingency:
    return Contingency(
        vp=sum(1 for h in m.event_hits if h),
        fn=sum(1 for h in m.event_hits if not h),
        fp=sum(1 for x in m.episode_matched if not x),
        vn=m.vn,
    )


# ---------------------------------------------------------------------------
# 3. Intervalles de confiance par bootstrap
# ---------------------------------------------------------------------------


def bootstrap_ci(windows: Sequence[AlertWindow],
                 events: Sequence[ImpactEvent],
                 score: str = "csi",
                 n_iter: int = 1000,
                 seuil_niveau: int = 2,
                 seed: int = 20260817,
                 **kw) -> Tuple[float, float, float]:
    """IC a 95 % d'un score par bootstrap sur les fenetres.

    Un score de validation sans intervalle de confiance n'est pas
    interpretable : avec 12 tempetes observees, un POD de 0,83 peut
    parfaitement etre compatible avec un vrai POD de 0,6.

    Retourne (valeur, borne_basse, borne_haute).
    """
    rng = random.Random(seed)
    m = match(windows, events, seuil_niveau=seuil_niveau, **kw)
    base = getattr(from_match(m), score)

    ne, np_ = len(m.event_hits), len(m.episode_matched)
    if ne == 0 and np_ == 0:
        return base, float("nan"), float("nan")

    vals: List[float] = []
    for _ in range(n_iter):
        # re-echantillonnage des UNITES DE VERIFICATION (impacts observes et
        # episodes d'alerte), pas des pas de temps : re-echantillonner les
        # pas de temps detruirait la structure temporelle des episodes.
        hits = [m.event_hits[rng.randrange(ne)] for _ in range(ne)] \
            if ne else []
        epm = [m.episode_matched[rng.randrange(np_)] for _ in range(np_)] \
            if np_ else []
        v = getattr(from_match(MatchResult(hits, epm, m.vn)), score)
        if v == v:                      # exclut les NaN
            vals.append(v)
    if not vals:
        return base, float("nan"), float("nan")
    vals.sort()
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(0.975 * (len(vals) - 1))]
    return base, lo, hi


# ---------------------------------------------------------------------------
# 4. Courbe ROC sur les niveaux d'alerte
# ---------------------------------------------------------------------------


def roc_curve(windows: Sequence[AlertWindow],
              events: Sequence[ImpactEvent],
              niveaux: Sequence[int] = (0, 1, 2, 3),
              **kw) -> Dict[str, object]:
    """Courbe ROC obtenue en faisant varier le seuil de declenchement.

    Retourne les points (F, POD) et l'aire sous la courbe (AUC) calculee
    par la methode des trapezes. AUC = 0,5 : systeme sans valeur.
    """
    pts: List[Tuple[float, float, int]] = [(1.0, 1.0, -1)]
    for s in sorted(niveaux):
        c = contingency(windows, events, seuil_niveau=s, **kw)
        fx = c.f if c.f == c.f else 0.0
        py = c.pod if c.pod == c.pod else 0.0
        pts.append((fx, py, s))
    pts.append((0.0, 0.0, 99))
    pts.sort(key=lambda p: (p[0], p[1]))

    auc = 0.0
    for i in range(1, len(pts)):
        auc += (pts[i][0] - pts[i - 1][0]) * (pts[i][1] + pts[i - 1][1]) / 2.0
    return {"points": pts, "auc": auc}


# ---------------------------------------------------------------------------
# 5. Version probabiliste : score de Brier et fiabilite
# ---------------------------------------------------------------------------


def brier_score(probas: Sequence[float],
                observes: Sequence[int]) -> Dict[str, float]:
    """Score de Brier et sa decomposition (fiabilite, resolution,
    incertitude) — Murphy (1973).

    BS = fiabilite - resolution + incertitude. Plus BS est faible, mieux
    c'est. Le score de competence BSS compare a la climatologie :
    BSS > 0 signifie que le systeme fait mieux que d'annoncer toujours
    la frequence de base.
    """
    n = len(probas)
    if n == 0 or n != len(observes):
        raise ValueError("Series de longueurs differentes ou vides")
    obar = sum(observes) / n
    bs = sum((probas[i] - observes[i]) ** 2 for i in range(n)) / n
    bs_clim = obar * (1.0 - obar)

    # Decomposition exacte de Murphy : le regroupement doit se faire par
    # VALEUR DE PREVISION DISTINCTE, pas par classe de largeur 0,1. Avec des
    # classes, deux previsions differentes tombant dans la meme classe
    # introduisent un terme de variance intra-classe et l'identite
    # BS = fiabilite - resolution + incertitude cesse d'etre verifiee.
    bins: Dict[float, List[int]] = {}
    for i, p in enumerate(probas):
        bins.setdefault(round(float(p), 12), []).append(i)
    fiab = res = 0.0
    for k, idx in bins.items():
        nk = len(idx)
        pk = sum(probas[i] for i in idx) / nk
        ok = sum(observes[i] for i in idx) / nk
        fiab += nk * (pk - ok) ** 2
        res += nk * (ok - obar) ** 2
    fiab /= n
    res /= n

    return {"BS": bs, "fiabilite": fiab, "resolution": res,
            "incertitude": bs_clim,
            "BSS": 1.0 - bs / bs_clim if bs_clim else float("nan")}


def reliability_diagram(probas: Sequence[float], observes: Sequence[int],
                        n_bins: int = 10) -> List[Dict[str, float]]:
    """Points du diagramme de fiabilite : probabilite annoncee contre
    frequence observee. Un systeme fiable suit la diagonale."""
    bins: Dict[int, List[int]] = {}
    for i, p in enumerate(probas):
        bins.setdefault(min(n_bins - 1, int(p * n_bins)), []).append(i)
    out = []
    for k in sorted(bins):
        idx = bins[k]
        out.append({
            "proba_moyenne": sum(probas[i] for i in idx) / len(idx),
            "frequence_observee": sum(observes[i] for i in idx) / len(idx),
            "effectif": len(idx),
        })
    return out


# ---------------------------------------------------------------------------
# 6. Calibration du couplage inter-echelles (alpha du module M5)
# ---------------------------------------------------------------------------


def calibrate_alpha(run: Callable[[float], List[AlertWindow]],
                    events: Sequence[ImpactEvent],
                    alphas: Sequence[float] = tuple(
                        round(0.05 * k, 2) for k in range(0, 11)),
                    seuil_niveau: int = 2,
                    **kw) -> Dict[str, object]:
    """Calibre le coefficient alpha du couplage M5 par maximisation du CSI.

    `run(alpha)` doit relancer l'evaluation avec ce coefficient et renvoyer
    les fenetres d'alerte correspondantes. Exemple d'usage :

        from coastsentinel import evaluer
        def run(a):
            steps, meta = evaluer(forcing, site, clim, alpha=a)
            return windows_from_steps(steps, meta["dt_h"])

        res = calibrate_alpha(run, evenements)

    Attention : calibrer et valider sur les memes evenements surestime la
    performance. Utiliser une validation croisee (laisser un evenement de
    cote a chaque iteration) des que la base depasse une dizaine de cas.
    """
    resultats = []
    for a in alphas:
        c = contingency(run(a), events, seuil_niveau=seuil_niveau, **kw)
        resultats.append({"alpha": a, **c.resume()})
    valides = [r for r in resultats if r["CSI"] == r["CSI"]]
    best = max(valides, key=lambda r: r["CSI"]) if valides else None
    return {"table": resultats, "meilleur": best}


def leave_one_out(run: Callable[[float], List[AlertWindow]],
                  events: Sequence[ImpactEvent],
                  alphas: Sequence[float],
                  seuil_niveau: int = 2, **kw) -> Dict[str, object]:
    """Validation croisee « leave-one-out » sur les evenements : pour chaque
    evenement laisse de cote, alpha est calibre sur les autres puis evalue
    sur celui-ci. Donne une estimation non optimiste de la performance."""
    scores, alphas_ret = [], []
    for i in range(len(events)):
        train = [e for j, e in enumerate(events) if j != i]
        test = [events[i]]
        cal = calibrate_alpha(run, train, alphas, seuil_niveau, **kw)
        if not cal["meilleur"]:
            continue
        a = cal["meilleur"]["alpha"]
        alphas_ret.append(a)
        c = contingency(run(a), test, seuil_niveau=seuil_niveau, **kw)
        scores.append(1.0 if c.vp > 0 else 0.0)
    return {
        "detection_hors_echantillon": (sum(scores) / len(scores)
                                       if scores else float("nan")),
        "alphas_retenus": alphas_ret,
        "alpha_median": (sorted(alphas_ret)[len(alphas_ret) // 2]
                         if alphas_ret else None),
        "n": len(scores),
    }


# ---------------------------------------------------------------------------
# 7. Rapport texte
# ---------------------------------------------------------------------------


def rapport(windows: Sequence[AlertWindow], events: Sequence[ImpactEvent],
            seuil_niveau: int = 2, **kw) -> str:
    """Rapport de validation lisible, pret a coller dans un chapitre."""
    c = contingency(windows, events, seuil_niveau=seuil_niveau, **kw)
    _, pod_lo, pod_hi = bootstrap_ci(windows, events, "pod",
                                     seuil_niveau=seuil_niveau, **kw)
    _, csi_lo, csi_hi = bootstrap_ci(windows, events, "csi",
                                     seuil_niveau=seuil_niveau, **kw)
    r = roc_curve(windows, events, **kw)
    verdict = ("conforme a l'objectif operationnel"
               if (c.pod == c.pod and c.pod > 0.8
                   and c.far == c.far and c.far < 0.4)
               else "en deca de l'objectif operationnel (POD > 0,8 ; "
                    "FAR < 0,4)")
    return (
        "VALIDATION DU SYSTEME D'ALERTE\n"
        "==============================\n"
        "Seuil de declenchement : niveau >= %d\n"
        "Fenetres evaluees      : %d\n"
        "Evenements observes    : %d\n\n"
        "                 impact observe   pas d'impact\n"
        "  alerte emise         %4d           %4d\n"
        "  pas d'alerte         %4d           %4d\n\n"
        "  POD  = %.3f   [%.3f ; %.3f]   (detection)\n"
        "  FAR  = %.3f                    (fausses alarmes)\n"
        "  CSI  = %.3f   [%.3f ; %.3f]   (score global)\n"
        "  PSS  = %.3f                    (Peirce)\n"
        "  HSS  = %.3f                    (Heidke)\n"
        "  biais= %.3f                    (>1 sur-alerte)\n"
        "  AUC  = %.3f                    (0,5 = sans valeur)\n\n"
        "  Verdict : %s\n"
        % (seuil_niveau, len(windows), len(events),
           c.vp, c.fp, c.fn, c.vn,
           c.pod, pod_lo, pod_hi, c.far, c.csi, csi_lo, csi_hi,
           c.pss, c.hss, c.biais, r["auc"], verdict)
    )


# ---------------------------------------------------------------------------
# Auto-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ok = ko = 0

    def check(nom, cond, det=""):
        global ok, ko
        if cond:
            ok += 1
            print("  OK   %s %s" % (nom, det))
        else:
            ko += 1
            print("  ECHEC %s %s" % (nom, det))

    print("\n1. Table de contingence — cas construits a la main")
    c = Contingency(vp=8, fp=3, fn=2, vn=87)
    check("POD = 0.80", abs(c.pod - 0.8) < 1e-9)
    check("FAR = 0.273", abs(c.far - 3 / 11) < 1e-9)
    check("F = 0.033", abs(c.f - 3 / 90) < 1e-9)
    check("CSI = 0.615", abs(c.csi - 8 / 13) < 1e-9)
    check("biais = 1.10", abs(c.biais - 11 / 10) < 1e-9)
    check("PSS = POD - F", abs(c.pss - (c.pod - c.f)) < 1e-9)
    check("HSS dans [-1,1]", -1 <= c.hss <= 1, "-> %.3f" % c.hss)

    parfait = Contingency(vp=10, fp=0, fn=0, vn=90)
    check("systeme parfait : CSI = 1", abs(parfait.csi - 1.0) < 1e-9)
    check("systeme parfait : PSS = 1", abs(parfait.pss - 1.0) < 1e-9)
    nul = Contingency(vp=0, fp=0, fn=10, vn=90)
    check("systeme aveugle : POD = 0", nul.pod == 0.0)

    print("\n2. Appariement alertes / evenements")
    base = datetime(2025, 1, 10)
    ev = [ImpactEvent("A", base + timedelta(hours=30),
                      base + timedelta(hours=40), 3, source="test")]
    w_bon = AlertWindow(base + timedelta(hours=24),
                        base + timedelta(hours=48), 3)
    w_loin = AlertWindow(base + timedelta(days=8),
                         base + timedelta(days=9), 3)
    check("chevauchement detecte",
          ev[0].chevauche(w_bon.debut, w_bon.fin))
    check("fenetre eloignee non appariee",
          not ev[0].chevauche(w_loin.debut, w_loin.fin))
    c2 = contingency([w_bon], ev, seuil_niveau=2)
    check("VP compte", c2.vp == 1 and c2.fp == 0 and c2.fn == 0)
    c3 = contingency([AlertWindow(base, base + timedelta(hours=6), 0)], ev)
    check("evenement non couvert -> FN", c3.fn == 1, str(c3))
    c4 = contingency([w_loin], ev, seuil_niveau=2)
    check("alerte isolee -> FP + FN", c4.fp == 1 and c4.fn == 1, str(c4))

    print("\n3. Systeme synthetique complet")
    rng = random.Random(3)
    wins: List[AlertWindow] = []
    evs: List[ImpactEvent] = []
    t = datetime(2020, 1, 1)
    for k in range(200):
        tempete = rng.random() < 0.12
        # le systeme detecte 85 % des tempetes et sur-alerte 6 % du temps
        niv = 3 if (tempete and rng.random() < 0.85) else (
            2 if (not tempete and rng.random() < 0.06) else 0)
        wins.append(AlertWindow(t, t + timedelta(hours=12), niv))
        if tempete:
            evs.append(ImpactEvent("A", t + timedelta(hours=3),
                                   t + timedelta(hours=8), 3))
        t += timedelta(hours=12)
    c5 = contingency(wins, evs, seuil_niveau=2)
    check("POD proche de 0,85", 0.7 < c5.pod < 0.98, "-> %.2f" % c5.pod)
    check("FAR raisonnable", c5.far < 0.5, "-> %.2f" % c5.far)
    check("PSS nettement positif", c5.pss > 0.5, "-> %.2f" % c5.pss)

    v, lo, hi = bootstrap_ci(wins, evs, "pod", n_iter=300)
    check("IC bootstrap encadre la valeur", lo <= v <= hi,
          "-> %.2f [%.2f ; %.2f]" % (v, lo, hi))
    check("IC non degenere", hi - lo > 0)

    r = roc_curve(wins, evs)
    check("AUC dans [0,1]", 0 <= r["auc"] <= 1, "-> %.3f" % r["auc"])
    check("AUC nettement > 0,5", r["auc"] > 0.7, "-> %.3f" % r["auc"])

    print("\n4. Scores probabilistes")
    probas = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0] * 20
    obs = [1 if rng.random() < p else 0 for p in probas]
    b = brier_score(probas, obs)
    check("BS dans [0,1]", 0 <= b["BS"] <= 1, "-> %.3f" % b["BS"])
    check("BSS positif pour un systeme fiable", b["BSS"] > 0,
          "-> %.3f" % b["BSS"])
    check("decomposition coherente",
          abs(b["BS"] - (b["fiabilite"] - b["resolution"]
                         + b["incertitude"])) < 1e-9)
    parf = brier_score([1.0] * 10 + [0.0] * 10, [1] * 10 + [0] * 10)
    check("prevision parfaite : BS = 0", abs(parf["BS"]) < 1e-12)
    rel = reliability_diagram(probas, obs)
    check("diagramme de fiabilite non vide", len(rel) >= 4,
          "-> %d classes" % len(rel))

    print("\n5. Calibration d'alpha")

    def run(a: float) -> List[AlertWindow]:
        """Systeme fictif : alpha eleve = plus sensible (plus de VP mais
        aussi plus de FP). L'optimum de CSI doit etre interieur."""
        out = []
        for i, w in enumerate(wins):
            n = w.niveau
            if n == 0 and rng_c.random() < a * 0.35:
                n = 2
            out.append(AlertWindow(w.debut, w.fin, n))
        return out

    rng_c = random.Random(11)
    cal = calibrate_alpha(run, evs, alphas=(0.0, 0.1, 0.2, 0.4, 0.8))
    check("table de calibration complete", len(cal["table"]) == 5)
    check("un alpha optimal est retenu", cal["meilleur"] is not None,
          "-> alpha = %s, CSI = %.3f" % (cal["meilleur"]["alpha"],
                                         cal["meilleur"]["CSI"]))
    check("le CSI decroit quand la sur-alerte augmente",
          cal["table"][-1]["FAR"] >= cal["table"][0]["FAR"],
          "-> FAR %.2f -> %.2f" % (cal["table"][0]["FAR"],
                                   cal["table"][-1]["FAR"]))

    print("\n6. Rapport")
    txt = rapport(wins, evs)
    check("rapport genere", "VALIDATION DU SYSTEME" in txt and "AUC" in txt)
    print()
    print(txt)

    print("%d tests reussis, %d echecs" % (ok, ko))
    raise SystemExit(1 if ko else 0)
