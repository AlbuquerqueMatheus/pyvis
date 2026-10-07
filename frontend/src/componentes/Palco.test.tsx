import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { useMotor } from "../motor/useMotor";
import type { Formato, Modo } from "../motor/tipos";
import { previsoes, pythonFalso, rastros } from "../testes/pythonFalso";
import { INTERVALO_MS, Palco, type RegistroDoPalco } from "./Palco";

type Opcoes = { modo?: Modo; formato?: Formato; somenteLeitura?: boolean; semAtividade?: boolean };

function Tela({ nome, modo, formato, somenteLeitura, criar, aoRegistrar }: Opcoes & { nome: string; criar: ReturnType<typeof pythonFalso>["criar"]; aoRegistrar: (r: RegistroDoPalco) => void }) {
  const motor = useMotor(criar);
  const [codigo, setCodigo] = useState(rastros[nome].codigo);
  return (
    <Palco
      motor={motor}
      codigo={codigo}
      aoMudarCodigo={somenteLeitura ? undefined : setCodigo}
      entradas={rastros[nome].entradas.join("\n")}
      modo={modo ?? "prever"}
      formato={formato ?? "alternativas"}
      aoRegistrar={aoRegistrar}
    />
  );
}

async function abrir(nome: string, opcoes: Opcoes = {}, usuario = userEvent.setup()) {
  const python = pythonFalso({ semAtividade: opcoes.semAtividade });
  const registros: RegistroDoPalco[] = [];
  render(<Tela nome={nome} {...opcoes} criar={python.criar} aoRegistrar={(r) => registros.push(r)} />);
  const executar = screen.getByRole("button", { name: "▶ Executar" });
  await waitFor(() => expect(executar).toBeEnabled());
  await usuario.click(executar);
  return { usuario, python, registros };
}

/** O id da alternativa gravada (o Python sorteia a ordem). */
function idDe(nome: string, ponto: string, texto: string) {
  const atividade = previsoes[nome].atividades.alternativas;
  const achado = [atividade.palpite_inicial!, ...atividade.pontos].find((p) => p.id === ponto)!;
  return achado.alternativas!.find((a) => a.texto === texto)!.id;
}

const balao = () => document.querySelector<HTMLElement>("[data-balao='previsao']");
const textoDoPasso = () => screen.getByText(/^Passo \d+/).textContent!;
const passoAtual = () => textoDoPasso().match(/^Passo (\d+)/)![1];
const avancar = () => screen.getByRole("button", { name: "Avançar ▶" });

async function escolher(usuario: ReturnType<typeof userEvent.setup>, texto: string) {
  const caixa = balao()!;
  const radio = within(caixa)
    .getAllByRole("radio")
    .find((r) => r.closest("label")!.textContent!.replace(/^\d/, "").replace(/[●○]$/, "") === texto);
  if (!radio) throw new Error(`alternativa ${texto} não encontrada`);
  await usuario.click(radio);
  await usuario.click(within(caixa).getByRole("button", { name: "Confirmar" }));
}

