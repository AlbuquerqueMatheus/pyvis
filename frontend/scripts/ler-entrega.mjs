// Lê os arquivos que os alunos entregam ("Entregar ao professor") e escreve
// os eventos de todos, um por linha (JSONL), para a análise em Python.
// Uso: node scripts/ler-entrega.mjs pyvis-aula3-*.json > eventos.jsonl
// O apelido vai para o stderr, só para conferir quem já entregou.
import { readFileSync } from "node:fs";
import lzString from "lz-string";

const { decompressFromBase64 } = lzString; // o lz-string é CommonJS

function lerEntrega(texto) {
  let codigo = texto.trim();
  try {
    const envelope = JSON.parse(codigo);
    if (envelope?.formato !== "pyvis-entrega" || envelope.v !== 1) return null;
    codigo = envelope.lz;
  } catch {
    // Não é o arquivo: pode ser o código colado da reserva.
  }
  try {
    const entrega = JSON.parse(decompressFromBase64(String(codigo)) || "null");
    return entrega?.v === 1 && Array.isArray(entrega.eventos) ? entrega : null;
  } catch {
    return null;
  }
}

const arquivos = process.argv.slice(2);
if (arquivos.length === 0) {
  console.error("Uso: node scripts/ler-entrega.mjs ARQUIVO.json [...]");
  process.exit(2);
}
let falhas = 0;
for (const arquivo of arquivos) {
  const entrega = lerEntrega(readFileSync(arquivo, "utf8"));
  if (!entrega) {
    console.error(`${arquivo}: não é uma entrega do PyVis.`);
    falhas++;
    continue;
  }
  console.error(`${arquivo}: ${entrega.apelido}, ${entrega.eventos.length} eventos.`);
  for (const evento of entrega.eventos) process.stdout.write(JSON.stringify(evento) + "\n");
}
process.exit(falhas > 0 ? 1 : 0);
