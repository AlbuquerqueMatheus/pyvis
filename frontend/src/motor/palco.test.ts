import { describe, expect, it } from "vitest";
import { previsoes, rastros } from "../testes/pythonFalso";
import {
  PALCO_VAZIO,
  balaoDoPalco,
  comAspas,
  destinoPermitido,
  ondeOlhar,
  palco,
  passoResolvido,
  pontoPendente,
  trechosDeCodigo,
  type AcaoDoPalco,
  type EstadoDoPalco,
} from "./palco";
import { aplicarAtividade } from "./revelacao";
import type { Atividade, Correcao } from "./tipos";

function execucaoDe(nome: string, formato: "alternativas" | "livre" = "alternativas") {
  const atividade = previsoes[nome].atividades[formato];
  return { resultado: aplicarAtividade(rastros[nome].resultado, atividade), atividade };
}

function correcaoDe(nome: string, ponto: string, resposta: object, formato: "alternativas" | "livre" = "alternativas"): Correcao {
  const gravada = previsoes[nome].correcoes.find(
    (c) => c.formato === formato && c.ponto === ponto && JSON.stringify(c.resposta) === JSON.stringify(resposta),
  );
  if (!gravada) throw new Error(`sem correção gravada: ${nome} ${ponto} ${JSON.stringify(resposta)}`);
  return gravada.correcao;
}

const alternativa = (atividade: Atividade, ponto: string, texto: string) => {
  const achado = [...atividade.pontos, atividade.palpite_inicial!].find((p) => p.id === ponto)!;
  return { alternativa: achado.alternativas!.find((a) => a.texto === texto)!.id };
};

function rodar(acoes: AcaoDoPalco[], inicio: EstadoDoPalco = PALCO_VAZIO) {
  return acoes.reduce(palco, inicio);
}

// O for: palpite inicial (saída), p2 voltas no passo 1, p3 valor no 4, p4 valor no 7; 12 passos.
// (O print do fim é a mesma pergunta do palpite inicial: não vira ponto.)
const FOR = execucaoDe("for");
const ATIVIDADE = FOR.atividade;
const certa = (ponto: string, texto: string) => correcaoDe("for", ponto, alternativa(ATIVIDADE, ponto, texto));

