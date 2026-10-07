// O estado do palco: em que passo o aluno está, o que já respondeu e que
// retorno de palpite está aberto. É uma máquina pura (um reducer): a página só
// despacha ações e desenha. A regra que manda é uma só: a linha do tempo nunca
// passa de um ponto de previsão sem resposta (nem com o autoplay, nem pulando
// para o fim), porque o passo seguinte mostraria a resposta.

import type { Atividade, Correcao, Feedback, Ponto, Resultado } from "./tipos";

/** Quem moveu a linha do tempo. Só o aluno conta como movimento (leitor de tela e diário). */
export type Origem = "aluno" | "autoplay" | "detetive";
/** Camadas do Detetive: 1 onde olhar, 2 a regra, 3 me mostra. */
export type Camada = 1 | 2 | 3;
export type Fase = "palpite_inicial" | "passos";

export type Execucao = { resultado: Resultado; atividade: Atividade | null };

export type EstadoDoPalco = {
  execucao: Execucao | null;
  fase: Fase;
  passo: number;
  /** O passo mais adiante já visto: a regra de revelação conta a partir dele. */
  alcancado: number;
  /** Muda só quando o aluno anda: o narrador fala e o diário registra. */
  movimento: number;
  /** Pontos respondidos ou pulados. */
  respondidos: ReadonlySet<string>;
  correcoes: Readonly<Record<string, Correcao>>;
  /** O retorno de um palpite no balão; `noPasso` é onde ele foi aberto. */
  aberto: { ponto: string; noPasso: number } | null;
  camadas: readonly Camada[];
  /** A caixinha que 'Onde olhar' contornou, só naquele passo. */
  contorno: { passo: number; nome: string } | null;
  tocando: boolean;
  /** Muda quando o aluno tenta passar de um ponto sem responder: o balão chama a atenção. */
  atencao: number;
  /** Palpites diferentes do Python nesta execução (nunca aparece na tela). */
  errados: number;
  inicialMostrado: boolean;
};

export type AcaoDoPalco =
  | { tipo: "rodou"; execucao: Execucao }
  | { tipo: "esquecer" }
  | { tipo: "ir"; destino: number; origem: Origem }
  | { tipo: "respondeu"; ponto: string; correcao: Correcao }
  | { tipo: "pulou"; ponto: string }
  | { tipo: "continuar" }
  | { tipo: "camada"; camada: Camada; passo?: number; contorno?: string | null }
  | { tipo: "tocar"; tocando: boolean };

export const PALCO_VAZIO: EstadoDoPalco = {
  execucao: null,
  fase: "passos",
  passo: 0,
  alcancado: 0,
  movimento: 0,
  respondidos: new Set(),
  correcoes: {},
  aberto: null,
  camadas: [],
  contorno: null,
  tocando: false,
  atencao: 0,
  errados: 0,
  inicialMostrado: false,
};

/** Os pontos do passo a passo, em ordem de passo (o palpite antes de rodar fica de fora). */
export function pontosDoPasso(atividade: Atividade | null | undefined): readonly Ponto[] {
  return atividade?.pontos ?? [];
}

export function pontoPorId(atividade: Atividade | null | undefined, id: string): Ponto | null {
  if (!atividade) return null;
  if (atividade.palpite_inicial?.id === id) return atividade.palpite_inicial;
  return atividade.pontos.find((ponto) => ponto.id === id) ?? null;
}

/** O ponto sem resposta que aparece no passo k, se houver. */
export function pontoPendente(pontos: readonly Ponto[], respondidos: ReadonlySet<string>, k: number): Ponto | null {
  return pontos.find((ponto) => ponto.passo === k && !respondidos.has(ponto.id)) ?? null;
}

/**
 * Até onde a linha do tempo pode ir de `atual` em direção a `destino`: para no
 * primeiro ponto sem resposta do caminho. Voltar é sempre livre.
 */
