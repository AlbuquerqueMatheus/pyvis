import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import type { ItemDaSerie } from "../motor/tipos";
import { BANCO_FALSO, CATALOGO_FALSO, contextoFalso, pythonFalso, rastros, serieFalsa } from "../testes/pythonFalso";

type Usuario = ReturnType<typeof userEvent.setup>;
type Python = ReturnType<typeof pythonFalso>;

function abrir(hash: string, opcoes: Parameters<typeof pythonFalso>[0] = {}) {
  window.history.replaceState(null, "", `/${hash}`);
  const python = pythonFalso(opcoes);
  const tela = render(<App criarCanal={python.criar} />);
  return { python, tela, usuario: userEvent.setup() };
}

/** Os pedidos de série que a página fez ao motor, na ordem. */
function pedidosDeSerie(python: Python) {
  return python.pedidos.filter((pedido) => pedido.acao === "montar_serie").map((pedido) => pedido.dados as Record<string, unknown>);
}

/** O contexto do exercício na tela (a frase do motor, aqui com a família e a semente). */
async function contextoNaTela(): Promise<string> {
  const frase = await screen.findByText(/^Programa [a-z_]+ \d+\.$/);
  return frase.textContent!;
}

async function esperarExercicio(k: number, total = 5) {
  return screen.findByRole("heading", { name: `Exercício ${k} de ${total}` });
}

/** Anda pela série inteira com 'Próximo' e devolve os contextos, um por exercício. */
async function percorrer(usuario: Usuario, total = 5): Promise<string[]> {
  const contextos: string[] = [];
  for (let k = 1; k <= total; k++) {
    await esperarExercicio(k, total);
    contextos.push(await contextoNaTela());
    await usuario.click(screen.getByRole("button", { name: k < total ? "Próximo ▶" : "Terminar" }));
    if (k < total) await waitFor(() => expect(screen.queryByText(contextos[k - 1])).toBeNull());
  }
  return contextos;
}

/** As sementes que a página vai sortear (crypto.getRandomValues), em ordem; a última se repete. */
function sortear(sementes: number[]) {
  let vez = 0;
  return vi.spyOn(globalThis.crypto, "getRandomValues").mockImplementation(((destino: Uint32Array) => {
    destino[0] = sementes[Math.min(vez++, sementes.length - 1)];
    return destino;
  }) as typeof globalThis.crypto.getRandomValues);
}

/** Uma semente cuja série (sem excluir nada) não tem nenhuma das chaves dadas, como a página procura em 'Mais 5'. */
function sementeSemAsChaves(tema: string, nivel: number, chaves: string[]): number {
  for (let semente = 0; semente < 100_000; semente++) {
    if (serieFalsa({ tema, nivel, semente }).every((item) => !chaves.includes(item.chave))) return semente;
  }
  throw new Error("nenhuma semente sem as chaves");
}

