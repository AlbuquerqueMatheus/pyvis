import { afterEach, describe, expect, it, vi } from "vitest";
import { decompressFromBase64 } from "lz-string";
import type { Entrega, Evento } from "../motor/tipos";
import { arquivoDaEntrega, baixarArquivo, copiarTexto, lerEntrega, semAcento } from "./arquivos";

const evento: Evento = {
  v: 1,
  ts: 1791252682915,
  sala: "K7PX",
  sujeito: "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f",
  atividade: "aula3",
  programa: 0,
  condicao: "prever",
  code_hash: "a1ef8f734b61a380",
  tipo: "Prediction",
  ponto: "p2",
  formato: "alternativas",
  resposta: { alternativa: "p2a1" },
  certa: false,
  concepcao: "C01",
  testadas: ["C01"],
  ms: 1200,
};
const entrega: Entrega = { v: 1, apelido: "Libélula Anil 77", eventos: [evento] };

afterEach(() => vi.restoreAllMocks());

describe("arquivo da entrega", () => {
  it("é um .json com a entrega comprimida, e o código da reserva é o mesmo texto", () => {
    const arquivo = arquivoDaEntrega(entrega, "aula3");
    expect(arquivo.nome).toBe("pyvis-aula3-libelula-anil-77.json");
    const envelope = JSON.parse(arquivo.conteudo);
    expect(envelope).toEqual({ formato: "pyvis-entrega", v: 1, lz: arquivo.codigo });
    expect(JSON.parse(decompressFromBase64(arquivo.codigo))).toEqual(entrega);
    // Comprimido: o arquivo não mostra os eventos a olho nu.
    expect(arquivo.conteudo).not.toContain("Prediction");
  });

  it("lê o arquivo ou o código colado; recusa o resto", () => {
    const arquivo = arquivoDaEntrega(entrega, "aula3");
    expect(lerEntrega(arquivo.conteudo)).toEqual(entrega);
    expect(lerEntrega(`  ${arquivo.codigo}\n`)).toEqual(entrega);
    expect(lerEntrega("{}")).toBeNull();
    expect(lerEntrega("qualquer coisa")).toBeNull();
    expect(lerEntrega(JSON.stringify({ formato: "pyvis-entrega", v: 1, lz: "xx" }))).toBeNull();
  });

  it("nomes de arquivo sem acento nem espaço", () => {
    expect(semAcento("Bem-te-vi Cinza 48")).toBe("bem-te-vi-cinza-48");
    expect(semAcento("Jacaré Dourado 94")).toBe("jacare-dourado-94");
  });

  it("baixa pelo link temporário e avisa quando o navegador não deixa", () => {
    const criar = vi.fn(() => "blob:teste");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: criar, revokeObjectURL: vi.fn() }));
    const clique = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    expect(baixarArquivo("a.json", "{}")).toBe(true);
    expect(criar).toHaveBeenCalledOnce();
    expect(clique).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download]")).toBeNull();
    criar.mockImplementation(() => {
      throw new Error("sem blob");
    });
    expect(baixarArquivo("a.json", "{}")).toBe(false);
  });

  it("copiar devolve false sem permissão", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.reject(new Error("negado")) } });
    expect(await copiarTexto("x")).toBe(false);
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.resolve() } });
    expect(await copiarTexto("x")).toBe(true);
    vi.unstubAllGlobals();
  });
});
