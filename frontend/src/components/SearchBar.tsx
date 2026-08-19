import { useQuery } from '@tanstack/react-query'
import { Loader2, MapPin, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { api, parseCoords, type Lieu } from '../api/client'
import { useStore } from '../store'

export default function SearchBar() {
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const [ouvert, setOuvert] = useState(false)
  const [sel, setSel] = useState(-1)
  const boite = useRef<HTMLDivElement>(null)
  const setPoint = useStore((s) => s.setPoint)

  const coords = parseCoords(q)

  useEffect(() => {
    const id = setTimeout(() => setDebounced(q.trim()), 300)
    return () => clearTimeout(id)
  }, [q])

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!boite.current?.contains(e.target as Node)) setOuvert(false)
    }
    document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [])

  const { data, isFetching, error } = useQuery({
    queryKey: ['lieux', debounced],
    queryFn: () => api.lieux(debounced),
    enabled: debounced.length >= 2 && !coords && ouvert,
    staleTime: 5 * 60_000,
    retry: false,
  })

  const items: Lieu[] = coords
    ? [{ nom: `Aller à ${coords.lat.toFixed(4)}° / ${coords.lon.toFixed(4)}°`, ...coords, pays: 'saisie directe' }]
    : (data ?? [])

  const choisir = (l: Lieu) => {
    setPoint(l.lat, l.lon, l.pays === 'saisie directe' ? undefined : l.nom)
    setQ(l.pays === 'saisie directe' ? q : l.nom)
    setOuvert(false)
  }

  return (
    <div ref={boite} className="relative w-full max-w-[520px]">
      <Search
        size={16}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
        style={{ color: 'var(--ink-3)' }}
      />
      <input
        className="field pl-9"
        style={{ paddingTop: 9, paddingBottom: 9, fontSize: 14 }}
        placeholder="Rechercher une ville, un port, ou saisir « 30.42, -9.62 »"
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setOuvert(true)
          setSel(-1)
        }}
        onFocus={() => setOuvert(true)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') return setOuvert(false)
          if (!items.length) return
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault()
            setSel((i) => (i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length)
          } else if (e.key === 'Enter') {
            e.preventDefault()
            choisir(items[sel >= 0 ? sel : 0])
          }
        }}
        aria-label="Recherche de lieu"
      />
      {isFetching && (
        <Loader2
          size={15}
          className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin"
          style={{ color: 'var(--ink-3)' }}
        />
      )}

      {ouvert && (q.trim().length >= 2) && (
        <div
          className="card absolute left-0 right-0 top-full z-50 mt-1.5 max-h-[320px] overflow-auto"
          style={{ boxShadow: '0 10px 30px rgba(0,0,0,.28)' }}
        >
          {error && !coords ? (
            <div className="px-3 py-2.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
              Recherche indisponible. Saisissez les coordonnées directement,
              par exemple <b>30.42, -9.62</b>.
            </div>
          ) : items.length === 0 && !isFetching ? (
            <div className="px-3 py-2.5 text-[12.5px]" style={{ color: 'var(--ink-2)' }}>
              Aucun lieu trouvé.
            </div>
          ) : (
            items.map((l, i) => (
              <button
                key={`${l.nom}-${l.lat}-${l.lon}`}
                onClick={() => choisir(l)}
                onMouseEnter={() => setSel(i)}
                className="flex w-full items-start gap-2.5 px-3 py-2 text-left"
                style={{
                  background: i === sel ? 'var(--surface-2)' : 'transparent',
                  borderBottom: i < items.length - 1 ? '1px solid var(--grid)' : 'none',
                }}
              >
                <MapPin size={14} className="mt-0.5 shrink-0" style={{ color: 'var(--serie-1)' }} />
                <span className="min-w-0">
                  <span className="block truncate text-[13.5px] font-semibold">{l.nom}</span>
                  <span className="block truncate text-[11.5px] tabular" style={{ color: 'var(--ink-2)' }}>
                    {[l.region, l.pays].filter(Boolean).join(' · ')}
                    {l.population ? ` · ${new Intl.NumberFormat('fr').format(l.population)} hab.` : ''}
                    {` · ${l.lat.toFixed(3)}° / ${l.lon.toFixed(3)}°`}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
