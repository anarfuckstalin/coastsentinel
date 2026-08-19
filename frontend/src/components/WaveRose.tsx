import { useState } from 'react'

import type { Rose } from '../api/client'
import { ordinalColors } from '../lib/palette'
import { useStore } from '../store'

/**
 * Rose de direction — histogramme polaire empilé.
 *
 * Les classes d'intensité sont **ordinales** : une rampe à une seule teinte,
 * du clair au foncé, laisse lire l'ordre dans la couleur elle-même. Une
 * palette catégorielle ici serait une faute — elle suggérerait que les
 * classes sont interchangeables.
 *
 * Convention : directions **de provenance**. « NO » = houle venant du
 * nord-ouest, ce qui est la convention océanographique et météorologique.
 */

const R_EXT = 118
const R_INT = 26
const TAILLE = 300
const C = TAILLE / 2

const polaire = (rayon: number, angleDeg: number) => {
  const a = ((angleDeg - 90) * Math.PI) / 180
  return [C + rayon * Math.cos(a), C + rayon * Math.sin(a)] as const
}

function secteurPath(r0: number, r1: number, a0: number, a1: number): string {
  const [x0, y0] = polaire(r0, a0)
  const [x1, y1] = polaire(r1, a0)
  const [x2, y2] = polaire(r1, a1)
  const [x3, y3] = polaire(r0, a1)
  return [
    `M ${x0.toFixed(2)} ${y0.toFixed(2)}`,
    `L ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    `A ${r1.toFixed(2)} ${r1.toFixed(2)} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`,
    `L ${x3.toFixed(2)} ${y3.toFixed(2)}`,
    `A ${r0.toFixed(2)} ${r0.toFixed(2)} 0 0 0 ${x0.toFixed(2)} ${y0.toFixed(2)}`,
    'Z',
  ].join(' ')
}

export default function WaveRose({ rose }: { rose: Rose }) {
  const [survol, setSurvol] = useState<{ s: number; c: number } | null>(null)
  const sombre = useStore((st) => st.theme) === 'dark'
  if (!rose || !rose.n) return null

  const n = rose.secteurs.length
  const largeur = 360 / n
  const couleurs = ordinalColors(rose.classes.length, sombre)

  const totaux = rose.frequences.map((l) => l.reduce((a, b) => a + b, 0))
  const max = Math.max(...totaux, 0.001)
  /* Graduations rondes : on cherche un pas lisible plutôt que de diviser le
     maximum, pour que les cercles portent des valeurs interprétables. */
  const pas = [0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3].find((p) => max / p <= 4)
    ?? 0.5
  const graduations: number[] = []
  for (let v = pas; v <= max + pas * 0.5; v += pas) graduations.push(+v.toFixed(3))
  const rMax = graduations[graduations.length - 1] || max
  const rayon = (f: number) => R_INT + (R_EXT - R_INT) * (f / rMax)

  const info = survol
    ? {
        secteur: rose.secteurs[survol.s],
        classe: rose.classes[survol.c],
        freq: rose.frequences[survol.s][survol.c],
        total: totaux[survol.s],
      }
    : null

  return (
    <div className="card p-4">
      <h3 className="mb-0.5 text-[14px] font-semibold">
        Rose de {rose.variable === 'Hs' ? 'houle' : rose.variable}
      </h3>
      <p className="mb-2 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
        Fréquence conjointe intensité × direction <b>de provenance</b>.
        Source : {rose.source}.
      </p>

      <div className="flex flex-wrap items-start gap-4">
        <svg
          viewBox={`0 0 ${TAILLE} ${TAILLE}`}
          className="w-[290px] max-w-full shrink-0"
          role="img"
          aria-label={`Rose de ${rose.variable}, secteur dominant ${rose.secteur_dominant}`}
        >
          {/* cercles de graduation */}
          {graduations.map((g) => (
            <circle
              key={g}
              cx={C}
              cy={C}
              r={rayon(g)}
              fill="none"
              stroke="var(--grid)"
              strokeWidth="1"
            />
          ))}
          {/* axes cardinaux */}
          {[0, 90, 180, 270].map((a) => {
            const [x, y] = polaire(R_EXT + 4, a)
            return (
              <line
                key={a}
                x1={C}
                y1={C}
                x2={x}
                y2={y}
                stroke="var(--grid)"
                strokeWidth="1"
              />
            )
          })}

          {/* secteurs empilés */}
          {rose.frequences.map((classes, si) => {
            const a0 = si * largeur - largeur / 2
            const a1 = a0 + largeur
            let cumul = 0
            return classes.map((f, ci) => {
              if (f <= 0) return null
              const r0 = rayon(cumul)
              cumul += f
              const r1 = rayon(cumul)
              const actif = survol?.s === si && survol?.c === ci
              return (
                <path
                  key={`${si}-${ci}`}
                  d={secteurPath(r0, r1, a0 + 0.6, a1 - 0.6)}
                  fill={couleurs[ci]}
                  stroke="var(--surface-1)"
                  strokeWidth={actif ? 2 : 1}
                  opacity={survol && !actif ? 0.55 : 1}
                  onMouseEnter={() => setSurvol({ s: si, c: ci })}
                  onMouseLeave={() => setSurvol(null)}
                />
              )
            })
          })}

          {/* étiquettes cardinales */}
          {[
            ['N', 0], ['E', 90], ['S', 180], ['O', 270],
          ].map(([nom, a]) => {
            const [x, y] = polaire(R_EXT + 16, a as number)
            return (
              <text
                key={nom as string}
                x={x}
                y={y + 4}
                textAnchor="middle"
                fill="var(--ink-2)"
                fontSize="12"
                fontWeight="600"
              >
                {nom}
              </text>
            )
          })}

          {/* valeurs des graduations, le long de l'axe NE pour ne rien masquer */}
          {graduations.map((g) => {
            const [x, y] = polaire(rayon(g), 45)
            return (
              <text
                key={`g-${g}`}
                x={x}
                y={y}
                textAnchor="middle"
                fill="var(--ink-3)"
                fontSize="9.5"
                style={{ fontVariantNumeric: 'tabular-nums' }}
              >
                {(g * 100).toFixed(0)} %
              </text>
            )
          })}

          {/* cœur : part des calmes */}
          <circle cx={C} cy={C} r={R_INT - 2} fill="var(--surface-2)" />
          <text
            x={C}
            y={C + 4}
            textAnchor="middle"
            fill="var(--ink-2)"
            fontSize="10.5"
          >
            {(rose.calme * 100).toFixed(0)} %
          </text>
        </svg>

        <div className="min-w-[150px] flex-1">
          <div className="mb-2 text-[11px] uppercase tracking-wide"
            style={{ color: 'var(--ink-2)' }}>
            Classes de {rose.variable}
          </div>
          <div className="space-y-1">
            {rose.classes.map((c, i) => (
              <div key={c} className="flex items-center gap-2 text-[12px]">
                <span
                  className="inline-block size-3 shrink-0 rounded-[3px]"
                  style={{ background: couleurs[i] }}
                />
                <span style={{ color: 'var(--ink-2)' }}>{c}</span>
              </div>
            ))}
          </div>

          <dl className="mt-3 space-y-1 text-[12px]" style={{ color: 'var(--ink-2)' }}>
            <div>
              Secteur dominant{' '}
              <b style={{ color: 'var(--ink-1)' }}>{rose.secteur_dominant}</b>{' '}
              ({(rose.part_dominante * 100).toFixed(0)} %)
            </div>
            <div>
              Moyenne{' '}
              <b className="tabular" style={{ color: 'var(--ink-1)' }}>
                {rose.moyenne.toFixed(2)} {rose.unite}
              </b>{' '}
              · P95{' '}
              <b className="tabular" style={{ color: 'var(--ink-1)' }}>
                {rose.p95.toFixed(2)} {rose.unite}
              </b>
            </div>
            <div className="tabular">
              {new Intl.NumberFormat('fr').format(rose.n)} observations
            </div>
          </dl>

          {info && (
            <div className="mt-3 rounded-lg px-2.5 py-2 text-[12px]"
              style={{ background: 'var(--surface-2)' }}>
              <b>{info.secteur}</b> · {info.classe}
              <br />
              <span className="tabular">{(info.freq * 100).toFixed(1)} %</span> du
              total (secteur :{' '}
              <span className="tabular">{(info.total * 100).toFixed(1)} %</span>)
            </div>
          )}
        </div>
      </div>

      {rose.source.includes('non climatologique') && (
        <p className="mt-3 pl-3 text-[12px]"
          style={{ color: 'var(--ink-2)', borderLeft: '3px solid var(--serie-2)' }}>
          Cette rose ne porte que sur la période analysée : elle décrit un
          épisode, pas un régime. Choisissez une climatologie de 10 ou 20 ans
          pour obtenir une rose exploitable dans un mémoire.
        </p>
      )}
    </div>
  )
}
