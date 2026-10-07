// @vitest-environment node
import { describe, expect, it } from "vitest";

// Vocabulário de jogo de azar não aparece em nada do PyVis (Lei 14.790/2023):
// a ferramenta fala em palpite e previsão. A palavra é montada em pedaços para
// este arquivo não acusar a si mesmo.
const PROIBIDA = new RegExp("a" + "post", "i");

const ARQUIVOS = {
  ...import.meta.glob("/src/**/*.{ts,tsx,css,json,html}", { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob("/index.html", { query: "?raw", import: "default", eager: true }),
} as Record<string, string>;

describe("textos para o aluno", () => {
  it("a busca enxerga os arquivos da página", () => {
    expect(Object.keys(ARQUIVOS)).toContain("/src/App.tsx");
    expect(Object.keys(ARQUIVOS)).toContain("/src/exemplos.ts");
    expect(Object.keys(ARQUIVOS).length).toBeGreaterThan(10);
  });

  it(`nenhum arquivo de frontend/src tem a palavra proibida`, () => {
    const achados = Object.entries(ARQUIVOS).flatMap(([caminho, texto]) =>
      texto
        .split("\n")
        .map((linha, n) => [linha, n] as const)
        .filter(([linha]) => PROIBIDA.test(linha))
        .map(([linha, n]) => `${caminho}:${n + 1}: ${linha.trim()}`),
    );
    expect(achados).toEqual([]);
  });

  it("o exemplo com input não pede o nome do aluno", () => {
    const exemplos = ARQUIVOS["/src/exemplos.ts"];
    expect(exemplos).not.toMatch(/seu nome/i);
    expect(exemplos).toMatch(/nome do seu robô/);
  });

  it("o campo de entradas avisa para não usar o nome de verdade", () => {
    expect(ARQUIVOS["/src/componentes/Palco.tsx"]).toContain("Não use seu nome de verdade.");
  });

  it("nenhum texto da tela fala em acertos, sequência ou porcentagem", () => {
    // Sem placar durante a atividade (spec 2.2): nada de 'acertos', 'sequência', '%' de acerto.
    const telas = Object.entries(ARQUIVOS).filter(([caminho]) => caminho.endsWith(".tsx") && !caminho.includes(".test."));
    const placar = /acertos|sequência|seguidos|pontuação|\d+ ?%/i;
    const achados = telas.flatMap(([caminho, texto]) =>
      texto
        .split("\n")
        .filter((linha) => !linha.trim().startsWith("//") && !linha.trim().startsWith("*") && !linha.trim().startsWith("{/*"))
        .filter((linha) => placar.test(linha))
        .map((linha) => `${caminho}: ${linha.trim()}`),
    );
    expect(achados).toEqual([]);
  });
});
