// O link de uma atividade (spec 2.5). Tudo vai no fragmento da URL (depois do
// #), que o navegador não manda para nenhum servidor.
//
//   Só exemplos:        #a=ex3,ex5&m=prever&f=alt&sala=K7PX&id=aula3&s=4821
//   Com código próprio: #c=<programas em JSON, com lz-string>&m=prever&...&s=4821
//
// Os programas vêm primeiro e a semente por último: o link termina em dígitos,
// e o chat não corta um '$' ou '-' do fim do texto comprimido. Qualquer pessoa
// pode montar um link, então tudo é conferido antes de usar.

import { compressToEncodedURIComponent } from "lz-string";
import { descomprimirComTeto } from "./descomprimir";
import { exemploPorId } from "../exemplos";
import type { AtividadeLink, Formato, ProgramaDoLink } from "../motor/tipos";

// Os mesmos formatos que pyvis_motor/registro.py aceita nos eventos.
export const PADRAO_SALA = /^[A-Za-z0-9][A-Za-z0-9-]{1,15}$/;
export const PADRAO_ATIVIDADE = /^[A-Za-z0-9_-]{1,32}$/;

export const MODOS_DO_LINK = ["assistir", "prever", "estudo"] as const;
export type ModoDoLink = (typeof MODOS_DO_LINK)[number];

export const MAX_PROGRAMAS = 20;
export const MAX_CODIGO = 20_000;
export const MAX_ENTRADAS = 50;
export const MAX_ENTRADA = 500;
export const SEMENTE_MAXIMA = 2 ** 31 - 1;
const MAX_FRAGMENTO = 200_000;
// O maior texto de programas que lerProgramas aceitaria (no JSON, um caractere escapado vira dois),
// com folga. Um link comprimido que passa disso é parado no meio da descompressão.
const TETO_DESCOMPRIMIDO = MAX_PROGRAMAS * (2 * MAX_CODIGO + MAX_ENTRADAS * (2 * MAX_ENTRADA + 3) + 1_000);

/**
 * Até onde um link cabe numa mensagem do chat do Meet. Medir antes do piloto
 * (spec 2.5); acima disso a atividade vai como arquivo.
 */
export const LIMITE_DO_CHAT = 500;

export type LeituraDoLink =
  | { tipo: "nenhuma" }
  | { tipo: "atividade"; atividade: AtividadeLink }
  | { tipo: "invalida"; motivo: string };

/** O código da sala como o aluno digita: sem espaços e em maiúsculas. */
export function normalizarSala(texto: string): string {
  return texto.replace(/\s+/g, "").toUpperCase();
}

export function codificarAtividade(atividade: AtividadeLink): string {
  const soExemplos = atividade.programas.every((programa) => "ex" in programa && !programa.entradas);
  const programas = soExemplos
    ? `a=${atividade.programas.map((programa) => (programa as { ex: string }).ex).join(",")}`
    : `c=${compressToEncodedURIComponent(JSON.stringify(atividade.programas))}`;
  const partes = [programas, `m=${atividade.modo}`, `f=${atividade.formato === "livre" ? "livre" : "alt"}`];
  if (atividade.sala) partes.push(`sala=${atividade.sala}`);
  partes.push(`id=${atividade.id}`, `s=${atividade.semente}`);
  return partes.join("&");
}

/** O link completo, para copiar: o endereço desta página com a atividade no fragmento. */
export function linkDaAtividade(atividade: AtividadeLink, base = window.location.href.split("#")[0]): string {
  return `${base}#${codificarAtividade(atividade)}`;
}

