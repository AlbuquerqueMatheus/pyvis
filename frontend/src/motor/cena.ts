// O que a tela mostra num passo: linha destacada, ramo pulado, balão da
// decisão, pílula da volta e retorno de função. Tudo passa pela regra de
// revelação, para nada do futuro aparecer antes do palpite.

import { visivel } from "./revelacao";
import type { Comando, Decisao, Faixa, Passo, Resultado, Retorno } from "./tipos";

/** O que o aluno já respondeu e até onde já chegou na linha do tempo. */
export type Revelacao = { respondidos: ReadonlySet<string>; alcancado: number };

export const NADA_RESPONDIDO: ReadonlySet<string> = new Set();

export type TrechoDoBalao = { texto: string; naoCalculado: boolean };

/** '7 >= 6 → Verdadeiro', no fim do cabeçalho do if, elif ou while. */
export type Balao = { linha: number; trechos: TrechoDoBalao[]; valor: boolean | null };

export type CenaDoEditor = {
  atual: Faixa | null;
  erro: number | null;
  pulados: Faixa[];
  balao: Balao | null;
  /** Partes da condição que o curto-circuito pulou: [linha, coluna, linha_fim, coluna_fim], colunas em bytes UTF-8. */
  naoCalculado: [number, number, number, number][];
};

export const CENA_VAZIA: CenaDoEditor = { atual: null, erro: null, pulados: [], balao: null, naoCalculado: [] };

export type PilulaDaVolta = { laco: number; linha: number; n: number | null; total: number | null; saindo: boolean };

function ver(passo: Passo, campo: string, revelacao: Revelacao) {
  return visivel(passo, campo, revelacao.respondidos, revelacao.alcancado);
}

/** Linhas que a linha destacada cobre: só o cabeçalho de um bloco, o comando inteiro nos outros. */
export function linhasDoComando(comando: Comando): Faixa {
  return comando.cabecalho ?? comando.linhas;
}

/** O ramo que a decisão não tomou: o else (ou elif) quando entrou, o corpo quando não entrou. */
function ramoPulado(decisao: Decisao, comando: Comando): Faixa | null {
  if (comando.corpo_mesma_linha) return null; // esmaecer o corpo esmaeceria o próprio cabeçalho
  if (decisao.ramo === "corpo") return comando.orelse;
  if (decisao.ramo === "orelse" || decisao.ramo === "sai") return comando.corpo;
  return null;
}

/**
 * Ramos pulados que valem para o passo k: o da decisão logo antes dele (no
 * mesmo quadro) e o de cada if ou elif em cujo ramo tomado o passo k está.
 * Só depois que a decisão aconteceu (decisao.ramo visível). A busca para na
 * vez anterior do próprio comando: o que veio antes dela é de outra volta
 * (no cabeçalho do if, a decisão desta volta ainda nem aconteceu).
 */
export function ramosPulados(resultado: Resultado, k: number, revelacao: Revelacao): Faixa[] {
  const { passos } = resultado;
  const { comandos } = resultado.estrutura;
  const atual = passos[k];
  if (!atual) return [];
  const linha = atual.evento === "linha" ? atual.linha : null;
  const pulados: Faixa[] = [];
  const vistos = new Set<number>();
  let imediato = true;
  for (let j = k - 1; j >= 0; j--) {
    const passo = passos[j];
    if (passo.quadro !== atual.quadro) continue;
    if (passo.comando !== null && passo.comando === atual.comando) break;
    const anterior = imediato;
    imediato = false;
    // Só a vez mais recente de cada comando: as voltas antigas de um laço não contam.
    if (passo.comando === null || vistos.has(passo.comando)) continue;
    vistos.add(passo.comando);
    const comando = comandos[passo.comando];
    if (!passo.decisao || !comando || (comando.tipo !== "if" && comando.tipo !== "elif")) continue;
    // Dentro do ramo que a decisão tomou (o cabeçalho do if não conta).
    const tomado = passo.decisao.ramo === "corpo" ? comando.corpo : passo.decisao.ramo === "orelse" ? comando.orelse : null;
    const dentro = linha !== null && tomado !== null && linha >= tomado[0] && linha <= tomado[1];
    if (!anterior && !dentro) continue;
    if (!ver(passo, "decisao.ramo", revelacao)) continue;
    const faixa = ramoPulado(passo.decisao, comando);
    if (faixa) pulados.push(faixa);
  }
  return pulados;
}

