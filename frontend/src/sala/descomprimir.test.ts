import { describe, expect, it } from "vitest";
import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from "lz-string";
import { EXEMPLOS } from "../exemplos";
import { descomprimirComTeto } from "./descomprimir";
import { lerAtividade } from "./link";

function sorteado(semente: number, tamanho: number): string {
  // Letras comuns, acentos, quebras de linha e alguns fora do plano básico (emoji).
  const letras = ["a", "b", " ", "\n", "=", "(", ")", "\"", "ç", "ã", "é", "→", "😀", "x", "1", "2"];
  let estado = semente;
  let texto = "";
  for (let k = 0; k < tamanho; k++) {
    estado = (estado * 1103515245 + 12345) % 2 ** 31;
    texto += letras[estado % letras.length];
  }
  return texto;
}

describe("descomprimirComTeto", () => {
  it("devolve o mesmo que o lz-string", () => {
    const textos = [
      "x",
      "[]",
      JSON.stringify(EXEMPLOS.map((exemplo) => ({ codigo: exemplo.codigo, entradas: exemplo.entradas?.split("\n") }))),
      ...[1, 2, 3, 50, 500, 5000].map((tamanho, k) => sorteado(k + 1, tamanho)),
      "a".repeat(10_000),
    ];
    for (const texto of textos) {
      const c = compressToEncodedURIComponent(texto);
      expect(decompressFromEncodedURIComponent(c)).toBe(texto);
      expect(descomprimirComTeto(c, 1_000_000)).toEqual({ tipo: "texto", texto });
    }
  });

  it("um texto quebrado é 'cortado', como no lz-string", () => {
    const c = compressToEncodedURIComponent(sorteado(9, 300));
    expect(descomprimirComTeto(c.slice(0, c.length / 2), 1_000_000)).toEqual({ tipo: "cortado" });
    expect(decompressFromEncodedURIComponent(c.slice(0, c.length / 2))).toBeFalsy();
    expect(descomprimirComTeto("", 10)).toEqual({ tipo: "cortado" });
  });

  it("para no teto, sem montar o texto inteiro", () => {
    const c = compressToEncodedURIComponent("a".repeat(300_000));
    expect(descomprimirComTeto(c, 100_000)).toEqual({ tipo: "grande" });
    expect(descomprimirComTeto(c, 300_000)).toEqual({ tipo: "texto", texto: "a".repeat(300_000) });
  });
});

describe("lerAtividade com uma bomba de descompressão", () => {
  // Quase 2 milhões de letras cabem em poucos milhares de letras de link (comprimir é que demora).
  it("recusa o link sem descomprimir tudo", { timeout: 30_000 }, () => {
    const c = compressToEncodedURIComponent(JSON.stringify([{ codigo: "a".repeat(1_900_000) }]));
    expect(c.length).toBeLessThan(10_000);
    expect(lerAtividade(`c=${c}`)).toEqual({ tipo: "invalida", motivo: "os programas do link são grandes demais" });
  });
});
