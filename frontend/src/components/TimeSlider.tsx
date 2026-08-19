import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useStore } from '../store'

/** Curseur temporel des couches cartographiques, avec animation. */
export default function TimeSlider() {
  const { grille, tIndex, setTIndex } = useStore()
  const [joue, setJoue] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (!joue || !grille) return
    timer.current = window.setInterval(() => {
      const { tIndex: i, grille: g, setTIndex: set } = useStore.getState()
      if (g) set((i + 1) % g.times.length)
    }, 420)
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [joue, grille])

  if (!grille) return null
  const d = new Date(`${grille.times[tIndex]}Z`)

  return (
    <div className="card pointer-events-auto flex items-center gap-2.5 px-3 py-2"
      style={{ boxShadow: '0 6px 26px rgba(0,0,0,.3)' }}>
      <button className="btn !px-2 !py-1" onClick={() => { setJoue(false); setTIndex(Math.max(0, tIndex - 1)) }}
        aria-label="Pas précédent">
        <ChevronLeft size={15} />
      </button>
      <button className="btn !px-2.5 !py-1" onClick={() => setJoue((p) => !p)}
        aria-label={joue ? 'Pause' : 'Animer'}>
        {joue ? <Pause size={15} /> : <Play size={15} />}
      </button>
      <button className="btn !px-2 !py-1"
        onClick={() => { setJoue(false); setTIndex(Math.min(grille.times.length - 1, tIndex + 1)) }}
        aria-label="Pas suivant">
        <ChevronRight size={15} />
      </button>
      <input type="range" min={0} max={grille.times.length - 1} value={tIndex}
        className="w-[240px] min-w-[120px] flex-1"
        onChange={(e) => { setJoue(false); setTIndex(+e.target.value) }}
        aria-label="Pas de temps" />
      <span className="tabular whitespace-nowrap text-[12.5px] font-semibold">
        {d.toUTCString().slice(5, 22)} UTC
      </span>
    </div>
  )
}