export function destinoPermitido(pontos: readonly Ponto[], respondidos: ReadonlySet<string>, atual: number, destino: number): number {
  if (destino <= atual) return destino;
  let limite = destino;
  for (const ponto of pontos) {
    if (respondidos.has(ponto.id)) continue;
    if (ponto.passo >= atual && ponto.passo < limite) limite = ponto.passo;
  }
  return limite;
}

function limitar(valor: number, minimo: number, maximo: number) {
  return Math.max(minimo, Math.min(maximo, valor));
}

/** No fim do programa, o palpite antes de rodar ganha a correção (uma vez só). */
function chegar(estado: EstadoDoPalco): EstadoDoPalco {
  const execucao = estado.execucao;
  const inicial = execucao?.atividade?.palpite_inicial;
  if (!execucao || !inicial || estado.inicialMostrado || estado.fase !== "passos") return estado;
  const ultimo = execucao.resultado.passos.length - 1;
  if (estado.passo !== ultimo || !estado.correcoes[inicial.id]) return estado;
  // O palpite de antes só conta como diferente agora, quando o aluno fica sabendo.
  const errados = estado.errados + (estado.correcoes[inicial.id].certa ? 0 : 1);
  return { ...estado, aberto: { ponto: inicial.id, noPasso: ultimo }, camadas: [], contorno: null, tocando: false, inicialMostrado: true, errados };
}

function ir(estado: EstadoDoPalco, destino: number, origem: Origem): EstadoDoPalco {
  const execucao = estado.execucao;
  if (!execucao || estado.fase !== "passos") return estado;
  const total = execucao.resultado.passos.length;
  if (total === 0) return estado;
  const pontos = pontosDoPasso(execucao.atividade);
  const pedido = limitar(destino, 0, total - 1);
  const permitido = destinoPermitido(pontos, estado.respondidos, estado.passo, pedido);
  const parou = permitido < pedido;
  let { aberto, camadas, contorno } = estado;
  // Andar para a frente depois do passo do palpite fecha o retorno; o Detetive pode levar a outro passo sem fechar.
  if (origem !== "detetive") {
    contorno = null;
    if (aberto && permitido > aberto.noPasso) {
      aberto = null;
      camadas = [];
    }
  }
  const pendente = pontoPendente(pontos, estado.respondidos, permitido);
  const tocando = origem === "autoplay" && estado.tocando && !parou && !pendente && aberto === null && permitido < total - 1;
  const andou = permitido !== estado.passo;
  return chegar({
    ...estado,
    passo: permitido,
    alcancado: Math.max(estado.alcancado, permitido),
    movimento: andou && origem === "aluno" ? estado.movimento + 1 : estado.movimento,
    aberto,
    camadas,
    contorno,
    tocando,
    atencao: parou && origem === "aluno" ? estado.atencao + 1 : estado.atencao,
  });
}

function comecarPassos(estado: EstadoDoPalco): EstadoDoPalco {
  return chegar({ ...estado, fase: "passos", movimento: estado.movimento + 1 });
}

