import { AlertTriangle, Download, Info } from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Line, ComposedChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

import type { Analyse, PasDeTemps } from '../api/client'
import { champByKey, echelle, NIVEAUX, rampCss, STATUS } from '../lib/palette'
import { useStore } from '../store'
import WaveRose from './WaveRose'

const hhmm = (t: string) => {
  const d = new Date(`${t}Z`)
  return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}h`
}

function Tuile({ titre, valeur, couleur, sous }: {
  titre: string
  valeur: string
  couleur: string
  sous: string
}) {
  return (
    <div className="card px-4 py-3">
      <div className="lbl mb-1.5">{titre}</div>
      <div className="flex items-center gap-2 text-[21px] font-semibold leading-tight break-words">
        <span className="inline-block size-3 shrink-0 rounded" style={{ background: couleur }} />
        {valeur}
      </div>
      <div className="mt-1.5 text-[12px]" style={{ color: 'var(--ink-2)' }}>{sous}</div>
    </div>
  )
}

function InfoBulle({ actif, payload }: { actif?: boolean; payload?: Array<{ payload: Row }> }) {
  if (!actif || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="card px-3 py-2 text-[12.5px] leading-relaxed"
      style={{ boxShadow: '0 6px 22px rgba(0,0,0,.24)' }}>
      <div className="mb-1 font-semibold">{d.label} UTC</div>
      <div>Hs <b className="tabular">{d.hs.toFixed(2)} m</b> · Tp <b className="tabular">{d.tp.toFixed(1)} s</b></div>
      <div>Marée + surcote <b className="tabular">{d.sl.toFixed(2)} m</b></div>
      <div>Jet de rive R2% <b className="tabular">{d.r2.toFixed(2)} m</b></div>
      <div>TWL <b className="tabular">{d.twl.toFixed(2)} m</b> · ξ0 {d.xi0.toFixed(2)}</div>
      <div>Régime <b>{d.regime}</b> · niveau <b>{NIVEAUX[d.niveau].label}</b></div>
    </div>
  )
}

interface Row {
  label: string
  hs: number
  tp: number
  sl: number
  setup: number
  swash: number
  r2: number
  twl: number
  xi0: number
  regime: string
  niveau: number
}

const toRow = (s: PasDeTemps): Row => ({
  label: hhmm(s.t), hs: s.hs, tp: s.tp, sl: s.sea_level,
  setup: s.setup, swash: s.r2 - s.setup, r2: s.r2, twl: s.twl,
  xi0: s.xi0, regime: s.regime, niveau: s.niveau,
})

const axe = { stroke: 'var(--ink-3)', fontSize: 11 }

export default function Results({ a }: { a: Analyse }) {
  const grille = useStore((s) => s.grille)
  const champ = useStore((s) => s.champ)
  const rows = a.serie.map(toRow)
  const n = NIVEAUX[a.niveau_max]
  const dtPic = new Date(`${a.pic.t}Z`)
  const delai = (Date.parse(`${a.pic.t}Z`) - Date.parse(`${a.serie[0].t}Z`)) / 3.6e6

  const exporter = (format: 'csv' | 'json') => {
    const nom = String(a.site.nom ?? 'site')
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase()
    let blob: Blob
    if (format === 'csv') {
      const head =
        'time,hs,tp,dir,sea_level,setup,swash,r2,xi0,twl,power,regime,niveau,' +
        'hs_houle,tp_houle,dir_houle,hs_vent,dir_vent,courant,courant_dir,sst'
      const num = (v: number | null | undefined) =>
        v == null || !Number.isFinite(v) ? '' : String(v)
      const lignes = a.serie.map((s) =>
        [s.t, s.hs, s.tp, s.direction, s.sea_level, s.setup, s.swash, s.r2,
         s.xi0, s.twl, s.power, s.regime, s.niveau,
         num(s.hs_houle), num(s.tp_houle), num(s.dir_houle),
         num(s.hs_vent), num(s.dir_vent),
         num(s.courant), num(s.courant_dir), num(s.sst)].join(','))
      blob = new Blob([[head, ...lignes].join('\n')], { type: 'text/csv' })
    } else {
      blob = new Blob([JSON.stringify(a, null, 2)], { type: 'application/json' })
    }
    const url = URL.createObjectURL(blob)
    const el = document.createElement('a')
    el.href = url
    el.download = `coastsentinel_${nom}.${format}`
    el.click()
    setTimeout(() => URL.revokeObjectURL(url), 500)
  }

  const sc = grille ? echelle(champByKey(champ), grille.stats[champ]) : null

  /* P95 et P99 sont souvent très proches : deux étiquettes se chevaucheraient.
     En deçà de 6 % de l'amplitude affichée, on n'en écrit qu'une, combinée. */
  const ampl = Math.max(...rows.map((r) => r.twl)) - Math.min(...rows.map((r) => r.sl))
  const seuilsSerres =
    Math.abs(a.seuils.twl_p99_eff - a.seuils.twl_p95_eff) < 0.06 * (ampl || 1)
  const etiqSeuils = seuilsSerres
    ? `P95 ${a.seuils.twl_p95_eff.toFixed(2)} · P99 ${a.seuils.twl_p99_eff.toFixed(2)} m`
    : `P99 ${a.seuils.twl_p99_eff.toFixed(2)} m`

  return (
    <div className="space-y-3">
      <div className="card px-4 py-3 text-[13.5px]"
        style={{ borderLeft: `4px solid ${n.hex}` }}>
        <b>{String(a.site.nom)} — action recommandée : </b>
        {a.action}
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <div className="col-span-2">
          <Tuile titre="Niveau maximal" valeur={`${n.icone} ${n.label}`} couleur={n.hex}
            sous="sur la période analysée" />
        </div>
        <Tuile titre="TWL au pic" valeur={`${a.pic.twl.toFixed(2)} m`} couleur="var(--serie-2)"
          sous={`${delai > 0 ? `dans ${delai.toFixed(0)} h — ` : ''}${dtPic.toUTCString().slice(5, 17)} UTC`} />
        <Tuile titre="Hs au pic" valeur={`${a.pic.hs.toFixed(2)} m`} couleur="var(--serie-1)"
          sous={`Tp ${a.pic.tp.toFixed(1)} s — P99 local ${a.climatologie.hs_p99.toFixed(2)} m`} />
        <Tuile titre="Régime d'impact" valeur={a.pic.regime} couleur="var(--serie-3)"
          sous="échelle de Sallenger (2000)" />
        <Tuile titre="Durée en alerte" valeur={`${a.heures_alerte.toFixed(0)} h`} couleur={STATUS[1]}
          sous={`SPI ${a.spi.toFixed(0)} m²·h (Dolan & Davis)`} />
      </div>

      {/* frise des niveaux */}
      <div className="card p-4">
        <h3 className="mb-0.5 text-[14px] font-semibold">Niveau d'alerte heure par heure</h3>
        <p className="mb-3 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          Le niveau combine le dépassement des seuils climatologiques locaux, le
          régime d'impact de Sallenger et la règle de persistance (12 h).
        </p>
        <div className="mb-2 flex flex-wrap gap-3.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          {NIVEAUX.map((x) => (
            <span key={x.code} className="inline-flex items-center gap-1.5">
              <span className="inline-block size-3 rounded-[3px]" style={{ background: x.hex }} />
              {x.icone} {x.label}
            </span>
          ))}
        </div>
        <div className="flex h-6 overflow-hidden rounded">
          {a.serie.map((s, i) => (
            <span key={i} title={`${hhmm(s.t)} — ${NIVEAUX[s.niveau].label}`}
              className="h-full flex-1" style={{ background: STATUS[s.niveau] }} />
          ))}
        </div>
      </div>

      {/* TWL */}
      <div className="card p-4">
        <h3 className="mb-0.5 text-[14px] font-semibold">Niveau d'eau total au rivage (TWL)</h3>
        <p className="mb-3 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          TWL = marée + surcote + jet de rive R2% (Stockdon et al., 2006), comparé
          aux seuils climatologiques locaux et à la topographie du profil.
        </p>
        <ResponsiveContainer width="100%" height={230}>
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={axe} minTickGap={34} tickMargin={6} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
            <YAxis tick={axe} tickLine={false} axisLine={false} unit=" m" width={56} />
            <Tooltip content={<InfoBulle />} />
            <Area type="monotone" dataKey="sl" name="Marée + surcote"
              stroke="var(--serie-1)" strokeWidth={2} fill="var(--serie-1)" fillOpacity={0.16} />
            <Line type="monotone" dataKey="twl" name="TWL" stroke="var(--serie-2)"
              strokeWidth={2.5} dot={false} />
            <ReferenceLine y={a.seuils.twl_p95_eff} stroke={STATUS[1]} strokeDasharray="5 4"
              label={seuilsSerres ? undefined : {
                value: `P95 ${a.seuils.twl_p95_eff.toFixed(2)} m`,
                position: 'insideBottomRight', fill: 'var(--ink-2)', fontSize: 10.5, dy: 12,
              }} />
            <ReferenceLine y={a.seuils.twl_p99_eff} stroke={STATUS[2]} strokeDasharray="5 4"
              label={{ value: etiqSeuils, position: 'insideTopRight',
                fill: 'var(--ink-2)', fontSize: 10.5, dy: -4 }} />
            <ReferenceLine y={Number(a.site.z_crete)} stroke={STATUS[3]} strokeDasharray="2 3"
              label={{ value: `Crête ${Number(a.site.z_crete).toFixed(2)} m`, position: 'insideTopRight', fill: 'var(--ink-2)', fontSize: 10.5, dy: -3 }} />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="mt-1 flex flex-wrap gap-3.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block size-3 rounded-[3px]" style={{ background: 'var(--serie-2)' }} />
            TWL (jet de rive)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block size-3 rounded-[3px]" style={{ background: 'var(--serie-1)' }} />
            Niveau statique (marée + surcote)
          </span>
        </div>
      </div>

      {/* décomposition */}
      <div className="card p-4">
        <h3 className="mb-0.5 text-[14px] font-semibold">Décomposition du niveau d'eau</h3>
        <p className="mb-3 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          Quelle composante domine à chaque instant — information directement
          utile pour choisir la mesure de protection.
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={rows} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={axe} minTickGap={34} tickMargin={6} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
            <YAxis tick={axe} tickLine={false} axisLine={false} unit=" m" width={56} />
            <Tooltip content={<InfoBulle />} />
            <Area type="monotone" dataKey="sl" stackId="1" name="Marée + surcote"
              stroke="var(--surface-1)" strokeWidth={2} fill="var(--serie-1)" fillOpacity={0.9} />
            <Area type="monotone" dataKey="setup" stackId="1" name="Setup"
              stroke="var(--surface-1)" strokeWidth={2} fill="var(--serie-3)" fillOpacity={0.9} />
            <Area type="monotone" dataKey="swash" stackId="1" name="Swash"
              stroke="var(--surface-1)" strokeWidth={2} fill="var(--serie-2)" fillOpacity={0.9} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="mt-1 flex flex-wrap gap-3.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          {[['Marée + surcote', 'var(--serie-1)'], ['Setup de houle', 'var(--serie-3)'],
            ['Swash (jet de rive)', 'var(--serie-2)']].map(([l, c]) => (
            <span key={l} className="inline-flex items-center gap-1.5">
              <span className="inline-block size-3 rounded-[3px]" style={{ background: c }} />
              {l}
            </span>
          ))}
        </div>
      </div>

      {/* Hs */}
      <div className="card p-4">
        <h3 className="mb-0.5 text-[14px] font-semibold">Hauteur significative de houle</h3>
        <p className="mb-3 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
          Comparée aux percentiles de la climatologie locale — c'est ce qui rend
          les seuils transposables à n'importe quel littoral du monde.
        </p>
        <ResponsiveContainer width="100%" height={210}>
          <AreaChart data={rows} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={axe} minTickGap={34} tickMargin={6} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
            <YAxis tick={axe} tickLine={false} axisLine={false} unit=" m" width={56} />
            <Tooltip content={<InfoBulle />} />
            <Area type="monotone" dataKey="hs" name="Hs" stroke="var(--serie-1)"
              strokeWidth={2.5} fill="var(--serie-1)" fillOpacity={0.14} />
            <ReferenceLine y={a.climatologie.hs_p95} stroke={STATUS[1]} strokeDasharray="5 4"
              label={{ value: `P95 ${a.climatologie.hs_p95.toFixed(2)} m`, position: 'insideBottomRight', fill: 'var(--ink-2)', fontSize: 10.5, dy: 12 }} />
            <ReferenceLine y={a.climatologie.hs_p99} stroke={STATUS[2]} strokeDasharray="5 4"
              label={{ value: `P99 ${a.climatologie.hs_p99.toFixed(2)} m`, position: 'insideTopRight', fill: 'var(--ink-2)', fontSize: 10.5, dy: -3 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {a.rose && <WaveRose rose={a.rose} />}

      {/* grandeurs océaniques complémentaires */}
      {(a.pic.hs_houle != null || a.pic.courant != null || a.pic.sst != null) && (
        <div className="card p-4">
          <h3 className="mb-0.5 text-[14px] font-semibold">
            Autres grandeurs océaniques au pic
          </h3>
          <p className="mb-3 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
            Partition mer du vent / houle de fond, courant de surface et
            température — servies par le modèle quand elles sont disponibles
            pour ce point.
          </p>
          <dl className="grid grid-cols-2 gap-3 text-[12.5px]"
            style={{ color: 'var(--ink-2)' }}>
            {a.pic.hs_houle != null && (
              <div>
                <dt>Houle de fond</dt>
                <dd className="tabular text-[15px] font-semibold"
                  style={{ color: 'var(--ink-1)' }}>
                  {a.pic.hs_houle.toFixed(2)} m
                </dd>
                <dd className="tabular">
                  {a.pic.tp_houle != null ? `${a.pic.tp_houle.toFixed(1)} s · ` : ''}
                  {a.pic.dir_houle != null ? `${a.pic.dir_houle.toFixed(0)}°` : ''}
                </dd>
              </div>
            )}
            {a.pic.hs_vent != null && (
              <div>
                <dt>Mer du vent</dt>
                <dd className="tabular text-[15px] font-semibold"
                  style={{ color: 'var(--ink-1)' }}>
                  {a.pic.hs_vent.toFixed(2)} m
                </dd>
                <dd className="tabular">
                  {a.pic.dir_vent != null ? `${a.pic.dir_vent.toFixed(0)}°` : ''}
                </dd>
              </div>
            )}
            {a.pic.courant != null && (
              <div>
                <dt>Courant de surface</dt>
                <dd className="tabular text-[15px] font-semibold"
                  style={{ color: 'var(--ink-1)' }}>
                  {a.pic.courant.toFixed(2)} m/s
                </dd>
                <dd className="tabular">
                  {a.pic.courant_dir != null ? `vers ${a.pic.courant_dir.toFixed(0)}°` : ''}
                </dd>
              </div>
            )}
            {a.pic.sst != null && (
              <div>
                <dt>Température de surface</dt>
                <dd className="tabular text-[15px] font-semibold"
                  style={{ color: 'var(--ink-1)' }}>
                  {a.pic.sst.toFixed(1)} °C
                </dd>
              </div>
            )}
          </dl>
          {a.pic.hs_houle != null && a.pic.hs_vent != null && (
            <p className="mt-3 text-[12px]" style={{ color: 'var(--ink-2)' }}>
              Sur une côte ouverte, c'est la <b>houle de fond</b> qui porte
              l'essentiel du jet de rive : sa période plus longue la fait
              déferler plus haut sur l'estran que la mer du vent, à hauteur
              égale.
            </p>
          )}
        </div>
      )}

      {/* légende de la couche cartographique active */}
      {grille && sc && (
        <div className="card p-4">
          <h3 className="mb-2 text-[14px] font-semibold">
            Couche affichée — {sc.def.nom}
            {sc.def.unite ? ` (${sc.def.unite})` : ''}
          </h3>
          {sc.def.type === 'status' ? (
            <div className="flex flex-wrap gap-3.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
              {NIVEAUX.map((x) => (
                <span key={x.code} className="inline-flex items-center gap-1.5">
                  <span className="inline-block size-3 rounded-[3px]" style={{ background: x.hex }} />
                  {x.icone} {x.label}
                </span>
              ))}
            </div>
          ) : (
            <>
              <div className="h-3 rounded" style={{ background: rampCss(sc.def), border: '1px solid var(--border)' }} />
              <div className="mt-1 flex justify-between text-[11px] tabular" style={{ color: 'var(--ink-3)' }}>
                <span>{sc.min.toFixed(2)}</span>
                <span>{((sc.min + sc.max) / 2).toFixed(2)}</span>
                <span>{sc.max.toFixed(2)}</span>
              </div>
            </>
          )}
          <p className="mt-2 text-[11.5px]" style={{ color: 'var(--ink-2)' }}>{sc.def.aide}</p>
        </div>
      )}

      {/* provenance */}
      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-[14px] font-semibold">Provenance, paramètres et confiance</h3>
          <div className="flex gap-2">
            <button className="btn inline-flex items-center gap-1.5 !py-1.5 !text-[12px]"
              onClick={() => exporter('csv')}>
              <Download size={13} /> CSV
            </button>
            <button className="btn inline-flex items-center gap-1.5 !py-1.5 !text-[12px]"
              onClick={() => exporter('json')}>
              <Download size={13} /> JSON
            </button>
          </div>
        </div>
        <dl className="grid gap-3 text-[12.5px] sm:grid-cols-2 xl:grid-cols-3"
          style={{ color: 'var(--ink-2)' }}>
          <div><dt>Source du forçage</dt><dd className="font-semibold" style={{ color: 'var(--ink-1)' }}>{a.source}</dd></div>
          <div><dt>Seuils TWL</dt><dd className="font-semibold" style={{ color: 'var(--ink-1)' }}>{a.seuils.source}</dd>
            <dd className="tabular">P95 {a.seuils.twl_p95.toFixed(2)} m · P99 {a.seuils.twl_p99.toFixed(2)} m</dd></div>
          <div><dt>Climatologie</dt>
            <dd className="font-semibold" style={{ color: 'var(--ink-1)' }}>{a.climatologie.source}</dd>
            <dd>confiance {a.climatologie.confiance}
              {a.climatologie.annees ? ` · ${a.climatologie.annees.toFixed(1)} ans` : ''}</dd></div>
          <div><dt>Pente d'estran βf</dt>
            <dd className="font-semibold tabular" style={{ color: 'var(--ink-1)' }}>{Number(a.site.beta_f).toFixed(3)}</dd>
            <dd>saisie utilisateur — à remplacer par un levé local</dd></div>
          <div><dt>Profil</dt>
            <dd className="font-semibold tabular" style={{ color: 'var(--ink-1)' }}>
              berme {Number(a.site.z_berme).toFixed(2)} m / crête {Number(a.site.z_crete).toFixed(2)} m</dd></div>
          <div><dt>Couplage M5</dt>
            <dd className="font-semibold tabular" style={{ color: 'var(--ink-1)' }}>
              I = {Number(a.site.i_erosion).toFixed(2)}</dd>
            <dd>seuils abaissés de {((1 - a.seuils.facteur_couplage) * 100).toFixed(0)} %</dd></div>
          <div><dt>Incertitude sur R2%</dt>
            <dd className="font-semibold" style={{ color: 'var(--ink-1)' }}>± 20 % environ</dd>
            <dd>écart-type publié de Stockdon et al. (2006)</dd></div>
          <div><dt>Périodes de retour Hs</dt>
            <dd className="font-semibold tabular" style={{ color: 'var(--ink-1)' }}>
              {Object.keys(a.climatologie.hs_return).length
                ? Object.entries(a.climatologie.hs_return)
                    .map(([t, v]) => `T${t}=${v.toFixed(2)} m`).join(' · ')
                : 'non estimables (échantillon trop court)'}</dd></div>
        </dl>

        {a.avertissements.map((m, i) => (
          <p key={i} className="mt-3 flex gap-2 pl-3 text-[12.5px]"
            style={{ color: 'var(--ink-2)', borderLeft: `3px solid ${STATUS[3]}` }}>
            <AlertTriangle size={14} className="mt-0.5 shrink-0" style={{ color: STATUS[3] }} />
            <span>{m}</span>
          </p>
        ))}
        {a.note && (
          <p className="mt-3 flex gap-2 pl-3 text-[12.5px]"
            style={{ color: 'var(--ink-2)', borderLeft: '3px solid var(--serie-1)' }}>
            <Info size={14} className="mt-0.5 shrink-0" style={{ color: 'var(--serie-1)' }} />
            <span>{a.note}</span>
          </p>
        )}
      </div>

      {/* table */}
      <details className="card p-4">
        <summary className="cursor-pointer text-[13.5px] font-semibold">
          Vue tabulaire ({a.serie.length} pas de temps)
        </summary>
        <div className="mt-3 max-h-[340px] overflow-auto">
          <table className="w-full text-[12.5px] tabular">
            <thead>
              <tr style={{ color: 'var(--ink-2)' }}>
                {['Date UTC', 'Hs (m)', 'Tp (s)', 'Dir (°)', 'Niv. stat.', 'R2% (m)',
                  'TWL (m)', 'ξ0', 'P (kW/m)', 'Régime', 'Niveau'].map((h, i) => (
                  <th key={h} className="sticky top-0 px-2 py-1.5 font-semibold"
                    style={{ background: 'var(--surface-1)', textAlign: i === 0 || i > 8 ? 'left' : 'right' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {a.serie.map((s, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="px-2 py-1">{hhmm(s.t)}</td>
                  <td className="px-2 py-1 text-right">{s.hs.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">{s.tp.toFixed(1)}</td>
                  <td className="px-2 py-1 text-right">{s.direction.toFixed(0)}</td>
                  <td className="px-2 py-1 text-right">{s.sea_level.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">{s.r2.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">{s.twl.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">{s.xi0.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">{s.power.toFixed(1)}</td>
                  <td className="px-2 py-1">{s.regime}</td>
                  <td className="px-2 py-1">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="inline-block size-2.5 rounded-[3px]" style={{ background: STATUS[s.niveau] }} />
                      {NIVEAUX[s.niveau].label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  )
}
