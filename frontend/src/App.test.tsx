import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { EXEMPLOS } from "./exemplos";
import type { Canal, Pedido } from "./motor/ponte";
import rastrosJson from "./testes/rastros.json";
import type { Resultado } from "./motor/tipos";

const rastros = rastrosJson as unknown as Record<string, { codigo: string; resultado: Resultado }>;

/** Um Python de mentira que responde com os rastros gravados pelo motor de verdade. */
function pythonFalso(opcoes: { travar?: boolean } = {}) {
  const pedidos: Pedido[] = [];
  const criar = (aoReceber: (mensagem: unknown) => void): Canal => {
    queueMicrotask(() => aoReceber({ tipo: "pronto" }));
    return {
      enviar(pedido) {
        pedidos.push(pedido);
        if (opcoes.travar) return;
        const { codigo } = pedido.dados as { codigo: string };
        const gravado = Object.values(rastros).find((r) => r.codigo === codigo);
        const resposta = gravado
          ? { id: pedido.id, ok: true, resultado: gravado.resultado }
          : { id: pedido.id, ok: false, erro: "ValueError: programa sem rastro gravado" };
        queueMicrotask(() => aoReceber(JSON.stringify(resposta)));
      },
      encerrar() {},
    };
  };
  return { criar, pedidos };
}

/** A página abre no Prever; os testes do Assistir trocam o modo antes de executar. */
function escolherAssistir() {
  fireEvent.click(screen.getByRole("radio", { name: "Assistir" }));
}

async function abrirExemplo(titulo: string, criar: ReturnType<typeof pythonFalso>["criar"], { assistir = true } = {}) {
  const usuario = userEvent.setup();
  render(<App criarCanal={criar} />);
  await screen.findByText("Python pronto!");
  if (assistir) escolherAssistir();
  await usuario.selectOptions(screen.getByLabelText("Exemplos:"), String(EXEMPLOS.findIndex((e) => e.titulo === titulo)));
  return usuario;
}

