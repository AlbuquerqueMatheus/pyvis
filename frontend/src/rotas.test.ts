import { describe, expect, it } from "vitest";
import { lerRota } from "./rotas";

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
});
