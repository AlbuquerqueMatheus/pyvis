// @vitest-environment node
import { describe, expect, it } from "vitest";
import rastrosJson from "../testes/rastros.json";
import {
  anteriorNoQuadro,
  balaoDaDecisao,
  cenaDoEditor,
  NADA_RESPONDIDO,
  pilulaDaVolta,
  ramosPulados,
  retornosVisiveis,
  textoDaVolta,
  type Revelacao,
} from "./cena";
import { aplicarAtividade } from "./revelacao";
import type { Atividade, Resultado } from "./tipos";

const rastros = rastrosJson as unknown as Record<string, { codigo: string; resultado: Resultado; atividade?: Atividade }>;

/** Modo assistir: nada a responder; o aluno já viu até `alcancado`. */
const assistindo = (alcancado: number): Revelacao => ({ respondidos: NADA_RESPONDIDO, alcancado });

describe("linha destacada", () => {
  it("é o cabeçalho de um bloco e o comando inteiro nos outros", () => {
    const { resultado } = rastros.if_else;
    expect(cenaDoEditor(resultado, 1, assistindo(1)).atual).toEqual([2, 2]);
    expect(cenaDoEditor(resultado, 2, assistindo(2)).atual).toEqual([3, 3]);
  });

  it("some no fim do programa e vira a linha do erro no último passo", () => {
    const { resultado } = rastros.if_else;
    const fim = resultado.passos.length - 1;
    expect(cenaDoEditor(resultado, fim, assistindo(fim)).atual).toBeNull();
    const erro = rastros.erro.resultado;
    expect(cenaDoEditor(erro, 1, assistindo(1)).erro).toBeNull();
    expect(cenaDoEditor(erro, 2, assistindo(2)).erro).toBe(3);
    expect(cenaDoEditor(rastros.sintaxe.resultado, 0, assistindo(0)).erro).toBe(1);
  });

  it("sem resultado não há nada", () => {
    expect(cenaDoEditor(null, 0, assistindo(0))).toEqual({ atual: null, erro: null, pulados: [], balao: null, naoCalculado: [] });
  });
});

describe("ramo pulado", () => {
  it("o else só fica esmaecido depois da decisão", () => {
    const { resultado } = rastros.if_else;
    // No passo da decisão, o ramo ainda não foi tomado.
    expect(ramosPulados(resultado, 1, assistindo(1))).toEqual([]);
    // Dentro do if, o else (linhas 4 e 5) foi pulado.
    expect(ramosPulados(resultado, 2, assistindo(2))).toEqual([[4, 5]]);
    // Depois do if, já não há o que esmaecer.
    expect(ramosPulados(resultado, 3, assistindo(3))).toEqual([]);
  });

  it("no elif, o corpo do if e o else ficam pulados", () => {
    const { resultado } = rastros.elif;
    expect(ramosPulados(resultado, 2, assistindo(2))).toEqual([[3, 3]]);
    expect(ramosPulados(resultado, 3, assistindo(3))).toEqual([
      [6, 7],
      [3, 3],
    ]);
  });

  it("no if dentro do for, o ramo de uma volta não aparece na volta seguinte", () => {
    // Exemplo 6: o if de 'n > maior' entra na volta 2 (9 > 4) e não entra nas voltas 1, 3 e 4.
    const { resultado } = rastros.maior;
    const ifs = resultado.passos.filter((passo) => passo.decisao && resultado.estrutura.comandos[passo.comando!].tipo === "if");
    expect(ifs.map((passo) => passo.decisao!.ramo)).toEqual(["sai", "corpo", "sai", "sai"]);
    // No cabeçalho do if, a decisão desta volta ainda não aconteceu: nada fica pulado.
    for (const passo of ifs) expect(ramosPulados(resultado, passo.i, assistindo(passo.i))).toEqual([]);
    // Dentro do if (maior = n), nada foi pulado (o if não tem else).
    const dentro = resultado.passos.find((passo) => passo.linha === 5)!;
    expect(ramosPulados(resultado, dentro.i, assistindo(dentro.i))).toEqual([]);
    // Logo depois de um if que não entrou, o corpo dele fica pulado.
    expect(ramosPulados(resultado, ifs[0].i + 1, assistindo(ifs[0].i + 1))).toEqual([[5, 5]]);
  });

  it("um palpite pendente sobre a decisão esconde o ramo", () => {
    const { resultado } = rastros.if_else;
    const comPalpite = aplicarAtividade(resultado, { depende_de_por_passo: { "1": { "decisao.valor": ["p9"] } }, traduzida_depende_de: {} });
    expect(ramosPulados(comPalpite, 2, assistindo(4))).toEqual([]);
    expect(ramosPulados(comPalpite, 2, { respondidos: new Set(["p9"]), alcancado: 4 })).toEqual([[4, 5]]);
  });
});

