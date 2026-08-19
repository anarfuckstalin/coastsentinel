/** Client typé de l'API CoastSentinel. */

export interface ProfilPlage {
  beta_f: number
  z_berme: number
  z_crete: number
  msl_trend: number
  i_erosion: number
  alpha: number
}

export interface PasDeTemps {
  t: string
  hs: number
  tp: number
  direction: number
  sea_level: number
  surge: number
  setup: number
  swash: number
  r2: number
  xi0: number
  twl: number
  regime: string
  rank: number
  power: number
  niveau: number
  hs_vent?: number | null
  dir_vent?: number | null
  hs_houle?: number | null
  dir_houle?: number | null
  tp_houle?: number | null
  courant?: number | null
  courant_dir?: number | null
  sst?: number | null
}

export interface Rose {
  source: string
  variable: string
  unite: string
  n: number
  secteurs: string[]
  classes: string[]
  bornes: number[]
  /** frequences[secteur][classe] — fractions du total */
  frequences: number[][]
  calme: number
  secteur_dominant: string
  part_dominante: number
  moyenne: number
  p95: number
}

export interface Analyse {
  site: Record<string, unknown>
  niveau_max: number
  niveau_label: string
  action: string
  pic: PasDeTemps
  seuils: {
    twl_p95: number
    twl_p99: number
    twl_p95_eff: number
    twl_p99_eff: number
    facteur_couplage: number
    source: string
  }
  climatologie: {
    source: string
    confiance: string
    annees: number
    hs_p50: number
    hs_p95: number
    hs_p99: number
    hs_p999: number
    hs_return: Record<string, number>
    gpd_diag: Record<string, unknown>
  }
  spi: number
  heures_alerte: number
  dt_h: number
  regime_max: number
  serie: PasDeTemps[]
  episodes: Episode[]
  source: string
  note: string
  tide_estimee: boolean
  variables_disponibles: string[]
  rose: Rose | null
  avertissements: string[]
}

export interface Episode {
  debut: string
  fin: string
  niveau: number
  duree_h: number
  twl_max: number
  hs_max: number
  regime: string
}

export interface Grille {
  lats: number[]
  lons: number[]
  times: string[]
  champs: Record<string, (number | null)[][][]>
  directions: (number | null)[][][]
  stats: Record<string, { min: number; max: number }>
  n_mer: number
  n_total: number
  seuils: { p95_eff: number; p99_eff: number }
  /** Nombre de valeurs servies par champ. 0 = variable non fournie ici. */
  couverture: Record<string, number>
  champs_disponibles: string[]
  diagnostic: Record<string, unknown>
  avertissements: string[]
}

/** Un champ porte-t-il des données ?
 *
 *  On distingue trois cas, et l'interface doit les distinguer aussi :
 *  couverture absente = backend antérieur à cette version ; couverture nulle
 *  = variable non servie sur l'emprise ; couverture positive = champ utile.
 */
export function champServi(g: Grille | null, cle: string): boolean {
  if (!g) return true
  if (!g.couverture) return Array.isArray(g.champs?.[cle])
  return (g.couverture[cle] ?? 0) > 0
}

/** Vrai si l'API tourne encore sur une version qui ignore ces champs. */
export function backendObsolete(g: Grille | null): boolean {
  return !!g && g.couverture == null
}

export interface Station {
  nom: string
  pays: string
  lat: number
  lon: number
  region: string
  src: string
}

export interface Lieu {
  nom: string
  lat: number
  lon: number
  pays?: string | null
  region?: string | null
  population?: number | null
}

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(
      "L'API est injoignable. Vérifiez que le serveur backend tourne " +
        '(http://localhost:8000).',
      0,
    )
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((d: { msg?: string }) => (d.msg ?? '').replace(/^Value error, /, ''))
          .filter(Boolean)
          .join(' · ')
      }
    } catch {
      /* réponse non JSON : on garde le statut */
    }
    throw new ApiError(detail, res.status)
  }
  return res.json() as Promise<T>
}

export const api = {
  sante: () => request<{ statut: string; version: string }>('/api/sante'),

  lieux: (q: string) => request<Lieu[]>(`/api/lieux?q=${encodeURIComponent(q)}`),

  stations: (q?: string) =>
    request<{ total: number; retournees: number; stations: Station[]; note: string }>(
      `/api/stations${q ? `?q=${encodeURIComponent(q)}` : ''}`,
    ),

  analyse: (body: unknown) =>
    request<Analyse>('/api/analyse', { method: 'POST', body: JSON.stringify(body) }),

  grille: (body: unknown) =>
    request<Grille>('/api/grille', { method: 'POST', body: JSON.stringify(body) }),
}

/** Coordonnées saisies directement : « 30.42, -9.62 » ou « 30,42 -9,62 ». */
export function parseCoords(s: string): { lat: number; lon: number } | null {
  const m = s
    .trim()
    .match(/^(-?\d{1,2}(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:[.,]\d+)?)$/)
  if (!m) return null
  const lat = parseFloat(m[1].replace(',', '.'))
  const lon = parseFloat(m[2].replace(',', '.'))
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null
  return { lat, lon }
}
