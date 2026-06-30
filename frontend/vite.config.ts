import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // В Docker на macOS/Windows нативный file-watcher не пробрасывается через
    // смонтированный том, поэтому HMR не видит правок. Polling это исправляет.
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY ?? "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
