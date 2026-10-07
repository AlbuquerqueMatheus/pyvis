import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import type { AtividadeLink, Evento } from "../motor/tipos";
import { PREFIXO, VALIDADE_MS, type SalaGuardada } from "../sala/armazenamento";
import { lerEntrega } from "../sala/arquivos";
import { codificarAtividade } from "../sala/link";
import { APELIDOS, REGRAS, pythonFalso, rastros } from "../testes/pythonFalso";
import { AVISO } from "./Entrada";

const SUJEITO = "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f";
const ATIVIDADE: AtividadeLink = {
  v: 1,
  id: "aula3",
  // O if do exemplo 2 e o programa da conta (a = input; b = a * 2): os dois têm palpites gravados.
  programas: [{ ex: "ex2" }, { codigo: rastros.conta.codigo, entradas: ["4"] }],
  modo: "prever",
  formato: "alternativas",
  sala: "K7PX",
  semente: 7,
};

type Usuario = ReturnType<typeof userEvent.setup>;

function abrir(hash: string) {
  window.history.replaceState(null, "", `/${hash}`);
  const python = pythonFalso();
  render(<App criarCanal={python.criar} />);
  return { python, usuario: userEvent.setup() };
}

function guardada(sala = "K7PX"): SalaGuardada | null {
  const texto = localStorage.getItem(PREFIXO + sala);
  return texto ? (JSON.parse(texto) as SalaGuardada) : null;
}

function guardar(registro: SalaGuardada) {
  localStorage.setItem(PREFIXO + registro.sala, JSON.stringify(registro));
}

async function eventosGuardados(quantos: (eventos: Evento[]) => boolean): Promise<Evento[]> {
  let eventos: Evento[] = [];
  await waitFor(() => {
    eventos = guardada()?.eventos ?? [];
    expect(quantos(eventos)).toBe(true);
  });
  return eventos;
}

async function entrar(usuario: Usuario, codigo = "k7px", apelido?: string) {
  await screen.findByText(APELIDOS[0], { selector: "strong" });
  if (apelido) await usuario.click(screen.getByRole("radio", { name: apelido }));
  await usuario.type(screen.getByLabelText("Código da sala"), codigo);
  await usuario.click(screen.getByRole("button", { name: /Começar/ }));
}

const balao = () => document.querySelector<HTMLElement>("[data-balao='previsao']")!;

async function escolher(usuario: Usuario, texto: string) {
  await waitFor(() => expect(balao()).not.toBeNull());
  const radio = within(balao())
    .getAllByRole("radio")
    .find((r) => r.closest("label")!.textContent!.replace(/^\d/, "").replace(/[●○]$/, "") === texto);
  if (!radio) throw new Error(`alternativa ${texto} não encontrada`);
  await usuario.click(radio);
  await usuario.click(within(balao()).getByRole("button", { name: "Confirmar" }));
}

