import { afterEach, describe, expect, it, vi } from "vitest";
import {
  PREFIXO,
  VALIDADE_MS,
  apagarSala,
  apagarTudo,
  guardarSala,
  lerSala,
  limparVencidas,
  novoSujeito,
  salasGuardadas,
  type SalaGuardada,
} from "./armazenamento";
import { armazenamentoFalso, armazenamentoQueFalha } from "../testes/armazenamentoFalso";

const AGORA = Date.UTC(2026, 9, 6, 12);

function sala(nome: string, atualizado = AGORA): SalaGuardada {
  return { v: 1, sala: nome, sujeito: "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f", apelido: "Tucano Azul 7", atualizado, eventos: [] };
}

afterEach(() => vi.unstubAllGlobals());

describe("diário no aparelho", () => {
  it("uma chave por sala; ler, guardar e apagar", () => {
    const armazenamento = armazenamentoFalso();
    expect(lerSala("K7PX", armazenamento, AGORA)).toBeNull();
    expect(guardarSala(sala("K7PX"), armazenamento)).toBe(true);
    expect(guardarSala(sala("8A"), armazenamento)).toBe(true);
    expect([...armazenamento.dados.keys()]).toEqual([`${PREFIXO}K7PX`, `${PREFIXO}8A`]);
    expect(lerSala("K7PX", armazenamento, AGORA)).toEqual(sala("K7PX"));
    expect(salasGuardadas(armazenamento, AGORA).map((s) => s.sala)).toEqual(["8A", "K7PX"]);
    expect(apagarSala("K7PX", armazenamento)).toBe(true);
    expect(lerSala("K7PX", armazenamento, AGORA)).toBeNull();
    expect(lerSala("8A", armazenamento, AGORA)).not.toBeNull();
  });

  it("sala sem uso há 30 dias some ao abrir; o resto do aparelho fica", () => {
    const armazenamento = armazenamentoFalso();
    guardarSala(sala("VELHA", AGORA - VALIDADE_MS - 1), armazenamento);
    guardarSala(sala("QUASE", AGORA - VALIDADE_MS + 60_000), armazenamento);
    armazenamento.setItem(`${PREFIXO}ESTRAGADA`, "{não é json");
    armazenamento.setItem(`${PREFIXO}TROCADA`, JSON.stringify(sala("OUTRA")));
    armazenamento.setItem("outro-site", "fica");
    expect(limparVencidas(armazenamento, AGORA)).toBe(3);
    expect([...armazenamento.dados.keys()].sort()).toEqual(["outro-site", `${PREFIXO}QUASE`]);
    // Ler uma sala vencida também a apaga.
    guardarSala(sala("VELHA", AGORA - VALIDADE_MS - 1), armazenamento);
    expect(lerSala("VELHA", armazenamento, AGORA)).toBeNull();
    expect(armazenamento.dados.has(`${PREFIXO}VELHA`)).toBe(false);
  });

  it("sala com formato estranho não é lida", () => {
    const armazenamento = armazenamentoFalso();
    for (const [nome, estranha] of Object.entries({
      SEMV: { ...sala("SEMV"), v: 2 },
      NOME: { ...sala("NOME"), sujeito: "Maria" },
      SEMEV: { ...sala("SEMEV"), eventos: "x" },
    })) {
      armazenamento.setItem(`${PREFIXO}${nome}`, JSON.stringify(estranha));
      expect(lerSala(nome, armazenamento, AGORA)).toBeNull();
    }
  });

  it("'apagar tudo' tira só o que é do PyVis", () => {
    const armazenamento = armazenamentoFalso();
    guardarSala(sala("A1"), armazenamento);
    guardarSala(sala("B2"), armazenamento);
    armazenamento.setItem("outro-site", "fica");
    expect(apagarTudo(armazenamento)).toBe(2);
    expect([...armazenamento.dados.keys()]).toEqual(["outro-site"]);
  });

  it("quando o navegador não deixa guardar, nada quebra", () => {
    expect(lerSala("K7PX", armazenamentoQueFalha)).toBeNull();
    expect(guardarSala(sala("K7PX"), armazenamentoQueFalha)).toBe(false);
    expect(apagarSala("K7PX", armazenamentoQueFalha)).toBe(false);
    expect(salasGuardadas(armazenamentoQueFalha)).toEqual([]);
    expect(apagarTudo(armazenamentoQueFalha)).toBe(0);
    expect(limparVencidas(armazenamentoQueFalha)).toBe(0);
    expect(lerSala("K7PX", null)).toBeNull();
    expect(guardarSala(sala("K7PX"), null)).toBe(false);
  });

  it("o sujeito é um UUID v4 aleatório, também sem randomUUID (fora de https)", () => {
    const formato = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    const vistos = new Set(Array.from({ length: 20 }, novoSujeito));
    expect(vistos.size).toBe(20);
    for (const sujeito of vistos) expect(sujeito).toMatch(formato);
    vi.stubGlobal("crypto", { getRandomValues: (bytes: Uint8Array) => bytes.fill(0xff) });
    expect(novoSujeito()).toMatch(formato);
  });
});
