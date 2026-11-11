import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const gameName = env.VITE_GAME_NAME || env.GAME_NAME || 'Apple Worm Adventure'
  const apiBase = env.VITE_API_BASE_URL || '/api'
  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_GAME_NAME': JSON.stringify(gameName),
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiBase),
    },
  }
})