/** Roda o programa da tela e responde: o palpite antes de rodar e o palpite do passo 1. */
/** `inicial` null: o programa não tem palpite antes de rodar (com input, por exemplo). */
async function rodarComPalpites(usuario: Usuario, inicial: string | null, doPasso: string) {
  const executar = screen.getByRole("button", { name: "▶ Executar" });
  await waitFor(() => expect(executar).toBeEnabled());
  await usuario.click(executar);
  if (inicial !== null) {
    await screen.findByText("Antes de rodar");
    await escolher(usuario, inicial);
  }
  await usuario.click(await screen.findByRole("button", { name: "Avançar ▶" }));
  await escolher(usuario, doPasso);
  await usuario.click(await within(balao()).findByRole("button", { name: /Continuar/ }));
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("atividade por link", () => {
  it("a entrada mostra o aviso, dá um apelido trocável e confere o código da sala", async () => {
    const { usuario } = abrir(`#${codificarAtividade(ATIVIDADE)}`);
    for (const frase of AVISO) expect(screen.getByText(frase)).toBeInTheDocument();
    expect(AVISO).toEqual(["O professor vê suas respostas desta aula.", "Não pedimos seu nome.", "Você pode apagar tudo deste aparelho."]);
    expect(screen.getByRole("link", { name: /Para pais e responsáveis/ })).toHaveAttribute("href", "#/pais");
    expect(screen.queryByLabelText(/nome/i)).toBeNull(); // nenhum campo pede o nome

    await screen.findByText(APELIDOS[0], { selector: "strong" });
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    await usuario.click(screen.getByRole("button", { name: "Ver outros apelidos" }));
    await waitFor(() => expect(screen.getAllByRole("radio")).toHaveLength(8));
    await usuario.click(screen.getByRole("radio", { name: "Jabuti Anil 8" }));
    expect(screen.getByText("Jabuti Anil 8", { selector: "strong" })).toBeInTheDocument();

    // Nada fica guardado antes de entrar.
    expect(localStorage.length).toBe(0);
    await usuario.click(screen.getByRole("button", { name: /Começar/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("Digite o código da sala.");
    await usuario.type(screen.getByLabelText("Código da sala"), "XYZ9");
    await usuario.click(screen.getByRole("button", { name: /Começar/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("Esse não é o código desta sala. Confira com o professor.");
    expect(screen.getByLabelText("Código da sala")).toHaveFocus();
    expect(localStorage.length).toBe(0);

    await usuario.clear(screen.getByLabelText("Código da sala"));
    await usuario.type(screen.getByLabelText("Código da sala"), " k7px ");
    await usuario.click(screen.getByRole("button", { name: /Começar/ }));
    expect(await screen.findByText("Programa 1 de 2")).toBeInTheDocument();
    // O foco vai para o nome do programa, não se perde no body.
    const nomeDoPrograma = within(screen.getByRole("navigation", { name: "Programas da atividade" })).getByRole("heading", { level: 2 });
    await waitFor(() => expect(nomeDoPrograma).toHaveFocus());
    // 'Sair e apagar' fica num cabeçalho preso no alto da tela grande.
    expect(screen.getByRole("banner").className).toMatch(/lg:sticky/);
    expect(within(screen.getByRole("banner")).getByRole("button", { name: "Sair e apagar deste aparelho" })).toBeInTheDocument();
    expect(screen.getByText("Jabuti Anil 8", { selector: "strong" })).toBeInTheDocument();
    const sala = guardada()!;
    expect(sala).toMatchObject({ v: 1, sala: "K7PX", apelido: "Jabuti Anil 8" });
    expect(sala.sujeito).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    const [inicio] = await eventosGuardados((eventos) => eventos.length === 1);
    expect(inicio).toMatchObject({ tipo: "Session.Start", sala: "K7PX", sujeito: sala.sujeito, atividade: "aula3", programa: null, condicao: null, code_hash: null });
  });

  it("palpites viram eventos; o resumo põe as ideias antes dos números; a entrega baixa o arquivo; apagar limpa o aparelho", async () => {
    const { usuario, python } = abrir(`#${codificarAtividade(ATIVIDADE)}`);
    await entrar(usuario, "K7PX", "Lobo Verde 50");
    await screen.findByText("Programa 1 de 2");
    expect(screen.getByText("Aqui você dá palpites antes de ver cada passo.")).toBeInTheDocument();
    // O programa da atividade é só para ler.
    expect(document.querySelector(".cm-content")).toHaveAttribute("aria-readonly", "true");

    await rodarComPalpites(usuario, "Situação: aprovado", "Verdadeiro: entra no if");
    expect(python.pedidos.find((p) => p.acao === "rastrear")).toMatchObject({ dados: { semente: 7, entradas: [] } });
    await usuario.click(screen.getByRole("button", { name: "Próximo programa ▶" }));
    await screen.findByText("Programa do professor");
    expect(screen.getByRole("button", { name: "Programa 1: Decisão com if, já rodou" })).toBeInTheDocument();
    await rodarComPalpites(usuario, null, "8");

    const eventos = await eventosGuardados((lista) => lista.filter((e) => e.tipo === "Prediction").length === 3);
    const tipos = eventos.map((e) => e.tipo);
    expect(tipos[0]).toBe("Session.Start");
    expect(tipos.filter((t) => t === "Run.Program")).toHaveLength(2);
    const palpites = eventos.filter((e) => e.tipo === "Prediction");
    expect(palpites.map((e) => [e.programa, e.ponto, e.certa, e.concepcao ?? null])).toEqual([
      [0, "p1", true, null],
      [0, "p2", true, null],
      [1, "p1", false, "C03"],
    ]);
    for (const evento of eventos.filter((e) => e.programa !== null)) {
      expect(evento).toMatchObject({ condicao: "prever", atividade: "aula3" });
      expect(evento.code_hash).toMatch(/^[0-9a-f]{16}$/);
    }
    expect(eventos.filter((e) => e.programa === 0)[0].code_hash).not.toBe(eventos.filter((e) => e.programa === 1)[0].code_hash);
    // Nada de código, entradas, texto livre ou apelido nos eventos.
    const texto = JSON.stringify(eventos);
    for (const proibido of ["nota", "input", "Situação", "Lobo", "apelido", '"4"']) expect(texto).not.toContain(proibido);

    await usuario.click(screen.getByRole("button", { name: "Terminei: ver meu resumo" }));
    const janela = await screen.findByRole("dialog", { name: "Meu resumo" });
    await within(janela).findByText("O que você fez");
    const textoDaJanela = janela.textContent!;
    expect(textoDaJanela.indexOf("Ideias que você já entendeu")).toBeLessThan(textoDaJanela.indexOf("Ideias para revisar"));
    expect(textoDaJanela.indexOf("Ideias para revisar")).toBeLessThan(textoDaJanela.indexOf("O que você fez"));
    expect(textoDaJanela.indexOf(REGRAS.C05)).toBeGreaterThan(-1);
    expect(textoDaJanela.indexOf(REGRAS.C03)).toBeGreaterThan(textoDaJanela.indexOf("Ideias para revisar"));
    expect(textoDaJanela).not.toMatch(/C0\d/);
    expect(within(janela).getByText("Palpites que você deu: 3")).toBeInTheDocument();

    let baixado: Blob | null = null;
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: (blob: Blob) => ((baixado = blob), "blob:teste"), revokeObjectURL: () => {} }));
    const clique = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await usuario.click(within(janela).getByRole("button", { name: "Entregar ao professor" }));
    await within(janela).findByText("Pronto! O arquivo foi baixado.");
    expect(within(janela).getByText("pyvis-aula3-lobo-verde-50.json")).toBeInTheDocument();
    expect(clique).toHaveBeenCalledOnce();
    const entrega = lerEntrega(await baixado!.text())!;
    expect(entrega.apelido).toBe("Lobo Verde 50");
    expect(entrega.eventos).toEqual(guardada()!.eventos);

    await usuario.click(within(janela).getByRole("button", { name: "Sair e apagar deste aparelho" }));
    const confirmar = await screen.findByRole("alertdialog", { name: "Sair e apagar deste aparelho?" });
    expect(within(confirmar).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    await usuario.click(within(confirmar).getByRole("button", { name: "Sim, apagar" }));
    expect(await screen.findByText("Pronto! Nada desta sala ficou neste aparelho.")).toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(screen.queryByText("Lobo Verde 50")).toBeNull();
    // Entrar de novo começa do zero, com outro sujeito.
    await usuario.click(screen.getByRole("button", { name: "Entrar de novo" }));
    expect(await screen.findByText("Antes de começar")).toBeInTheDocument();
  });

  it("quem volta à página continua na sala, com uma sessão nova", async () => {
    guardar({ v: 1, sala: "K7PX", sujeito: SUJEITO, apelido: "Panda Cinza 21", atualizado: Date.now(), eventos: [] });
    const { usuario } = abrir(`#${codificarAtividade(ATIVIDADE)}`);
    expect(await screen.findByText("Programa 1 de 2")).toBeInTheDocument();
    expect(screen.queryByText("Antes de começar")).toBeNull();
    expect(screen.getByText("Panda Cinza 21")).toBeInTheDocument();
    const [inicio] = await eventosGuardados((eventos) => eventos.length === 1);
    expect(inicio).toMatchObject({ tipo: "Session.Start", sujeito: SUJEITO });
    // 'Sair e apagar' está no cabeçalho, com confirmação; cancelar não apaga.
    await usuario.click(screen.getByRole("button", { name: "Sair e apagar deste aparelho" }));
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(guardada()).not.toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Sair e apagar deste aparelho" }));
    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(guardada()).not.toBeNull();
  });

  it("no estudo, cada programa tem a sua condição, e o Assistir não pede palpites", async () => {
    const { usuario, python } = abrir(`#${codificarAtividade({ ...ATIVIDADE, modo: "estudo", programas: [{ ex: "ex2" }, { ex: "ex3" }] })}`);
    await entrar(usuario);
    await screen.findByText("Programa 1 de 2");
    expect(python.pedidos.find((p) => p.acao === "sortear_condicoes")).toMatchObject({ dados: { atividade: { modo: "estudo", id: "aula3" } } });
    expect(screen.getByText("Aqui você dá palpites antes de ver cada passo.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Próximo programa ▶" }));
    expect(screen.getByText("Aqui você assiste o programa passo a passo.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("total recebe 0: variável nova.", { selector: "p" });
    expect(document.querySelector("[data-balao='previsao']")).toBeNull();
    expect(python.pedidos.some((p) => p.acao === "preparar_atividade")).toBe(false);
    const eventos = await eventosGuardados((lista) => lista.some((e) => e.tipo === "Run.Program"));
    expect(eventos.find((e) => e.tipo === "Run.Program")).toMatchObject({ programa: 1, condicao: "assistir" });
  });

  it("um link sem sala aceita o código que o aluno digitar e passa a levar a sala", async () => {
    const { usuario } = abrir("#a=ex3&m=prever&f=alt");
    await entrar(usuario, "turma-8a");
    await screen.findByText("Programa 1 de 1");
    expect(guardada("TURMA-8A")).toMatchObject({ sala: "TURMA-8A" });
    expect(window.location.hash).toBe("#a=ex3&m=prever&f=alt&sala=TURMA-8A&id=ex3&s=0");
  });

  it("um aparelho que não deixa guardar avisa e a atividade segue na memória", async () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const { usuario } = abrir(`#${codificarAtividade(ATIVIDADE)}`);
    await entrar(usuario);
    expect(await screen.findByText(/Este aparelho não deixa guardar/)).toBeInTheDocument();
    await rodarComPalpites(usuario, "Situação: aprovado", "Verdadeiro: entra no if");
    await usuario.click(screen.getByRole("button", { name: "Meu resumo" }));
    const janela = await screen.findByRole("dialog", { name: "Meu resumo" });
    expect(await within(janela).findByText("Palpites que você deu: 2")).toBeInTheDocument();
  });

  it("apagar a sala em outra aba (a página dos pais) tira esta aba da sala", async () => {
    const { usuario } = abrir(`#${codificarAtividade(ATIVIDADE)}`);
    await entrar(usuario);
    await screen.findByText("Programa 1 de 2");
    const chave = PREFIXO + "K7PX";
    const antes = localStorage.getItem(chave);
    localStorage.removeItem(chave);
    act(() => window.dispatchEvent(new StorageEvent("storage", { key: chave, oldValue: antes, newValue: null })));
    expect(await screen.findByText("Os dados foram apagados em outra página.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Meu resumo" })).toBeNull();
  });

  it("um link quebrado diz o que houve e não abre nada", async () => {
    abrir("#a=ex99&m=prever");
    expect(screen.getByRole("alert")).toHaveTextContent("Este link de atividade não abriu.");
    expect(screen.getByRole("alert")).toHaveTextContent("o exemplo do programa 1 não existe");
    expect(localStorage.length).toBe(0);
  });
});

describe("fora de uma sala", () => {
  it("o uso livre não guarda nada e a limpeza ao abrir tira salas vencidas", async () => {
    guardar({ v: 1, sala: "VELHA", sujeito: SUJEITO, apelido: "Panda Cinza 21", atualizado: Date.now() - VALIDADE_MS - 1000, eventos: [] });
    guardar({ v: 1, sala: "NOVA", sujeito: SUJEITO, apelido: "Panda Cinza 21", atualizado: Date.now(), eventos: [] });
    const { usuario } = abrir("");
    await screen.findByText("Python pronto!");
    expect(localStorage.getItem(PREFIXO + "VELHA")).toBeNull();
    expect(localStorage.getItem(PREFIXO + "NOVA")).not.toBeNull();
    await usuario.selectOptions(screen.getByLabelText("Exemplos:"), "1");
    // A página abre no Prever: um palpite fora de uma sala também não deixa rastro.
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    expect(await screen.findByText("Antes de rodar")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: /Pular/ }));
    expect(Object.keys(localStorage)).toEqual([PREFIXO + "NOVA"]);

    await usuario.click(screen.getByRole("radio", { name: "Assistir" }));
    await usuario.click(screen.getByRole("button", { name: "▶ Executar" }));
    await screen.findByText("nota recebe 7: variável nova.", { selector: "p" });
    await usuario.keyboard("{ArrowRight}");
    expect(Object.keys(localStorage)).toEqual([PREFIXO + "NOVA"]);
  });

  it("uma atividade num arquivo abre pelo uso livre", async () => {
    const { usuario } = abrir("");
    const conteudo = JSON.stringify({ formato: "pyvis-atividade", v: 1, link: codificarAtividade(ATIVIDADE) });
    await usuario.upload(screen.getByLabelText("Abrir atividade de um arquivo"), new File([conteudo], "atividade-aula3.json", { type: "application/json" }));
    expect(await screen.findByText("Antes de começar")).toBeInTheDocument();
    expect(window.location.hash).toBe(`#${codificarAtividade(ATIVIDADE)}`);
  });

  it("um arquivo que não é de atividade é recusado", async () => {
    const { usuario } = abrir("");
    await usuario.upload(screen.getByLabelText("Abrir atividade de um arquivo"), new File(["{}"], "x.json", { type: "application/json" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Esse arquivo não é de uma atividade do PyVis.");
  });
});
