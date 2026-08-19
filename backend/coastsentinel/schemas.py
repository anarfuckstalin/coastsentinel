"""Schémas d'entrée et de sortie de l'API (Pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfilPlage(BaseModel):
    """Profil morphologique du site — le paramètre βf domine l'incertitude."""

    beta_f: float = Field(0.045, ge=0.005, le=0.3,
                          description="Pente d'estran [-]")
    z_berme: float = Field(2.2, ge=-5, le=30,
                           description="Altitude du pied de dune / berme [m/NM]")
    z_crete: float = Field(4.6, ge=-5, le=60,
                           description="Altitude de crête [m/NM]")
    msl_trend: float = Field(0.0, ge=-2, le=5,
                             description="Élévation eustatique cumulée [m]")
    i_erosion: float = Field(0.0, ge=0, le=1,
                             description="Indice d'érosion M5 [0-1]")
    alpha: float = Field(0.2, ge=0, le=0.5,
                         description="Force du couplage inter-échelles")

    @model_validator(mode="after")
    def crete_au_dessus_de_la_berme(self) -> ProfilPlage:
        if self.z_crete <= self.z_berme:
            raise ValueError(
                "L'altitude de crête doit être supérieure à celle de la berme."
            )
        return self


class AnalyseRequest(BaseModel):
    nom: str = Field("Site", max_length=120)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    source: Literal["openmeteo", "demo"] = "openmeteo"
    days: int = Field(5, ge=1, le=10)
    start: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    climatologie_annees: int = Field(10, ge=0, le=30)
    profil: ProfilPlage = ProfilPlage()

    @model_validator(mode="after")
    def periode_coherente(self) -> AnalyseRequest:
        if bool(self.start) != bool(self.end):
            raise ValueError("Renseignez les deux dates, ou aucune.")
        if self.start and self.end and self.start > self.end:
            raise ValueError("La date de début est postérieure à la date de fin.")
        return self


class GrilleRequest(BaseModel):
    """Emprise et résolution d'une grille de champs cartographiques."""

    sud: float = Field(..., ge=-90, le=90)
    nord: float = Field(..., ge=-90, le=90)
    ouest: float = Field(..., ge=-180, le=180)
    est: float = Field(..., ge=-180, le=180)
    nx: int = Field(9, ge=2, le=14)
    ny: int = Field(7, ge=2, le=14)
    source: Literal["openmeteo", "demo"] = "openmeteo"
    days: int = Field(3, ge=1, le=7)
    start: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    profil: ProfilPlage = ProfilPlage()
    seuil_p95: float | None = None
    seuil_p99: float | None = None
    ref_p95: float = 2.8

    @model_validator(mode="after")
    def emprise_valide(self) -> GrilleRequest:
        if self.nord <= self.sud:
            raise ValueError("La latitude nord doit être supérieure à la sud.")
        if self.est <= self.ouest:
            raise ValueError("La longitude est doit être supérieure à l'ouest.")
        if self.nord - self.sud > 25 or self.est - self.ouest > 25:
            raise ValueError(
                "Emprise trop vaste — zoomez sur un secteur littoral "
                "(moins de 25° d'étendue)."
            )
        return self


class PasDeTemps(BaseModel):
    """Un pas de temps évalué. ``from_attributes`` permet de valider
    directement les dataclasses du moteur, sans conversion intermédiaire."""

    model_config = ConfigDict(from_attributes=True)

    t: str
    hs: float
    tp: float
    direction: float
    sea_level: float
    surge: float
    setup: float
    swash: float
    r2: float
    xi0: float
    twl: float
    regime: str
    rank: int
    power: float
    niveau: int
    hs_vent: float | None = None
    dir_vent: float | None = None
    hs_houle: float | None = None
    dir_houle: float | None = None
    tp_houle: float | None = None
    courant: float | None = None
    courant_dir: float | None = None
    sst: float | None = None


class ClimatologieOut(BaseModel):
    source: str
    confiance: str
    annees: float
    hs_p50: float
    hs_p95: float
    hs_p99: float
    hs_p999: float
    hs_return: dict[int, float]
    gpd_diag: dict[str, object]


class SeuilsOut(BaseModel):
    twl_p95: float
    twl_p99: float
    twl_p95_eff: float
    twl_p99_eff: float
    facteur_couplage: float
    source: str


class RoseOut(BaseModel):
    """Distribution conjointe intensité × direction de provenance."""

    model_config = ConfigDict(from_attributes=True)

    source: str
    variable: str
    unite: str
    n: int
    secteurs: list[str]
    classes: list[str]
    bornes: list[float]
    frequences: list[list[float]]
    calme: float
    secteur_dominant: str
    part_dominante: float
    moyenne: float
    p95: float


class AnalyseResponse(BaseModel):
    site: dict
    niveau_max: int
    niveau_label: str
    action: str
    pic: PasDeTemps
    seuils: SeuilsOut
    climatologie: ClimatologieOut
    spi: float
    heures_alerte: float
    dt_h: float
    regime_max: int
    serie: list[PasDeTemps]
    episodes: list[dict]
    source: str
    note: str
    tide_estimee: bool
    variables_disponibles: list[str]
    rose: RoseOut | None = None
    avertissements: list[str]


class GrilleResponse(BaseModel):
    lats: list[float]
    lons: list[float]
    times: list[str]
    champs: dict[str, list[list[list[float | None]]]]
    directions: list[list[list[float | None]]]
    stats: dict[str, dict[str, float]]
    n_mer: int
    n_total: int
    seuils: dict[str, float]
    couverture: dict[str, int] = Field(
        default_factory=dict,
        description="Nombre de valeurs servies par champ, tous pas de temps "
                    "confondus. Zéro = variable non fournie sur cette emprise.",
    )
    champs_disponibles: list[str] = Field(default_factory=list)
    avertissements: list[str]


class LieuOut(BaseModel):
    nom: str
    lat: float
    lon: float
    pays: str | None = None
    region: str | None = None
    population: int | None = None
