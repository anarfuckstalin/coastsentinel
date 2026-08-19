/**
 * Export des couches chargées.
 *
 * Deux formats, deux usages :
 *   • **GeoJSON** — un instantané : un point par nœud au pas de temps affiché,
 *     avec tous les champs en attributs. S'ouvre tel quel dans QGIS.
 *   • **CSV long** — toute la séquence : une ligne par nœud et par pas de temps.
 *     C'est le format qu'attendent pandas, R et les tableurs pour une analyse
 *     temporelle.
 *
 * Les nœuds à terre sont omis, jamais exportés avec des zéros : un zéro se
 * confondrait avec une mesure.
 */

import type { Analyse, Grille } from '../api/client'
import { CHAMPS } from './palette'

const CLES = CHAMPS.map((c) => c.cle)

export function slug(nom: string): string {
  return (
    nom
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, '_')
      .replace(/^_|_$/g, '')
      .toLowerCase() || 'site'
  )
}

export function telecharger(nom: string, contenu: string, mime: string): void {
  const url = URL.createObjectURL(new Blob([contenu], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = nom
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 800)
}

const arrondi = (v: number | null | undefined, n = 4): number | null =>
  v == null || !Number.isFinite(v) ? null : +v.toFixed(n)

interface Contexte {
  site?: Analyse['site']
  seuils?: Grille['seuils']
}

/** Instantané GeoJSON au pas de temps `t`. */
export function grilleVersGeoJSON(g: Grille, t: number, ctx: Contexte = {}): string {
  const features: unknown[] = []
  for (let i = 0; i < g.lats.length; i++) {
    for (let j = 0; j < g.lons.length; j++) {
      const props: Record<string, unknown> = { time: g.times[t] }
      let valide = false
      for (const cle of CLES) {
        const v = g.champs[cle]?.[t]?.[i]?.[j]
        if (v != null) valide = true
        props[cle] = arrondi(v)
      }
      if (!valide) continue // nœud à terre
      props.direction = arrondi(g.directions?.[t]?.[i]?.[j], 1)
      features.push({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [+g.lons[j].toFixed(5), +g.lats[i].toFixed(5)],
        },
        properties: props,
      })
    }
  }

  return JSON.stringify(
    {
      type: 'FeatureCollection',
      crs: {
        type: 'name',
        properties: { name: 'urn:ogc:def:crs:OGC:1.3:CRS84' },
      },
      metadata: {
        producteur: 'CoastSentinel',
        source: 'Open-Meteo Marine API (ECMWF / GFS-Wave / MFWAM)',
        pas_de_temps: g.times[t],
        grille: `${g.lons.length} × ${g.lats.length}`,
        noeuds_marins: g.n_mer,
        seuils: ctx.seuils ?? null,
        profil_applique: ctx.site ?? null,
        avertissement:
          "La couche d'alerte suppose un profil de plage uniforme sur toute " +
          "la grille : c'est une projection spatiale du forçage, pas une " +
          'carte de vulnérabilité. Aide à la décision et recherche — ne se ' +
          'substitue pas aux alertes officielles des services nationaux.',
      },
      features,
    },
    null,
    1,
  )
}

/** Séquence complète en CSV long (un enregistrement par nœud et par pas). */
export function grilleVersCSV(g: Grille): string {
  const entete = [
    'time', 'lat', 'lon', ...CLES, 'direction',
  ]
  const lignes: string[] = [entete.join(',')]

  for (let t = 0; t < g.times.length; t++) {
    for (let i = 0; i < g.lats.length; i++) {
      for (let j = 0; j < g.lons.length; j++) {
        const vals = CLES.map((cle) => g.champs[cle]?.[t]?.[i]?.[j])
        if (vals.every((v) => v == null)) continue
        lignes.push(
          [
            g.times[t],
            g.lats[i].toFixed(5),
            g.lons[j].toFixed(5),
            ...vals.map((v) => (v == null ? '' : v)),
            g.directions?.[t]?.[i]?.[j] ?? '',
          ].join(','),
        )
      }
    }
  }
  return lignes.join('\n')
}
