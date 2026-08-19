import { create } from 'zustand'

import type { Analyse, Grille, ProfilPlage } from './api/client'

export type Fond = 'sombre' | 'clair' | 'satellite'

export interface SiteMarque {
  nom: string
  lat: number
  lon: number
  niveau: number
  twl: number
  ratio: number
}

interface Etat {
  /* point courant */
  nom: string
  lat: number
  lon: number
  setPoint: (lat: number, lon: number, nom?: string) => void
  setNom: (nom: string) => void

  /* période */
  mode: 'now' | 'past'
  jours: number
  debut: string
  fin: string
  climatologieAnnees: number
  setMode: (m: 'now' | 'past') => void
  setPeriode: (p: Partial<Pick<Etat, 'jours' | 'debut' | 'fin' | 'climatologieAnnees'>>) => void

  /* profil de plage */
  profil: ProfilPlage
  setProfil: (p: Partial<ProfilPlage>) => void

  /* résultats */
  analyse: Analyse | null
  setAnalyse: (a: Analyse | null) => void
  /* incrémenté par la carte pour demander une analyse du point courant */
  analyseDemandee: number
  demanderAnalyse: (lat: number, lon: number, nom: string) => void
  sites: SiteMarque[]
  addSite: (s: SiteMarque) => void
  clearSites: () => void

  /* couches */
  grille: Grille | null
  setGrille: (g: Grille | null) => void
  nx: number
  ny: number
  joursGrille: number
  setGrilleParams: (p: Partial<Pick<Etat, 'nx' | 'ny' | 'joursGrille'>>) => void
  champ: string
  setChamp: (c: string) => void
  tIndex: number
  setTIndex: (i: number) => void
  opacite: number
  setOpacite: (o: number) => void
  fleches: boolean
  toggleFleches: () => void

  /* carte */
  bbox: [number, number, number, number] | null
  setBbox: (b: [number, number, number, number]) => void
  fond: Fond
  setFond: (f: Fond) => void
  raster: Record<string, boolean>
  toggleRaster: (k: string) => void
  gibsDate: string
  setGibsDate: (d: string) => void
  stationsVisibles: boolean
  toggleStations: () => void

  /* interface */
  theme: 'dark' | 'light'
  toggleTheme: () => void
  panneau: boolean
  togglePanneau: () => void
}

const hier = () => new Date(Date.now() - 864e5).toISOString().slice(0, 10)

export const useStore = create<Etat>((set) => ({
  nom: 'Agadir',
  lat: 30.42,
  lon: -9.62,
  setPoint: (lat, lon, nom) =>
    set((s) => ({ lat: +lat.toFixed(4), lon: +lon.toFixed(4), nom: nom ?? s.nom })),
  setNom: (nom) => set({ nom }),

  mode: 'now',
  jours: 5,
  debut: new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10),
  fin: hier(),
  climatologieAnnees: 10,
  setMode: (mode) => set({ mode }),
  setPeriode: (p) => set(p),

  profil: {
    beta_f: 0.045,
    z_berme: 2.2,
    z_crete: 4.6,
    msl_trend: 0,
    i_erosion: 0,
    alpha: 0.2,
  },
  setProfil: (p) => set((s) => ({ profil: { ...s.profil, ...p } })),

  analyse: null,
  setAnalyse: (analyse) => set({ analyse }),
  analyseDemandee: 0,
  demanderAnalyse: (lat, lon, nom) =>
    set((s) => ({
      lat: +lat.toFixed(4), lon: +lon.toFixed(4), nom,
      analyseDemandee: s.analyseDemandee + 1,
    })),
  sites: [],
  addSite: (s) => set((st) => ({ sites: [...st.sites.filter((x) => x.nom !== s.nom), s] })),
  clearSites: () => set({ sites: [], analyse: null }),

  grille: null,
  setGrille: (grille) => set({ grille, tIndex: 0 }),
  nx: 9,
  ny: 7,
  joursGrille: 3,
  setGrilleParams: (p) => set(p),
  champ: 'alerte',
  setChamp: (champ) => set({ champ }),
  tIndex: 0,
  setTIndex: (tIndex) => set({ tIndex }),
  opacite: 0.72,
  setOpacite: (opacite) => set({ opacite }),
  fleches: true,
  toggleFleches: () => set((s) => ({ fleches: !s.fleches })),

  bbox: null,
  setBbox: (bbox) => set({ bbox }),
  fond: 'sombre',
  setFond: (fond) => set({ fond }),
  raster: {
    gebco: false, emodnet: false, bluemarble: false, seamark: false,
    truecolor: false, truecolorTerra: false, chloro: false, sst: false,
    sstAnom: false,
  },
  toggleRaster: (k) => set((s) => ({ raster: { ...s.raster, [k]: !s.raster[k] } })),
  gibsDate: hier(),
  setGibsDate: (gibsDate) => set({ gibsDate }),
  stationsVisibles: false,
  toggleStations: () => set((s) => ({ stationsVisibles: !s.stationsVisibles })),

  theme: 'dark',
  toggleTheme: () =>
    set((s) => {
      const theme = s.theme === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('dark', theme === 'dark')
      return { theme }
    }),
  panneau: true,
  togglePanneau: () => set((s) => ({ panneau: !s.panneau })),
}))
