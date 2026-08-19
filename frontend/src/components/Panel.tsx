import { useMutation } from '@tanstack/react-query'
import {
  AlertTriangle, Download, Eraser, Layers, Loader2, Play, Radio, Settings2,
  Waves,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

import { api, ApiError, backendObsolete, champServi } from '../api/client'
import { grilleVersCSV, grilleVersGeoJSON, slug, telecharger } from '../lib/export'
import { CHAMPS, champByKey } from '../lib/palette'
import { useStore } from '../store'

function Section({ titre, icone, children, defaut = true }: {
  titre: string
  icone: ReactNode
  children: ReactNode
  defaut?: boolean
}) {
  const [ouvert, setOuvert] = useState(defaut)
  return (
    <div style={{ borderBottom: '1px solid var(--grid)' }}>
      <button
        onClick={() => setOuvert((o) => !o)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <span style={{ color: 'var(--serie-1)' }}>{icone}</span>
        <span className="lbl flex-1">{titre}</span>
        <span className="text-[11px]" style={{ color: 'var(--ink-3)' }}>
          {ouvert ? '▾' : '▸'}
        </span>
      </button>
      {ouvert && <div className="space-y-3 px-4 pb-4">{children}</div>}
    </div>
  )
}

function Champ({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="lbl mb-1 block">{label}</span>
      {children}
    </label>
  )
}

function Num({ v, on, step = 0.1, min, max }: {
  v: number
  on: (n: number) => void
  step?: number
  min?: number
  max?: number
}) {
  return (
    <input
      type="number"
      className="field tabular"
      value={v}
      step={step}
      min={min}
      max={max}
      onChange={(e) => {
        const n = parseFloat(e.target.value)
        if (Number.isFinite(n)) on(n)
      }}
    />
  )
}

export default function Panel() {
  const s = useStore()
  const [erreur, setErreur] = useState<string | null>(null)

  const periode = () =>
    s.mode === 'past' ? { start: s.debut, end: s.fin } : { days: s.jours }

  const analyse = useMutation({
    mutationFn: () =>
      api.analyse({
        nom: s.nom, lat: s.lat, lon: s.lon,
        source: 'openmeteo',
        climatologie_annees: s.climatologieAnnees,
        profil: s.profil,
        ...periode(),
      }),
    onMutate: () => setErreur(null),
    onSuccess: (d) => {
      s.setAnalyse(d)
      s.addSite({
        nom: s.nom, lat: s.lat, lon: s.lon,
        niveau: d.niveau_max, twl: d.pic.twl,
        ratio: d.seuils.twl_p99_eff ? d.pic.twl / d.seuils.twl_p99_eff : 0,
      })
    },
    onError: (e) => setErreur(e instanceof ApiError ? e.message : String(e)),
  })

  const demo = useMutation({
    mutationFn: () =>
      api.analyse({
        nom: s.nom, lat: s.lat, lon: s.lon, source: 'demo',
        climatologie_annees: 0, profil: s.profil,
      }),
    onMutate: () => setErreur(null),
    onSuccess: (d) => {
      s.setAnalyse(d)
      s.addSite({
        nom: s.nom, lat: s.lat, lon: s.lon, niveau: d.niveau_max,
        twl: d.pic.twl, ratio: d.pic.twl / (d.seuils.twl_p99_eff || 1),
      })
    },
    onError: (e) => setErreur(e instanceof ApiError ? e.message : String(e)),
  })

  const grille = useMutation({
    mutationFn: (bbox: { sud: number; nord: number; ouest: number; est: number }) =>
      api.grille({
        ...bbox,
        nx: Math.min(14, Math.max(2, Math.round(s.nx ?? 9))),
        ny: Math.min(14, Math.max(2, Math.round(s.ny ?? 7))),
        source: s.analyse?.source.startsWith('DÉMO') ? 'demo' : 'openmeteo',
        days: Math.min(7, Math.max(1, Math.round(s.joursGrille ?? 3))),
        ...(s.mode === 'past' ? { start: s.debut, end: s.fin } : {}),
        profil: s.profil,
        seuil_p95: s.analyse?.seuils.twl_p95_eff ?? null,
        seuil_p99: s.analyse?.seuils.twl_p99_eff ?? null,
        ref_p95: s.analyse?.climatologie.hs_p95 ?? 2.8,
      }),
    onMutate: () => setErreur(null),
    onSuccess: (g) => s.setGrille(g),
    onError: (e) => setErreur(e instanceof ApiError ? e.message : String(e)),
  })

  const chargerCouches = () => {
    if (!s.bbox) {
      setErreur('Carte non prête — patientez une seconde puis réessayez.')
      return
    }
    const [ouest, sud, est, nord] = s.bbox
    if (nord - sud > 25 || est - ouest > 25) {
      setErreur(
        "Emprise trop vaste — zoomez sur un secteur littoral (moins de 25°).",
      )
      return
    }
    grille.mutate({ sud, nord, ouest, est })
  }

  /* La carte peut demander une analyse (bouton « Analyser ce point » de
     l'infobulle d'une station). On ne réagit qu'aux incréments, pas au
     montage initial. */
  const dernierDeclencheur = useRef(s.analyseDemandee)
  useEffect(() => {
    if (s.analyseDemandee !== dernierDeclencheur.current) {
      dernierDeclencheur.current = s.analyseDemandee
      analyse.mutate()
    }
  }, [s.analyseDemandee, analyse])

  const exporterGrille = (format: 'geojson' | 'csv') => {
    if (!s.grille) return
    const base = `coastsentinel_grille_${slug(s.nom)}`
    if (format === 'geojson') {
      const horodatage = s.grille.times[s.tIndex].replace(/[:T-]/g, '')
      telecharger(
        `${base}_${horodatage}.geojson`,
        grilleVersGeoJSON(s.grille, s.tIndex, {
          site: s.analyse?.site,
          seuils: s.grille.seuils,
        }),
        'application/geo+json',
      )
    } else {
      telecharger(`${base}.csv`, grilleVersCSV(s.grille), 'text/csv;charset=utf-8')
    }
  }

  const enCours = analyse.isPending || demo.isPending

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <Section titre="Point et période" icone={<Waves size={15} />}>
        <Champ label="Nom du site">
          <input className="field" value={s.nom} onChange={(e) => s.setNom(e.target.value)} />
        </Champ>
        <div className="grid grid-cols-2 gap-2.5">
          <Champ label="Latitude">
            <Num v={s.lat} step={0.0001} min={-90} max={90} on={(v) => s.setPoint(v, s.lon)} />
          </Champ>
          <Champ label="Longitude">
            <Num v={s.lon} step={0.0001} min={-180} max={180} on={(v) => s.setPoint(s.lat, v)} />
          </Champ>
        </div>

        <div className="flex overflow-hidden rounded-lg" style={{ border: '1px solid var(--border)' }}>
          {(['now', 'past'] as const).map((m) => (
            <button
              key={m}
              onClick={() => s.setMode(m)}
              className="flex-1 px-2 py-2 text-[12.5px]"
              style={{
                background: s.mode === m ? 'var(--serie-1)' : 'var(--surface-2)',
                color: s.mode === m ? '#fff' : 'var(--ink-2)',
                fontWeight: s.mode === m ? 600 : 400,
              }}
            >
              {m === 'now' ? 'Temps réel' : 'Période choisie'}
            </button>
          ))}
        </div>

        {s.mode === 'past' ? (
          <div className="grid grid-cols-2 gap-2.5">
            <Champ label="Du">
              <input type="date" className="field" value={s.debut}
                onChange={(e) => s.setPeriode({ debut: e.target.value })} />
            </Champ>
            <Champ label="Au">
              <input type="date" className="field" value={s.fin}
                onChange={(e) => s.setPeriode({ fin: e.target.value })} />
            </Champ>
          </div>
        ) : (
          <Champ label={`Horizon de prévision — ${s.jours} jours`}>
            <input type="range" min={1} max={10} value={s.jours} className="w-full"
              onChange={(e) => s.setPeriode({ jours: +e.target.value })} />
          </Champ>
        )}

        <Champ label="Climatologie des seuils">
          <select className="field" value={s.climatologieAnnees}
            onChange={(e) => s.setPeriode({ climatologieAnnees: +e.target.value })}>
            <option value={0}>Aucune — seuils génériques (rapide, peu fiable)</option>
            <option value={3}>3 dernières années</option>
            <option value={10}>10 dernières années (recommandé)</option>
            <option value={20}>20 dernières années (plus lent)</option>
          </select>
        </Champ>

        <div className="flex gap-2 pt-1">
          <button className="btn btn-primary flex-1 inline-flex items-center justify-center gap-2"
            disabled={enCours} onClick={() => analyse.mutate()}>
            {enCours ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Lancer l'analyse
          </button>
          <button className="btn" disabled={enCours} onClick={() => demo.mutate()}
            title="Jeu synthétique — vérifie la chaîne sans dépendre du réseau">
            Démo
          </button>
        </div>
        {erreur && (
          <p className="flex gap-2 text-[12px]" style={{ color: 'var(--ink-2)' }}>
            <AlertTriangle size={14} className="mt-0.5 shrink-0" style={{ color: '#d03b3b' }} />
            <span>{erreur}</span>
          </p>
        )}
      </Section>

      <Section titre="Profil de plage" icone={<Settings2 size={15} />} defaut={false}>
        <p className="text-[11.5px] leading-relaxed" style={{ color: 'var(--ink-2)' }}>
          La pente d'estran βf domine l'incertitude sur le jet de rive.
          Renseignez-la si vous l'avez mesurée ; à défaut, la valeur reste
          générique et le résultat le signale.
        </p>
        <div className="grid grid-cols-2 gap-2.5">
          <Champ label="Pente βf">
            <Num v={s.profil.beta_f} step={0.005} min={0.005} max={0.3}
              on={(v) => s.setProfil({ beta_f: v })} />
          </Champ>
          <Champ label="Berme D_low (m)">
            <Num v={s.profil.z_berme} on={(v) => s.setProfil({ z_berme: v })} />
          </Champ>
          <Champ label="Crête D_high (m)">
            <Num v={s.profil.z_crete} on={(v) => s.setProfil({ z_crete: v })} />
          </Champ>
          <Champ label="Élévation MSL (m)">
            <Num v={s.profil.msl_trend} step={0.05} on={(v) => s.setProfil({ msl_trend: v })} />
          </Champ>
        </div>
        <Champ label={`Indice d'érosion M5 — ${s.profil.i_erosion.toFixed(2)}`}>
          <input type="range" min={0} max={1} step={0.05} className="w-full"
            value={s.profil.i_erosion}
            onChange={(e) => s.setProfil({ i_erosion: +e.target.value })} />
        </Champ>
        <Champ label={`Couplage inter-échelles α — ${s.profil.alpha.toFixed(2)}`}>
          <input type="range" min={0} max={0.5} step={0.05} className="w-full"
            value={s.profil.alpha}
            onChange={(e) => s.setProfil({ alpha: +e.target.value })} />
        </Champ>
      </Section>

      <Section titre="Couches cartographiques" icone={<Layers size={15} />}>
        <button className="btn btn-primary w-full inline-flex items-center justify-center gap-2"
          disabled={grille.isPending} onClick={chargerCouches}>
          {grille.isPending ? <Loader2 size={14} className="animate-spin" /> : <Layers size={14} />}
          Charger sur la zone visible
        </button>

        <Champ label="Résolution de la grille">
          <select
            className="field"
            value={`${s.nx ?? 9}x${s.ny ?? 7}`}
            onChange={(e) => {
              const [nx, ny] = e.target.value.split('x').map(Number)
              s.setGrilleParams({ nx, ny })
            }}
          >
            <option value="4x3">4 × 3 — très rapide (12 points)</option>
            <option value="6x5">6 × 5 — rapide (30 points)</option>
            <option value="9x7">9 × 7 — standard (63 points)</option>
            <option value="12x9">12 × 9 — fin (108 points)</option>
            <option value="14x11">14 × 11 — très fin (154 points, lent)</option>
          </select>
        </Champ>
        <div className="grid grid-cols-2 gap-2.5">
          <Champ label="Colonnes (nx)">
            <Num v={s.nx ?? 9} step={1} min={2} max={14}
              on={(v) => s.setGrilleParams({ nx: Math.round(v) })} />
          </Champ>
          <Champ label="Lignes (ny)">
            <Num v={s.ny ?? 7} step={1} min={2} max={14}
              on={(v) => s.setGrilleParams({ ny: Math.round(v) })} />
          </Champ>
        </div>
        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--ink-3)' }}>
          {(s.nx ?? 9) * (s.ny ?? 7)} points interrogés en une requête. Le modèle de vagues a
          une maille d'environ 8 km : au-delà, une grille plus fine n'ajoute
          plus d'information, elle interpole seulement.
        </p>
        <Champ label={`Horizon des couches — ${s.joursGrille ?? 3} jour${(s.joursGrille ?? 3) > 1 ? 's' : ''}`}>
          <input type="range" min={1} max={7} value={s.joursGrille ?? 3} className="w-full"
            onChange={(e) => s.setGrilleParams({ joursGrille: +e.target.value })} />
        </Champ>

        <Champ label="Champ affiché">
          <select className="field" value={s.champ} onChange={(e) => s.setChamp(e.target.value)}>
            {CHAMPS.map((c) => {
              const servi = champServi(s.grille, c.cle)
              return (
                <option key={c.cle} value={c.cle} disabled={!servi}>
                  {c.nom}
                  {c.unite ? ` (${c.unite})` : ''}
                  {servi ? '' : ' — non servi ici'}
                </option>
              )
            })}
          </select>
        </Champ>
        {s.grille && !champServi(s.grille, s.champ) && (
          <p className="rounded-lg px-2.5 py-2 text-[12px] leading-relaxed"
            style={{ background: 'var(--surface-2)', color: 'var(--ink-2)' }}>
            <b>{champByKey(s.champ).nom}</b> : le fournisseur n'a renvoyé
            aucune valeur sur cette emprise. La carte reste donc vide pour ce
            champ — ce n'est pas un défaut d'affichage. Courants et température
            sont modélisés à 8 km : près de la côte, les nœuds tombent souvent
            hors couverture. Élargissez l'emprise vers le large, ou lancez{' '}
            <code className="tabular">python -m coastsentinel.cli diag</code>{' '}
            pour voir ce que la source sert réellement en ce point.
          </p>
        )}
        {backendObsolete(s.grille) && (
          <p className="rounded-lg px-2.5 py-2 text-[12px] leading-relaxed"
            style={{ background: 'var(--surface-2)', color: 'var(--ink-2)',
              borderLeft: '3px solid var(--serie-2)' }}>
            L'API tourne sur une version antérieure : elle ne connaît pas les
            champs houle de fond, courant et température. Le front s'est
            rechargé tout seul, pas uvicorn — arrêtez le serveur (Ctrl+C) et
            relancez-le.
          </p>
        )}
        <Champ label={`Opacité — ${Math.round(s.opacite * 100)} %`}>
          <input type="range" min={0.15} max={1} step={0.01} className="w-full"
            value={s.opacite} onChange={(e) => s.setOpacite(+e.target.value)} />
        </Champ>
        <label className="flex items-center gap-2 text-[12.5px]">
          <input type="checkbox" checked={s.fleches} onChange={s.toggleFleches} />
          <span className="inline-block h-0.5 w-4 shrink-0 rounded"
            style={{ background: '#ffffff', outline: '1px solid var(--border)' }} />
          Direction de houle (provenance)
        </label>
        {s.grille ? (
          <>
            <p className="text-[11.5px] tabular" style={{ color: 'var(--ink-3)' }}>
              Couche active · {s.grille.n_mer} nœuds marins sur {s.grille.n_total} ·{' '}
              {s.grille.times.length} pas de temps · opacité{' '}
              {Math.round(s.opacite * 100)} %
            </p>
            <p className="text-[11.5px]" style={{ color: 'var(--ink-3)' }}>
              Champs servis :{' '}
              {CHAMPS.filter((c) => champServi(s.grille, c.cle)).length} sur{' '}
              {CHAMPS.length}
              {CHAMPS.some((c) => !champServi(s.grille, c.cle)) && (
                <>
                  {' '}— absents :{' '}
                  {CHAMPS.filter((c) => !champServi(s.grille, c.cle))
                    .map((c) => c.nom.toLowerCase())
                    .join(', ')}
                </>
              )}
            </p>
          </>
        ) : (
          <p className="text-[11.5px]" style={{ color: 'var(--ink-3)' }}>
            Aucune couche chargée. Cadrez la carte sur un secteur littoral puis
            cliquez sur « Charger sur la zone visible ».
          </p>
        )}
        {s.grille && (
          <>
            <div className="flex gap-2">
              <button className="btn flex-1 inline-flex items-center justify-center gap-1.5"
                onClick={() => exporterGrille('geojson')}
                title="Instantané au pas de temps affiché — s'ouvre dans QGIS">
                <Download size={13} /> GeoJSON
              </button>
              <button className="btn flex-1 inline-flex items-center justify-center gap-1.5"
                onClick={() => exporterGrille('csv')}
                title="Séquence complète, un enregistrement par nœud et par pas">
                <Download size={13} /> CSV
              </button>
            </div>
            <p className="text-[11px] leading-relaxed" style={{ color: 'var(--ink-3)' }}>
              GeoJSON : instantané du pas affiché, pour la cartographie.
              CSV : toute la séquence en format long, pour l'analyse
              temporelle. Les nœuds à terre sont omis, jamais exportés à zéro.
            </p>
          </>
        )}
        {s.grille?.avertissements?.length ? (
          <div className="space-y-1.5">
            {s.grille.avertissements.map((m, i) => (
              <p key={i} className="pl-2.5 text-[11.5px] leading-relaxed"
                style={{ color: 'var(--ink-2)',
                  borderLeft: '2px solid var(--serie-2)' }}>
                {m}
              </p>
            ))}
          </div>
        ) : null}
        <button className="btn w-full inline-flex items-center justify-center gap-2"
          onClick={() => { s.setGrille(null); s.clearSites() }}>
          <Eraser size={14} /> Tout effacer
        </button>
      </Section>

      <Section titre="Fonds et couches externes" icone={<Radio size={15} />} defaut={false}>
        <Champ label="Fond de carte">
          <select className="field" value={s.fond}
            onChange={(e) => s.setFond(e.target.value as never)}>
            <option value="sombre">Sombre (CARTO)</option>
            <option value="clair">Clair (CARTO)</option>
            <option value="satellite">Satellite (Esri)</option>
          </select>
        </Champ>
        {[
          ['— Bathymétrie et fonds —', ''],
          ['gebco', 'GEBCO 2025 — bathymétrie mondiale'],
          ['emodnet', 'EMODnet Bathymetry — haute résolution'],
          ['bluemarble', 'NASA Blue Marble — relief et bathymétrie'],
          ['seamark', 'OpenSeaMap — balisage maritime'],
          ['— Observation satellitaire (NASA GIBS) —', ''],
          ['truecolor', 'Vraies couleurs VIIRS NOAA-20'],
          ['truecolorTerra', 'Vraies couleurs MODIS Terra'],
          ['chloro', 'Chlorophylle a — proxy de turbidité'],
          ['sst', 'Température de surface (MUR)'],
          ['sstAnom', 'Anomalie de température (MUR)'],
        ].map(([cle, nom]) =>
          nom === '' ? (
            <div key={cle} className="pt-1.5 text-[10.5px] uppercase tracking-wide"
              style={{ color: 'var(--ink-3)' }}>
              {String(cle).replace(/—/g, '').trim()}
            </div>
          ) : (
            <label key={cle} className="flex items-center gap-2 text-[12.5px]">
              <input type="checkbox" checked={!!s.raster[cle]}
                onChange={() => s.toggleRaster(cle)} />
              {nom}
            </label>
          ),
        )}
        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--ink-3)' }}>
          Une couche restée blanche signifie que son serveur ne dessert pas ce
          niveau de zoom, ou qu'il est momentanément indisponible. Dézoomez d'un
          cran avant de conclure à une panne.
        </p>
        <Champ label="Date des images satellitaires">
          <input type="date" className="field" value={s.gibsDate}
            onChange={(e) => s.setGibsDate(e.target.value)} />
        </Champ>
        <label className="flex items-center gap-2 text-[12.5px]">
          <input type="checkbox" checked={s.stationsVisibles} onChange={s.toggleStations} />
          Stations mondiales de référence
        </label>
        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--ink-3)' }}>
          Positions portuaires, précises à environ un kilomètre : repérage et
          amorce d'analyse, jamais calcul.
        </p>
      </Section>
    </div>
  )
}
