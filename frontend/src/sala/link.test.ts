import { describe, expect, it } from "vitest";
import { compressToEncodedURIComponent } from "lz-string";
import { EXEMPLOS } from "../exemplos";
import type { AtividadeLink } from "../motor/tipos";
import {
  LIMITE_DO_CHAT,
  MAX_PROGRAMAS,
  PADRAO_SALA,
  abrirPrograma,
  arquivoDaAtividade,
  codificarAtividade,
  idPadrao,
  lerArquivoDaAtividade,
  lerAtividade,
  linkDaAtividade,
  normalizarSala,
  novaSala,
  novaSemente,
} from "./link";

const base: AtividadeLink = { v: 1, id: "aula3", programas: [{ ex: "ex3" }, { ex: "ex5" }], modo: "prever", formato: "alternativas", sala: "K7PX", semente: 4821 };

function lida(fragmento: string): AtividadeLink {
  const resultado = lerAtividade(fragmento);
  if (resultado.tipo !== "atividade") throw new Error(`esperava uma atividade: ${JSON.stringify(resultado)}`);
  return resultado.atividade;
}

function motivo(fragmento: string): string {
  const resultado = lerAtividade(fragmento);
  if (resultado.tipo !== "invalida") throw new Error(`esperava um link inválido: ${JSON.stringify(resultado)}`);
  return resultado.motivo;
}

