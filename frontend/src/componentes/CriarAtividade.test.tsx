import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { EXEMPLOS } from "../exemplos";
import { LIMITE_DO_CHAT, PADRAO_SALA, lerArquivoDaAtividade, lerAtividade } from "../sala/link";

function abrirCriar() {
  window.history.replaceState(null, "", "/#/criar");
  // A tela do professor não carrega o Python.
  const criarCanal = vi.fn(() => {
    throw new Error("não devia carregar o Python");
  });
  render(<App criarCanal={criarCanal} />);
  return { criarCanal, usuario: userEvent.setup() };
}

const campoDoLink = () => screen.getByLabelText<HTMLTextAreaElement>("Link da atividade");

function atividadeDoLink() {
  const link = campoDoLink().value;
  const resultado = lerAtividade(link.slice(link.indexOf("#")));
  if (resultado.tipo !== "atividade") throw new Error(`link inválido: ${link}`);
  return resultado.atividade;
}

async function escreverCodigo(numero: number, codigo: string) {
  const grupo = screen.getByRole("group", { name: `Código do programa ${numero}` });
  const view = (await import("@codemirror/view")).EditorView.findFromDOM(grupo.querySelector(".cm-content") as HTMLElement)!;
  act(() => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: codigo } }));
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

describe("criar atividade (professor)", () => {
  it("monta o link dos exemplos pelo id, com sala sorteada e nome do dia", async () => {
    const { usuario, criarCanal } = abrirCriar();
    expect(document.title).toMatch(/Criar atividade/);
    expect(screen.getByText("Escolha pelo menos um programa.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Link da atividade")).toBeNull();

    await usuario.click(screen.getByRole("button", { name: "+ Adicionar exemplo" }));
    await usuario.selectOptions(screen.getByLabelText("Exemplo"), "ex7");
    await usuario.click(screen.getByRole("button", { name: "+ Adicionar exemplo" }));
    const link = campoDoLink().value;
    expect(link).toMatch(/^http:\/\/localhost(:\d+)?\/#a=ex3,ex7&m=prever&f=alt&sala=[A-Z0-9]{4}&id=aula-\d{4}&s=\d+$/);
    const atividade = atividadeDoLink();
    expect(atividade.sala).toMatch(PADRAO_SALA);
    expect(screen.getByRole("link", { name: /Abrir como aluno/ })).toHaveAttribute("href", link);
    expect(screen.getByText(`${link.length} caracteres`)).toBeInTheDocument();
    expect(screen.getByText(atividade.sala, { selector: "strong" })).toBeInTheDocument();

    // As entradas do exemplo só vão no link quando o professor as troca.
    const entradas = screen.getByRole("textbox", { name: "Respostas para o input() (uma por linha)" });
    expect(entradas).toHaveValue(EXEMPLOS[6].entradas);
    await usuario.clear(entradas);
    await usuario.type(entradas, "Lua{Enter}2");
    expect(atividadeDoLink().programas).toEqual([{ ex: "ex3" }, { ex: "ex7", entradas: ["Lua", "2"] }]);

    await usuario.click(screen.getByRole("button", { name: "Subir o programa 2" }));
    expect(atividadeDoLink().programas.map((p) => ("ex" in p ? p.ex : "?"))).toEqual(["ex7", "ex3"]);
    await usuario.click(screen.getByRole("button", { name: "Tirar o programa 1" }));
    expect(atividadeDoLink().programas).toEqual([{ ex: "ex3" }]);
    expect(criarCanal).not.toHaveBeenCalled();
  });

  it("modo, estudo, formato, sala e nome vão para o link; valores errados viram avisos", async () => {
    const { usuario } = abrirCriar();
    await usuario.click(screen.getByRole("button", { name: "+ Adicionar exemplo" }));

    await usuario.click(screen.getByRole("radio", { name: "Assistir" }));
    expect(atividadeDoLink().modo).toBe("assistir");
    // Em Assistir não há perguntas para escolher.
    expect(screen.queryByRole("radio", { name: /Resposta livre/ })).toBeNull();

    await usuario.click(screen.getByRole("checkbox", { name: /Atividade do estudo/ }));
    expect(screen.getByText("Com um programa só, o sorteio decide se ele é Prever ou Assistir.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Prever" })).toBeDisabled();
    await usuario.click(screen.getByRole("radio", { name: /Resposta livre/ }));
    expect(atividadeDoLink()).toMatchObject({ modo: "estudo", formato: "livre" });
    expect(campoDoLink().value).toContain("&m=estudo&f=livre&");

    const sala = screen.getByLabelText<HTMLInputElement>("Código da sala");
    await usuario.clear(sala);
    await usuario.type(sala, "8a turma");
    expect(sala).toHaveValue("8ATURMA");
    expect(atividadeDoLink().sala).toBe("8ATURMA");
    await usuario.clear(sala);
    await usuario.type(sala, "x");
    expect(screen.getByText("O código da sala precisa de 2 a 16 letras, números ou hífen.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Link da atividade")).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Sortear outro" }));
    expect(sala.value).toMatch(PADRAO_SALA);

    const nome = screen.getByLabelText("Nome da atividade");
    await usuario.clear(nome);
    await usuario.type(nome, "aula ção");
    expect(nome).toHaveValue("aulação");
    expect(screen.getByText(/O nome da atividade usa só letras sem acento/)).toBeInTheDocument();
    await usuario.clear(nome);
    await usuario.type(nome, "revisao_if");
    expect(atividadeDoLink().id).toBe("revisao_if");

    const semente = screen.getByLabelText("Semente dos sorteios");
    await usuario.clear(semente);
    await usuario.type(semente, "-3");
    expect(screen.getByText(/A semente é um número inteiro/)).toBeInTheDocument();
    await usuario.clear(semente);
    await usuario.type(semente, "42");
    expect(atividadeDoLink().semente).toBe(42);
  });

  it("código próprio vai comprimido; link longo sugere mandar como arquivo", async () => {
    const { usuario } = abrirCriar();
    await usuario.click(screen.getByRole("button", { name: "+ Escrever código próprio" }));
    expect(screen.getByText("O programa 1 está vazio.")).toBeInTheDocument();
    await escreverCodigo(1, 'nome = input("Nome? ")\nprint("Oi,", nome)\n');
    await usuario.type(screen.getByRole("textbox", { name: "Respostas para o input() (uma por linha)" }), "Bia");
    expect(campoDoLink().value).toMatch(/#c=[^&]+&m=prever&f=alt&/);
    expect(campoDoLink().value).not.toContain("input");
    expect(atividadeDoLink().programas).toEqual([{ codigo: 'nome = input("Nome? ")\nprint("Oi,", nome)\n', entradas: ["Bia"] }]);
    expect(screen.queryByText(/O link é longo/)).toBeNull();

    // Todos os exemplos num programa só: o link passa do que cabe no chat.
    await escreverCodigo(1, EXEMPLOS.map((exemplo) => exemplo.codigo).join("\n"));
    expect(campoDoLink().value.length).toBeGreaterThan(LIMITE_DO_CHAT);
    expect(screen.getByText("O link é longo e pode não caber no chat do Meet.")).toBeInTheDocument();
    let baixado: Blob | null = null;
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: (blob: Blob) => ((baixado = blob), "blob:teste"), revokeObjectURL: () => {} }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await usuario.click(screen.getByRole("button", { name: "Baixar arquivo da atividade" }));
    expect(lerArquivoDaAtividade(await baixado!.text())).toEqual({ tipo: "atividade", atividade: atividadeDoLink() });
    vi.unstubAllGlobals();
  });

  it("copiar o link avisa; sem permissão, deixa o link selecionado", async () => {
    const { usuario } = abrirCriar();
    await usuario.click(screen.getByRole("button", { name: "+ Adicionar exemplo" }));
    const escrever = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    await usuario.click(screen.getByRole("button", { name: "Copiar link" }));
    expect(escrever).toHaveBeenCalledWith(campoDoLink().value);
    expect(await screen.findByText("✓ Link copiado.")).toBeInTheDocument();

    escrever.mockRejectedValue(new Error("negado"));
    await usuario.click(screen.getByRole("button", { name: "Copiar link" }));
    expect(await screen.findByText(/Não deu para copiar sozinho/)).toBeInTheDocument();
    const campo = campoDoLink();
    expect([campo.selectionStart, campo.selectionEnd]).toEqual([0, campo.value.length]);
  });

  it("lembra o professor de não pôr nomes de alunos no código nem no nome da atividade", () => {
    abrirCriar();
    const main = screen.getByRole("main");
    expect(within(main).getByText("Não coloque nomes de alunos no código: quem abre o link vê o código.")).toBeInTheDocument();
    expect(within(main).getByText("Vai em cada resposta e no arquivo de entrega. Sem nomes de alunos.")).toBeInTheDocument();
  });
});
