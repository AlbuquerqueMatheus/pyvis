// As telas do PyVis, escolhidas pelo fragmento da URL (nada vai a um servidor):
//   (vazio)      uso livre
//   #/criar      o professor monta uma atividade
//   #/pais       página para pais e responsáveis
//   #/praticar   exercícios gerados por tema (#/praticar?t=variaveis&n=1&s=123&p=a abre uma série)
//   #a=... #c=... uma atividade (sala/link.ts)

import { useEffect, useMemo, useState } from "react";
import type { AtividadeLink, Formato, NivelDePraticar } from "./motor/tipos";
import { lerAtividade } from "./sala/link";

export type Rota =
  | { tela: "livre" }
  | { tela: "criar" }
  | { tela: "pais" }
  | { tela: "praticar"; pedido: PedidoDePraticar }
  | { tela: "atividade"; atividade: AtividadeLink; fragmento: string }
  | { tela: "link_invalido"; motivo: string };

/**
 * O que o link da área Praticar pede. Tudo opcional: cada parâmetro inválido é
 * ignorado, e sem tema, nível e semente a página abre a escolha do tema.
 * O tema e a família só têm o formato conferido aqui; quem confere se existem
 * é a página, com o catálogo do motor (ele cresce sem mexer nesta tela).
 */
export type PedidoDePraticar = { tema?: string; nivel?: NivelDePraticar; semente?: number; familia?: string; formato?: Formato };

/** A maior semente da série: cabe num Uint32 (gerador.SEMENTE_MAXIMA no motor). */
export const SEMENTE_MAXIMA_DA_SERIE = 2 ** 32 - 1;
const ID = /^[a-z][a-z0-9_]{0,39}$/;
const NIVEIS: Record<string, NivelDePraticar> = { "1": 1, "2": 2, "3": 3 };
const FORMATOS: Record<string, Formato> = { a: "alternativas", l: "livre" };
const LETRA_DO_FORMATO: Record<Formato, string> = { alternativas: "a", livre: "l" };

function lerPraticar(consulta: string): PedidoDePraticar {
  const lidos = new URLSearchParams(consulta);
  const pedido: PedidoDePraticar = {};
  const t = lidos.get("t");
  if (t !== null && ID.test(t)) pedido.tema = t;
  const n = lidos.get("n");
  if (n !== null && Object.hasOwn(NIVEIS, n)) pedido.nivel = NIVEIS[n];
  const s = lidos.get("s");
  if (s !== null && /^\d{1,10}$/.test(s) && Number(s) <= SEMENTE_MAXIMA_DA_SERIE) pedido.semente = Number(s);
  const f = lidos.get("f");
  if (f !== null && ID.test(f)) pedido.familia = f;
  const p = lidos.get("p");
  if (p !== null && Object.hasOwn(FORMATOS, p)) pedido.formato = FORMATOS[p];
  return pedido;
}

/** O fragmento de uma série (#/praticar?t=...&n=...&s=...&p=...), o mesmo que lerRota lê de volta. */
export function fragmentoDePraticar(pedido: PedidoDePraticar): string {
  const partes: string[] = [];
  if (pedido.tema) partes.push(`t=${pedido.tema}`);
  if (pedido.nivel) partes.push(`n=${pedido.nivel}`);
  if (pedido.semente !== undefined) partes.push(`s=${pedido.semente}`);
  if (pedido.familia) partes.push(`f=${pedido.familia}`);
  if (pedido.formato) partes.push(`p=${LETRA_DO_FORMATO[pedido.formato]}`);
  return partes.length > 0 ? `#/praticar?${partes.join("&")}` : "#/praticar";
}

export function lerRota(hash: string): Rota {
  const fragmento = hash.replace(/^#/, "");
  if (fragmento === "/criar") return { tela: "criar" };
  if (fragmento === "/pais") return { tela: "pais" };
  if (fragmento === "/praticar") return { tela: "praticar", pedido: {} };
  if (fragmento.startsWith("/praticar?")) return { tela: "praticar", pedido: lerPraticar(fragmento.slice("/praticar?".length)) };
  const lido = lerAtividade(fragmento);
  if (lido.tipo === "atividade") return { tela: "atividade", atividade: lido.atividade, fragmento };
  if (lido.tipo === "invalida") return { tela: "link_invalido", motivo: lido.motivo };
  return { tela: "livre" };
}

/**
 * A rota do endereço e quantas navegações de verdade (hashchange) já houve nesta aba.
 *
 * O Praticar reescreve o endereço com history.replaceState (que não dispara
 * hashchange), então o hash guardado aqui pode ficar velho. Colar de novo o
 * link antigo dá um hash igual ao guardado e o React não redesenharia nada: a
 * contagem muda a cada hashchange, e a App usa ela na key da página.
 */
export function useRota(): { rota: Rota; navegacao: number } {
  const [estado, setEstado] = useState(() => ({ hash: window.location.hash, navegacao: 0 }));
  useEffect(() => {
    const mudar = () => setEstado(({ navegacao }) => ({ hash: window.location.hash, navegacao: navegacao + 1 }));
    window.addEventListener("hashchange", mudar);
    return () => window.removeEventListener("hashchange", mudar);
  }, []);
  const rota = useMemo(() => lerRota(estado.hash), [estado.hash]);
  return { rota, navegacao: estado.navegacao };
}
