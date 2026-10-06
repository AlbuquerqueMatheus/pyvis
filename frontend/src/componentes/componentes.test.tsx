import { describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import rastrosJson from "../testes/rastros.json";
import { CENA_VAZIA, NADA_RESPONDIDO, pilulaDaVolta } from "../motor/cena";
import type { AtividadeLink, Resultado, Resumo } from "../motor/tipos";
import type { Motor } from "../motor/useMotor";
import { CaixaErro } from "./CaixaErro";
import { Controles } from "./Controles";
import { Editor } from "./Editor";
import { Escolha } from "./Escolha";
import { UsoLivre } from "./UsoLivre";
import { pythonFalso } from "../testes/pythonFalso";
import { MeuResumo, TITULO_ENTENDIDAS } from "./MeuResumo";
import { Narracao } from "./Narracao";
import { Variaveis } from "./Variaveis";

const rastros = rastrosJson as unknown as Record<string, { resultado: Resultado }>;

describe("Variaveis", () => {
  it("mostra o valor antigo riscado, com texto, quando a caixinha muda", () => {
    const { passos } = rastros.for.resultado;
    // Passo 4 (cabeçalho do for): total acabou de mudar de 0 para 1.
    render(<Variaveis variaveis={passos[3].globais} anteriores={passos[2].globais} />);
    const antigo = document.querySelector("[data-variavel='total'] del");
    expect(antigo).toHaveTextContent("antes era 0");
    expect(screen.getByText("mudou")).toBeInTheDocument();
    // numero continua 1 até o for rodar de novo; nenhuma está nova.
    expect(document.querySelector("[data-variavel='numero'] del")).toBeNull();
    expect(document.querySelectorAll("del")).toHaveLength(1);
    expect(screen.queryByText("nova")).toBeNull();
  });

  it("marca a variável nova com texto e não risca nada", () => {
    const { passos } = rastros.for.resultado;
    render(<Variaveis variaveis={passos[1].globais} anteriores={passos[0].globais} />);
    expect(screen.getByText("nova")).toBeInTheDocument();
    expect(document.querySelector("del")).toBeNull();
  });

  it("sem passo anterior não marca nada", () => {
    const { passos } = rastros.for.resultado;
    render(<Variaveis variaveis={passos[2].globais} />);
    expect(screen.queryByText("nova")).toBeNull();
    expect(screen.queryByText("mudou")).toBeNull();
  });

  it("compara pelo resumo h, não pelo valor inteiro", () => {
    const valor = { tipo: "int", valor: "1", h: "aaaa" };
    const { rerender } = render(<Variaveis variaveis={{ x: valor }} anteriores={{ x: { ...valor, valor: "outro texto" } }} />);
    expect(document.querySelector("del")).toBeNull();
    rerender(<Variaveis variaveis={{ x: valor }} anteriores={{ x: { ...valor, h: "bbbb" } }} />);
    expect(document.querySelector("del")).not.toBeNull();
  });

  it("mostra texto com aspas duplas, como o narrador e as perguntas", () => {
    const valor = (repr: string) => ({ tipo: "str", valor: repr, h: repr });
    render(
      <Variaveis
        variaveis={{
          nome: valor("'Ana'"),
          fala: valor(`'Diga "oi"'`),
          lista: { tipo: "list", itens: [valor("'a'"), { tipo: "int", valor: "1", h: "1" }], cortado: true, h: "l" },
        }}
      />,
    );
    expect(document.querySelector("[data-variavel='nome']")).toHaveTextContent('"Ana"');
    // Com aspas duplas dentro, fica o repr do Python (que não precisa de barra).
    expect(document.querySelector("[data-variavel='fala']")).toHaveTextContent(`'Diga "oi"'`);
    const lista = document.querySelector("[data-variavel='lista']")!;
    expect(lista).toHaveTextContent('"a"');
    expect(lista).toHaveTextContent("… e mais itens");
  });

  it("uma variável escondida pelo palpite vira '?' sem tipo nem valor antigo", () => {
    const { passos } = rastros.for.resultado;
    render(<Variaveis variaveis={passos[3].globais} anteriores={passos[2].globais} ocultas={new Set(["total"])} />);
    const caixa = document.querySelector("[data-variavel='total']")!;
    expect(caixa).toHaveTextContent("?");
    expect(caixa).not.toHaveTextContent("inteiro");
    expect(caixa.querySelector("del")).toBeNull();
  });
});

describe("Controles", () => {
  const { resultado } = rastros.for;
  const comandos = resultado.estrutura.comandos;

  it("mostra a pílula da volta, com o total só quando visível", () => {
    const volta = pilulaDaVolta(resultado.passos[3], comandos, { respondidos: NADA_RESPONDIDO, alcancado: 3 });
    const { rerender } = render(<Controles passo={3} total={12} fim={false} volta={volta} irPara={() => {}} />);
    expect(screen.getByText(/volta 2$/)).toBeInTheDocument();
    const comTotal = pilulaDaVolta(resultado.passos[3], comandos, { respondidos: NADA_RESPONDIDO, alcancado: 11 });
    rerender(<Controles passo={3} total={12} fim={false} volta={comTotal} irPara={() => {}} />);
    expect(screen.getByText(/volta 2 de 4/)).toBeInTheDocument();
  });

  it("as setas do teclado andam, mas não dentro de um campo de texto", async () => {
    const irPara = vi.fn();
    render(
      <>
        <textarea aria-label="campo" />
        <Controles passo={3} total={12} fim={false} volta={null} irPara={irPara} />
      </>,
    );
    const usuario = userEvent.setup();
    await usuario.keyboard("{ArrowRight}");
    expect(irPara).toHaveBeenLastCalledWith(4);
    await usuario.keyboard("{ArrowLeft}");
    expect(irPara).toHaveBeenLastCalledWith(2);
    irPara.mockClear();
    await usuario.click(screen.getByLabelText("campo"));
    await usuario.keyboard("{ArrowRight}");
    expect(irPara).not.toHaveBeenCalled();
  });

  it("os botões têm alvo de toque de 44 px", () => {
    render(<Controles passo={3} total={12} fim={false} volta={null} irPara={() => {}} />);
    for (const botao of screen.getAllByRole("button")) expect(botao.className).toMatch(/min-h-11/);
  });
});

describe("Narracao", () => {
  const { resultado } = rastros.if_else;

  it("mostra a frase curta e a longa em 'Mais detalhes'", async () => {
    render(<Narracao passo={resultado.passos[1]} revelacao={{ respondidos: NADA_RESPONDIDO, alcancado: 1 }} movimento={0} />);
    expect(screen.getByText("nota >= 6? 7 >= 6, Verdadeiro: entra no if.")).toBeInTheDocument();
    const botao = screen.getByRole("button", { name: "Mais detalhes" });
    expect(botao).toHaveAttribute("aria-expanded", "false");
    await userEvent.setup().click(botao);
    expect(screen.getByText(/O if testa nota >= 6/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menos detalhes" })).toHaveAttribute("aria-expanded", "true");
  });

  it("com o palpite pendente não mostra o desfecho", () => {
    const passo = { ...resultado.passos[1], depende_de: { "decisao.valor": ["p1"] } };
    render(<Narracao passo={passo} revelacao={{ respondidos: NADA_RESPONDIDO, alcancado: 4 }} movimento={0} />);
    expect(screen.getByText("nota >= 6? 7 >= 6")).toBeInTheDocument();
    expect(screen.queryByText(/Verdadeiro/)).toBeNull();
  });

  it("o leitor de tela só ouve a frase quando o aluno anda", () => {
    const revelacao = { respondidos: NADA_RESPONDIDO, alcancado: 2 };
    const { rerender } = render(<Narracao passo={resultado.passos[1]} revelacao={revelacao} movimento={0} />);
    const anuncio = document.querySelector("[aria-live='polite']")!;
    expect(anuncio).toHaveTextContent("");
    act(() => rerender(<Narracao passo={resultado.passos[2]} revelacao={revelacao} movimento={1} />));
    expect(anuncio).toHaveTextContent('resultado recebe "aprovado": variável nova.');
    // Uma revelação sem movimento não fala de novo.
    act(() => rerender(<Narracao passo={resultado.passos[1]} revelacao={revelacao} movimento={1} />));
    expect(anuncio).toHaveTextContent('resultado recebe "aprovado": variável nova.');
  });
});

describe("CaixaErro", () => {
  it("mostra a mensagem curta com o código marcado, e o resto em 'Mais detalhes'", () => {
    render(
      <CaixaErro
        erro={{
          tipo: "NameError",
          linha: 2,
          mensagem: "`bonu` ainda não existe. Você quis dizer `bonus`?",
          detalhe: "Confira se o nome está escrito igualzinho.",
          original: "NameError: name 'bonu' is not defined",
        }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Problema na linha 2");
    // As crases viram código: o aluno não vê a crase solta.
    expect(screen.getByText("bonu", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).not.toHaveTextContent("`");
    const mais = screen.getByText("Mais detalhes");
    expect(mais.closest("details")).not.toHaveAttribute("open");
    expect(mais.closest("details")).toHaveTextContent("Confira se o nome");
    expect(mais.closest("details")).toHaveTextContent("Mensagem original do Python");
  });
});

describe("MeuResumo", () => {
  const atividade: AtividadeLink = { v: 1, id: "aula3", programas: [], modo: "prever", formato: "alternativas", sala: "ABC123", semente: 1 };
  const sala = { v: 1 as const, sala: "ABC123", sujeito: "s1", apelido: "Tucano Azul 7", atualizado: 0, eventos: [] };
  const comResumo = (resumo: Resumo) => vi.fn(async () => resumo) as unknown as Motor["pedir"];

  it("acertos sem regra por trás não viram 'nenhuma ideia entendida'", async () => {
    const pedir = comResumo({ entendidas: [], revisar: [], numeros: { programas: 2, palpites: 3, pulados: 0, explicacoes: 0 } });
    render(<MeuResumo atividade={atividade} sala={sala} pedir={pedir} aoVoltar={() => {}} aoApagar={() => {}} />);
    const entendidas = (await screen.findByRole("heading", { name: TITULO_ENTENDIDAS })).closest("section")!;
    expect(entendidas).toHaveTextContent("As ideias aparecem aqui quando um palpite mostra uma regra do Python.");
    expect(entendidas).not.toHaveTextContent(/nenhuma/i);
  });

  it("sem palpites, convida a dar palpites", async () => {
    const pedir = comResumo({ entendidas: [], revisar: [], numeros: { programas: 1, palpites: 0, pulados: 0, explicacoes: 0 } });
    render(<MeuResumo atividade={atividade} sala={sala} pedir={pedir} aoVoltar={() => {}} aoApagar={() => {}} />);
    expect(await screen.findByText("As ideias aparecem quando você dá palpites.")).toBeInTheDocument();
  });
});

describe("Editor", () => {
  it("o Tab sai do editor e não mexe no código", async () => {
    const aoMudar = vi.fn();
    render(
      <>
        <Editor codigo={'nome = "Ana"\nprint(nome)'} aoMudar={aoMudar} cena={CENA_VAZIA} />
        <button type="button">Executar</button>
      </>,
    );
    const conteudo = document.querySelector<HTMLElement>(".cm-content")!;
    conteudo.focus();
    const usuario = userEvent.setup();
    await usuario.tab();
    expect(aoMudar).not.toHaveBeenCalled();
    expect(conteudo).toHaveTextContent('nome = "Ana"');
    expect(screen.getByRole("button", { name: "Executar" })).toHaveFocus();
  });
});

describe("alvos de toque de 44 px (min-h-11)", () => {
  it("as chaves de escolha e os links do cabeçalho do uso livre", () => {
    render(<UsoLivre criarCanal={pythonFalso().criar} />);
    const links = within(screen.getByRole("navigation", { name: "Outras páginas" }));
    for (const link of links.getAllByRole("link")) expect(link.className).toMatch(/min-h-11/);
    expect(links.getByText("Abrir atividade de um arquivo").className).toMatch(/min-h-11/);
    for (const opcao of screen.getAllByRole("radio")) expect(opcao.closest("label")!.className).toMatch(/min-h-11/);
  });

  it("Escolha sozinha", () => {
    render(<Escolha legenda="Modo:" opcoes={[{ valor: "a", rotulo: "A" }, { valor: "b", rotulo: "B" }]} valor="a" aoMudar={() => {}} />);
    for (const opcao of screen.getAllByRole("radio")) expect(opcao.closest("label")!.className).toMatch(/min-h-11/);
  });
});
