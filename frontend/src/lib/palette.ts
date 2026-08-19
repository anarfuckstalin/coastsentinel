/**
 * Rampes de couleur et règles d'encodage.
 *
 * Une seule règle par tâche :
 *   magnitude → rampe SÉQUENTIELLE une teinte, clair → foncé
 *   polarité  → rampe DIVERGENTE deux teintes + gris neutre au centre
 *   état      → palette de STATUT réservée (niveaux d'alerte)
 *
 * Jamais d'arc-en-ciel : une rampe arc-en-ciel invente des frontières
 * qui n'existent pas dans la donnée.
 */

export type RGB = [number, number, number]

/** Rampe séquentielle bleue, steps 100 → 700 de la palette validée. */
export const RAMP_SEQ = [
  '#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7',
  '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b',
]

/** Divergente : bras froid (bleu) + gris neutre + bras chaud (rouge). */
export const RAMP_DIV = [
  '#0d366b', '#184f95', '#256abf', '#3987e5', '#86b6ef', '#cde2fb',
  '#f0efec',
  '#f6dcd6', '#efbdb2', '#e79c8e', '#de7a6b', '#d75a4f', '#d03b3b',
]

/** Statut — réservé aux niveaux d'alerte, toujours accompagné d'un libellé. */
export const STATUS = ['#0ca30c', '#fab219', '#ec835a', '#d03b3b'] as const

export const NIVEAUX = [
  { code: 'VERT', label: 'Vert', icone: '●', hex: STATUS[0] },
  { code: 'JAUNE', label: 'Jaune', icone: '▲', hex: STATUS[1] },
  { code: 'ORANGE', label: 'Orange', icone: '◆', hex: STATUS[2] },
  { code: 'ROUGE', label: 'Rouge', icone: '■', hex: STATUS[3] },
] as const

export function hexToRgb(hex: string): RGB {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
}

const RGB_SEQ = RAMP_SEQ.map(hexToRgb)
const RGB_DIV = RAMP_DIV.map(hexToRgb)
const RGB_STATUS = STATUS.map(hexToRgb)

/** Interpole une rampe en t ∈ [0,1] (bornée hors intervalle). */
export function rampColor(rgbs: RGB[], t: number): RGB {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0)) * (rgbs.length - 1)
  const i = Math.min(rgbs.length - 2, Math.floor(x))
  const f = x - i
  const a = rgbs[i]
  const b = rgbs[i + 1]
  return [
    a[0] + (b[0] - a[0]) * f,
    a[1] + (b[1] - a[1]) * f,
    a[2] + (b[2] - a[2]) * f,
  ]
}

export type ChampType = 'status' | 'seq' | 'div'

export interface ChampDef {
  cle: string
  nom: string
  unite: string
  type: ChampType
  centre?: number
  aide: string
}

export const CHAMPS: ChampDef[] = [
  {
    cle: 'alerte', nom: "Niveau d'alerte", unite: '', type: 'status',
    aide: 'Calculé en chaque nœud avec le profil de plage du panneau.',
  },
  {
    cle: 'twl', nom: "Niveau d'eau total", unite: 'm', type: 'seq',
    aide: 'Marée + surcote + jet de rive R2% (Stockdon et al., 2006).',
  },
  {
    cle: 'hs', nom: 'Hauteur significative Hs', unite: 'm', type: 'seq',
    aide: 'Grandeur brute du modèle de vagues, sans hypothèse ajoutée.',
  },
  {
    cle: 'anom', nom: 'Anomalie Hs / P95 local', unite: '×', type: 'div',
    centre: 1,
    aide: 'Position dans la climatologie du point de référence : 1 = P95.',
  },
  {
    cle: 'tp', nom: 'Période de pic Tp', unite: 's', type: 'seq',
    aide: 'Les houles longues pénètrent plus loin et déferlent plus haut.',
  },
  {
    cle: 'power', nom: 'Puissance de houle', unite: 'kW/m', type: 'seq',
    aide: "Flux d'énergie ρg²Hs²Te/64π — proxy du potentiel érosif.",
  },
  {
    cle: 'r2', nom: 'Jet de rive R2%', unite: 'm', type: 'seq',
    aide: 'Part de la houle dans le niveau au rivage, hors marée.',
  },
  {
    cle: 'sl', nom: "Niveau d'eau (marée + surcote)", unite: 'm', type: 'div',
    centre: 0, aide: 'Composante statique seule.',
  },
]

/** Rampe ORDINALE : classes ordonnées (ex. tranches de Hs d'une rose).
 *
 * L'ancrage s'inverse selon le fond, comme le veut une rampe séquentielle :
 *   • sur fond clair, on va du pas 250 au pas 700 — le plus clair reste
 *     lisible (les pas 100-200 se confondraient avec la surface) ;
 *   • sur fond sombre, on va du pas 550 au pas 100 — les pas les plus foncés
 *     disparaîtraient dans le fond, et la classe la plus intense doit rester
 *     la plus saillante.
 */
export function ordinalColors(n: number, sombre = false): string[] {
  const [debut, fin] = sombre ? [9, 0] : [3, RAMP_SEQ.length - 1]
  if (n <= 1) return [RAMP_SEQ[Math.round((debut + fin) / 2)]]
  return Array.from({ length: n }, (_, i) =>
    RAMP_SEQ[Math.round(debut + ((fin - debut) * i) / (n - 1))],
  )
}

export const champByKey = (k: string) =>
  CHAMPS.find((c) => c.cle === k) ?? CHAMPS[0]

export interface Echelle {
  min: number
  max: number
  def: ChampDef
}

export function echelle(
  def: ChampDef,
  stats?: { min: number; max: number },
): Echelle {
  if (def.type === 'status') return { min: 0, max: 3, def }
  if (!stats || !Number.isFinite(stats.min)) return { min: 0, max: 1, def }
  if (def.type === 'div') {
    const c = def.centre ?? 0
    const r = Math.max(Math.abs(stats.max - c), Math.abs(c - stats.min)) || 1
    return { min: c - r, max: c + r, def }
  }
  return { min: stats.min > 0 ? 0 : stats.min, max: stats.max || 1, def }
}

/** Couleur d'une valeur dans son échelle. `null` = pas de donnée (masqué). */
export function colorFor(v: number | null, sc: Echelle): RGB | null {
  if (v === null || !Number.isFinite(v)) return null
  if (sc.def.type === 'status') {
    return RGB_STATUS[Math.max(0, Math.min(3, Math.round(v)))]
  }
  const t = (v - sc.min) / (sc.max - sc.min || 1)
  return rampColor(sc.def.type === 'div' ? RGB_DIV : RGB_SEQ, t)
}

export const rampCss = (def: ChampDef) =>
  `linear-gradient(to right, ${(def.type === 'div' ? RAMP_DIV : RAMP_SEQ).join(',')})`