// À mão, e não com URLSearchParams: ele troca '+' por espaço, e o '+' faz parte do texto comprimido.
function parametros(fragmento: string): Map<string, string> {
  const lidos = new Map<string, string>();
  for (const parte of fragmento.replace(/^#/, "").split("&")) {
    const igual = parte.indexOf("=");
    const chave = igual < 0 ? parte : parte.slice(0, igual);
    if (!chave || lidos.has(chave)) continue;
    let valor = igual < 0 ? "" : parte.slice(igual + 1);
    try {
      valor = decodeURIComponent(valor);
    } catch {
      // um '%' solto fica como veio; a conferência abaixo decide
    }
    lidos.set(chave, valor);
  }
  return lidos;
}

function invalida(motivo: string): LeituraDoLink {
  return { tipo: "invalida", motivo };
}

function lerEntradas(entradas: unknown): string[] | string {
  if (!Array.isArray(entradas) || entradas.length > MAX_ENTRADAS) return `as entradas precisam ser uma lista de até ${MAX_ENTRADAS} textos`;
  for (const entrada of entradas) {
    if (typeof entrada !== "string" || entrada.length > MAX_ENTRADA || /[\r\n]/.test(entrada)) return "cada entrada precisa ser um texto de uma linha";
  }
  return [...entradas];
}

/** Os programas do link, já conferidos (só os campos conhecidos), ou o motivo de não servirem. */
function lerProgramas(lidos: unknown): ProgramaDoLink[] | string {
  if (!Array.isArray(lidos) || lidos.length === 0) return "a atividade não tem programas";
  if (lidos.length > MAX_PROGRAMAS) return `a atividade tem mais de ${MAX_PROGRAMAS} programas`;
  const programas: ProgramaDoLink[] = [];
  for (const [k, lido] of lidos.entries()) {
    if (typeof lido !== "object" || lido === null || Array.isArray(lido)) return `o programa ${k + 1} não está no formato certo`;
    const item = lido as Record<string, unknown>;
    let programa: ProgramaDoLink;
    if ("ex" in item) {
      if (typeof item.ex !== "string" || !exemploPorId(item.ex)) return `o exemplo do programa ${k + 1} não existe`;
      programa = { ex: item.ex };
    } else if (typeof item.codigo === "string") {
      if (item.codigo.trim() === "") return `o programa ${k + 1} está vazio`;
      if (item.codigo.length > MAX_CODIGO) return `o programa ${k + 1} é grande demais`;
      programa = { codigo: item.codigo };
    } else {
      return `o programa ${k + 1} não tem exemplo nem código`;
    }
    if (item.entradas !== undefined) {
      const entradas = lerEntradas(item.entradas);
      if (typeof entradas === "string") return `programa ${k + 1}: ${entradas}`;
      programa.entradas = entradas;
    }
    programas.push(programa);
  }
  return programas;
}

/** Lê o fragmento da URL: não é uma atividade, é uma atividade válida ou é um link quebrado. */
export function lerAtividade(fragmento: string): LeituraDoLink {
  if (fragmento.length > MAX_FRAGMENTO) return invalida("o link é grande demais");
  const lidos = parametros(fragmento);
  if (!lidos.has("a") && !lidos.has("c")) return { tipo: "nenhuma" };
  if (lidos.has("v") && lidos.get("v") !== "1") return invalida("o link é de outra versão do PyVis");

  let brutos: unknown;
  if (lidos.has("a")) {
    brutos = lidos
      .get("a")!
      .split(",")
      .filter((ex) => ex !== "")
      .map((ex) => ({ ex }));
  } else {
    const descomprimido = descomprimirComTeto(lidos.get("c")!, TETO_DESCOMPRIMIDO);
    if (descomprimido.tipo === "grande") return invalida("os programas do link são grandes demais");
    if (descomprimido.tipo === "cortado" || !descomprimido.texto) return invalida("os programas do link estão cortados");
    try {
      brutos = JSON.parse(descomprimido.texto);
    } catch {
      return invalida("os programas do link estão cortados");
    }
  }
  const programas = lerProgramas(brutos);
  if (typeof programas === "string") return invalida(programas);

  const modo = lidos.get("m") ?? "assistir";
  if (!(MODOS_DO_LINK as readonly string[]).includes(modo)) return invalida("o modo da atividade não existe");
  const f = lidos.get("f") ?? "alt";
  const formatos: Record<string, Formato> = { alt: "alternativas", alternativas: "alternativas", livre: "livre" };
  if (!(f in formatos)) return invalida("o formato das perguntas não existe");

  // Sem sala no link (um link escrito à mão), o aluno digita a que o professor falar.
  const sala = normalizarSala(lidos.get("sala") ?? "");
  if (sala !== "" && !PADRAO_SALA.test(sala)) return invalida("o código da sala não está no formato certo");

  const padraoDoId = programas.map((programa) => ("ex" in programa ? programa.ex : "prog")).join("-").slice(0, 32);
  const id = lidos.get("id") ?? (lidos.has("a") ? padraoDoId : "atividade");
  if (!PADRAO_ATIVIDADE.test(id)) return invalida("o nome da atividade não está no formato certo");

  const s = lidos.get("s") ?? "0";
  if (!/^\d{1,10}$/.test(s) || Number(s) > SEMENTE_MAXIMA) return invalida("a semente não está no formato certo");

  return { tipo: "atividade", atividade: { v: 1, id, programas, modo: modo as ModoDoLink, formato: formatos[f], sala, semente: Number(s) } };
}

// --- Os programas de uma atividade, prontos para o palco ----------------------------

export type ProgramaPronto = { titulo: string; codigo: string; entradas: string; exemplo: string | null };

/** O título do exemplo sem o número do menu ('3. Repetição com for' vira 'Repetição com for'). */
function semNumero(titulo: string): string {
  return titulo.replace(/^\d+\.\s*/, "");
}

export function abrirPrograma(programa: ProgramaDoLink): ProgramaPronto {
  if ("ex" in programa) {
    const exemplo = exemploPorId(programa.ex);
    if (!exemplo) throw new Error(`exemplo desconhecido: ${programa.ex}`);
    const entradas = programa.entradas ? programa.entradas.join("\n") : (exemplo.entradas ?? "");
    return { titulo: semNumero(exemplo.titulo), codigo: exemplo.codigo, entradas, exemplo: exemplo.id };
  }
  return { titulo: "Programa do professor", codigo: programa.codigo, entradas: (programa.entradas ?? []).join("\n"), exemplo: null };
}

// --- A atividade como arquivo (quando o link não cabe no chat) ----------------------

export const FORMATO_DO_ARQUIVO = "pyvis-atividade";

export function arquivoDaAtividade(atividade: AtividadeLink): { nome: string; conteudo: string } {
  const conteudo = JSON.stringify({ formato: FORMATO_DO_ARQUIVO, v: 1, link: codificarAtividade(atividade) }, null, 2);
  return { nome: `atividade-${atividade.id}.json`, conteudo };
}

/** O arquivo de atividade passa pela mesma conferência do link. */
export function lerArquivoDaAtividade(texto: string): LeituraDoLink {
  let dados: unknown;
  try {
    dados = JSON.parse(texto);
  } catch {
    return invalida("o arquivo não é de uma atividade do PyVis");
  }
  const arquivo = dados as { formato?: unknown; link?: unknown } | null;
  if (!arquivo || arquivo.formato !== FORMATO_DO_ARQUIVO || typeof arquivo.link !== "string") return invalida("o arquivo não é de uma atividade do PyVis");
  const lido = lerAtividade(arquivo.link);
  return lido.tipo === "nenhuma" ? invalida("o arquivo não tem programas") : lido;
}

// --- Valores novos para o professor -------------------------------------------------

// Sem letras e números que se confundem quando ditos ou lidos (0/O, 1/I/L, 5/S, 2/Z, 8/B).
const LETRAS_DA_SALA = "ACDEFGHJKMNPQRTUVWXY34679";

function sorteio(quantos: number): Uint32Array {
  return globalThis.crypto.getRandomValues(new Uint32Array(quantos));
}

/** Um código curto para falar em voz alta na aula, como 'K7PX'. */
export function novaSala(tamanho = 4): string {
  return [...sorteio(tamanho)].map((n) => LETRAS_DA_SALA[n % LETRAS_DA_SALA.length]).join("");
}

export function novaSemente(): number {
  return sorteio(1)[0] % 1_000_000;
}

/** O nome padrão da atividade: 'aula-0610' para 6 de outubro. */
export function idPadrao(data = new Date()): string {
  const dois = (n: number) => String(n).padStart(2, "0");
  return `aula-${dois(data.getDate())}${dois(data.getMonth() + 1)}`;
}