describe("palco: a linha do tempo nunca passa de um palpite sem resposta", () => {
  it("destinoPermitido para no primeiro ponto aberto e deixa voltar", () => {
    const pontos = ATIVIDADE.pontos;
    expect(destinoPermitido(pontos, new Set(), 0, 11)).toBe(1);
    expect(destinoPermitido(pontos, new Set(["p2"]), 1, 11)).toBe(4);
    expect(destinoPermitido(pontos, new Set(["p2", "p3", "p4"]), 1, 11)).toBe(11);
    // Já parado no ponto aberto: não sai do lugar, mas pode voltar.
    expect(destinoPermitido(pontos, new Set(), 1, 2)).toBe(1);
    expect(destinoPermitido(pontos, new Set(), 5, 0)).toBe(0);
    expect(pontoPendente(pontos, new Set(), 4)?.id).toBe("p3");
    expect(pontoPendente(pontos, new Set(["p3"]), 4)).toBeNull();
  });

  it("começa pelo palpite antes de rodar e vai ao passo 0 depois dele", () => {
    let estado = rodar([{ tipo: "rodou", execucao: FOR }]);
    expect(estado.fase).toBe("palpite_inicial");
    expect(balaoDoPalco(estado)).toMatchObject({ ponto: { id: "p1" }, correcao: null, inicial: true });
    // Andar antes do palpite não faz nada.
    expect(palco(estado, { tipo: "ir", destino: 3, origem: "aluno" })).toBe(estado);

    const inicial = correcaoDe("for", "p1", alternativa(ATIVIDADE, "p1", "A soma é 15"));
    estado = palco(estado, { tipo: "respondeu", ponto: "p1", correcao: inicial });
    expect(estado).toMatchObject({ fase: "passos", passo: 0, aberto: null, errados: 0 });
    expect(balaoDoPalco(estado)).toBeNull();
  });

  it("Último passo para no ponto aberto e chama a atenção do balão", () => {
    const comeco = rodar([{ tipo: "rodou", execucao: FOR }, { tipo: "pulou", ponto: "p1" }]);
    const estado = palco(comeco, { tipo: "ir", destino: 11, origem: "aluno" });
    expect(estado.passo).toBe(1);
    expect(estado.atencao).toBe(comeco.atencao + 1);
    expect(balaoDoPalco(estado)).toMatchObject({ ponto: { id: "p2" }, correcao: null });
    const deNovo = palco(estado, { tipo: "ir", destino: 2, origem: "aluno" });
    expect(deNovo.passo).toBe(1);
    expect(deNovo.atencao).toBe(estado.atencao + 1);
  });

  it("um palpite diferente abre o retorno ali mesmo; Continuar fecha e anda", () => {
    let estado = rodar([
      { tipo: "rodou", execucao: FOR },
      { tipo: "pulou", ponto: "p1" },
      { tipo: "ir", destino: 1, origem: "aluno" },
    ]);
    const errada = correcaoDe("for", "p2", alternativa(ATIVIDADE, "p2", "5"));
    expect(errada.concepcao).toBe("C01");
    estado = palco(estado, { tipo: "respondeu", ponto: "p2", correcao: errada });
    expect(estado).toMatchObject({ passo: 1, aberto: { ponto: "p2", noPasso: 1 }, errados: 1 });
    expect(balaoDoPalco(estado)).toMatchObject({ ponto: { id: "p2" }, correcao: { certa: false } });
    // Responder de novo o mesmo ponto não muda nada.
    expect(palco(estado, { tipo: "respondeu", ponto: "p2", correcao: certa("p2", "4") })).toBe(estado);

    estado = palco(estado, { tipo: "continuar" });
    expect(estado).toMatchObject({ passo: 2, aberto: null, camadas: [] });
  });

  it("o Detetive leva a outro passo sem fechar o retorno; andar para a frente fecha", () => {
    let estado = rodar([
      { tipo: "rodou", execucao: FOR },
      { tipo: "pulou", ponto: "p1" },
      { tipo: "ir", destino: 1, origem: "aluno" },
      { tipo: "respondeu", ponto: "p2", correcao: correcaoDe("for", "p2", alternativa(ATIVIDADE, "p2", "5")) },
    ]);
    estado = palco(estado, { tipo: "camada", camada: 1, passo: 2, contorno: "numero" });
    expect(estado).toMatchObject({ passo: 2, aberto: { ponto: "p2" }, camadas: [1], contorno: { passo: 2, nome: "numero" } });
    // A mesma camada não se repete.
    expect(palco(estado, { tipo: "camada", camada: 1 }).camadas).toEqual([1]);
    // O Detetive também não passa de um ponto aberto (p3, no passo 4).
    expect(palco(estado, { tipo: "camada", camada: 3, passo: 9 }).passo).toBe(4);

    const voltou = palco(estado, { tipo: "ir", destino: 1, origem: "aluno" });
    expect(voltou).toMatchObject({ passo: 1, aberto: { ponto: "p2" }, contorno: null });
    const andou = palco(voltou, { tipo: "ir", destino: 3, origem: "aluno" });
    expect(andou).toMatchObject({ passo: 3, aberto: null, camadas: [] });
  });

  it("pular marca o ponto e anda um passo", () => {
    const estado = rodar([
      { tipo: "rodou", execucao: FOR },
      { tipo: "pulou", ponto: "p1" },
      { tipo: "ir", destino: 1, origem: "aluno" },
      { tipo: "pulou", ponto: "p2" },
    ]);
    expect(estado.passo).toBe(2);
    expect(estado.respondidos.has("p2")).toBe(true);
    expect(estado.correcoes.p2).toBeUndefined();
    expect(estado.errados).toBe(0);
  });

  it("o autoplay para sozinho no ponto aberto e não liga em cima dele", () => {
    let estado = rodar([
      { tipo: "rodou", execucao: FOR },
      { tipo: "pulou", ponto: "p1" },
      { tipo: "ir", destino: 1, origem: "aluno" },
      { tipo: "respondeu", ponto: "p2", correcao: certa("p2", "4") },
    ]);
    // Com o retorno aberto, tocar não liga.
    expect(palco(estado, { tipo: "tocar", tocando: true }).tocando).toBe(false);
    estado = palco(estado, { tipo: "continuar" });
    estado = palco(estado, { tipo: "tocar", tocando: true });
    expect(estado.tocando).toBe(true);
    const movimento = estado.movimento;
    estado = palco(estado, { tipo: "ir", destino: 3, origem: "autoplay" });
    expect(estado.tocando).toBe(true);
    estado = palco(estado, { tipo: "ir", destino: 4, origem: "autoplay" });
    expect(estado).toMatchObject({ passo: 4, tocando: false });
    // O autoplay não conta como movimento do aluno.
    expect(estado.movimento).toBe(movimento);
    const parado = palco(estado, { tipo: "tocar", tocando: true });
    expect(parado.tocando).toBe(false);
    expect(parado.atencao).toBe(estado.atencao + 1);
  });

  it("no fim, o palpite antes de rodar ganha o retorno, uma vez só", () => {
    const inicial = correcaoDe("for", "p1", alternativa(ATIVIDADE, "p1", "A soma é 15"));
    let estado = rodar([{ tipo: "rodou", execucao: FOR }, { tipo: "respondeu", ponto: "p1", correcao: inicial }]);
    for (const id of ["p2", "p3", "p4", "p5"]) {
      estado = palco(estado, { tipo: "ir", destino: 11, origem: "aluno" });
      estado = palco(estado, { tipo: "pulou", ponto: id });
    }
    estado = palco(estado, { tipo: "ir", destino: 11, origem: "aluno" });
    expect(estado).toMatchObject({ passo: 11, aberto: { ponto: "p1", noPasso: 11 }, inicialMostrado: true, errados: 1 });
    expect(balaoDoPalco(estado)).toMatchObject({ ponto: { id: "p1" }, correcao: { certa: false }, inicial: true });
    estado = palco(estado, { tipo: "continuar" });
    expect(estado).toMatchObject({ passo: 11, aberto: null });
    estado = palco(palco(estado, { tipo: "ir", destino: 5, origem: "aluno" }), { tipo: "ir", destino: 11, origem: "aluno" });
    expect(estado.aberto).toBeNull();
  });

  it("rodar de novo começa do zero; esquecer apaga a execução", () => {
    const estado = rodar([{ tipo: "rodou", execucao: FOR }, { tipo: "pulou", ponto: "p1" }, { tipo: "ir", destino: 1, origem: "aluno" }, { tipo: "pulou", ponto: "p2" }]);
    const outra = palco(estado, { tipo: "rodou", execucao: FOR });
    expect(outra).toMatchObject({ fase: "palpite_inicial", passo: 0, alcancado: 0, aberto: null });
    expect(outra.respondidos.size).toBe(0);
    expect(palco(estado, { tipo: "esquecer" }).execucao).toBeNull();
  });

  it("sem atividade (Assistir) anda livre e nunca abre balão", () => {
    let estado = rodar([{ tipo: "rodou", execucao: { resultado: rastros.for.resultado, atividade: null } }]);
    expect(estado.fase).toBe("passos");
    estado = palco(estado, { tipo: "ir", destino: 11, origem: "aluno" });
    expect(estado.passo).toBe(11);
    expect(balaoDoPalco(estado)).toBeNull();
  });
});