describe("link da atividade", () => {
  it("só com exemplos, vai pelo id e termina na semente", () => {
    const fragmento = codificarAtividade(base);
    expect(fragmento).toBe("a=ex3,ex5&m=prever&f=alt&sala=K7PX&id=aula3&s=4821");
    expect(lida(fragmento)).toEqual(base);
    expect(lida(`#${fragmento}`)).toEqual(base);
  });

  it("o link da spec (#a=ex3&m=prever&f=alt) abre com os padrões", () => {
    expect(lida("#a=ex3&m=prever&f=alt")).toEqual({ v: 1, id: "ex3", programas: [{ ex: "ex3" }], modo: "prever", formato: "alternativas", sala: "", semente: 0 });
    expect(lida("a=ex1").modo).toBe("assistir");
  });

  it("código do professor vai comprimido e volta igual, com acentos e entradas", () => {
    const atividade: AtividadeLink = {
      ...base,
      modo: "estudo",
      formato: "livre",
      programas: [{ ex: "ex7", entradas: ["Zé", "9"] }, { codigo: 'nome = input("Robô? ")\nprint(nome * 2)\n', entradas: ["Bip"] }, { ex: "ex1" }],
    };
    const fragmento = codificarAtividade(atividade);
    expect(fragmento.startsWith("c=")).toBe(true);
    expect(fragmento).toMatch(/&s=4821$/);
    expect(fragmento).not.toContain("input");
    expect(lida(fragmento)).toEqual(atividade);
  });

  it("o '+' do texto comprimido não vira espaço", () => {
    // Procura um programa cuja compressão tenha '+' (o URLSearchParams o trocaria por espaço).
    let atividade: AtividadeLink | null = null;
    for (let n = 0; n < 200 && !atividade; n++) {
      const tentativa: AtividadeLink = { ...base, programas: [{ codigo: `x = ${n}\nprint(x * ${n + 1})\n` }] };
      if (codificarAtividade(tentativa).includes("+")) atividade = tentativa;
    }
    expect(atividade).not.toBeNull();
    expect(lida(codificarAtividade(atividade!))).toEqual(atividade);
  });

  it("um '$' que o chat transformou em %24 ainda abre", () => {
    const atividade: AtividadeLink = { ...base, programas: [{ codigo: "print(1)\n" }] };
    const fragmento = codificarAtividade(atividade).replace(/\$/g, "%24");
    expect(lida(fragmento)).toEqual(atividade);
  });

  it("o que não é atividade fica de fora", () => {
    for (const fragmento of ["", "#", "/pais", "/criar", "m=prever", "x=1&y=2"]) expect(lerAtividade(fragmento)).toEqual({ tipo: "nenhuma" });
  });

  it("recusa links quebrados ou montados à mão com valores errados", () => {
    expect(motivo("a=ex99")).toMatch(/não existe/);
    expect(motivo("a=")).toMatch(/não tem programas/);
    expect(motivo("a=ex1&m=jogo")).toMatch(/modo/);
    expect(motivo("a=ex1&f=prova")).toMatch(/formato/);
    expect(motivo("a=ex1&sala=@@")).toMatch(/sala/);
    expect(motivo("a=ex1&sala=A")).toMatch(/sala/);
    expect(motivo("a=ex1&id=aula%203")).toMatch(/nome da atividade/);
    expect(motivo(`a=ex1&id=${"x".repeat(33)}`)).toMatch(/nome da atividade/);
    expect(motivo("a=ex1&s=-1")).toMatch(/semente/);
    expect(motivo("a=ex1&s=2147483648")).toMatch(/semente/);
    expect(motivo("a=ex1&v=2")).toMatch(/versão/);
    expect(motivo("c=isto-nao-e-lz")).toMatch(/cortados/);
    expect(motivo(`c=${compressToEncodedURIComponent('{"ex":"ex1"}')}`)).toMatch(/não tem programas/);
    expect(motivo(`c=${compressToEncodedURIComponent('[{"codigo":"   "}]')}`)).toMatch(/vazio/);
    expect(motivo(`c=${compressToEncodedURIComponent(JSON.stringify([{ codigo: "x".repeat(20_001) }]))}`)).toMatch(/grande demais/);
    expect(motivo(`c=${compressToEncodedURIComponent('[{"codigo":"x=1","entradas":["a\\nb"]}]')}`)).toMatch(/uma linha/);
    expect(motivo(`c=${compressToEncodedURIComponent('[{"codigo":"x=1","entradas":"4"}]')}`)).toMatch(/lista/);
    expect(motivo(`c=${compressToEncodedURIComponent("[null]")}`)).toMatch(/formato certo/);
    expect(motivo(`a=${Array(MAX_PROGRAMAS + 1).fill("ex1").join(",")}`)).toMatch(/mais de/);
    expect(motivo(`a=ex1&x=${"y".repeat(200_001)}`)).toMatch(/grande demais/);
  });

  it("guarda só os campos conhecidos de cada programa", () => {
    const sujo = [{ ex: "ex2", codigo: "import js", extra: 1 }, { codigo: "x = 1", __proto__: { mal: true }, outro: "?" }];
    const atividade = lida(`c=${compressToEncodedURIComponent(JSON.stringify(sujo))}&sala=8a`);
    expect(atividade.programas).toEqual([{ ex: "ex2" }, { codigo: "x = 1" }]);
    expect(atividade.sala).toBe("8A");
  });

  it("o link completo leva o endereço da página", () => {
    expect(linkDaAtividade(base, "https://pyvis.example/app/")).toBe("https://pyvis.example/app/#a=ex3,ex5&m=prever&f=alt&sala=K7PX&id=aula3&s=4821");
    expect(LIMITE_DO_CHAT).toBeGreaterThan(linkDaAtividade(base, "https://pyvis.example/").length);
  });

  it("abre os programas para o palco", () => {
    expect(abrirPrograma({ ex: "ex3" })).toEqual({ titulo: "Repetição com for", codigo: EXEMPLOS[2].codigo, entradas: "", exemplo: "ex3" });
    expect(abrirPrograma({ ex: "ex7" }).entradas).toBe("Bip\n3");
    expect(abrirPrograma({ ex: "ex7", entradas: ["Lua", "2"] }).entradas).toBe("Lua\n2");
    expect(abrirPrograma({ codigo: "print(1)", entradas: ["a"] })).toEqual({ titulo: "Programa do professor", codigo: "print(1)", entradas: "a", exemplo: null });
  });

  it("a atividade como arquivo passa pela mesma conferência", () => {
    const arquivo = arquivoDaAtividade(base);
    expect(arquivo.nome).toBe("atividade-aula3.json");
    expect(lerArquivoDaAtividade(arquivo.conteudo)).toEqual({ tipo: "atividade", atividade: base });
    expect(lerArquivoDaAtividade("{}").tipo).toBe("invalida");
    expect(lerArquivoDaAtividade("não é json").tipo).toBe("invalida");
    expect(lerArquivoDaAtividade(JSON.stringify({ formato: "pyvis-atividade", v: 1, link: "m=prever" })).tipo).toBe("invalida");
    expect(lerArquivoDaAtividade(JSON.stringify({ formato: "pyvis-atividade", v: 1, link: "a=ex99" })).tipo).toBe("invalida");
  });

  it("valores novos para o professor saem no formato certo", () => {
    for (let n = 0; n < 50; n++) {
      const sala = novaSala();
      expect(sala).toMatch(PADRAO_SALA);
      expect(sala).not.toMatch(/[0O1IL5S2Z8B]/);
      expect(novaSemente()).toBeLessThan(1_000_000);
    }
    expect(idPadrao(new Date(2026, 9, 6))).toBe("aula-0610");
    expect(normalizarSala(" k7 px ")).toBe("K7PX");
  });
});
