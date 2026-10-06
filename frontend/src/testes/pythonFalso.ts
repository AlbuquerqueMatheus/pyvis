// Um Python de mentira para os testes da tela: responde com o que o motor de
// verdade gravou em rastros.json e previsoes.json (scripts/casos_revelacao.py).
import type { Canal, Pedido } from "../motor/ponte";
import type { Atividade, ConfigDaAtividade, Correcao, Evento, Resultado, RespostaDoAluno } from "../motor/tipos";
import rastrosJson from "./rastros.json";
import previsoesJson from "./previsoes.json";

export type Gravado = { codigo: string; entradas: string[]; resultado: Resultado };
export type Previsao = {
  atividades: Record<"alternativas" | "livre", Atividade>;
  correcoes: { formato: "alternativas" | "livre"; ponto: string; resposta: RespostaDoAluno; correcao: Correcao }[];
};

export const rastros = rastrosJson as unknown as Record<string, Gravado>;
export const previsoes = previsoesJson as unknown as Record<string, Previsao>;

function mesmaResposta(a: RespostaDoAluno, b: RespostaDoAluno): boolean {
  const chaves = (r: RespostaDoAluno) => Object.entries(r).sort(([x], [y]) => x.localeCompare(y));
  return JSON.stringify(chaves(a)) === JSON.stringify(chaves(b));
}

// --- Sala e diário (2.5): imitações simples de apelido.py e registro.py ---------------
// O motor de verdade é conferido no navegador e nos testes em Python; aqui basta
// um comportamento parecido para a tela.

export const APELIDOS = ["Tucano Azul 7", "Coruja Amarela 12", "Jabuti Anil 8", "Lobo Verde 50", "Panda Cinza 21", "Raposa Prateada 97", "Lince Lilás 26", "Gaivota Anil 1"];
export const REGRAS: Record<string, string> = {
  C01: "O range para antes do último número.",
  C03: "O input sempre devolve texto, mesmo quando você digita número.",
  C05: "O else só roda quando a condição do if é falsa.",
};
const CONTEXTO = ["sala", "sujeito", "atividade", "programa", "condicao", "code_hash"] as const;
const SO_EM_PREVER = ["Prediction", "Prediction.Skip", "Feedback.Layer"];

type Resposta = { ok: true; resultado: unknown } | { ok: false; erro: string };

function hashFalso(texto: string): string {
  let h = 0x811c9dc5;
  for (const letra of texto) h = Math.imul(h ^ letra.charCodeAt(0), 0x01000193) >>> 0;
  return (h.toString(16).padStart(8, "0") + "c0debabe").slice(0, 16);
}

