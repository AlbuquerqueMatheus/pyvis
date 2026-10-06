// @vitest-environment node
import { describe, expect, it } from "vitest";
import casosJson from "../testes/casos-revelacao.json";
import rastrosJson from "../testes/rastros.json";
import {
  aplicarAtividade,
  desfecho,
  DESFECHO,
  DESFECHO_DO_CABECALHO,
  leituraVisivel,
  montar,
  narracaoVisivel,
  relacionados,
  visivel,
  type PassoRevelavel,
} from "./revelacao";
import type { Atividade, Comando, Leitura, Resultado } from "./tipos";

// Casos calculados pelo Python (frontend/scripts/casos_revelacao.py).
type CasoDePasso = { passo: PassoRevelavel; respondidos: string[][]; atuais: number[]; esperado: string };
type Frase = ["curta" | "longa", string[], number, string | null];
type Programa = {
  nome: string;
  comandos: { id: number; leitura: Leitura }[];
  depende_de_por_passo: Atividade["depende_de_por_passo"];
  traduzida_depende_de: Atividade["traduzida_depende_de"];
  passos: (CasoDePasso & { frases: Frase[] })[];
  leituras: [number, string[], string][];
};
const casos = casosJson as unknown as { campos: string[]; sinteticos: CasoDePasso[]; programas: Programa[] };
const rastros = rastrosJson as unknown as Record<string, { resultado: Resultado; atividade?: Atividade }>;

/** Os mesmos '0'/'1' que o Python escreveu: campo x respondidos x passo atual. */
function bits(caso: CasoDePasso) {
  let texto = "";
  for (const campo of casos.campos) {
    for (const conjunto of caso.respondidos) {
      for (const atual of caso.atuais) texto += visivel(caso.passo, campo, new Set(conjunto), atual) ? "1" : "0";
    }
  }
  return texto;
}

describe("paridade com pyvis_motor/revelacao.py", () => {
  it("tem casos dos dois tipos", () => {
    expect(casos.sinteticos.length).toBeGreaterThan(50);
    expect(casos.programas.length).toBeGreaterThan(10);
    // Há pontos pendentes de verdade nos programas: a paridade testa o caso que importa.
    expect(casos.programas.some((p) => p.passos.some((caso) => caso.passo.depende_de))).toBe(true);
  });

  it("visivel dá as mesmas respostas nos passos sorteados", () => {
    for (const caso of casos.sinteticos) expect(bits(caso), JSON.stringify(caso.passo)).toBe(caso.esperado);
  });

  it("visivel dá as mesmas respostas nos programas reais", () => {
    for (const programa of casos.programas) {
      for (const caso of programa.passos) expect(bits(caso), `${programa.nome}, passo ${caso.passo.i}`).toBe(caso.esperado);
    }
  });

  it("montar escreve as mesmas frases", () => {
    let conferidas = 0;
    for (const programa of casos.programas) {
      for (const caso of programa.passos) {
        for (const [versao, conjunto, atual, esperada] of caso.frases) {
          const partes = versao === "curta" ? caso.passo.narracao!.partes_curta : caso.passo.narracao!.partes_longa;
          const inteira = partes.map((parte) => parte.texto).join("");
          expect(montar(partes, caso.passo, new Set(conjunto), atual), `${programa.nome}, passo ${caso.passo.i}`).toBe(esperada ?? inteira);
          expect(narracaoVisivel(caso.passo, new Set(conjunto), atual, versao)).toBe(esperada ?? inteira);
          conferidas += 1;
        }
      }
    }
    expect(conferidas).toBeGreaterThan(500);
  });

  it("leituraVisivel escolhe a mesma leitura", () => {
    let conferidas = 0;
    for (const programa of casos.programas) {
      for (const [id, conjunto, esperada] of programa.leituras) {
        const comando = programa.comandos.find((c) => c.id === id)!;
        expect(leituraVisivel(comando, new Set(conjunto))).toBe(esperada);
        conferidas += 1;
      }
    }
    expect(conferidas).toBeGreaterThan(0);
  });

  it("aplicarAtividade grava as mesmas dependências que aplicar_dependencias", () => {
    for (const programa of casos.programas) {
      const leituras = programa.comandos.map((c) => ({ ...c.leitura, traduzida_depende_de: [] }));
      // Um Resultado da página antes da atividade: sem depende_de e sem dependências nas leituras.
      const resultado = {
        estrutura: { comandos: programa.comandos.map((c, k) => ({ id: c.id, leitura: leituras[k] }) as unknown as Comando) },
        passos: programa.passos.map(({ passo }) => {
          const { depende_de: _ignorado, ...resto } = passo;
          return { ...resto, depende_de: { velho: ["p99"] } };
        }),
      } as unknown as Resultado;
      const aplicado = aplicarAtividade(resultado, programa);
      programa.passos.forEach(({ passo }, k) => {
        expect(aplicado.passos[k].depende_de, `${programa.nome}, passo ${passo.i}`).toEqual(passo.depende_de);
      });
      programa.comandos.forEach((comando, k) => {
        expect(aplicado.estrutura.comandos[k].leitura!.traduzida_depende_de).toEqual(comando.leitura.traduzida_depende_de);
      });
      // O original fica como estava: a página nunca muda o que já mostrou.
      expect(resultado.passos[0].depende_de).toEqual({ velho: ["p99"] });
    }
  });
});