export function palco(estado: EstadoDoPalco, acao: AcaoDoPalco): EstadoDoPalco {
  switch (acao.tipo) {
    case "rodou": {
      const inicial = acao.execucao.atividade?.palpite_inicial ?? null;
      return chegar({
        ...PALCO_VAZIO,
        execucao: acao.execucao,
        fase: inicial ? "palpite_inicial" : "passos",
        movimento: estado.movimento + 1,
        atencao: estado.atencao,
      });
    }
    case "esquecer":
      return estado.execucao === null ? estado : { ...PALCO_VAZIO, movimento: estado.movimento, atencao: estado.atencao };
    case "ir":
      return ir(estado, acao.destino, acao.origem);
    case "respondeu": {
      const atividade = estado.execucao?.atividade;
      const ponto = pontoPorId(atividade, acao.ponto);
      if (!ponto || estado.respondidos.has(ponto.id)) return estado;
      const respondidos = new Set(estado.respondidos).add(ponto.id);
      const correcoes = { ...estado.correcoes, [ponto.id]: acao.correcao };
      if (atividade?.palpite_inicial?.id === ponto.id) {
        // O palpite antes de rodar só é corrigido no fim: agora começa o passo a passo.
        return comecarPassos({ ...estado, respondidos, correcoes });
      }
      const errados = estado.errados + (acao.correcao.certa ? 0 : 1);
      return { ...estado, respondidos, correcoes, errados, aberto: { ponto: ponto.id, noPasso: estado.passo }, camadas: [], contorno: null, tocando: false };
    }
    case "pulou": {
      const atividade = estado.execucao?.atividade;
      const ponto = pontoPorId(atividade, acao.ponto);
      if (!ponto || estado.respondidos.has(ponto.id)) return estado;
      const respondidos = new Set(estado.respondidos).add(ponto.id);
      if (atividade?.palpite_inicial?.id === ponto.id) return comecarPassos({ ...estado, respondidos });
      return ir({ ...estado, respondidos, tocando: false }, estado.passo + 1, "aluno");
    }
    case "continuar": {
      if (!estado.aberto) return estado;
      const noPasso = estado.aberto.noPasso;
      const fechado = { ...estado, aberto: null, camadas: [], contorno: null };
      const ultimo = (estado.execucao?.resultado.passos.length ?? 1) - 1;
      return noPasso >= ultimo ? fechado : ir(fechado, noPasso + 1, "aluno");
    }
    case "camada": {
      if (!estado.aberto) return estado;
      const camadas = estado.camadas.includes(acao.camada) ? estado.camadas : [...estado.camadas, acao.camada];
      let novo: EstadoDoPalco = { ...estado, camadas };
      if (acao.passo !== undefined) novo = ir(novo, acao.passo, "detetive");
      if (acao.contorno !== undefined) novo = { ...novo, contorno: acao.contorno === null ? null : { passo: novo.passo, nome: acao.contorno } };
      return novo;
    }
    case "tocar": {
      if (!acao.tocando) return estado.tocando ? { ...estado, tocando: false } : estado;
      const execucao = estado.execucao;
      if (!execucao || estado.fase !== "passos" || estado.aberto) return estado;
      const pontos = pontosDoPasso(execucao.atividade);
      if (estado.passo >= execucao.resultado.passos.length - 1) return estado;
      if (pontoPendente(pontos, estado.respondidos, estado.passo)) return { ...estado, atencao: estado.atencao + 1 };
      return { ...estado, tocando: true };
    }
  }
}

/** O que o balão mostra agora: a pergunta pendente do passo ou um retorno aberto. */
export type BalaoDoPalco = { ponto: Ponto; correcao: Correcao | null; inicial: boolean };

export function balaoDoPalco(estado: EstadoDoPalco): BalaoDoPalco | null {
  const atividade = estado.execucao?.atividade;
  if (!atividade) return null;
  const inicial = atividade.palpite_inicial;
  if (estado.fase === "palpite_inicial") return inicial ? { ponto: inicial, correcao: null, inicial: true } : null;
  if (estado.aberto) {
    const ponto = pontoPorId(atividade, estado.aberto.ponto);
    const correcao = estado.correcoes[estado.aberto.ponto] ?? null;
    return ponto ? { ponto, correcao, inicial: ponto.id === inicial?.id } : null;
  }
  const pendente = pontoPendente(atividade.pontos, estado.respondidos, estado.passo);
  return pendente ? { ponto: pendente, correcao: null, inicial: false } : null;
}

// --- O Detetive -----------------------------------------------------------------

/**
 * O passo de 'Onde olhar' e a caixinha que ganha contorno. Vale o passo do
 * feedback (ou o do ponto); se a caixinha ainda não existe ali, segue o mesmo
 * quadro por alguns passos até ela aparecer.
 */
