import { Github, Moon, PanelLeftClose, PanelLeftOpen, Sun } from 'lucide-react'

import MapView from './components/MapView'
import Panel from './components/Panel'
import Results from './components/Results'
import SearchBar from './components/SearchBar'
import TimeSlider from './components/TimeSlider'
import { useStore } from './store'

export default function App() {
  const { analyse, theme, toggleTheme, panneau, togglePanneau } = useStore()

  return (
    <div className="flex h-full flex-col">
      <header className="flex shrink-0 flex-wrap items-center gap-3 px-4 py-2.5"
        style={{ background: 'var(--surface-1)', borderBottom: '1px solid var(--border)' }}>
        <button className="btn !px-2 !py-1.5" onClick={togglePanneau}
          aria-label={panneau ? 'Masquer le panneau' : 'Afficher le panneau'}>
          {panneau ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>

        <div className="flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <rect width="32" height="32" rx="7" fill="#0d366b" />
            <path d="M4 20c3.2 0 3.2-4 6.4-4s3.2 4 6.4 4 3.2-4 6.4-4 3.2 4 6.4 4"
              stroke="#86b6ef" strokeWidth="2.4" fill="none" strokeLinecap="round" />
            <path d="M4 25.5c3.2 0 3.2-4 6.4-4s3.2 4 6.4 4 3.2-4 6.4-4 3.2 4 6.4 4"
              stroke="#2a78d6" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity=".55" />
            <circle cx="16" cy="9" r="3.2" fill="#ec835a" />
          </svg>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">CoastSentinel</div>
            <div className="text-[11px]" style={{ color: 'var(--ink-2)' }}>
              Système d'Alerte Côtière Multi-échelle
            </div>
          </div>
        </div>

        <div className="mx-auto min-w-[240px] flex-1">
          <SearchBar />
        </div>

        <a className="btn inline-flex items-center gap-1.5 !py-1.5 !text-[12px]"
          href="/api/docs" target="_blank" rel="noreferrer">
          <Github size={13} /> API
        </a>
        <button className="btn !px-2 !py-1.5" onClick={toggleTheme}
          aria-label="Changer de thème">
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        {panneau && (
          <aside className="w-[330px] shrink-0 overflow-hidden"
            style={{ background: 'var(--surface-1)', borderRight: '1px solid var(--border)' }}>
            <Panel />
          </aside>
        )}

        <main className="relative min-w-0 flex-1">
          <MapView />
          <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex justify-center px-4">
            <TimeSlider />
          </div>
        </main>

        {analyse && (
          <aside className="w-[430px] shrink-0 overflow-y-auto p-3 2xl:w-[520px]"
            style={{ background: 'var(--plane)', borderLeft: '1px solid var(--border)' }}>
            <Results a={analyse} />
          </aside>
        )}
      </div>

      <footer className="shrink-0 px-4 py-1.5 text-[11px]"
        style={{ background: 'var(--surface-1)', borderTop: '1px solid var(--border)', color: 'var(--ink-3)' }}>
        Données Open-Meteo Marine (ECMWF / GFS-Wave / MFWAM) · fonds CARTO, Esri,
        GEBCO, EMODnet, NASA GIBS · Stockdon et al. (2006), Sallenger (2000),
        Dolan &amp; Davis (1992). <b>Aide à la décision et recherche — ne se
        substitue pas aux alertes officielles des services nationaux.</b>
      </footer>
    </div>
  )
}