/** Corta `texto` nas faixas de `nao_calculado`, que contam caracteres do Python (code points). */
function trechos(texto: string, faixas: [number, number][]): TrechoDoBalao[] {
  const letras = Array.from(texto);
  const resultado: TrechoDoBalao[] = [];
  let inicio = 0;
  for (const [de, ate] of [...faixas].sort((a, b) => a[0] - b[0])) {
    if (de < inicio) continue;
    if (de > inicio) resultado.push({ texto: letras.slice(inicio, de).join(""), naoCalculado: false });
    resultado.push({ texto: letras.slice(de, ate).join(""), naoCalculado: true });
    inicio = ate;
  }
  if (inicio < letras.length) resultado.push({ texto: letras.slice(inicio).join(""), naoCalculado: false });
  return resultado;
}

/** O balão da decisão do passo, com só o que já pode aparecer. */
export function balaoDaDecisao(passo: Passo, comando: Comando | undefined, revelacao: Revelacao): Balao | null {
  const decisao = passo.decisao;
  if (!decisao || !comando) return null;
  const valorVisivel = decisao.valor !== null && ver(passo, "decisao.valor", revelacao);
  const textoVisivel = decisao.texto !== null && ver(passo, "decisao.texto", revelacao);
  if (!valorVisivel && !textoVisivel) return null;
  // O que o curto-circuito pulou diz o resultado: só aparece junto com o valor.
  const marcar = valorVisivel && ver(passo, "decisao.nao_calculado", revelacao);
  return {
    linha: linhasDoComando(comando)[1],
    trechos: textoVisivel ? trechos(decisao.texto!, marcar ? decisao.nao_calculado : []) : [],
    valor: valorVisivel ? decisao.valor : null,
  };
}

/** Tudo o que o editor desenha no passo k. */
export function cenaDoEditor(resultado: Resultado | null, k: number, revelacao: Revelacao): CenaDoEditor {
  if (!resultado) return CENA_VAZIA;
  const { passos } = resultado;
  const comandos = resultado.estrutura.comandos;
  const ultimo = passos.length === 0 || k === passos.length - 1;
  const erro = resultado.erro && ultimo ? resultado.erro.linha : null;
  const passo = passos[k];
  if (!passo) return { ...CENA_VAZIA, erro };
  const comando = passo.comando !== null ? comandos[passo.comando] : undefined;
  const balao = balaoDaDecisao(passo, comando, revelacao);
  const decisao = passo.decisao;
  const naoCalculado =
    balao && balao.valor !== null && decisao && ver(passo, "decisao.nao_calculado", revelacao) ? decisao.nao_calculado_codigo : [];
  return {
    atual: comando && passo.evento === "linha" ? linhasDoComando(comando) : null,
    erro,
    pulados: ramosPulados(resultado, k, revelacao),
    balao,
    naoCalculado,
  };
}

/** A pílula 'volta 2' do laço em que o passo está; o total só quando já pode aparecer. */
export function pilulaDaVolta(passo: Passo | undefined, comandos: Comando[], revelacao: Revelacao): PilulaDaVolta | null {
  const volta = passo?.volta;
  if (!passo || !volta) return null;
  return {
    laco: volta.laco,
    linha: comandos[volta.laco]?.linhas[0] ?? passo.linha,
    n: ver(passo, "volta.n", revelacao) ? volta.n : null,
    total: volta.total !== null && ver(passo, "volta.total", revelacao) ? volta.total : null,
    saindo: volta.saindo && ver(passo, "volta.saindo", revelacao),
  };
}

export function textoDaVolta(pilula: PilulaDaVolta): string {
  const voltas = pilula.total === null ? "" : ` · ${pilula.total} ${pilula.total === 1 ? "volta" : "voltas"}`;
  if (pilula.saindo) return `saindo do laço${voltas}`;
  const total = pilula.total === null ? "" : ` de ${pilula.total}`;
  return pilula.n === null ? "volta ?" : `volta ${pilula.n}${total}`;
}

/** Quantos retornos de uma vez aparecem: numa recursão funda, só os últimos. */
export const RETORNOS_VISIVEIS = 3;

/**
 * 'dobro devolveu 8', no passo seguinte ao fim de uma chamada. Na recursão,
 * vários quadros terminam antes do próximo passo: um retorno para cada um,
 * do mais interno ao mais externo (só os últimos RETORNOS_VISIVEIS).
 */
export function retornosVisiveis(passo: Passo | undefined, revelacao: Revelacao): Retorno[] {
  if (!passo?.retorno || !ver(passo, "retorno", revelacao)) return [];
  const todos = passo.retornos ?? [passo.retorno];
  return todos.slice(-RETORNOS_VISIVEIS);
}

/** O passo anterior do mesmo quadro: as variáveis locais mudaram em relação a ele. */
export function anteriorNoQuadro(passos: Passo[], k: number): Passo | undefined {
  const atual = passos[k];
  if (!atual) return undefined;
  for (let j = k - 1; j >= 0; j--) if (passos[j].quadro === atual.quadro) return passos[j];
  return undefined;
}