describe("Detetive: onde olhar e me mostra", () => {
  const { resultado } = FOR;

  it("'Onde olhar' segue o quadro até a caixinha existir", () => {
    const p2 = ATIVIDADE.pontos[0];
    const feedback = correcaoDe("for", "p2", alternativa(ATIVIDADE, "p2", "5")).feedback;
    const onde = ondeOlhar(resultado, p2, feedback);
    expect(onde.destacar).toBe("numero");
    expect("numero" in resultado.passos[onde.passo].globais).toBe(true);
    expect(onde.passo).toBeGreaterThanOrEqual(p2.passo);
  });

  it("nas voltas, 'Onde olhar' vai à última volta (com ou sem modelo)", () => {
    const p2 = ATIVIDADE.pontos[0];
    expect(p2.tipo).toBe("voltas");
    const feedback = correcaoDe("for", "p2", alternativa(ATIVIDADE, "p2", "5")).feedback;
    for (const onde of [ondeOlhar(resultado, p2, feedback), ondeOlhar(resultado, p2, null)]) {
      const passo = resultado.passos[onde.passo];
      expect(passo.volta?.n).toBe(4);
      expect(passo.comando).toBe(p2.alvo.comando);
    }
  });

  it("sem modelo, o ponto de valor olha a própria variável", () => {
    const p3 = ATIVIDADE.pontos[1];
    expect(ondeOlhar(resultado, p3, null)).toEqual({ passo: 4, destacar: "total" });
  });

  it("sem modelo, o palpite antes de rodar olha a primeira linha que escreve na tela", () => {
    const onde = ondeOlhar(resultado, ATIVIDADE.palpite_inicial!, null);
    expect(onde.destacar).toBeNull();
    expect(resultado.passos[onde.passo].saida).toBe("");
    expect(resultado.passos[onde.passo + 1].saida).not.toBe("");
  });

  it("'Me mostra' vai aonde o resultado aparece", () => {
    const [p2, p3] = ATIVIDADE.pontos;
    const ultimo = resultado.passos.length - 1;
    expect(passoResolvido(resultado, ATIVIDADE.palpite_inicial!)).toBe(ultimo);
    expect(passoResolvido(resultado, p2)).toBe(resultado.passos[p2.passo].volta!.total_visivel_desde);
    expect(passoResolvido(resultado, p3)).toBe(resultado.passos[p3.passo].proximo_no_quadro);
    expect(resultado.passos[passoResolvido(resultado, p3)].globais.total.valor).toBe("3");
  });
});

describe("textos do retorno", () => {
  it("separa o código entre crases", () => {
    expect(trechosDeCodigo("O `range(1, 5)` para antes do `5`.")).toEqual([
      { texto: "O ", codigo: false },
      { texto: "range(1, 5)", codigo: true },
      { texto: " para antes do ", codigo: false },
      { texto: "5", codigo: true },
      { texto: ".", codigo: false },
    ]);
    // Uma crase sem par fica no texto.
    expect(trechosDeCodigo("a `b")).toEqual([{ texto: "a `b", codigo: false }]);
  });

  it("a resposta marcada como texto ganha aspas uma vez só", () => {
    expect(comAspas("44")).toBe('"44"');
    expect(comAspas(" oi ")).toBe('"oi"');
    expect(comAspas('"oi"')).toBe('"oi"');
    expect(comAspas("'oi'")).toBe('"oi"');
    expect(comAspas("")).toBe("");
  });
});
