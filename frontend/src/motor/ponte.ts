// Toda conversa com o motor Python passa por aqui.
//
// Hoje o motor roda num Web Worker. Na publicação ele vai para um iframe numa
// origem separada (o executor isolado de 1.1): aí só muda o Canal, que também
// passa a conferir event.origin. O resto da página não sabe onde o Python mora.
//
// Protocolo: pedido {id, acao, dados} -> resposta {id, ok, resultado | erro},
// que chega como texto JSON (o worker repassa o que o Python escreveu). O
// canal também avisa {tipo: 'pronto'} e {tipo: 'falha'} enquanto carrega.

import type {
  Atividade,
  AtividadeLink,
  ConfigDaAtividade,
  ContextoDoEvento,
  Correcao,
  Entrega,
  Evento,
  RespostaDoAluno,
  Resultado,
  Resumo,
  TipoDeEvento,
} from "./tipos";

/** O que cada ação recebe e devolve (pyvis_motor/api.py). */
export type Acoes = {
  rastrear: { dados: { codigo: string; entradas: string[]; semente?: number; limite?: number }; resultado: Resultado };
  preparar_atividade: { dados: { config?: ConfigDaAtividade }; resultado: Atividade };
  corrigir: { dados: { ponto_id: string; resposta: RespostaDoAluno }; resultado: Correcao };
  gerar_apelido: { dados: { semente?: string | number }; resultado: string };
  sugerir_apelidos: { dados: { semente: string | number; quantidade?: number }; resultado: string[] };
  validar_apelido: { dados: { apelido: string }; resultado: boolean };
  code_hash: { dados: { codigo: string }; resultado: string };
  higienizar: { dados: { codigo: string }; resultado: string };
  validar_evento: { dados: { evento: unknown }; resultado: string[] };
  montar_evento: {
    dados: { tipo: TipoDeEvento; contexto: ContextoDoEvento; ts?: number; campos?: Record<string, unknown> };
    resultado: Evento;
  };
  resumo: { dados: { eventos: Evento[]; atividade?: string }; resultado: Resumo };
  sortear_condicoes: { dados: { sujeito: string; atividade: AtividadeLink }; resultado: ("prever" | "assistir")[] };
  montar_entrega: { dados: { apelido: string; eventos: Evento[] }; resultado: Entrega };
};

export type Acao = keyof Acoes;

export type EstadoDoMotor = "carregando" | "pronto" | "ocupado" | "falhou";

export const TEMPO_LIMITE_MS = 5000;
/**
 * preparar_atividade tem orçamento de 500 ms no Python, mas um modelo pode
 * rodar o que o programa nunca rodou (o else da C05) dentro de uma função
 * embutida longa, sem passos onde parar. Aqui é o teto do lado da página.
 */
export const TEMPO_LIMITE_ATIVIDADE_MS = 3000;
export const MENSAGEM_TEMPO_ESGOTADO = "O programa demorou demais e foi parado.";
const MENSAGEM_ATIVIDADE_ESGOTADA = "As perguntas demoraram demais para ficar prontas.";
const MENSAGEM_REINICIO = "O Python foi reiniciado. Tente de novo.";
const MENSAGEM_FALHA = "Não foi possível carregar o Python. Recarregue a página.";

/**
 * Um pedido que não deu certo. `tipo` 'TempoEsgotado' é o programa que passou
 * do tempo; 'Reiniciado', um pedido perdido quando o Python foi recriado;
 * 'Motor', um defeito do motor (nunca um erro no código do aluno, que vem
 * dentro do Resultado).
 */
export class ErroDoMotor extends Error {
  readonly tipo: "TempoEsgotado" | "Reiniciado" | "Falha" | "Motor";
  constructor(tipo: ErroDoMotor["tipo"], mensagem: string) {
    super(mensagem);
    this.name = "ErroDoMotor";
    this.tipo = tipo;
  }
}

/** Onde o Python roda. O canal entrega à ponte tudo o que chega, sem interpretar. */
export type Canal = {
  enviar(pedido: Pedido): void;
  encerrar(): void;
};
export type CriarCanal = (aoReceber: (mensagem: unknown) => void) => Canal;

export type Pedido = { id: number; acao: Acao; dados: unknown };