/** O cabeçalho da última volta do laço do ponto de voltas: é ali que se vê onde o laço para. */
function ultimaVolta(resultado: Resultado, ponto: Ponto): number | null {
  const volta = resultado.passos[ponto.passo]?.volta;
  if (!volta || volta.total === null) return null;
  const fim = volta.total_visivel_desde ?? resultado.passos.length;
  for (let k = Math.min(fim, resultado.passos.length) - 1; k >= ponto.passo; k--) {
    const outra = resultado.passos[k].volta;
    if (resultado.passos[k].comando === volta.laco && outra?.laco === volta.laco && outra.n === volta.total && !outra.saindo) return k;
  }
  return null;
}

export function ondeOlhar(resultado: Resultado, ponto: Ponto, feedback: Feedback | null): { passo: number; destacar: string | null } {
  const passos = resultado.passos;
  // Nas voltas, a primeira volta não mostra onde o laço para: sem passo do motor, a última.
  const doPonto = (ponto.tipo === "voltas" ? ultimaVolta(resultado, ponto) : null) ?? ponto.passo;
  const base = limitar(feedback?.onde.passo ?? doPonto, 0, Math.max(0, passos.length - 1));
  const destacar = feedback?.onde.destacar ?? (ponto.tipo === "valor" ? ponto.alvo.nome ?? null : null);
  if (!destacar) {
    // O palpite antes de rodar, sem modelo: a primeira linha que escreve na tela.
    if (ponto.alvo.comando === null && feedback?.onde.passo == null) {
      const escreve = passos.findIndex((passo, k) => k + 1 < passos.length && passos[k + 1].saida !== passo.saida);
      if (escreve >= 0) return { passo: escreve, destacar: null };
    }
    return { passo: base, destacar: null };
  }
  let k: number | null = base;
  for (let saltos = 0; k !== null && saltos < 6; saltos++) {
    const passo: Resultado["passos"][number] | undefined = passos[k];
    if (!passo) break;
    if (destacar in passo.locais || destacar in passo.globais) return { passo: k, destacar };
    k = passo.proximo_no_quadro;
  }
  return { passo: base, destacar };
}

/** O passo de 'Me mostra': onde o resultado do ponto já aparece na tela. */
export function passoResolvido(resultado: Resultado, ponto: Ponto): number {
  const ultimo = resultado.passos.length - 1;
  const passo = resultado.passos[ponto.passo];
  if (ponto.alvo.comando === null || !passo) return ultimo; // o palpite antes de rodar: a tela inteira
  if (ponto.tipo === "voltas") return passo.volta?.total_visivel_desde ?? ponto.passo;
  return passo.proximo_no_quadro ?? Math.min(ponto.passo + 1, ultimo);
}

// --- Textos ---------------------------------------------------------------------

export type TrechoDeTexto = { texto: string; codigo: boolean };

/** Os textos do motor marcam código entre crases: `range(1, 5)`. */
export function trechosDeCodigo(texto: string): TrechoDeTexto[] {
  const trechos: TrechoDeTexto[] = [];
  texto.split("`").forEach((parte, n, partes) => {
    // Uma crase sem par fica como texto comum.
    const codigo = n % 2 === 1 && n < partes.length - 1;
    if (parte === "" && !codigo) return;
    const anterior = trechos[trechos.length - 1];
    if (!codigo && anterior && !anterior.codigo) anterior.texto += "`" + parte;
    else trechos.push({ texto: parte, codigo });
  });
  return trechos;
}

/** Como o Python vai ler a resposta marcada como texto: ganha aspas sozinha. */
export function comAspas(texto: string): string {
  const limpo = texto.trim();
  if (limpo === "") return "";
  const ja = limpo.length >= 2 && limpo[0] === limpo[limpo.length - 1] && (limpo[0] === '"' || limpo[0] === "'");
  return `"${ja ? limpo.slice(1, -1) : limpo}"`;
}
