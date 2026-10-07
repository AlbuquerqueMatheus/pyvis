import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { previsoes, rastros } from "../testes/pythonFalso";
import type { Camada } from "../motor/palco";
import type { Correcao, Ponto, RespostaDoAluno } from "../motor/tipos";
import { BalaoPrevisao, RASCUNHO_VAZIO, type Rascunho } from "./BalaoPrevisao";
import { Controles } from "./Controles";
import { PainelDetetive } from "./PainelDetetive";
import { Variaveis } from "./Variaveis";

const FOR = previsoes.for.atividades;
const CONTA = previsoes.conta.atividades;

function correcaoDe(nome: string, formato: "alternativas" | "livre", ponto: string, resposta: RespostaDoAluno): Correcao {
  const gravada = previsoes[nome].correcoes.find(
    (c) => c.formato === formato && c.ponto === ponto && JSON.stringify(c.resposta) === JSON.stringify(resposta),
  );
  if (!gravada) throw new Error("sem correção gravada");
  return gravada.correcao;
}

type Extras = Partial<Parameters<typeof BalaoPrevisao>[0]>;

/** O balão com o rascunho guardado fora dele, como faz a página. */
function Balao({ ponto, ...extras }: { ponto: Ponto } & Extras) {
  const [rascunho, setRascunho] = useState<Rascunho>(RASCUNHO_VAZIO);
  return (
    <BalaoPrevisao
      ponto={ponto}
      correcao={null}
      inicial={false}
      aviso={null}
      ocupado={false}
      rascunho={rascunho}
      aoMudarRascunho={setRascunho}
      aoResponder={() => {}}
      aoPular={() => {}}
      aoContinuar={() => {}}
      atencao={0}
      {...extras}
    />
  );
}

/** Nenhum texto da tela mostra o id técnico de uma concepção. */
function semIdTecnico() {
  expect(document.body.textContent).not.toMatch(/\bC\d{2}\b/);
  expect(document.body.textContent).not.toMatch(/[a-z]+_[a-z]+_[a-z]+/);
}