type Resposta = { id: number; ok: true; resultado: unknown } | { id: number; ok: false; erro: string };
type Aviso = { tipo: "pronto" } | { tipo: "falha"; mensagem?: string };

export function canalDeWorker(aoReceber: (mensagem: unknown) => void): Canal {
  const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
  worker.onmessage = (evento) => aoReceber(evento.data);
  worker.onerror = () => aoReceber({ tipo: "falha", mensagem: "erro no worker" });
  return { enviar: (pedido) => worker.postMessage(pedido), encerrar: () => worker.terminate() };
}

/** Lê uma mensagem do canal; qualquer coisa fora do formato é ignorada. */
export function lerMensagem(mensagem: unknown): Resposta | Aviso | null {
  let dados = mensagem;
  if (typeof dados === "string") {
    try {
      dados = JSON.parse(dados);
    } catch {
      return null;
    }
  }
  if (typeof dados !== "object" || dados === null) return null;
  const objeto = dados as Record<string, unknown>;
  if (objeto.tipo === "pronto") return { tipo: "pronto" };
  if (objeto.tipo === "falha") return { tipo: "falha", mensagem: typeof objeto.mensagem === "string" ? objeto.mensagem : undefined };
  if (typeof objeto.id !== "number" || typeof objeto.ok !== "boolean") return null;
  if (objeto.ok) return "resultado" in objeto ? { id: objeto.id, ok: true, resultado: objeto.resultado } : null;
  return { id: objeto.id, ok: false, erro: typeof objeto.erro === "string" ? objeto.erro : "erro desconhecido" };
}

/** Em aparelhos com pouca memória, o rastro para antes (spec 1.4). */
export function limiteDePassos(memoria = (globalThis.navigator as { deviceMemory?: number } | undefined)?.deviceMemory): number | undefined {
  return memoria !== undefined && memoria <= 2 ? 300 : undefined;
}

/**
 * O que o aluno vê acontecer: só essas ações deixam o motor 'ocupado' (o botão
 * Executar espera e o cabeçalho avisa). As do diário e da sala correm por baixo,
 * sem piscar o aviso a cada passo.
 */
const ACOES_VISIVEIS: ReadonlySet<Acao> = new Set<Acao>(["rastrear", "preparar_atividade", "corrigir"]);

type Pendente = {
  pedido: Pedido;
  resolver: (resultado: unknown) => void;
  rejeitar: (erro: ErroDoMotor) => void;
};

/**
 * Fila de pedidos ao motor. Um pedido por vez vai ao Python (ele roda um de
 * cada vez mesmo). `rastrear` e `preparar_atividade` têm tempo limite: se
 * passar, o Python é descartado e recriado do zero, e a página continua
 * funcionando (o novo Python não tem o último rastro: a atividade se perde).
 */
export class Ponte {
  estado: EstadoDoMotor = "carregando";
  private readonly criarCanal: CriarCanal;
  private readonly tempoLimiteMs: number;
  private readonly tempoDaAtividadeMs: number;
  private canal: Canal;
  private readonly pendentes = new Map<number, Pendente>();
  private readonly fila: number[] = [];
  private emCurso: number | null = null;
  private relogio: ReturnType<typeof setTimeout> | undefined;
  private proximoId = 1;
  private readonly ouvintes = new Set<(estado: EstadoDoMotor) => void>();

  constructor(criarCanal: CriarCanal = canalDeWorker, tempoLimiteMs = TEMPO_LIMITE_MS, tempoDaAtividadeMs = TEMPO_LIMITE_ATIVIDADE_MS) {
    this.criarCanal = criarCanal;
    this.tempoLimiteMs = tempoLimiteMs;
    this.tempoDaAtividadeMs = tempoDaAtividadeMs;
    this.canal = this.abrir();
  }

  /** Avisa cada mudança de estado; devolve a função que para de avisar. */
  observar(ouvinte: (estado: EstadoDoMotor) => void): () => void {
    this.ouvintes.add(ouvinte);
    return () => this.ouvintes.delete(ouvinte);
  }

