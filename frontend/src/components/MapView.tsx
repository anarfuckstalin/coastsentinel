import { MapboxOverlay } from '@deck.gl/mapbox'
import { BitmapLayer, IconLayer, ScatterplotLayer } from '@deck.gl/layers'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import type maplibregl from 'maplibre-gl'
import Map, {
  Layer,
  NavigationControl,
  Popup,
  ScaleControl,
  Source,
  useControl,
  type MapRef,
} from 'react-map-gl/maplibre'

import { api, champServi, type Station } from '../api/client'
import { buildArrows, renderField } from '../lib/field'
import { champByKey, echelle, hexToRgb, STATUS } from '../lib/palette'
import { useStore } from '../store'

/* Fonds de carte libres, sans clé d'API. */
const FONDS = {
  sombre: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  clair: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  satellite: {
    version: 8 as const,
    sources: {
      sat: {
        type: 'raster' as const,
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        attribution: 'Esri, Maxar, Earthstar Geographics',
      },
    },
    layers: [{ id: 'sat', type: 'raster' as const, source: 'sat' }],
    glyphs: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/{fontstack}/{range}.pbf',
  },
}

const gibsUrl = (id: string, niveau: number, ext: string, date: string) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${id}/default/${date}` +
  `/GoogleMapsCompatible_Level${niveau}/{z}/{y}/{x}.${ext}`

const RASTERS: Record<
  string,
  { url: (d: string) => string; max: number; attr: string; opacite: number }
> = {
  gebco: {
    url: () =>
      'https://wms.gebco.net/mapserv?service=WMS&version=1.3.0&request=GetMap' +
      '&layers=GEBCO_LATEST&styles=&format=image/png&transparent=true' +
      '&crs=EPSG:3857&width=256&height=256&bbox={bbox-epsg-3857}',
    max: 12,
    attr: 'GEBCO Compilation Group',
    opacite: 0.8,
  },
  emodnet: {
    url: () =>
      'https://ows.emodnet-bathymetry.eu/wms?service=WMS&version=1.3.0&request=GetMap' +
      '&layers=emodnet:mean_multicolour&styles=&format=image/png&transparent=true' +
      '&crs=EPSG:3857&width=256&height=256&bbox={bbox-epsg-3857}',
    max: 14,
    attr: 'EMODnet Bathymetry',
    opacite: 0.75,
  },
  truecolor: {
    url: (d) => gibsUrl('VIIRS_NOAA20_CorrectedReflectance_TrueColor', 9, 'jpg', d),
    max: 9,
    attr: 'NASA EOSDIS GIBS',
    opacite: 0.9,
  },
  chloro: {
    url: (d) => gibsUrl('MODIS_Aqua_Chlorophyll_A', 7, 'png', d),
    max: 7,
    attr: 'NASA EOSDIS GIBS',
    opacite: 0.8,
  },
  sst: {
    url: (d) => gibsUrl('GHRSST_L4_MUR_Sea_Surface_Temperature', 7, 'png', d),
    max: 7,
    attr: 'NASA EOSDIS GIBS — JPL MUR',
    opacite: 0.8,
  },
  sstAnom: {
    url: (d) =>
      gibsUrl('GHRSST_L4_MUR_Sea_Surface_Temperature_Anomalies', 7, 'png', d),
    max: 7,
    attr: 'NASA EOSDIS GIBS — JPL MUR',
    opacite: 0.8,
  },
  truecolorTerra: {
    url: (d) => gibsUrl('MODIS_Terra_CorrectedReflectance_TrueColor', 9, 'jpg', d),
    max: 9,
    attr: 'NASA EOSDIS GIBS',
    opacite: 0.9,
  },
  bluemarble: {
    url: () =>
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/' +
      'BlueMarble_ShadedRelief_Bathymetry/default/' +
      'GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg',
    max: 8,
    attr: 'NASA Blue Marble — relief et bathymétrie',
    opacite: 0.85,
  },
  seamark: {
    url: () => 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
    max: 18,
    attr: 'OpenSeaMap',
    opacite: 1,
  },
}

/** L'emprise visible est publiée dans le store : le panneau en a besoin
    pour demander une grille sur exactement ce que l'utilisateur voit. */
function publierEmprise(e: { target: maplibregl.Map }) {
  const b = e.target.getBounds()
  useStore.getState().setBbox([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
}

/* Flèche vectorielle inline.
   On n'utilise PAS TextLayer avec un caractère « ➤ » : son jeu de caractères
   par défaut se limite à l'ASCII et la police par défaut est monospace — le
   glyphe n'existe donc pas et rien ne s'affiche. Une icône SVG ne dépend
   d'aucune police.

   `mask: false` conserve les couleurs propres du dessin : la flèche garde
   ainsi son liseré sombre, indispensable pour rester lisible aussi bien sur
   un champ clair que sur un champ foncé. */
const FLECHE_SVG =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" ' +
      'viewBox="0 0 64 64">' +
      '<path d="M3 26 H35 V12 L61 32 L35 52 V38 H3 Z" ' +
      'fill="#ffffff" stroke="rgba(0,0,0,0.62)" stroke-width="4" ' +
      'stroke-linejoin="round"/></svg>',
  )

const ICONE_FLECHE = {
  url: FLECHE_SVG,
  width: 64,
  height: 64,
  anchorX: 32,
  anchorY: 32,
  mask: false,
}

function DeckOverlay(props: Record<string, unknown>) {
  const overlay = useControl(() => new MapboxOverlay({ interleaved: false }))
  overlay.setProps(props)
  return null
}

export default function MapView() {
  const mapRef = useRef<MapRef>(null)
  const s = useStore()
  const [station, setStation] = useState<Station | null>(null)
  const [curseur, setCurseur] = useState('crosshair')

  const { data: stationsData } = useQuery({
    queryKey: ['stations'],
    queryFn: () => api.stations(),
    staleTime: Infinity,
  })

  /* recentrage quand le point change depuis la recherche ou une station */
  useEffect(() => {
    mapRef.current?.flyTo({ center: [s.lon, s.lat], duration: 900 })
  }, [s.lat, s.lon])

  const sc = useMemo(() => {
    const def = champByKey(s.champ)
    return echelle(def, s.grille?.stats[s.champ])
  }, [s.champ, s.grille])

  const field = useMemo(() => {
    if (!s.grille) return null
    return renderField(s.grille, s.champ, s.tIndex, sc)
  }, [s.grille, s.champ, s.tIndex, sc])

  const arrows = useMemo(
    () => (s.grille && s.fleches ? buildArrows(s.grille, s.tIndex) : []),
    [s.grille, s.fleches, s.tIndex],
  )

  const layers = useMemo(() => {
    const out: unknown[] = []

    if (field) {
      out.push(
        new BitmapLayer({
          id: `champ-${s.champ}-${s.tIndex}`,
          image: field.url,
          bounds: field.bounds,
          opacity: s.opacite,
          pickable: false,
          textureParameters: {
            minFilter: 'linear',
            magFilter: 'linear',
            addressModeU: 'clamp-to-edge',
            addressModeV: 'clamp-to-edge',
          },
        }),
      )
    }

    if (arrows.length) {
      out.push(
        new IconLayer({
          id: 'fleches',
          data: arrows,
          getPosition: (d: { position: [number, number] }) => d.position,
          getIcon: () => ICONE_FLECHE,
          getSize: (d: { taille: number }) => d.taille,
          getAngle: (d: { angle: number }) => d.angle,
          sizeUnits: 'pixels',
          sizeMinPixels: 18,
          sizeMaxPixels: 46,
          billboard: true,
          pickable: false,
        }),
      )
    }

    if (s.stationsVisibles && stationsData) {
      out.push(
        new ScatterplotLayer({
          id: 'stations',
          data: stationsData.stations,
          getPosition: (d: Station) => [d.lon, d.lat],
          getRadius: 7,
          radiusUnits: 'pixels',
          radiusMinPixels: 6,
          radiusMaxPixels: 14,
          getFillColor: [42, 120, 214, 235],
          getLineColor: [255, 255, 255, 235],
          lineWidthMinPixels: 1.8,
          stroked: true,
          pickable: true,
          autoHighlight: true,
          highlightColor: [235, 104, 52, 255],
          onHover: ({ object }: { object?: Station }) =>
            setCurseur(object ? 'pointer' : 'crosshair'),
          // `true` empêche la propagation vers la carte : sans cela le clic
          // déplacerait aussi le point d'analyse sous la station.
          onClick: ({ object }: { object?: Station }) => {
            if (!object) return false
            setStation(object)
            return true
          },
        }),
      )
    }

    if (s.sites.length) {
      out.push(
        new ScatterplotLayer({
          id: 'sites-analyses',
          data: s.sites,
          getPosition: (d: { lon: number; lat: number }) => [d.lon, d.lat],
          getRadius: 10,
          radiusUnits: 'pixels',
          getFillColor: (d: { niveau: number }) =>
            [...hexToRgb(STATUS[d.niveau] ?? STATUS[0]), 245] as [
              number,
              number,
              number,
              number,
            ],
          getLineColor: [255, 255, 255, 255],
          lineWidthMinPixels: 2,
          radiusMinPixels: 8,
          radiusMaxPixels: 16,
          stroked: true,
          pickable: true,
          autoHighlight: true,
          onHover: ({ object }: { object?: unknown }) =>
            setCurseur(object ? 'pointer' : 'crosshair'),
        }),
      )
    }
    return out
  }, [field, arrows, s.champ, s.tIndex, s.opacite,
      s.stationsVisibles, s.sites, stationsData])

  const analyserStation = () => {
    if (!station) return
    useStore.getState().demanderAnalyse(station.lat, station.lon, station.nom)
    setStation(null)
  }

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: s.lon, latitude: s.lat, zoom: 7 }}
      mapStyle={FONDS[s.fond] as never}
      style={{ width: '100%', height: '100%' }}
      onClick={(e) => useStore.getState().setPoint(e.lngLat.lat, e.lngLat.lng)}
      onLoad={publierEmprise}
      onMoveEnd={publierEmprise}
      cursor={curseur}
      attributionControl={{ compact: true }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <ScaleControl position="bottom-left" unit="metric" />

      {Object.entries(RASTERS).map(([cle, def]) =>
        s.raster[cle] ? (
          <Source
            key={`${cle}-${s.gibsDate}`}
            id={`src-${cle}`}
            type="raster"
            tiles={[def.url(s.gibsDate)]}
            tileSize={256}
            maxzoom={def.max}
            attribution={def.attr}
          >
            <Layer id={`lay-${cle}`} type="raster" paint={{ 'raster-opacity': def.opacite }} />
          </Source>
        ) : null,
      )}

      {station && (
        <Popup
          longitude={station.lon}
          latitude={station.lat}
          anchor="bottom"
          offset={14}
          closeButton
          closeOnClick={false}
          onClose={() => setStation(null)}
          maxWidth="260px"
        >
          <div className="min-w-[190px] font-sans text-[12.5px] leading-relaxed">
            <div className="text-[14px] font-semibold">{station.nom}</div>
            <div style={{ color: '#52514e' }}>
              {[station.region, station.pays].filter(Boolean).join(' · ')}
            </div>
            <div className="tabular" style={{ color: '#52514e' }}>
              {station.lat.toFixed(4)}° / {station.lon.toFixed(4)}°
            </div>
            <div className="mt-1 text-[11px]" style={{ color: '#898781' }}>
              {station.src} — position portuaire, indicative
            </div>
            <button
              onClick={analyserStation}
              className="mt-2.5 w-full cursor-pointer rounded-lg border-0 px-3 py-1.5
                         text-[12.5px] font-semibold text-white"
              style={{ background: '#2a78d6' }}
            >
              Analyser ce point
            </button>
          </div>
        </Popup>
      )}

      {/* Une carte muette est le pire des retours : elle se lit comme une
          panne. Quand le champ demandé n'a aucune valeur, on le dit ici, au
          centre du regard, plutôt que de laisser l'utilisateur douter. */}
      {s.grille && !champServi(s.grille, s.champ) && (
        <div className="pointer-events-none absolute inset-x-0 top-3 z-10 flex justify-center">
          <div className="pointer-events-auto max-w-[380px] rounded-xl px-3.5 py-2.5
                          text-[12.5px] leading-relaxed shadow-lg"
            style={{ background: 'var(--surface-1)', color: 'var(--ink-2)',
              border: '1px solid var(--border)' }}>
            <b style={{ color: 'var(--ink-1)' }}>{champByKey(s.champ).nom}</b> —
            aucune valeur servie sur cette emprise. Le fournisseur ne couvre pas
            cette variable ici ; les autres couches restent valides.
          </div>
        </div>
      )}

      <DeckOverlay layers={layers} />
    </Map>
  )
}
