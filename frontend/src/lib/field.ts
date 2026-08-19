/**
 * Rendu raster d'un champ de grille.
 *
 * Interpolation bilinéaire sur la grille régulière, avec masque terre/mer
 * strict : une maille dont un seul nœud est à terre n'est pas rendue, plutôt
 * que d'extrapoler une valeur de houle par-dessus la côte.
 *
 * L'image est produite dans l'espace **Mercator** (et non linéairement en
 * latitude) parce que c'est ainsi que deck.gl plaque une texture sur des
 * bornes géographiques : sans cette correction, le champ glisserait
 * verticalement d'autant plus que la latitude est élevée.
 */

import type { Grille } from '../api/client'
import { colorFor, type Echelle } from './palette'

const mercY = (lat: number) =>
  Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360))
const invMercY = (y: number) => ((2 * Math.atan(Math.exp(y)) - Math.PI / 2) * 180) / Math.PI

/** Échantillonne un champ au point (lat, lon) — `null` si masqué. */
export function sampleField(
  g: Grille,
  champ: string,
  t: number,
  lat: number,
  lon: number,
): number | null {
  const plan = g.champs[champ]?.[t]
  if (!plan) return null
  const { lats, lons } = g
  if (lats.length < 2 || lons.length < 2) return null

  const dla = (lats[lats.length - 1] - lats[0]) / (lats.length - 1)
  const dlo = (lons[lons.length - 1] - lons[0]) / (lons.length - 1)
  const gi = (lat - lats[0]) / dla
  const gj = (lon - lons[0]) / dlo
  if (gi < 0 || gj < 0 || gi > lats.length - 1 || gj > lons.length - 1) return null

  const i0 = Math.min(lats.length - 2, Math.floor(gi))
  const j0 = Math.min(lons.length - 2, Math.floor(gj))
  const fi = gi - i0
  const fj = gj - j0

  const v00 = plan[i0]?.[j0]
  const v01 = plan[i0]?.[j0 + 1]
  const v10 = plan[i0 + 1]?.[j0]
  const v11 = plan[i0 + 1]?.[j0 + 1]
  if (v00 == null || v01 == null || v10 == null || v11 == null) return null

  return (
    v00 * (1 - fi) * (1 - fj) +
    v01 * (1 - fi) * fj +
    v10 * fi * (1 - fj) +
    v11 * fi * fj
  )
}

export interface FieldImage {
  url: string
  bounds: [number, number, number, number]
}

/** Produit l'image du champ et ses bornes [ouest, sud, est, nord]. */
export function renderField(
  g: Grille,
  champ: string,
  t: number,
  sc: Echelle,
  maxPx = 640,
): FieldImage | null {
  const { lats, lons } = g
  if (lats.length < 2 || lons.length < 2) return null

  const south = lats[0]
  const north = lats[lats.length - 1]
  const west = lons[0]
  const east = lons[lons.length - 1]

  const ratio = (mercY(north) - mercY(south)) / ((east - west) * (Math.PI / 180))
  const w = maxPx
  const h = Math.max(16, Math.min(maxPx * 2, Math.round(maxPx * ratio)))

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const img = ctx.createImageData(w, h)
  const data = img.data
  const y0 = mercY(north)
  const y1 = mercY(south)

  for (let py = 0; py < h; py++) {
    const lat = invMercY(y0 + ((y1 - y0) * (py + 0.5)) / h)
    for (let px = 0; px < w; px++) {
      const lon = west + ((east - west) * (px + 0.5)) / w
      const col = colorFor(sampleField(g, champ, t, lat, lon), sc)
      if (!col) continue
      const o = (py * w + px) * 4
      data[o] = col[0]
      data[o + 1] = col[1]
      data[o + 2] = col[2]
      data[o + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  return { url: canvas.toDataURL(), bounds: [west, south, east, north] }
}

export interface Fleche {
  position: [number, number]
  angle: number
  taille: number
}

/** Vecteurs de direction : la flèche pointe vers où **va** la houle. */
export function buildArrows(g: Grille, t: number): Fleche[] {
  const dirs = g.directions?.[t]
  const hsPlan = g.champs.hs?.[t]
  if (!dirs || !hsPlan) return []
  const hsMax = g.stats.hs?.max || 1
  const out: Fleche[] = []
  for (let i = 0; i < g.lats.length; i++) {
    for (let j = 0; j < g.lons.length; j++) {
      const d = dirs[i]?.[j]
      const hs = hsPlan[i]?.[j]
      if (d == null || hs == null) continue
      out.push({
        position: [g.lons[j], g.lats[i]],
        // direction de provenance → cap de propagation = d + 180 ;
        // deck.gl mesure l'angle en trigonométrique depuis l'est
        angle: -90 - d,
        // la longueur porte l'information d'intensité : Hs relatif au maximum
        taille: 20 + 22 * Math.min(1, hs / hsMax),
      })
    }
  }
  return out
}