describe("App no modo assistir", () => {
  it("executa, anda com as setas e mostra decisão, ramo pulado e narração", async () => {
    const python = pythonFalso();
    const usuario = await abrirExemplo("2. Decisão com if", python.criar);
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    expect(await screen.findByText("nota recebe 7: variável nova.", { selector: "p" })).toBeInTheDocument();
    expect(python.pedidos[0]).toMatchObject({ acao: "rastrear", dados: { entradas: [] } });
    expect(document.querySelector(".cm-linha-atual")).toHaveTextContent("nota = 7");

    await usuario.keyboard("{ArrowRight}");
    expect(screen.getByText("nota >= 6? 7 >= 6, Verdadeiro: entra no if.", { selector: "p" })).toBeInTheDocument();
    // O leitor de tela ouve a mesma frase, porque o aluno andou.
    expect(document.querySelector("[aria-live='polite'].sr-only")).toHaveTextContent("nota >= 6? 7 >= 6, Verdadeiro: entra no if.");
    expect(document.querySelector(".cm-balao")).toHaveTextContent("7 >= 6 → Verdadeiro");
    expect(document.querySelector(".cm-balao")).toHaveAttribute("aria-hidden", "true");
    // O else ainda não aparece pulado: a decisão acontece neste passo.
    expect(document.querySelector(".cm-linha-pulada")).toBeNull();

    await usuario.keyboard("{ArrowRight}");
    expect(document.querySelector(".cm-balao")).toBeNull();
    const puladas = [...document.querySelectorAll(".cm-linha-pulada")].map((linha) => linha.textContent);
    expect(puladas[0]).toContain("else:");
    expect(puladas[1]).toContain('resultado = "recuperação"');
    expect(document.querySelector(".cm-rotulo-pulado")).toHaveTextContent("pulado");
    expect(screen.getByText("Passo 3 de 5")).toBeInTheDocument();
  });

  it("mostra a pílula da volta e o valor antigo riscado", async () => {
    const usuario = await abrirExemplo("3. Repetição com for", pythonFalso().criar);
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("total recebe 0: variável nova.", { selector: "p" });
    for (let k = 0; k < 3; k++) await usuario.click(screen.getByRole("button", { name: "Avançar ▶" }));
    expect(screen.getByText(/volta 2$/)).toBeInTheDocument();
    expect(document.querySelector("[data-variavel='total'] del")).toHaveTextContent("0");
    // Depois de ver o fim do laço, o total de voltas pode aparecer.
    await usuario.click(screen.getByRole("button", { name: "Último passo" }));
    await usuario.click(screen.getByRole("button", { name: "Primeiro passo" }));
    await usuario.click(screen.getByRole("button", { name: "Avançar ▶" }));
    expect(screen.getByText(/volta 1 de 4/)).toBeInTheDocument();
  });

  it("depois de uma chamada mostra o que a função devolveu", async () => {
    const python = pythonFalso();
    render(<App criarCanal={python.criar} />);
    await screen.findByText("Python pronto!");
    escolherAssistir();
    // O exemplo da função não está no menu: o aluno digita (aqui, o editor recebe o texto).
    const editor = document.querySelector(".cm-content") as HTMLElement;
    expect(editor).toHaveAttribute("aria-label", "Seu código Python");
    const usuario = userEvent.setup();
    const view = (await import("@codemirror/view")).EditorView.findFromDOM(editor)!;
    act(() => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: rastros.funcao.codigo } }));
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("Cria a função dobro. Ela só roda quando for chamada.", { selector: "p" });
    for (let k = 0; k < 3; k++) await usuario.keyboard("{ArrowRight}");
    expect(screen.getByText("devolveu")).toBeInTheDocument();
    expect(screen.getByText("devolveu").parentElement).toHaveTextContent("dobro devolveu 8");
  });

  it("escolher um exemplo logo depois de digitar troca o código na hora", async () => {
    const python = pythonFalso();
    render(<App criarCanal={python.criar} />);
    await screen.findByText("Python pronto!");
    escolherAssistir();
    const editor = document.querySelector(".cm-content") as HTMLElement;
    const view = (await import("@codemirror/view")).EditorView.findFromDOM(editor)!;
    // Digitação do aluno: o @uiw/react-codemirror passa a esperar uma pausa antes de aceitar valor de fora.
    act(() => view.dispatch({ changes: { from: 0, insert: "x = 1\n" }, userEvent: "input.type" }));
    const usuario = userEvent.setup();
    await usuario.selectOptions(screen.getByLabelText("Exemplos:"), "1");
    expect(view.state.doc.toString()).toBe(EXEMPLOS[1].codigo);
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("nota recebe 7: variável nova.", { selector: "p" });
    expect(document.querySelector(".cm-linha-atual")).toHaveTextContent("nota = 7");
  });

  it("um erro do programa aparece no último passo", async () => {
    const usuario = await abrirExemplo("8. Encontre o erro", pythonFalso().criar);
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("pontos recebe 10: variável nova.", { selector: "p" });
    expect(screen.queryByRole("alert")).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Último passo" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Problema na linha 3");
    expect(document.querySelector(".cm-linha-erro")).toHaveTextContent("total = pontos + bonu");
  });

  it("o exemplo 7 vem com o aviso e respostas de robô", async () => {
    await abrirExemplo("7. Perguntando com input", pythonFalso().criar);
    expect(screen.getByText("⚠ Não use seu nome de verdade.")).toBeVisible();
    expect(screen.getByLabelText("Respostas para o input()")).toHaveValue("Bip\n3");
  });

  it("um programa que passa de 5 s é parado e a página continua", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const python = pythonFalso({ travar: true });
      const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<App criarCanal={python.criar} />);
      await screen.findByText("Python pronto!");
      escolherAssistir();
      await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
      expect(screen.getByRole("button", { name: "Executando..." })).toBeDisabled();
      await act(async () => vi.advanceTimersByTime(5000));
      expect(await screen.findByRole("alert")).toHaveTextContent("O programa demorou demais e foi parado.");
      expect(await screen.findByText("Python pronto!")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "▶ Executar" })).toBeEnabled();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("App: o modo do uso livre", () => {
  it("começa no Prever, com a escolha das perguntas, e pede o palpite", async () => {
    const { pythonFalso: pythonComPrevisoes } = await import("./testes/pythonFalso");
    const python = pythonComPrevisoes();
    const usuario = await abrirExemplo("3. Repetição com for", python.criar, { assistir: false });
    expect(screen.getByRole("radio", { name: "Prever" })).toBeChecked();
    expect(screen.getByText("Clique em Executar. Antes de ver o resultado, você dá palpites.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Alternativas" })).toBeChecked();
    await usuario.click(screen.getByRole("radio", { name: "Resposta livre" }));
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    expect(await screen.findByText("Antes de rodar")).toBeInTheDocument();
    expect(python.pedidos[1]).toMatchObject({ acao: "preparar_atividade", dados: { config: { modo: "prever", formato: "livre" } } });
    expect(screen.getByLabelText("Seu palpite").tagName).toBe("TEXTAREA");

    // Trocar o modo esquece a execução: o palpite some, a escolha das perguntas some e o botão volta.
    await usuario.click(screen.getByRole("radio", { name: "Assistir" }));
    expect(screen.queryByText("Antes de rodar")).toBeNull();
    expect(screen.queryByRole("group", { name: "Perguntas:" })).toBeNull();
    expect(screen.getByRole("button", { name: "▶ Executar" })).toBeEnabled();
  });
});
