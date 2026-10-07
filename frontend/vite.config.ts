import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Os arquivos do motor Python ficam em ../pyvis_motor e são importados como texto.
  server: { fs: { allow: [".."] } },
  worker: { format: "es" },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testes/setup.ts"],
  },
});