/** Nenhum texto da tela mostra o id técnico de uma concepção. */
function semIdTecnico() {
  expect(document.body.textContent).not.toMatch(/\bC\d{2}\b/);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("Palco no modo Prever, com alternativas", () => {
  it("palpite inicial, palpite diferente com o Detetive, pular e o retorno do fim", async () => {
    const { usuario, python, registros } = await abrir("for");
    expect(await screen.findByText("Antes de rodar")).toBeInTheDocument();
    expect(python.pedidos.map((p) => p.acao)).toEqual(["rastrear", "preparar_atividade"]);
    expect(python.pedidos[1].dados).toMatchObject({ config: { modo: "prever", formato: "alternativas" } });
    // Antes do palpite não há linha do tempo nem caixinhas.
    expect(screen.queryByRole("button", { name: "Avançar ▶" })).toBeNull();
    expect(screen.getByText("Primeiro, dê o seu palpite.")).toBeInTheDocument();

    await escolher(usuario, "A soma é 15");
    await waitFor(() => expect(balao()).toBeNull());
    expect(passoAtual()).toBe("1");
    // Com perguntas abertas, o total de passos não aparece: ele diria quantas voltas o laço dá.
    expect(textoDoPasso()).toBe("Passo 1");
    expect(screen.getByRole("slider", { name: "Linha do tempo da execução" })).toHaveAttribute("max", "1");
    // O palpite inicial só é corrigido no fim: nada de ✓ ou ✗ agora.
    expect(screen.queryByText("Não foi isso.")).toBeNull();

    // Último passo para na primeira pergunta.
    await usuario.click(screen.getByRole("button", { name: "Último passo" }));
    expect(passoAtual()).toBe("2");
    expect(within(balao()!).getByRole("heading")).toHaveTextContent("Quantas voltas o laço vai dar?");
    expect(screen.getByText(/volta \?/)).toBeInTheDocument();
    await usuario.keyboard("{ArrowRight}");
    expect(passoAtual()).toBe("2");

    // O palpite de quem acha que o range chega ao fim.
    await escolher(usuario, "5");
    const status = await within(balao()!).findByRole("status");
    await waitFor(() => expect(status).toHaveTextContent("Seu palpite: 5. O laço deu 4 voltas."));
    expect(status).toHaveTextContent("✗ Não foi isso.");
    expect(screen.getByRole("region", { name: "Detetive" })).toHaveTextContent("Será que você pensou que o range(1, 5) chegava até o 5?");
    semIdTecnico();

    // 'Onde olhar' das voltas é a última volta, que ainda está depois de outra pergunta.
    await usuario.click(screen.getByRole("button", { name: "Onde olhar" }));
    expect(screen.getByRole("region", { name: "Detetive" })).toHaveTextContent("Você vai ver isso no fim do laço, depois da próxima pergunta.");
    expect(document.querySelector("[data-contorno]")).toBeNull();
    expect(passoAtual()).toBe("2");
    expect(balao()).not.toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    expect(balao()).toBeNull();
    expect(document.querySelector("[data-contorno]")).toBeNull();

    while (!balao()) await usuario.click(avancar());
    expect(passoAtual()).toBe("5");
    // A caixinha da pergunta mostra '?' no lugar do valor novo.
    expect(document.querySelector("[data-variavel='total']")).toHaveTextContent("?");
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    expect(passoAtual()).toBe("6");

    expect(registros.filter((r) => r.tipo !== "Step")).toEqual([
      { tipo: "Run.Program", ms: expect.any(Number) },
      { tipo: "Prediction", ponto: "p1", formato: "alternativas", resposta: { alternativa: idDe("for", "p1", "A soma é 15") }, certa: false, concepcao: "C01", testadas: ["C01"], ms: expect.any(Number) },
      { tipo: "Prediction", ponto: "p2", formato: "alternativas", resposta: { alternativa: idDe("for", "p2", "5") }, certa: false, concepcao: "C01", testadas: ["C01"], ms: expect.any(Number) },
      { tipo: "Feedback.Layer", ponto: "p2", camada: 1, concepcao: "C01" },
      { tipo: "Prediction.Skip", ponto: "p3", formato: "alternativas", ms: expect.any(Number) },
    ]);
    expect(registros.filter((r) => r.tipo === "Step").length).toBeGreaterThan(2);

    // Até o fim: o palpite inicial ganha o retorno, com 'Me mostra' oferecido sem custo (dois palpites diferentes).
    for (let guarda = 0; guarda < 20 && !screen.queryByText(/fim do programa/); guarda++) {
      const caixa = balao();
      if (caixa) await usuario.click(within(caixa).getByRole("button", { name: "Pular" }));
      else await usuario.click(avancar());
    }
    await waitFor(() => expect(within(balao()!).getByRole("status")).toHaveTextContent("Seu palpite: “A soma é 15”."));
    // Tudo respondido: o total volta.
    expect(textoDoPasso()).toMatch(/^Passo 12 de 12/);
    expect(screen.getByText("Tudo bem ver o passo resolvido.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar" })).toHaveFocus();
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    expect(balao()).toBeNull();
    semIdTecnico();
  });

  it("a camada que abre sem mudar de passo rola até o texto dela (no celular, ele abria embaixo da barra fixa)", async () => {
    const rolados: Element[] = [];
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (this: Element) {
      rolados.push(this);
    };
    try {
      const { usuario } = await abrir("for");
      await screen.findByText("Antes de rodar");
      await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
      await usuario.click(screen.getByRole("button", { name: "Último passo" }));
      await escolher(usuario, "5");
      const status = await within(balao()!).findByRole("status");
      await waitFor(() => expect(status).toHaveTextContent("Não foi isso."));
      rolados.length = 0;
      await usuario.click(screen.getByRole("button", { name: "A regra" }));
      await waitFor(() => expect(rolados.some((el) => el.getAttribute("data-camada") === "2")).toBe(true));
      const texto = document.querySelector("[data-camada='2']")!;
      expect(texto).toBeVisible();
      expect(texto.className).toContain("max-lg:scroll-mb-48");
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it("um palpite certo mostra ✓ e o motivo; Continuar anda um passo", async () => {
    const { usuario } = await abrir("for");
    await screen.findByText("Antes de rodar");
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    await usuario.click(avancar());
    await escolher(usuario, "4");
    await waitFor(() => expect(within(balao()!).getByRole("status")).toHaveTextContent("✓ Certo!"));
    expect(within(balao()!).getByRole("status")).toHaveTextContent("Isso! O range para antes do último número.");
    expect(screen.queryByRole("region", { name: "Detetive" })).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Continuar" }));
    expect(passoAtual()).toBe("3");
    expect(avancar()).toHaveFocus();
  });

  it("o autoplay anda sozinho e para na pergunta seguinte", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await abrir("for", {}, usuario);
    await screen.findByText("Antes de rodar");
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    await usuario.click(avancar());
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    expect(passoAtual()).toBe("3");
    await usuario.click(screen.getByRole("button", { name: /Tocar/ }));
    expect(screen.getByRole("button", { name: /Pausar/ })).toHaveAttribute("aria-pressed", "true");
    await act(async () => vi.advanceTimersByTime(INTERVALO_MS));
    expect(passoAtual()).toBe("4");
    await act(async () => vi.advanceTimersByTime(INTERVALO_MS));
    expect(passoAtual()).toBe("5");
    expect(balao()).not.toBeNull();
    expect(screen.getByRole("button", { name: /Tocar/ })).toHaveAttribute("aria-pressed", "false");
    await act(async () => vi.advanceTimersByTime(INTERVALO_MS * 3));
    expect(passoAtual()).toBe("5");
  });
});

describe("Palco no modo Prever, com resposta livre", () => {
  it("número ou texto: o aviso não registra nada; o palpite com a ideia do input traz o Detetive", async () => {
    // Com input, não há palpite antes de rodar: a tela teria as perguntas e o que foi digitado.
    const { usuario, registros } = await abrir("conta", { formato: "livre" });
    await screen.findByText(/^Passo 1/);
    expect(screen.queryByText("Antes de rodar")).toBeNull();
    await usuario.click(avancar());
    expect(within(balao()!).getByRole("heading")).toHaveTextContent("Depois desta linha, quanto vale b?");
    const campo = within(balao()!).getByLabelText("Seu palpite");
    expect(campo).toHaveFocus();

    await usuario.keyboard("abc");
    await usuario.click(within(balao()!).getByRole("button", { name: /^número/ }));
    await waitFor(() => expect(within(balao()!).getByRole("status")).toHaveTextContent("Isso não parece um número."));
    expect(registros.filter((r) => r.tipo === "Prediction")).toHaveLength(0);
    // Mexer no texto apaga o aviso.
    await usuario.clear(campo);
    expect(within(balao()!).getByRole("status")).toBeEmptyDOMElement();

    await usuario.type(campo, "8");
    expect(within(balao()!).getByRole("button", { name: /^texto/ })).toHaveTextContent('"8"');
    await usuario.click(within(balao()!).getByRole("button", { name: /^número/ }));
    await waitFor(() => expect(within(balao()!).getByRole("status")).toHaveTextContent('Seu palpite: 8. O Python guardou "44".'));
    expect(screen.getByRole("region", { name: "Detetive" })).toHaveTextContent("Será que você pensou que o input devolvia um número?");
    expect(registros.at(-1)).toMatchObject({ tipo: "Prediction", ponto: "p1", formato: "livre", resposta: { tipo_escolhido: "numero" }, certa: false, concepcao: "C03" });
    semIdTecnico();

    // 'Me mostra' vai ao passo resolvido e contorna a caixinha da pergunta.
    await usuario.click(screen.getByRole("button", { name: "Me mostra" }));
    expect(passoAtual()).toBe("3");
    expect(document.querySelector("[data-contorno]")).toHaveAttribute("data-variavel", "b");
    expect(document.querySelector("[data-variavel='b']")).toHaveTextContent('"44"');
    expect(registros.at(-1)).toEqual({ tipo: "Feedback.Layer", ponto: "p1", camada: 3, concepcao: "C03" });
  });

  it("o mesmo valor marcado como texto está certo", async () => {
    const { usuario, registros } = await abrir("conta", { formato: "livre" });
    await screen.findByText(/^Passo 1/);
    await usuario.click(avancar());
    await usuario.keyboard("44");
    await usuario.click(within(balao()!).getByRole("button", { name: /^texto/ }));
    await waitFor(() => expect(within(balao()!).getByRole("status")).toHaveTextContent("✓ Certo!"));
    expect(registros.at(-1)).toMatchObject({ tipo: "Prediction", ponto: "p1", resposta: { tipo_escolhido: "texto" }, certa: true, concepcao: null });
  });
});

describe("Palco: a tela segue o modo", () => {
  it("Assistir não pede atividade e anda livre até o fim, sem balão de palpite", async () => {
    const { usuario, python } = await abrir("for", { modo: "assistir" });
    await screen.findByText("total recebe 0: variável nova.", { selector: "p" });
    expect(python.pedidos.map((p) => p.acao)).toEqual(["rastrear"]);
    await usuario.click(screen.getByRole("button", { name: "Último passo" }));
    expect(passoAtual()).toBe("12");
    expect(balao()).toBeNull();
  });

  it("se a atividade não vem, o Prever roda sem perguntas", async () => {
    const { usuario } = await abrir("for", { semAtividade: true });
    await screen.findByText("total recebe 0: variável nova.", { selector: "p" });
    await usuario.click(screen.getByRole("button", { name: "Último passo" }));
    expect(passoAtual()).toBe("12");
    expect(balao()).toBeNull();
  });

  it("sem aoMudarCodigo o código é só para ler", async () => {
    await abrir("for", { modo: "assistir", somenteLeitura: true });
    expect(document.querySelector(".cm-content")).toHaveAttribute("aria-readonly", "true");
  });
});

/** Anda até o fim respondendo tudo e confere o orçamento de atenção em cada tela. */
async function percorrer(usuario: ReturnType<typeof userEvent.setup>, formato: Formato) {
  const telas: string[] = [];
  for (let guarda = 0; guarda < 120; guarda++) {
    const baloes = document.querySelectorAll("[data-balao]").length;
    const animadas = document.querySelectorAll("[data-destaque-animado]").length;
    telas.push(`${screen.queryByText(/^Passo \d+ de \d+/)?.textContent ?? "inicio"}: ${baloes} balão, ${animadas} animada`);
    expect(baloes, telas.at(-1)).toBeLessThanOrEqual(1);
    expect(animadas, telas.at(-1)).toBeLessThanOrEqual(1);

    const caixa = balao();
    if (caixa) {
      const continuar = within(caixa).queryByRole("button", { name: "Continuar" });
      if (continuar) {
        await usuario.click(continuar);
      } else if (formato === "alternativas") {
        await usuario.click(within(caixa).getAllByRole("radio")[0]);
        await usuario.click(within(caixa).getByRole("button", { name: "Confirmar" }));
        await waitFor(() => expect(caixa.isConnected && within(caixa).queryByRole("button", { name: "Confirmar" })).toBeFalsy());
      } else {
        await usuario.click(within(caixa).getByRole("button", { name: "Pular" }));
      }
      continue;
    }
    const botao = screen.queryByRole("button", { name: "Avançar ▶" });
    if (!botao || botao.hasAttribute("disabled")) return telas;
    await usuario.click(botao);
  }
  throw new Error("não chegou ao fim");
}

describe("Palco na tela grande", () => {
  it("o palpite antes de rodar, a linha do tempo e o narrador ficam na coluna da execução, ao lado do código", async () => {
    const { usuario } = await abrir("for");
    await screen.findByText("Antes de rodar");
    const execucao = screen.getByRole("region", { name: "Execução" });
    expect(execucao).toContainElement(balao());
    // O balão não cobre o código: ele não está preso ao editor.
    expect(balao()!.closest(".cm-tooltip")).toBeNull();
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    const avancarBotao = await screen.findByRole("button", { name: "Avançar ▶" });
    expect(execucao).toContainElement(avancarBotao);
    // Linha do tempo, depois o narrador, depois as caixinhas.
    const ordem = [avancarBotao, screen.getByRole("region", { name: "Narrador" }), screen.getByRole("heading", { name: "Variáveis" })];
    expect(ordem.every((elemento) => execucao.contains(elemento))).toBe(true);
    for (let k = 1; k < ordem.length; k++) expect(ordem[k - 1].compareDocumentPosition(ordem[k]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("orçamento de atenção: no máximo 1 balão e 1 destaque animado por passo", () => {
  const prever = ["for", "while", "if_else", "input", "conta"];
  for (const nome of prever) {
    for (const formato of ["alternativas", "livre"] as const) {
      it(`Prever (${formato}): ${nome}`, async () => {
        const { usuario } = await abrir(nome, { formato });
        await screen.findByText(previsoes[nome].atividades[formato].palpite_inicial ? "Antes de rodar" : /^Passo 1/);
        const telas = await percorrer(usuario, formato);
        expect(telas.length).toBeGreaterThanOrEqual(rastros[nome].resultado.passos.length);
        expect(screen.getByText(/fim do programa/)).toBeInTheDocument();
      });
    }
  }

  for (const nome of ["for", "while", "if_else", "funcao", "elif", "curto_circuito", "input", "erro", "troca"]) {
    it(`Assistir: ${nome}`, async () => {
      const { usuario } = await abrir(nome, { modo: "assistir" });
      await screen.findByText(/^Passo 1 de/);
      await percorrer(usuario, "alternativas");
      expect(passoAtual()).toBe(String(rastros[nome].resultado.passos.length));
    });
  }

  it("a troca muda duas caixinhas no mesmo passo e só uma anima", async () => {
    const { usuario } = await abrir("troca", { modo: "assistir" });
    await screen.findByText(/^Passo 1 de/);
    await usuario.click(avancar());
    await usuario.click(avancar());
    expect(screen.getAllByText("mudou")).toHaveLength(2);
    expect(document.querySelectorAll("[data-destaque-animado]")).toHaveLength(1);
  });
});

describe("Palco no celular", () => {
  function celular() {
    vi.stubGlobal("matchMedia", (consulta: string) => ({
      matches: consulta.includes("pointer: coarse"),
      media: consulta,
      addEventListener() {},
      removeEventListener() {},
    }));
  }

  it("duas abas, linha do tempo fixa embaixo e o balão logo abaixo da linha atual", async () => {
    celular();
    const { usuario } = await abrir("for");
    const abas = screen.getAllByRole("tab");
    expect(abas.map((aba) => aba.textContent)).toEqual(["Código", "Passos"]);
    for (const aba of abas) expect(aba.className).toMatch(/min-h-11/);
    expect(screen.getByRole("tab", { name: "Código" })).toHaveAttribute("aria-selected", "true");

    await screen.findByText("Antes de rodar");
    expect(screen.getByRole("tabpanel", { name: "Código" })).toContainElement(balao());
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    // Depois do palpite inicial, a aba Passos.
    expect(screen.getByRole("tab", { name: "Passos" })).toHaveAttribute("aria-selected", "true");

    await usuario.click(avancar());
    const caixa = balao()!;
    expect(caixa.closest(".cm-tooltip")).toBeNull();
    const painel = screen.getByRole("tabpanel", { name: "Execução" });
    expect(painel).toContainElement(caixa);
    // O trecho com a linha atual vem logo antes do balão.
    expect(caixa.previousElementSibling).toHaveTextContent("for numero in range(1, 5):");
    expect(avancar().closest(".fixed")).not.toBeNull();
    expect(document.querySelectorAll("[data-balao]")).toHaveLength(1);

    // Na aba Código, o mesmo balão vai para o editor, preso à linha.
    await usuario.click(screen.getByRole("tab", { name: "Código" }));
    expect(balao()!.closest(".cm-tooltip")).not.toBeNull();
  });

  it("a aba Passos mostra o balão da decisão e as linhas puladas, como o editor", async () => {
    celular();
    const { usuario } = await abrir("if_else", { modo: "assistir" });
    await screen.findByText(/^Passo 1 de/);
    await usuario.click(avancar());
    const passos = screen.getByRole("tabpanel", { name: "Execução" });
    const decisao = passos.querySelector("[data-balao='decisao']");
    expect(decisao).toHaveTextContent("7 >= 6 → Verdadeiro");
    while (!passos.querySelector("[data-pulados]")) await usuario.click(avancar());
    expect(passos.querySelector("[data-pulados]")).toHaveTextContent("↷ pulado: linhas 4 e 5");
  });

  it("com uma pergunta de valor, as caixinhas vêm antes do narrador", async () => {
    celular();
    const { usuario } = await abrir("for");
    await screen.findByText("Antes de rodar");
    await usuario.click(within(balao()!).getByRole("button", { name: "Pular" }));
    const passos = screen.getByRole("tabpanel", { name: "Execução" });
    const caixinhas = () => within(passos).getByRole("heading", { name: "Variáveis" });
    const narrador = () => within(passos).getByRole("region", { name: "Narrador" });
    const antes = (a: Element, b: Element) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    // Sem pergunta de valor, o narrador vem primeiro.
    expect(antes(narrador(), caixinhas())).toBe(true);
    while (!balao() || within(balao()!).getByRole("heading").textContent !== "Depois desta linha, quanto vale total?") {
      const caixa = balao();
      if (caixa) await usuario.click(within(caixa).getByRole("button", { name: "Pular" }));
      else await usuario.click(avancar());
    }
    expect(antes(caixinhas(), narrador())).toBe(true);
    expect(antes(balao()!, caixinhas())).toBe(true);
  });
});