const SALA: Record<string, (dados: Record<string, unknown>) => Resposta> = {
  gerar_apelido: () => ({ ok: true, resultado: APELIDOS[0] }),
  sugerir_apelidos: (dados) => ({ ok: true, resultado: APELIDOS.slice(0, Math.min(Number(dados.quantidade ?? 4), APELIDOS.length)) }),
  code_hash: (dados) => ({ ok: true, resultado: hashFalso(String(dados.codigo)) }),
  sortear_condicoes: (dados) => {
    const atividade = dados.atividade as { programas: unknown[]; modo: string };
    const lista = atividade.programas.map((_, k) => (atividade.modo === "estudo" ? (k % 2 === 0 ? "prever" : "assistir") : atividade.modo));
    return { ok: true, resultado: lista };
  },
  montar_evento: (dados) => {
    const contexto = dados.contexto as Record<string, unknown>;
    const campos = (dados.campos ?? {}) as Record<string, unknown>;
    if (SO_EM_PREVER.includes(String(dados.tipo)) && contexto.condicao === "assistir") return { ok: false, erro: "ValueError: só na condição prever" };
    const evento: Record<string, unknown> = { v: 1, ts: dados.ts };
    for (const campo of CONTEXTO) evento[campo] = contexto[campo] ?? null;
    evento.tipo = dados.tipo;
    for (const [campo, valor] of Object.entries(campos)) if (valor !== null && valor !== undefined) evento[campo] = valor;
    const resposta = evento.resposta as Record<string, unknown> | undefined;
    if (resposta && typeof resposta.valor_normalizado === "string" && /\p{L}/u.test(resposta.valor_normalizado)) {
      const { valor_normalizado: _, ...resto } = resposta;
      evento.resposta = resto;
    }
    return { ok: true, resultado: evento };
  },
  validar_evento: () => ({ ok: true, resultado: [] }),
  resumo: (dados) => {
    const eventos = dados.eventos as Evento[];
    const ultima = new Map<string, boolean>();
    for (const evento of eventos) {
      if (evento.tipo !== "Prediction") continue;
      if (evento.certa) for (const id of evento.testadas ?? []) ultima.set(id, true);
      else if (evento.concepcao) ultima.set(evento.concepcao, false);
    }
    const conta = (tipo: string) => eventos.filter((evento) => evento.tipo === tipo).length;
    const frases = (certo: boolean) => [...ultima].filter(([id, valor]) => valor === certo && REGRAS[id]).map(([id]) => REGRAS[id]);
    return {
      ok: true,
      resultado: {
        entendidas: frases(true),
        revisar: frases(false),
        numeros: {
          programas: new Set(eventos.filter((evento) => evento.programa !== null).map((evento) => evento.programa)).size,
          palpites: conta("Prediction"),
          pulados: conta("Prediction.Skip"),
          explicacoes: conta("Feedback.Layer"),
        },
      },
    };
  },
  montar_entrega: (dados) => {
    const eventos = dados.eventos as Evento[];
    if (new Set(eventos.map((evento) => evento.sujeito)).size > 1) return { ok: false, erro: "ValueError: mais de um aluno" };
    return { ok: true, resultado: { v: 1, apelido: dados.apelido, eventos } };
  },
};

type Opcoes = { travar?: boolean; semAtividade?: boolean };

export function pythonFalso(opcoes: Opcoes = {}) {
  const pedidos: Pedido[] = [];
  let nome: string | null = null;
  let formato: "alternativas" | "livre" = "alternativas";

  function responder(pedido: Pedido): Resposta {
    if (pedido.acao === "rastrear") {
      const { codigo } = pedido.dados as { codigo: string };
      nome = Object.keys(rastros).find((n) => rastros[n].codigo === codigo) ?? null;
      return nome ? { ok: true, resultado: rastros[nome].resultado } : { ok: false, erro: "ValueError: programa sem rastro gravado" };
    }
    if (pedido.acao === "preparar_atividade") {
      const config = (pedido.dados as { config?: ConfigDaAtividade }).config;
      formato = config?.formato === "livre" ? "livre" : "alternativas";
      const gravada = nome && !opcoes.semAtividade ? previsoes[nome]?.atividades[formato] : undefined;
      return gravada ? { ok: true, resultado: gravada } : { ok: false, erro: "RuntimeError: sem atividade gravada" };
    }
    if (pedido.acao === "corrigir") {
      const { ponto_id, resposta } = pedido.dados as { ponto_id: string; resposta: RespostaDoAluno };
      const gravada = nome
        ? previsoes[nome]?.correcoes.find((c) => c.formato === formato && c.ponto === ponto_id && mesmaResposta(c.resposta, resposta))
        : undefined;
      return gravada ? { ok: true, resultado: gravada.correcao } : { ok: false, erro: `KeyError: sem correção gravada para ${JSON.stringify(resposta)}` };
    }
    if (pedido.acao in SALA) return SALA[pedido.acao](pedido.dados as Record<string, unknown>);
    return { ok: false, erro: `ValueError: ação ${pedido.acao} fora do teste` };
  }

  const criar = (aoReceber: (mensagem: unknown) => void): Canal => {
    queueMicrotask(() => aoReceber({ tipo: "pronto" }));
    return {
      enviar(pedido) {
        pedidos.push(pedido);
        if (opcoes.travar) return;
        const resposta = { id: pedido.id, ...responder(pedido) };
        queueMicrotask(() => aoReceber(JSON.stringify(resposta)));
      },
      encerrar() {},
    };
  };
  return { criar, pedidos };
}
