// As telas do PyVis, escolhidas pelo fragmento da URL (nada vai a um servidor):
//   (vazio)      uso livre
//   #/criar      o professor monta uma atividade
//   #/pais       página para pais e responsáveis
//   #a=... #c=... uma atividade (sala/link.ts)

import { useEffect, useMemo, useState } from "react";
import type { AtividadeLink } from "./motor/tipos";
import { lerAtividade } from "./sala/link";

export type Rota =
  | { tela: "livre" }
  | { tela: "criar" }
  | { tela: "pais" }
  | { tela: "atividade"; atividade: AtividadeLink; fragmento: string }
  | { tela: "link_invalido"; motivo: string };

export function lerRota(hash: string): Rota {
  const fragmento = hash.replace(/^#/, "");
  if (fragmento === "/criar") return { tela: "criar" };
  if (fragmento === "/pais") return { tela: "pais" };
  const lido = lerAtividade(fragmento);
  if (lido.tipo === "atividade") return { tela: "atividade", atividade: lido.atividade, fragmento };
  if (lido.tipo === "invalida") return { tela: "link_invalido", motivo: lido.motivo };
  return { tela: "livre" };
}

export function useRota(): Rota {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const mudar = () => setHash(window.location.hash);
    window.addEventListener("hashchange", mudar);
    return () => window.removeEventListener("hashchange", mudar);
  }, []);
  return useMemo(() => lerRota(hash), [hash]);
}
