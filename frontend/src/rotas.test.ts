import { describe, expect, it } from "vitest";
import { fragmentoDePraticar, lerRota } from "./rotas";

describe("rotas", () => {
  it("cada fragmento leva a uma tela", () => {
    expect(lerRota("")).toEqual({ tela: "livre" });
    expect(lerRota("#")).toEqual({ tela: "livre" });
    expect(lerRota("#qualquer")).toEqual({ tela: "livre" });
    expect(lerRota("#/criar")).toEqual({ tela: "criar" });
    expect(lerRota("#/pais")).toEqual({ tela: "pais" });
    expect(lerRota("#a=ex3&m=prever&f=alt")).toMatchObject({ tela: "atividade", fragmento: "a=ex3&m=prever&f=alt", atividade: { programas: [{ ex: "ex3" }] } });
    expect(lerRota("#a=ex42")).toMatchObject({ tela: "link_invalido" });
  });

  it("#/praticar lê tema, nível, semente, família e formato; o que não vale é ignorado", () => {
    expect(lerRota("#/praticar")).toEqual({ tela: "praticar", pedido: {} });
    expect(lerRota("#/praticar?")).toEqual({ tela: "praticar", pedido: {} });
    expect(lerRota("#/praticar?t=variaveis&n=2&s=4294967295&f=robo_energia&p=l")).toEqual({
      tela: "praticar",
      pedido: { tema: "variaveis", nivel: 2, semente: 4294967295, familia: "robo_energia", formato: "livre" },
    });
    expect(lerRota("#/praticar?p=a&s=0&n=1&t=lacos")).toEqual({ tela: "praticar", pedido: { tema: "lacos", nivel: 1, semente: 0, formato: "alternativas" } });
    // Cada parâmetro ruim cai sozinho; os outros ficam.
    expect(lerRota("#/praticar?t=Variáveis&n=4&s=4294967296&f=1x&p=x")).toEqual({ tela: "praticar", pedido: {} });
    expect(lerRota("#/praticar?t=lacos&n=0&s=-3&p=livre")).toEqual({ tela: "praticar", pedido: { tema: "lacos" } });
    expect(lerRota("#/praticar?n=1.0&s=12a&s=7")).toEqual({ tela: "praticar", pedido: {} });
    expect(lerRota("#/praticar?t=__proto__&n=constructor&p=toString")).toEqual({ tela: "praticar", pedido: {} });
    // Só com '?' depois do nome da tela.
    expect(lerRota("#/praticarx")).toEqual({ tela: "livre" });
  });

  it("o fragmento da série volta igual pelo lerRota", () => {
    const pedido = { tema: "condicoes", nivel: 3, semente: 123, familia: "porta", formato: "livre" } as const;
    expect(fragmentoDePraticar(pedido)).toBe("#/praticar?t=condicoes&n=3&s=123&f=porta&p=l");
    expect(lerRota(fragmentoDePraticar(pedido))).toEqual({ tela: "praticar", pedido });
    expect(fragmentoDePraticar({ tema: "lacos", nivel: 1, semente: 0, formato: "alternativas" })).toBe("#/praticar?t=lacos&n=1&s=0&p=a");
    expect(fragmentoDePraticar({})).toBe("#/praticar");
  });
});