/** Copia o link do professor e devolve o texto copiado e o aviso que apareceu. */
async function copiarLink(usuario: Usuario): Promise<{ link: string; aviso: string }> {
  const escrever = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
  await usuario.click(screen.getByRole("button", { name: "Para o professor: copiar o link desta série" }));
  const aviso = await screen.findByText(/Link copiado/);
  return { link: escrever.mock.calls.at(-1)![0], aviso: aviso.textContent! };
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

describe("área Praticar", () => {
  it("o uso livre leva ao Praticar pelo primeiro link do menu", async () => {
    abrir("");
    const menu = screen.getByRole("navigation", { name: "Outras páginas" });
    const primeiro = within(menu).getAllByRole("link")[0];
    expect(primeiro).toHaveTextContent("Praticar");
    expect(primeiro).toHaveAttribute("href", "#/praticar");
  });

  it("escolher tema, o que praticar e o formato abre a série no Prever, com o foco no título", async () => {
    const { python, usuario } = abrir("#/praticar");
    expect(screen.getByText("Preparando...")).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("Praticar · PyVis"));
    // Os temas e os níveis vêm do catálogo do motor; o nível aparece pelo nome, nunca pelo número.
    const temas = await screen.findByRole("group", { name: "Tema:" });
    expect(within(temas).getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual(CATALOGO_FALSO.temas.map((t) => t.id));
    expect(within(temas).getByRole("radio", { name: "Variáveis" })).toBeChecked();
    expect(within(temas).getByRole("radio", { name: "Variáveis" })).toHaveAccessibleDescription("Guardar valores com nomes.");
    const niveis = screen.getByRole("group", { name: "O que praticar:" });
    expect(within(niveis).getAllByRole("radio").map((r) => r.closest("label")!.textContent)).toEqual(["●Guardar e mudar valores", "○Contas e textos"]);
    expect(niveis.textContent).not.toMatch(/\d|n[ií]vel/i);

    await usuario.click(within(temas).getByRole("radio", { name: "Condições" }));
    expect(within(niveis).getByRole("radio", { name: "Se e senão" })).toBeChecked();
    await usuario.click(screen.getByRole("radio", { name: "Resposta livre" }));
    await usuario.click(screen.getByRole("button", { name: "Começar ▶" }));

    expect(await esperarExercicio(1)).toHaveFocus();
    expect(screen.getByText("Condições · Se e senão")).toBeInTheDocument();
    const [pedido] = pedidosDeSerie(python);
    expect(pedido).toMatchObject({ tema: "condicoes", nivel: 1, quantidade: 5, excluir: [] });
    expect(pedido).not.toHaveProperty("familia");
    const semente = pedido.semente as number;
    expect(Number.isInteger(semente) && semente >= 0 && semente <= 2 ** 32 - 1).toBe(true);
    // O endereço vira o link da série: recarregar volta para ela.
    expect(window.location.hash).toBe(`#/praticar?t=condicoes&n=1&s=${semente}&p=l`);

    // O programa é só para ler, no Prever, com o formato escolhido.
    const contexto = await contextoNaTela();
    const exercicio = python.pedidos.find((p) => p.acao === "gerar_exercicio")!.dados as { familia: string; semente: number };
    expect(contexto).toBe(contextoFalso(exercicio.familia, exercicio.semente));
    const editor = document.querySelector(".cm-content") as HTMLElement;
    expect(editor).toHaveAttribute("aria-readonly", "true");
    const executar = screen.getByRole("button", { name: "▶ Executar" });
    await waitFor(() => expect(executar).toBeEnabled());
    await usuario.click(executar);
    await waitFor(() => expect(python.pedidos.some((p) => p.acao === "preparar_atividade")).toBe(true));
    const rodado = (python.pedidos.find((p) => p.acao === "rastrear")!.dados as { codigo: string }).codigo;
    expect(Object.values(rastros).map((r) => r.codigo)).toContain(rodado);
    expect(python.pedidos.find((p) => p.acao === "preparar_atividade")!.dados).toMatchObject({ config: { modo: "prever", formato: "livre" } });
  });

  it("'Outro exercício' troca o atual por um que ainda não apareceu; quando acaba, avisa e fica", async () => {
    const { python, usuario } = abrir("#/praticar?t=condicoes&n=1&s=99");
    await esperarExercicio(1);
    const primeiro = await contextoNaTela();
    const serie = (await waitFor(() => pedidosDeSerie(python)[0])) as Record<string, unknown>;
    expect(serie).toMatchObject({ tema: "condicoes", nivel: 1, semente: 99, quantidade: 5 });

    await usuario.click(screen.getByRole("button", { name: "Outro exercício" }));
    await waitFor(() => expect(screen.queryByText(primeiro)).toBeNull());
    expect(await esperarExercicio(1)).toHaveFocus();
    const segundo = await contextoNaTela();
    const troca = pedidosDeSerie(python)[1];
    expect(troca).toMatchObject({ tema: "condicoes", nivel: 1, semente: 99, quantidade: 1 });
    // A troca não repete nada da série: as cinco chaves vão em 'excluir'.
    expect(troca.excluir).toHaveLength(5);
    expect((troca.excluir as string[]).every((chave) => chave.startsWith("porta_teste@1:1:"))).toBe(true);
    expect(segundo).not.toBe(primeiro);

    // O banco falso tem 6 sementes: a próxima troca não acha mais nenhuma.
    await usuario.click(screen.getByRole("button", { name: "Outro exercício" }));
    expect(await screen.findByText("Não há outro exercício agora. Siga com este ou escolha outro tema.")).toBeInTheDocument();
    expect(screen.getByText(segundo)).toBeInTheDocument();
    expect(pedidosDeSerie(python)[2].excluir).toHaveLength(BANCO_FALSO.length);
  });

  it("'Terminar' leva ao fim sem contagem; 'Mais 5 deste tema' traz exercícios novos", async () => {
    const { python, usuario } = abrir("#/praticar?t=variaveis&n=1&s=4242&p=a");
    const limpa = sementeSemAsChaves("variaveis", 1, serieFalsa({ tema: "variaveis", nivel: 1, semente: 4242 }).map((i) => i.chave));
    sortear([limpa]);
    const primeiros = await percorrer(usuario);
    expect(new Set(primeiros).size).toBe(5);
    expect(primeiros.some((c) => c.includes("robo_teste")) && primeiros.some((c) => c.includes("pet_teste"))).toBe(true);

    const fim = await screen.findByRole("heading", { name: "Por hoje é isso." });
    expect(fim).toHaveFocus();
    const main = screen.getByRole("main");
    // Nada conta acertos nem mostra número, além do tamanho da próxima série no botão.
    expect(main.textContent!.replace("Mais 5 deste tema", "")).not.toMatch(/\d|acert|errou|certo|ponto/i);
    expect(within(main).getAllByRole("button").map((b) => b.textContent)).toEqual(["Mais 5 deste tema", "Escolher outro tema"]);
    expect(within(main).getByRole("link", { name: "Voltar ao início" })).toHaveAttribute("href", "#");

    await usuario.click(screen.getByRole("button", { name: "Mais 5 deste tema" }));
    expect(await esperarExercicio(1)).toHaveFocus();
    // 'Mais 5' sorteia uma semente nova cuja série não tem nada já visto: o link continua valendo.
    const mais = pedidosDeSerie(python).at(-1)!;
    expect(mais).toEqual({ tema: "variaveis", nivel: 1, semente: limpa, quantidade: 5, excluir: [] });
    expect(window.location.hash).toBe(`#/praticar?t=variaveis&n=1&s=${limpa}&p=a`);
    const seguintes = await percorrer(usuario);
    expect(seguintes.filter((c) => primeiros.includes(c))).toEqual([]);

    // 'Escolher outro tema' volta à escolha com o que estava marcado.
    await usuario.click(await screen.findByRole("button", { name: "Escolher outro tema" }));
    expect(await screen.findByRole("heading", { name: "Praticar" })).toHaveFocus();
    expect(screen.getByRole("radio", { name: "Variáveis" })).toBeChecked();
    expect(window.location.hash).toBe("#/praticar");
  });

  it("o mesmo link abre a mesma série (a turma inteira vê os mesmos exercícios)", async () => {
    const link = "#/praticar?t=variaveis&n=1&s=777&p=l";
    const primeira = abrir(link);
    const vistos = await percorrer(primeira.usuario);
    primeira.tela.unmount();

    const segunda = abrir(link);
    expect(await percorrer(segunda.usuario)).toEqual(vistos);
    expect(pedidosDeSerie(segunda.python)[0]).toEqual(pedidosDeSerie(primeira.python)[0]);
  });

  it("um link com família fixa só traz exercícios dela", async () => {
    const { usuario } = abrir("#/praticar?t=variaveis&n=1&s=5&f=pet_teste");
    const contextos = await percorrer(usuario);
    expect(contextos.every((c) => c.startsWith("Programa pet_teste "))).toBe(true);
    screen.getByRole("heading", { name: "Por hoje é isso." });
  });

  it.each([
    "#/praticar?t=xyz&n=1&s=5", // tema que o catálogo não tem
    "#/praticar?t=condicoes&n=3&s=5", // nível que o tema não tem
    "#/praticar?t=variaveis&n=1", // sem semente
    "#/praticar?t=variaveis&n=9&s=5",
    "#/praticar?t=variaveis&n=1&s=-1",
  ])("%s abre a escolha", async (hash) => {
    const { python } = abrir(hash);
    expect(await screen.findByRole("heading", { name: "Praticar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Começar ▶" })).toBeInTheDocument();
    expect(pedidosDeSerie(python)).toEqual([]);
  });

  it("uma família de outro tema no link é ignorada", async () => {
    const { python } = abrir("#/praticar?t=variaveis&n=1&s=5&f=porta_teste");
    await esperarExercicio(1);
    expect(pedidosDeSerie(python)[0]).not.toHaveProperty("familia");
  });

  it("o professor copia o link da série; sem área de transferência, o link fica à vista", async () => {
    const { usuario } = abrir("#/praticar?t=variaveis&n=1&s=777&p=l&f=robo_teste");
    await esperarExercicio(1);
    const escrever = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    await usuario.click(screen.getByRole("button", { name: "Para o professor: copiar o link desta série" }));
    expect(escrever).toHaveBeenCalledWith(`${window.location.origin}/#/praticar?t=variaveis&n=1&s=777&f=robo_teste&p=l`);
    expect(await screen.findByText(/Link copiado/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Link desta série" })).toBeNull();

    escrever.mockRejectedValue(new Error("negado"));
    await usuario.click(screen.getByRole("button", { name: "Para o professor: copiar o link desta série" }));
    expect(await screen.findByText("Não deu para copiar sozinho. Copie o link abaixo.")).toBeInTheDocument();
    const campo = screen.getByRole("textbox", { name: "Link desta série" }) as HTMLInputElement;
    expect(campo).toHaveAttribute("readonly");
    expect(campo.value).toBe(`${window.location.origin}/#/praticar?t=variaveis&n=1&s=777&f=robo_teste&p=l`);
    await waitFor(() => expect([campo.selectionStart, campo.selectionEnd]).toEqual([0, campo.value.length]));
  });

  it("um exercício que não abre avisa e deixa trocar por outro", async () => {
    // Primeiro, quais sementes a série 99 traz; depois, todas elas falham e só a sexta abre.
    const antes = abrir("#/praticar?t=condicoes&n=1&s=99");
    const sementes = (await percorrer(antes.usuario)).map((c) => Number(c.match(/(\d+)\.$/)![1]));
    antes.tela.unmount();
    const sexta = BANCO_FALSO.find((s) => !sementes.includes(s))!;

    const { python, usuario } = abrir("#/praticar?t=condicoes&n=1&s=99", { falharExercicios: sementes });
    await esperarExercicio(1);
    expect(await screen.findByText("Este exercício não abriu. Tente outro.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "▶ Executar" })).toBeNull();
    expect((python.pedidos.find((p) => p.acao === "gerar_exercicio")!.dados as ItemDaSerie).semente).toBe(sementes[0]);

    await usuario.click(screen.getByRole("button", { name: "Outro exercício" }));
    expect(await screen.findByText(contextoFalso("porta_teste", sexta))).toBeInTheDocument();
    expect(screen.queryByText("Este exercício não abriu. Tente outro.")).toBeNull();
    expect(await screen.findByRole("button", { name: "▶ Executar" })).toBeInTheDocument();
  });

  it("sem exercícios na escolha, ou com o banco visto até o fim, a página avisa sem números", async () => {
    abrir("#/praticar?t=lacos&n=2&s=1");
    expect(await screen.findByRole("heading", { name: "Ainda não há exercícios aqui." })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mais 5 deste tema" })).toBeNull();
    expect(screen.getByRole("button", { name: "Escolher outro tema" })).toBeInTheDocument();
    cleanup();

    // Condições tem 6 no banco falso: a segunda série tem 1, a terceira não tem nenhum.
    const { usuario } = abrir("#/praticar?t=condicoes&n=1&s=3");
    await percorrer(usuario);
    await usuario.click(await screen.findByRole("button", { name: "Mais 5 deste tema" }));
    await percorrer(usuario, 1);
    await usuario.click(await screen.findByRole("button", { name: "Mais 5 deste tema" }));
    expect(await screen.findByRole("heading", { name: "Você já viu todos os exercícios daqui." })).toHaveFocus();
  });

  it("depois de 'Mais 5', o link copiado abre o que o professor vê", async () => {
    const link = "#/praticar?t=variaveis&n=1&s=123&p=a";
    const limpa = sementeSemAsChaves("variaveis", 1, serieFalsa({ tema: "variaveis", nivel: 1, semente: 123 }).map((i) => i.chave));
    // A primeira semente sorteada repete exercícios já vistos: a página tenta outra.
    sortear([123, limpa]);
    const professor = abrir(link);
    const primeiros = await percorrer(professor.usuario);
    await professor.usuario.click(await screen.findByRole("button", { name: "Mais 5 deste tema" }));
    await esperarExercicio(1);
    const naTela = await contextoNaTela();
    expect(primeiros).not.toContain(naTela);
    const { link: copiado, aviso } = await copiarLink(professor.usuario);
    expect(aviso).toBe("✓ Link copiado. Quem abrir verá a mesma série.");
    expect(copiado).toBe(`${window.location.origin}/#/praticar?t=variaveis&n=1&s=${limpa}&p=a`);
    professor.tela.unmount();

    abrir(copiado.slice(window.location.origin.length + 1));
    await esperarExercicio(1);
    expect(await contextoNaTela()).toBe(naTela);
  });

  it("depois de 'Outro exercício', o link avisa que abre a série como começou", async () => {
    const link = "#/praticar?t=condicoes&n=1&s=99&p=a";
    const professor = abrir(link);
    await esperarExercicio(1);
    const original = await contextoNaTela();
    await professor.usuario.click(screen.getByRole("button", { name: "Outro exercício" }));
    // O título continua o mesmo: o aviso diz ao leitor de tela que o exercício mudou.
    expect(await screen.findByText("Exercício trocado.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(original)).toBeNull());
    const { link: copiado, aviso } = await copiarLink(professor.usuario);
    expect(aviso).toBe("✓ Link copiado. Ele abre esta série como começou, antes das trocas.");
    expect(copiado).toBe(`${window.location.origin}/${link}`);
    // 'Próximo' limpa o aviso da troca.
    await professor.usuario.click(screen.getByRole("button", { name: "Próximo ▶" }));
    await esperarExercicio(2);
    expect(screen.queryByText("Exercício trocado.")).toBeNull();
    professor.tela.unmount();

    abrir(link);
    await esperarExercicio(1);
    expect(await contextoNaTela()).toBe(original);
  });

  it("sem semente nova sem repetidos, a série pula os vistos e não oferece link", async () => {
    // Condições tem 6 exercícios no banco falso: depois de 5 vistos, toda série de 5 repete algum.
    const { python, usuario } = abrir("#/praticar?t=condicoes&n=1&s=3&p=a");
    await percorrer(usuario);
    const antes = pedidosDeSerie(python).length;
    await usuario.click(await screen.findByRole("button", { name: "Mais 5 deste tema" }));
    await esperarExercicio(1, 1);
    const pedidos = pedidosDeSerie(python).slice(antes);
    expect(pedidos.slice(0, -1).every((p) => (p.excluir as string[]).length === 0)).toBe(true);
    expect(pedidos.at(-1)!.excluir).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Para o professor: copiar o link desta série" })).toBeNull();
    // Recarregar não traz de volta o que o aluno já fez: o endereço volta à escolha deste tema.
    expect(window.location.hash).toBe("#/praticar?t=condicoes&n=1&p=a");
  });

  it("uma troca que chega depois de 'Próximo' não aparece no exercício seguinte", async () => {
    for (const atrasada of [{ ok: true as const, resultado: [] }, { ok: false as const, erro: "RuntimeError: x" }]) {
      const segurar = (pedido: { acao: string; dados: unknown }) =>
        pedido.acao === "montar_serie" && (pedido.dados as { quantidade: number }).quantidade === 1;
      const { python, usuario, tela } = abrir("#/praticar?t=variaveis&n=1&s=4242", { segurar });
      const python2 = python as ReturnType<typeof pythonFalso>;
      await esperarExercicio(1);
      const outro = screen.getByRole("button", { name: "Outro exercício" });
      await usuario.click(outro);
      await waitFor(() => expect(python2.segurados).toHaveLength(1));
      // Enquanto procura, o botão fica indisponível sem perder o foco (um segundo clique não pede de novo).
      expect(outro).toHaveAttribute("aria-disabled", "true");
      expect(outro).toHaveFocus();
      await usuario.click(outro);
      expect(python2.segurados).toHaveLength(1);

      await usuario.click(screen.getByRole("button", { name: "Próximo ▶" }));
      await esperarExercicio(2);
      expect(screen.getByRole("button", { name: "Outro exercício" })).toHaveAttribute("aria-disabled", "false");
      // O motor responde um pedido por vez: o exercício 2 abre depois que a troca velha volta.
      python2.segurados[0].soltar(atrasada);
      const segundo = await contextoNaTela();
      await new Promise((pronto) => setTimeout(pronto, 50));
      expect(screen.queryByText(/Não há outro exercício|Não deu para trocar|Exercício trocado/)).toBeNull();
      expect(screen.getByText(segundo)).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Exercício 2 de 5" })).toBeInTheDocument();
      tela.unmount();
    }
  });

  it("quando a troca acaba ou falha, o foco fica no botão 'Outro exercício'", async () => {
    const { usuario } = abrir("#/praticar?t=condicoes&n=1&s=99");
    await esperarExercicio(1);
    const outro = screen.getByRole("button", { name: "Outro exercício" });
    outro.focus();
    await usuario.keyboard("{Enter}");
    expect(await screen.findByText("Exercício trocado.")).toBeInTheDocument();
    // Depois de trocar, o foco vai para o título (o exercício novo).
    expect(await esperarExercicio(1)).toHaveFocus();
    screen.getByRole("button", { name: "Outro exercício" }).focus();
    await usuario.keyboard("{Enter}");
    expect(await screen.findByText("Não há outro exercício agora. Siga com este ou escolha outro tema.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Outro exercício" })).toHaveFocus();
  });

  it("um link colado de novo na mesma aba recomeça a página, mesmo depois de outra série", async () => {
    const link = "#/praticar?t=variaveis&n=1&s=5&p=a";
    const { usuario } = abrir(link);
    await esperarExercicio(1);
    const doLink = await contextoNaTela();
    await percorrer(usuario);
    await usuario.click(await screen.findByRole("button", { name: "Escolher outro tema" }));
    await usuario.click(await screen.findByRole("radio", { name: "Condições" }));
    await usuario.click(screen.getByRole("button", { name: "Começar ▶" }));
    await esperarExercicio(1);
    expect(window.location.hash).toMatch(/^#\/praticar\?t=condicoes&n=1&s=\d+&p=a$/);

    window.history.replaceState(null, "", `/${link}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    await waitFor(() => expect(screen.getByText(doLink)).toBeInTheDocument());
    expect(screen.getByText("Variáveis · Guardar e mudar valores")).toBeInTheDocument();
  });

  it("o Praticar não guarda nada no aparelho", async () => {
    const guardar = vi.spyOn(Storage.prototype, "setItem");
    const { usuario } = abrir("#/praticar");
    await usuario.click(await screen.findByRole("button", { name: "Começar ▶" }));
    await esperarExercicio(1);
    await usuario.click(screen.getByRole("button", { name: "Outro exercício" }));
    await screen.findByText("Exercício trocado.");
    await percorrer(usuario);
    await usuario.click(await screen.findByRole("button", { name: "Mais 5 deste tema" }));
    await esperarExercicio(1);
    await percorrer(usuario);
    await usuario.click(await screen.findByRole("button", { name: "Escolher outro tema" }));
    await screen.findByRole("heading", { name: "Praticar" });
    expect(guardar).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("se a série não abre, dá para tentar de novo", async () => {
    const { python, usuario } = abrir("#/praticar?t=variaveis&n=1&s=8", { falharSerie: true });
    expect(await screen.findByRole("heading", { name: "Os exercícios não abriram." })).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Tentar de novo" }));
    await waitFor(() => expect(pedidosDeSerie(python)).toHaveLength(2));
    expect(pedidosDeSerie(python)[1]).toEqual(pedidosDeSerie(python)[0]);
  });
});