describe("BalaoPrevisao com alternativas", () => {
  const p3 = FOR.alternativas.pontos[1];

  it("abre com o foco no balão (as setas não marcam nada); teclas 1 a 4 escolhem e Enter confirma", async () => {
    const aoResponder = vi.fn();
    render(<Balao ponto={p3} aoResponder={aoResponder} />);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(4);
    expect(screen.getByRole("dialog")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();

    const usuario = userEvent.setup();
    // Por hábito, o aluno aperta as setas da linha do tempo: nenhuma opção fica marcada.
    await usuario.keyboard("{ArrowRight}{ArrowRight}");
    for (const radio of radios) expect(radio).not.toBeChecked();
    await usuario.keyboard("3");
    expect(radios[2]).toBeChecked();
    expect(radios[2]).toHaveFocus();
    await usuario.keyboard("9"); // não existe: nada muda
    expect(radios[2]).toBeChecked();
    await usuario.keyboard("{Enter}");
    expect(aoResponder).toHaveBeenCalledWith({ alternativa: p3.alternativas![2].id });
  });

  it("a escolhida tem marca em texto (● e ○), não só cor", async () => {
    render(<Balao ponto={p3} />);
    await userEvent.setup().keyboard("2");
    const marcada = screen.getAllByRole("radio")[1].closest("label")!;
    expect(marcada).toHaveTextContent("●");
    expect(screen.getAllByRole("radio")[0].closest("label")).toHaveTextContent("○");
  });

  it("Pular está sempre à vista", async () => {
    const aoPular = vi.fn();
    render(<Balao ponto={p3} aoPular={aoPular} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Pular" }));
    expect(aoPular).toHaveBeenCalledOnce();
  });

  it("o retorno certo traz ✓ e o motivo; o foco vai para Continuar", () => {
    const certa = correcaoDe("for", "alternativas", "p3", { alternativa: "p3a2" });
    render(<Balao ponto={p3} correcao={certa} />);
    expect(screen.getByRole("status")).toHaveTextContent("✓ Certo!");
    expect(screen.getByRole("status")).toHaveTextContent(certa.mensagem);
    expect(screen.getByRole("button", { name: "Continuar" })).toHaveFocus();
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.queryByRole("button", { name: "Pular" })).toBeNull();
  });

  it("o retorno diferente diz o palpite e o que o Python guardou, e traz o Detetive", () => {
    const errada = correcaoDe("for", "alternativas", "p2", { alternativa: "p2a1" });
    render(<Balao ponto={FOR.alternativas.pontos[0]} correcao={errada} detetive={<p>detetive aqui</p>} />);
    expect(screen.getByRole("status")).toHaveTextContent("✗ Não foi isso.");
    expect(screen.getByRole("status")).toHaveTextContent("Seu palpite: 5. O laço deu 4 voltas.");
    expect(screen.getByText("detetive aqui")).toBeInTheDocument();
    semIdTecnico();
  });

  it("quando o aluno tenta passar, o foco volta para a pergunta", () => {
    const { rerender } = render(<Balao ponto={p3} atencao={0} />);
    screen.getByRole("dialog").blur();
    expect(document.body).toHaveFocus();
    rerender(<Balao ponto={p3} atencao={1} />);
    expect(screen.getByRole("dialog")).toHaveFocus();
  });
});

describe("BalaoPrevisao com resposta livre", () => {
  const b = CONTA.livre.pontos[0];

  it("valor: dois botões grandes, 'número' e 'texto' (com aspas sozinho)", async () => {
    const aoResponder = vi.fn();
    render(<Balao ponto={b} aoResponder={aoResponder} />);
    const campo = screen.getByLabelText("Seu palpite");
    expect(campo).toHaveFocus();
    expect(screen.getByRole("button", { name: /^número/ })).toBeDisabled();
    const usuario = userEvent.setup();
    await usuario.keyboard("44");
    expect(screen.getByRole("button", { name: /^número/ })).toHaveTextContent("44");
    expect(screen.getByRole("button", { name: /^texto/ })).toHaveTextContent('"44"');
    // As teclas de número escrevem no campo, não escolhem nada.
    expect(campo).toHaveValue("44");
    await usuario.click(screen.getByRole("button", { name: /^texto/ }));
    expect(aoResponder).toHaveBeenLastCalledWith({ texto: "44", tipo_escolhido: "texto" });
    await usuario.click(screen.getByRole("button", { name: /^número/ }));
    expect(aoResponder).toHaveBeenLastCalledWith({ texto: "44", tipo_escolhido: "numero" });
  });

  it("um aviso aparece na região viva e o campo volta a ter foco", () => {
    const { rerender } = render(<Balao ponto={b} aviso={null} />);
    screen.getByLabelText("Seu palpite").blur();
    rerender(<Balao ponto={b} aviso="Isso não parece um número. Confira ou escolha texto." />);
    expect(screen.getByRole("status")).toHaveTextContent("⚠ Isso não parece um número.");
    expect(screen.getByLabelText("Seu palpite")).toHaveFocus();
  });

  it("voltas: Enter confirma", async () => {
    const aoResponder = vi.fn();
    render(<Balao ponto={FOR.livre.pontos[0]} aoResponder={aoResponder} />);
    await userEvent.setup().keyboard("5{Enter}");
    expect(aoResponder).toHaveBeenCalledWith({ texto: "5" });
  });

  it("o palpite antes de rodar aceita várias linhas (Shift+Enter) e Enter confirma", async () => {
    const aoResponder = vi.fn();
    render(<Balao ponto={previsoes.while.atividades.livre.palpite_inicial!} inicial aoResponder={aoResponder} />);
    expect(screen.getByText("Antes de rodar")).toBeInTheDocument();
    await userEvent.setup().keyboard("Energia: 3{Shift>}{Enter}{/Shift}Energia: 2{Enter}");
    expect(aoResponder).toHaveBeenCalledWith({ texto: "Energia: 3\nEnergia: 2" });
  });
});

describe("PainelDetetive", () => {
  const p2 = FOR.alternativas.pontos[0];
  const comModelo = correcaoDe("for", "alternativas", "p2", { alternativa: "p2a1" });

  function Detetive(props: { ponto: Ponto; correcao: Correcao; oferecerMeMostra?: boolean; narracao?: string; ondeAdiante?: boolean; aoAbrir?: (camada: Camada) => void }) {
    const [camadas, setCamadas] = useState<Camada[]>([]);
    return (
      <PainelDetetive
        ponto={props.ponto}
        correcao={props.correcao}
        camadas={camadas}
        oferecerMeMostra={props.oferecerMeMostra ?? false}
        destacar="numero"
        narracao={props.narracao}
        ondeAdiante={props.ondeAdiante}
        aoAbrir={(camada) => {
          props.aoAbrir?.(camada);
          setCamadas((antes) => [...antes, camada]);
        }}
      />
    );
  }

  it("com modelo: a ideia provável e três camadas que abrem quando o aluno pede", async () => {
    const aoAbrir = vi.fn();
    render(<Detetive ponto={p2} correcao={comModelo} aoAbrir={aoAbrir} />);
    expect(screen.getByText(/Será que você pensou que o/)).toBeInTheDocument();
    expect(screen.getAllByText("range(1, 5)", { selector: "code" })[0]).toBeVisible();
    const botoes = ["Onde olhar", "A regra", "Me mostra"].map((nome) => screen.getByRole("button", { name: nome }));
    for (const botao of botoes) expect(botao).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(/Olhe a caixinha/)).not.toBeVisible();

    const usuario = userEvent.setup();
    await usuario.click(botoes[0]);
    expect(aoAbrir).toHaveBeenLastCalledWith(1);
    expect(botoes[0]).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/Olhe a caixinha/)).toBeVisible();
    await usuario.click(botoes[1]);
    expect(screen.getByText(/nunca entra/)).toBeVisible();
    await usuario.click(botoes[2]);
    expect(screen.getByText(/O laço dá 4 voltas/)).toBeVisible();
    semIdTecnico();
  });

  it("sem modelo: diz que não sabe, sem 'A regra' e sem inventar uma ideia", () => {
    const semModelo = correcaoDe("for", "alternativas", "p2", { alternativa: "p2a3" });
    expect(semModelo.feedback).toBeNull();
    render(<Detetive ponto={p2} correcao={semModelo} />);
    expect(screen.getByText("Não sei bem o que levou a esse palpite.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "A regra" })).toBeNull();
    expect(screen.getByRole("button", { name: "Onde olhar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Me mostra" })).toBeInTheDocument();
    expect(screen.queryByText(/Será que/)).toBeNull();
    semIdTecnico();
  });

  it("sem modelo, a camada 2 é a frase longa do narrador", async () => {
    const semModelo = correcaoDe("for", "alternativas", "p2", { alternativa: "p2a3" });
    render(<Detetive ponto={p2} correcao={semModelo} narracao="O for pega um valor de cada vez, de 1 até 4." />);
    await userEvent.setup().click(screen.getByRole("button", { name: "A regra" }));
    expect(screen.getByText("O for pega um valor de cada vez, de 1 até 4.")).toBeVisible();
    expect(screen.queryByText(/Será que/)).toBeNull();
  });

  it("'Onde olhar' que fica depois de outra pergunta diz que vem depois", async () => {
    render(<Detetive ponto={p2} correcao={comModelo} ondeAdiante />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Onde olhar" }));
    expect(screen.getByText("Você vai ver isso no fim do laço, depois da próxima pergunta.")).toBeVisible();
    expect(screen.queryByText(/Olhe a caixinha/)).toBeNull();
  });

  it("depois de dois palpites diferentes, oferece 'Me mostra' sem custo", async () => {
    render(<Detetive ponto={p2} correcao={comModelo} oferecerMeMostra />);
    expect(screen.getByText("Tudo bem ver o passo resolvido.")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Me mostra" }));
    expect(screen.queryByText("Tudo bem ver o passo resolvido.")).toBeNull();
  });
});

describe("Variaveis no modo Prever", () => {
  const { passos } = rastros.for.resultado;

  it("uma caixinha animada no máximo, mesmo com duas mudanças", () => {
    const troca = rastros.troca.resultado.passos;
    // Depois de 'a, b = b, a' as duas mudam no mesmo passo.
    const mudou = (i: number, nome: string) => nome in troca[i - 1].globais && troca[i - 1].globais[nome].h !== troca[i].globais[nome]?.h;
    const k = troca.findIndex((_, i) => i > 0 && mudou(i, "a") && mudou(i, "b"));
    expect(k).toBeGreaterThan(0);
    render(<Variaveis variaveis={troca[k].globais} anteriores={troca[k - 1].globais} />);
    expect(screen.getAllByText("mudou")).toHaveLength(2);
    expect(document.querySelectorAll("[data-destaque-animado]")).toHaveLength(1);
  });

  it("animada={null} desliga a animação, mas o texto 'mudou' fica", () => {
    render(<Variaveis variaveis={passos[3].globais} anteriores={passos[2].globais} animada={null} />);
    expect(screen.getByText("mudou")).toBeInTheDocument();
    expect(document.querySelector("[data-destaque-animado]")).toBeNull();
  });

  it("o contorno do Detetive vem com texto 'olhe aqui'", () => {
    render(<Variaveis variaveis={passos[3].globais} contorno="numero" />);
    const caixa = document.querySelector("[data-contorno]")!;
    expect(caixa).toHaveAttribute("data-variavel", "numero");
    expect(caixa).toHaveTextContent("olhe aqui");
  });

  it("uma variável que a linha vai criar aparece só com '?'", () => {
    render(<Variaveis variaveis={passos[0].globais} ocultas={new Set(["total"])} />);
    expect(document.querySelector("[data-variavel='total']")).toHaveTextContent("?");
    expect(screen.getByText("valor depois desta linha: é o seu palpite")).toBeInTheDocument();
  });
});

describe("Controles com autoplay", () => {
  it("Tocar e Pausar, com aria-pressed", async () => {
    const aoTocar = vi.fn();
    const { rerender } = render(<Controles passo={3} total={12} fim={false} volta={null} irPara={() => {}} tocando={false} aoTocar={aoTocar} />);
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: /Tocar/ }));
    expect(aoTocar).toHaveBeenLastCalledWith(true);
    rerender(<Controles passo={3} total={12} fim={false} volta={null} irPara={() => {}} tocando aoTocar={aoTocar} />);
    expect(screen.getByRole("button", { name: /Pausar/ })).toHaveAttribute("aria-pressed", "true");
    await usuario.click(screen.getByRole("button", { name: /Pausar/ }));
    expect(aoTocar).toHaveBeenLastCalledWith(false);
  });

  it("sem aoTocar não há botão de tocar (Assistir sem autoplay continua igual)", () => {
    render(<Controles passo={3} total={12} fim={false} volta={null} irPara={() => {}} />);
    expect(screen.queryByRole("button", { name: /Tocar/ })).toBeNull();
  });
});
