import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Le frontend appelle /api/... ; Vite relaie vers l'API FastAPI.
      // 127.0.0.1 et non « localhost » : sous Windows, Node résout localhost
      // en ::1 (IPv6) avant 127.0.0.1, alors qu'uvicorn n'écoute qu'en IPv4 —
      // d'où des ECONNREFUSED alors que l'API tourne bel et bien.
      '/api': { target: process.env.API_URL ?? 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false, chunkSizeWarningLimit: 1600 },
})
