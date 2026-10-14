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

// --- Praticar: uma imitação pequena de praticar.py --------------------------------
// Famílias de mentira com poucas sementes no banco; cada exercício é um dos
// programas gravados (if, for, while), para o palco rodar de verdade.

export const CATALOGO_FALSO = {
  temas: [
    { id: "variaveis", nome: "Variáveis", descricao: "Guardar valores com nomes.", niveis: [{ nivel: 1, nome: "Guardar e mudar valores" }, { nivel: 2, nome: "Contas e textos" }] },
    { id: "condicoes", nome: "Condições", descricao: "Escolher um caminho com if.", niveis: [{ nivel: 1, nome: "Se e senão" }] },
    // 'Repetir com for' ainda sem família: a série sai vazia.
    { id: "lacos", nome: "Laços", descricao: "Repetir comandos.", niveis: [{ nivel: 1, nome: "Repetir com while" }, { nivel: 2, nome: "Repetir com for" }] },
  ],
  familias: {
    robo_teste: { versao: 1, tema: "variaveis" },
    pet_teste: { versao: 2, tema: "variaveis" },
    porta_teste: { versao: 1, tema: "condicoes" },
    volta_teste: { versao: 1, tema: "lacos" },
  },
} as const;
const NIVEIS_FALSOS: Record<string, number[]> = { robo_teste: [1, 2], pet_teste: [1], porta_teste: [1], volta_teste: [1] };
export const BANCO_FALSO = [3, 8, 15, 21, 34, 42];
const PROGRAMAS_DO_EXERCICIO = ["if_else", "for", "while"] as const;

/** O contexto do exercício falso: diz a família e a semente, para o teste saber qual abriu. */
export function contextoFalso(familia: string, semente: number): string {
  return `Programa ${familia} ${semente}.`;
}

/** O montar_serie falso, também usado direto pelos testes (achar uma semente com a série que eles querem). */
export function serieFalsa(dados: Record<string, unknown>): ItemFalso[] {
  const { tema, nivel, semente } = dados as { tema: string; nivel: number; semente: number };
  const quantidade = Number(dados.quantidade ?? 5);
  const excluir = new Set((dados.excluir ?? []) as string[]);
  const familias = Object.entries(CATALOGO_FALSO.familias)
    .filter(([nome, f]) => f.tema === tema && NIVEIS_FALSOS[nome].includes(nivel) && (dados.familia === undefined || dados.familia === nome))
    .sort(([a], [b]) => hashFalso(`${semente}:${a}`).localeCompare(hashFalso(`${semente}:${b}`)));
  const filas = familias.map(([nome, f]) =>
    BANCO_FALSO.map((s) => `${nome}@${f.versao}:${nivel}:${s}`).sort((a, b) => hashFalso(`${semente}:${a}`).localeCompare(hashFalso(`${semente}:${b}`))),
  );
  const ordem = BANCO_FALSO.flatMap((_, k) => filas.map((fila) => fila[k]));
  return ordem
    .filter((chave) => !excluir.has(chave))
    .slice(0, quantidade)
    .map((chave) => {
      const [familia, resto] = chave.split("@");
      const [versao, , s] = resto.split(":");
      return { familia, versao: Number(versao), nivel, semente: Number(s), chave };
    });
}

type ItemFalso = { familia: string; versao: number; nivel: number; semente: number; chave: string };

const PRATICAR: Record<string, (dados: Record<string, unknown>, opcoes: Opcoes) => Resposta> = {
  catalogo_praticar: () => ({ ok: true, resultado: CATALOGO_FALSO }),
  montar_serie: (dados, opcoes) => (opcoes.falharSerie ? { ok: false, erro: "RuntimeError: falhou" } : { ok: true, resultado: serieFalsa(dados) }),
  gerar_exercicio: (dados, opcoes) => {
    const { familia, nivel, semente } = dados as { familia: string; nivel: number; semente: number };
    if (opcoes.falharExercicios?.includes(semente)) return { ok: false, erro: "ValueError: este exercício não passou na conferência" };
    const programa = rastros[PROGRAMAS_DO_EXERCICIO[semente % PROGRAMAS_DO_EXERCICIO.length]];
    const { versao, tema } = CATALOGO_FALSO.familias[familia as keyof typeof CATALOGO_FALSO.familias];
    return {
      ok: true,
      resultado: { familia, versao, tema, nivel, semente, esqueleto: "teste", contexto: contextoFalso(familia, semente), codigo: programa.codigo, entradas: [] },
    };
  },
};

/** Um pedido segurado pelo teste: `soltar()` manda a resposta de verdade, `soltar(resposta)` manda outra. */
export type Segurado = { pedido: Pedido; soltar: (resposta?: Resposta) => void };

type Opcoes = {
  travar?: boolean;
  semAtividade?: boolean;
  falharExercicios?: number[];
  falharSerie?: boolean;
  /** Os pedidos que o teste segura para responder depois (uma resposta que chega atrasada). */
  segurar?: (pedido: Pedido) => boolean;
};

export function pythonFalso(opcoes: Opcoes = {}) {
  const pedidos: Pedido[] = [];
  const segurados: Segurado[] = [];
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
    if (pedido.acao in PRATICAR) return PRATICAR[pedido.acao](pedido.dados as Record<string, unknown>, opcoes);
    return { ok: false, erro: `ValueError: ação ${pedido.acao} fora do teste` };
  }

  const criar = (aoReceber: (mensagem: unknown) => void): Canal => {
    queueMicrotask(() => aoReceber({ tipo: "pronto" }));
    return {
      enviar(pedido) {
        pedidos.push(pedido);
        if (opcoes.travar) return;
        if (opcoes.segurar?.(pedido)) {
          segurados.push({ pedido, soltar: (outra) => aoReceber(JSON.stringify({ id: pedido.id, ...(outra ?? responder(pedido)) })) });
          return;
        }
        const resposta = { id: pedido.id, ...responder(pedido) };
        queueMicrotask(() => aoReceber(JSON.stringify(resposta)));
      },
      encerrar() {},
    };
  };
  return { criar, pedidos, segurados };
}