  pedir<A extends Acao>(acao: A, dados: Acoes[A]["dados"]): Promise<Acoes[A]["resultado"]> {
    if (this.estado === "falhou") return Promise.reject(new ErroDoMotor("Falha", MENSAGEM_FALHA));
    const id = this.proximoId++;
    return new Promise((resolver, rejeitar) => {
      this.pendentes.set(id, { pedido: { id, acao, dados }, resolver: resolver as (r: unknown) => void, rejeitar });
      this.fila.push(id);
      this.enviarProximo();
    });
  }

  rastrear(codigo: string, entradas: string[], semente?: number): Promise<Resultado> {
    const dados: Acoes["rastrear"]["dados"] = { codigo, entradas };
    if (semente !== undefined) dados.semente = semente;
    const limite = limiteDePassos();
    if (limite !== undefined) dados.limite = limite;
    return this.pedir("rastrear", dados);
  }

  prepararAtividade(config?: ConfigDaAtividade): Promise<Atividade> {
    return this.pedir("preparar_atividade", config ? { config } : {});
  }

  corrigir(pontoId: string, resposta: RespostaDoAluno): Promise<Correcao> {
    return this.pedir("corrigir", { ponto_id: pontoId, resposta });
  }

  encerrar() {
    clearTimeout(this.relogio);
    this.canal.encerrar();
    this.rejeitarTodos(new ErroDoMotor("Reiniciado", MENSAGEM_REINICIO));
    this.ouvintes.clear();
  }

  private abrir(): Canal {
    this.mudarEstado("carregando");
    return this.criarCanal((mensagem) => this.receber(mensagem));
  }

  private mudarEstado(estado: EstadoDoMotor) {
    if (this.estado === estado) return;
    this.estado = estado;
    for (const ouvinte of this.ouvintes) ouvinte(estado);
  }

  private receber(mensagem: unknown) {
    const lida = lerMensagem(mensagem);
    if (lida === null) return;
    if ("tipo" in lida) {
      if (lida.tipo === "pronto") {
        this.mudarEstado("pronto");
        this.enviarProximo();
      } else {
        clearTimeout(this.relogio);
        this.mudarEstado("falhou");
        this.rejeitarTodos(new ErroDoMotor("Falha", MENSAGEM_FALHA));
      }
      return;
    }
    // Uma resposta atrasada de um pedido já encerrado não pode cair no lugar de outro.
    if (lida.id !== this.emCurso) return;
    const pendente = this.pendentes.get(lida.id);
    clearTimeout(this.relogio);
    this.pendentes.delete(lida.id);
    this.emCurso = null;
    if (pendente) {
      if (lida.ok) pendente.resolver(lida.resultado);
      else pendente.rejeitar(new ErroDoMotor("Motor", lida.erro));
    }
    this.mudarEstado("pronto");
    this.enviarProximo();
  }

  private enviarProximo() {
    if (this.emCurso !== null || this.estado === "carregando" || this.estado === "falhou") return;
    const id = this.fila.shift();
    if (id === undefined) return;
    const pendente = this.pendentes.get(id)!;
    this.emCurso = id;
    if (ACOES_VISIVEIS.has(pendente.pedido.acao)) this.mudarEstado("ocupado");
    const limite = pendente.pedido.acao === "rastrear" ? this.tempoLimiteMs : pendente.pedido.acao === "preparar_atividade" ? this.tempoDaAtividadeMs : null;
    if (limite !== null) {
      // O relógio só começa quando o Python recebe o pedido, não enquanto ele carrega.
      this.relogio = setTimeout(() => this.esgotarTempo(id), limite);
    }
    this.canal.enviar(pendente.pedido);
  }

  private esgotarTempo(id: number) {
    const pendente = this.pendentes.get(id);
    this.pendentes.delete(id);
    this.emCurso = null;
    this.canal.encerrar();
    const mensagem = pendente?.pedido.acao === "preparar_atividade" ? MENSAGEM_ATIVIDADE_ESGOTADA : MENSAGEM_TEMPO_ESGOTADO;
    pendente?.rejeitar(new ErroDoMotor("TempoEsgotado", mensagem));
    // Os outros pedidos da fila esperam o Python novo; o que estava rodando se perdeu.
    this.canal = this.abrir();
  }

  private rejeitarTodos(erro: ErroDoMotor) {
    const todos = [...this.pendentes.values()];
    this.pendentes.clear();
    this.fila.length = 0;
    this.emCurso = null;
    for (const pendente of todos) pendente.rejeitar(erro);
  }
}
