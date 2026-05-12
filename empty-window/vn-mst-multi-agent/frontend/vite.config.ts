import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/vietqr-api": {
        target: "https://api.vietqr.io",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/vietqr-api/, ""),
      },
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
