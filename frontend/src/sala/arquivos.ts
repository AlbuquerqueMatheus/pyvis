// Arquivos que saem do aparelho: a entrega ao professor e o arquivo da atividade.
//
// A entrega (spec 2.5) é um .json com o envelope do motor (montar_entrega:
// {v, apelido, eventos}) comprimido com lz-string. O mesmo texto comprimido é o
// "código da entrega", a reserva para colar num formulário sem login. Para ler
// no computador do professor: node frontend/scripts/ler-entrega.mjs <arquivos>.

import { compressToBase64, decompressFromBase64 } from "lz-string";
import type { Entrega } from "../motor/tipos";

export const FORMATO_DA_ENTREGA = "pyvis-entrega";

export type ArquivoDaEntrega = { nome: string; conteudo: string; codigo: string };

/** 'Libélula Anil 77' vira 'libelula-anil-77' (o nome do arquivo não leva acento nem espaço). */
export function semAcento(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function arquivoDaEntrega(entrega: Entrega, atividade: string): ArquivoDaEntrega {
  const codigo = compressToBase64(JSON.stringify(entrega));
  const conteudo = JSON.stringify({ formato: FORMATO_DA_ENTREGA, v: 1, lz: codigo });
  return { nome: `pyvis-${atividade}-${semAcento(entrega.apelido)}.json`, conteudo, codigo };
}

/** Lê o arquivo da entrega ou o código colado. Devolve null se não for uma entrega. */
export function lerEntrega(texto: string): Entrega | null {
  let codigo = texto.trim();
  let dado: unknown = null;
  try {
    dado = JSON.parse(codigo);
  } catch {
    // não é JSON: pode ser o código colado
  }
  if (typeof dado === "object" && dado !== null) {
    const arquivo = dado as { formato?: unknown; lz?: unknown };
    if (arquivo.formato !== FORMATO_DA_ENTREGA || typeof arquivo.lz !== "string") return null;
    codigo = arquivo.lz;
  }
  try {
    const entrega = JSON.parse(decompressFromBase64(codigo) || "null") as Entrega | null;
    return entrega && entrega.v === 1 && typeof entrega.apelido === "string" && Array.isArray(entrega.eventos) ? entrega : null;
  } catch {
    return null;
  }
}

/** Baixa um arquivo gerado na página. false quando o navegador não deixou. */
export function baixarArquivo(nome: string, conteudo: string, tipo = "application/json"): boolean {
  try {
    const url = URL.createObjectURL(new Blob([conteudo], { type: `${tipo};charset=utf-8` }));
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    // O navegador precisa da URL até o download começar.
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
    return true;
  } catch {
    return false;
  }
}

/** Copia para a área de transferência. false sem permissão (fora de https, por exemplo). */
export async function copiarTexto(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch {
    return false;
  }
}
