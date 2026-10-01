import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://127.0.0.1:8001" } },
  build: {
    sourcemap: false,
    rolldownOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes("node_modules/recharts") ||
            id.includes("node_modules/d3-")
          )
            return "charts";
        },
      },
    },
  },
});
