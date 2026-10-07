import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { PREFIXO, VALIDADE_MS, type SalaGuardada } from "../sala/armazenamento";

const SUJEITO = "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f";

function guardar(sala: string, apelido: string, eventos: number, atualizado = Date.now()) {
  const registro: SalaGuardada = { v: 1, sala, sujeito: SUJEITO, apelido, atualizado, eventos: [] };
  for (let k = 0; k < eventos; k++) registro.eventos.push({ v: 1, ts: atualizado, sala, sujeito: SUJEITO, atividade: "aula3", programa: null, condicao: null, code_hash: null, tipo: "Session.Start" });
  localStorage.setItem(PREFIXO + sala, JSON.stringify(registro));
}

function abrirPais() {
  window.history.replaceState(null, "", "/#/pais");
  const criarCanal = vi.fn(() => {
    throw new Error("não devia carregar o Python");
  });
  render(<App criarCanal={criarCanal} />);
  return { criarCanal, usuario: userEvent.setup() };
}

beforeEach(() => localStorage.clear());
afterEach(() => window.history.replaceState(null, "", "/"));

describe("página para pais e responsáveis", () => {
  it("explica o que fica guardado e diz quando não há nada", () => {
    const { criarCanal } = abrirPais();
    expect(document.title).toMatch(/pais/i);
    for (const titulo of ["O que fica guardado", "O que nunca fica guardado", "Onde fica e quem vê", "Por quanto tempo", "Como apagar"])
      expect(screen.getByRole("heading", { name: titulo })).toBeInTheDocument();
    expect(screen.getByText(/30 dias sem uso/)).toBeInTheDocument();
    expect(screen.getByText("Neste aparelho não há nada guardado pelo PyVis.")).toBeInTheDocument();
    expect(criarCanal).not.toHaveBeenCalled();
  });

  it("lista as salas do aparelho e apaga uma ou todas, sem tocar no resto", async () => {
    guardar("K7PX", "Tucano Azul 7", 1);
    guardar("8A", "Panda Cinza 21", 3);
    guardar("VELHA", "Lobo Verde 50", 2, Date.now() - VALIDADE_MS - 1);
    localStorage.setItem("outro-site", "fica");
    const { usuario } = abrirPais();
    // A sala vencida some ao abrir.
    expect(screen.queryByText("VELHA")).toBeNull();
    expect(screen.getByText("Tucano Azul 7").parentElement).toHaveTextContent(/Sala K7PX, apelido Tucano Azul 7\. 1 registro\. Apaga sozinho em/);
    expect(screen.getByText("Panda Cinza 21").parentElement).toHaveTextContent("3 registros.");

    await usuario.click(screen.getByRole("button", { name: "Apagar a sala K7PX" }));
    expect(screen.getByText("A sala K7PX foi apagada deste aparelho.")).toBeInTheDocument();
    expect(localStorage.getItem(PREFIXO + "K7PX")).toBeNull();
    expect(localStorage.getItem(PREFIXO + "8A")).not.toBeNull();
    expect(screen.queryByText("Tucano Azul 7")).toBeNull();

    await usuario.click(screen.getByRole("button", { name: "Apagar tudo do PyVis deste aparelho" }));
    expect(screen.getByText("Tudo o que o PyVis guardou neste aparelho foi apagado.")).toBeInTheDocument();
    expect(screen.getByText("Neste aparelho não há nada guardado pelo PyVis.")).toBeInTheDocument();
    expect(Object.keys(localStorage)).toEqual(["outro-site"]);
  });

  it("acompanha o que outra aba guarda", () => {
    abrirPais();
    guardar("K7PX", "Tucano Azul 7", 1);
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: PREFIXO + "K7PX" }));
    });
    expect(screen.getByText("Tucano Azul 7")).toBeInTheDocument();
  });
});
