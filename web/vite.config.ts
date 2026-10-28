import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI app serves /api; in development Vite proxies to it.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
