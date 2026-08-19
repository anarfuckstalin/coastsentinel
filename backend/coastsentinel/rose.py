"""Roses de direction — distribution conjointe intensité × direction.

Une rose est un objet **climatologique** : elle n'a de sens que sur une série
longue. Calculée sur cinq jours de prévision, elle décrit un épisode, pas un
régime. La source utilisée est donc toujours indiquée avec le résultat.

Convention : les directions sont des directions **de provenance** (convention
océanographique et météorologique usuelle). Un secteur « NO » signifie donc
« houle venant du nord-ouest ».
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

SECTEURS_16 = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO",
)

# Bornes par défaut des classes de hauteur significative, en mètres.
BORNES_HS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


@dataclass(slots=True)
class Rose:
    """Résultat d'une rose : fréquences par secteur et par classe."""

    source: str
    variable: str
    unite: str
    n: int
    secteurs: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    bornes: list[float] = field(default_factory=list)
    # frequences[secteur][classe] — fractions du total, somme ≤ 1
    frequences: list[list[float]] = field(default_factory=list)
    calme: float = 0.0
    secteur_dominant: str = ""
    part_dominante: float = 0.0
    moyenne: float = 0.0
    p95: float = 0.0


def _libelles(bornes: Sequence[float], unite: str) -> list[str]:
    out = [f"< {bornes[0]:g} {unite}"]
    for a, b in zip(bornes, bornes[1:], strict=False):
        out.append(f"{a:g}–{b:g} {unite}")
    out.append(f"≥ {bornes[-1]:g} {unite}")
    return out


def rose(
    valeurs: Sequence[float],
    directions: Sequence[float],
    *,
    source: str,
    variable: str = "Hs",
    unite: str = "m",
    n_secteurs: int = 16,
    bornes: Sequence[float] = BORNES_HS,
    seuil_calme: float = 0.0,
) -> Rose:
    """Distribution conjointe intensité × direction de provenance.

    Les secteurs sont centrés sur les caps cardinaux : le secteur « N » couvre
    [-11,25° ; +11,25°[ et non [0° ; 22,5°[. C'est la convention des roses
    publiées ; l'oublier décale toute la figure d'un demi-secteur.
    """
    if n_secteurs not in (8, 16):
        raise ValueError("n_secteurs doit valoir 8 ou 16")
    noms = SECTEURS_16 if n_secteurs == 16 else SECTEURS_16[::2]
    largeur = 360.0 / n_secteurs
    n_classes = len(bornes) + 1

    grille = [[0 for _ in range(n_classes)] for _ in range(n_secteurs)]
    total = 0
    calmes = 0
    retenues: list[float] = []

    for v, d in zip(valeurs, directions, strict=False):
        if v is None or d is None or v != v or d != d or v < 0:
            continue
        total += 1
        if v <= seuil_calme:
            calmes += 1
            continue
        retenues.append(v)
        # décalage d'un demi-secteur pour centrer « N » sur 0°
        s = int(((d % 360.0) + largeur / 2.0) // largeur) % n_secteurs
        k = n_classes - 1
        for i, b in enumerate(bornes):
            if v < b:
                k = i
                break
        grille[s][k] += 1

    if total == 0:
        return Rose(source=source, variable=variable, unite=unite, n=0)

    freq = [[c / total for c in ligne] for ligne in grille]
    parts = [sum(ligne) for ligne in freq]
    i_dom = max(range(n_secteurs), key=lambda i: parts[i])
    ordonnees = sorted(retenues)

    return Rose(
        source=source,
        variable=variable,
        unite=unite,
        n=total,
        secteurs=list(noms),
        classes=_libelles(bornes, unite),
        bornes=list(bornes),
        frequences=freq,
        calme=calmes / total,
        secteur_dominant=noms[i_dom],
        part_dominante=parts[i_dom],
        moyenne=(sum(retenues) / len(retenues)) if retenues else 0.0,
        p95=(ordonnees[min(len(ordonnees) - 1, int(0.95 * (len(ordonnees) - 1)))]
             if ordonnees else 0.0),
    )