describe("regras de visivel", () => {
  const sintetico = (extra: Partial<PassoRevelavel> = {}): PassoRevelavel => ({
    i: 3,
    comando: 1,
    desfecho_visivel_desde: 3,
    decisao: null,
    volta: null,
    ...extra,
  });

  it("relacionados olha o caminho com ponto", () => {
    expect(relacionados("decisao", "decisao.valor")).toBe(true);
    expect(relacionados("efeito.saida_nova", "efeito")).toBe(true);
    expect(relacionados("decisao.valor", "decisao.ramo")).toBe(false);
    expect(relacionados("volta", "voltas")).toBe(false);
  });

  it("no cabeçalho do laço a volta faz parte do desfecho", () => {
    const volta = { laco: 1, total_visivel_desde: 9 };
    expect(desfecho(sintetico({ volta }))).toBe(DESFECHO_DO_CABECALHO);
    expect(desfecho(sintetico({ volta, comando: 4 }))).toBe(DESFECHO);
  });

  it("nada de um passo que ainda não chegou", () => {
    expect(visivel(sintetico(), "decisao.texto", new Set(), 2)).toBe(false);
    expect(visivel(sintetico(), "decisao.texto", new Set(), 3)).toBe(true);
  });

  it("um palpite pendente esconde o desfecho inteiro, e responder mostra", () => {
    const passo = sintetico({ depende_de: { "decisao.valor": ["p1"] } });
    expect(visivel(passo, "efeito", new Set(), 10)).toBe(false);
    expect(visivel(passo, "decisao.ramo", new Set(), 10)).toBe(false);
    expect(visivel(passo, "decisao.texto", new Set(), 10)).toBe(true);
    expect(visivel(passo, "efeito", new Set(["p1"]), 10)).toBe(true);
  });

  it("desfecho_visivel_desde ausente vale o próprio passo; null é nunca", () => {
    expect(visivel({ i: 2 }, "efeito", new Set(), 2)).toBe(true);
    expect(visivel({ i: 2, desfecho_visivel_desde: null }, "efeito", new Set(), 99)).toBe(false);
  });

  it("o total de voltas só aparece na saída do laço", () => {
    const passo = sintetico({ comando: 2, volta: { laco: 0, total_visivel_desde: 10 } });
    expect(visivel(passo, "volta.n", new Set(), 3)).toBe(true);
    expect(visivel(passo, "volta.total", new Set(), 9)).toBe(false);
    expect(visivel(passo, "volta.total", new Set(), 10)).toBe(true);
  });
});

describe("atividade aplicada a um rastro de verdade", () => {
  it("esconde o total de voltas e a leitura traduzida até o palpite", () => {
    const { resultado, atividade } = rastros.for;
    const aplicado = aplicarAtividade(resultado, atividade!);
    const cabecalho = aplicado.passos[1];
    const ultimo = aplicado.passos.length - 1;
    const pendentes = cabecalho.depende_de!["volta.total"];
    expect(pendentes.length).toBeGreaterThan(0);
    expect(visivel(cabecalho, "volta.total", new Set(), ultimo)).toBe(false);
    expect(narracaoVisivel(cabecalho, new Set(), ultimo)).toContain("range(1, 5)");
    const todos = new Set(atividade!.pontos.map((p) => p.id));
    expect(visivel(cabecalho, "volta.total", todos, ultimo)).toBe(true);
    expect(narracaoVisivel(cabecalho, todos, ultimo)).toContain("de 1 até 4");
    // Sem atividade (modo assistir) nada depende de palpite.
    const assistir = aplicarAtividade(aplicado, { depende_de_por_passo: {}, traduzida_depende_de: {} });
    expect(assistir.passos.every((p) => p.depende_de === undefined)).toBe(true);
  });
});