describe("balão da decisão", () => {
  it("mostra a conta e o valor", () => {
    const { resultado } = rastros.if_else;
    const cena = cenaDoEditor(resultado, 1, assistindo(1));
    expect(cena.balao).toEqual({ linha: 2, trechos: [{ texto: "7 >= 6", naoCalculado: false }], valor: true });
  });

  it("marca o que o curto-circuito pulou", () => {
    const { resultado } = rastros.curto_circuito;
    const cena = cenaDoEditor(resultado, 8, assistindo(8));
    expect(cena.balao?.valor).toBe(false);
    expect(cena.balao?.trechos).toEqual([
      { texto: "3 < 3 and ", naoCalculado: false },
      { texto: "lista[i] > 0", naoCalculado: true },
    ]);
    expect(cena.naoCalculado).toEqual([[3, 25, 3, 37]]);
  });

  it("com o palpite pendente mostra só a conta, sem valor e sem o que foi pulado", () => {
    const { resultado } = rastros.curto_circuito;
    const comPalpite = aplicarAtividade(resultado, {
      depende_de_por_passo: { "8": { "decisao.valor": ["p1"], "decisao.nao_calculado": ["p1"] } },
      traduzida_depende_de: {},
    });
    const cena = cenaDoEditor(comPalpite, 8, assistindo(10));
    expect(cena.balao).toEqual({ linha: 3, trechos: [{ texto: "3 < 3 and lista[i] > 0", naoCalculado: false }], valor: null });
    expect(cena.naoCalculado).toEqual([]);
  });

  it("sem comando ou sem decisão não há balão", () => {
    const { resultado } = rastros.if_else;
    expect(balaoDaDecisao(resultado.passos[0], resultado.estrutura.comandos[0], assistindo(0))).toBeNull();
  });

  it("conta caracteres do Python, não unidades do JavaScript", () => {
    const passo = {
      ...rastros.if_else.resultado.passos[1],
      decisao: { texto: "'🐍' == x and y", valor: false, ramo: "sai" as const, nao_calculado: [[13, 14]] as [number, number][], nao_calculado_codigo: [], ramo_visivel_desde: 2 },
    };
    const balao = balaoDaDecisao(passo, rastros.if_else.resultado.estrutura.comandos[1], assistindo(1));
    expect(balao?.trechos).toEqual([
      { texto: "'🐍' == x and ", naoCalculado: false },
      { texto: "y", naoCalculado: true },
    ]);
  });
});

describe("pílula da volta", () => {
  it("mostra a volta e só mostra o total quando o laço acaba", () => {
    const { resultado } = rastros.for;
    const comandos = resultado.estrutura.comandos;
    const pilula = pilulaDaVolta(resultado.passos[3], comandos, assistindo(3));
    expect(pilula).toMatchObject({ n: 2, total: null, saindo: false, linha: 2 });
    expect(textoDaVolta(pilula!)).toBe("volta 2");
    const depois = pilulaDaVolta(resultado.passos[3], comandos, assistindo(10));
    expect(textoDaVolta(depois!)).toBe("volta 2 de 4");
    expect(textoDaVolta(pilulaDaVolta(resultado.passos[9], comandos, assistindo(9))!)).toBe("saindo do laço");
    expect(textoDaVolta(pilulaDaVolta(resultado.passos[9], comandos, assistindo(11))!)).toBe("saindo do laço · 4 voltas");
    expect(pilulaDaVolta(resultado.passos[10], comandos, assistindo(10))).toBeNull();
  });

  it("no modo prever, o total espera o palpite das voltas", () => {
    const { resultado, atividade } = rastros.for;
    const aplicado = aplicarAtividade(resultado, atividade!);
    const comandos = aplicado.estrutura.comandos;
    const ultimo = aplicado.passos.length - 1;
    expect(pilulaDaVolta(aplicado.passos[1], comandos, assistindo(ultimo))?.total).toBeNull();
    const todos = new Set(atividade!.pontos.map((p) => p.id));
    expect(pilulaDaVolta(aplicado.passos[1], comandos, { respondidos: todos, alcancado: ultimo })?.total).toBe(4);
    // Um palpite sobre o efeito do cabeçalho esconde o número da volta.
    const p4 = aplicado.passos[7];
    expect(textoDaVolta(pilulaDaVolta(p4, comandos, { respondidos: new Set(["p2"]), alcancado: 7 })!)).toBe("volta ?");
  });
});

describe("retorno e quadros", () => {
  it("o passo depois da chamada mostra o que a função devolveu", () => {
    const { resultado } = rastros.funcao;
    expect(retornosVisiveis(resultado.passos[3], assistindo(3))).toMatchObject([{ funcao: "dobro", valor: { valor: "8" } }]);
    expect(retornosVisiveis(resultado.passos[1], assistindo(3))).toEqual([]);
    expect(retornosVisiveis(resultado.passos[3], assistindo(2))).toEqual([]);
  });

  it("na recursão, cada quadro que terminou tem o seu retorno", () => {
    const { passos } = rastros.recursao.resultado;
    const comVarios = passos.find((passo) => (passo.retornos?.length ?? 0) > 1)!;
    const retornos = retornosVisiveis(comVarios, assistindo(comVarios.i));
    // fat(1) devolve 1, fat(2) devolve 2, fat(3) devolve 6: do mais interno ao mais externo.
    expect(retornos.map((r) => [r.funcao, r.valor.valor])).toEqual([
      ["fat", "1"],
      ["fat", "2"],
      ["fat", "6"],
    ]);
  });

  it("o anterior no quadro pula os passos de dentro da função", () => {
    const { passos } = rastros.funcao.resultado;
    expect(anteriorNoQuadro(passos, 3)?.i).toBe(1);
    expect(anteriorNoQuadro(passos, 2)).toBeUndefined();
  });
});
