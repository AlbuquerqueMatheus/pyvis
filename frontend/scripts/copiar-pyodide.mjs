// Copia o Pyodide (o Python do navegador) de node_modules para public/,
// para o site servir o próprio Python sem depender de um CDN externo.
import { copyFileSync, mkdirSync } from "node:fs";

const ARQUIVOS = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];
const destino = new URL("../public/pyodide/", import.meta.url);
mkdirSync(destino, { recursive: true });
for (const nome of ARQUIVOS) {
  copyFileSync(new URL(`../node_modules/pyodide/${nome}`, import.meta.url), new URL(nome, destino));
}
