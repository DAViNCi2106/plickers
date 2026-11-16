import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    basicSsl(),   // generates a local self-signed cert — enables HTTPS for camera access on mobile/LAN
  ],
  server: {
    host: '0.0.0.0',   // listen on all network interfaces (LAN access)
    port: 5173,
    https: true,        // required for camera on mobile/LAN (secure context)
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})

