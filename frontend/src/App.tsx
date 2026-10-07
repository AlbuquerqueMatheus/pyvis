import { useEffect } from "react";
import { MotionConfig } from "motion/react";
import { Cabecalho } from "./componentes/Cabecalho";
import { CriarAtividade } from "./componentes/CriarAtividade";
import { PaginaDaAtividade } from "./componentes/PaginaDaAtividade";
import { PaginaDosPais } from "./componentes/PaginaDosPais";
import { UsoLivre } from "./componentes/UsoLivre";
import type { CriarCanal } from "./motor/ponte";
import { useRota, type Rota } from "./rotas";
import { limparVencidas } from "./sala/armazenamento";

type Props = { criarCanal?: CriarCanal };

const TITULOS: Record<Rota["tela"], string> = {
  livre: "PyVis",
  criar: "Criar atividade · PyVis",
  pais: "Para pais e responsáveis · PyVis",
  atividade: "Atividade · PyVis",
  link_invalido: "Link quebrado · PyVis",
};

function LinkInvalido({ motivo }: { motivo: string }) {
  return (
    <div className="min-h-screen">
      <Cabecalho linkParaInicio />
      <main className="mx-auto max-w-xl p-4">
        <div role="alert" className="rounded-xl border-2 border-red-300 bg-red-50 p-4">
          <p className="text-lg font-bold text-red-800">Este link de atividade não abriu.</p>
          <p className="mt-1">Peça um link novo ao professor.</p>
          <p className="mt-3 text-sm text-gray-700">Para o professor: {motivo}.</p>
        </div>
        <a
          href="#"
          className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-primaria px-4 font-semibold text-white focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          Ir para o PyVis
        </a>
      </main>
    </div>
  );
}

/**
 * O PyVis inteiro: a tela vem do fragmento da URL (rotas.ts). Só o uso livre e
 * a atividade carregam o Python; a tela do professor e a dos pais não rodam código.
 */
export default function App({ criarCanal }: Props = {}) {
  const rota = useRota();

  // A limpeza ao abrir (spec 2.5): sala sem uso há 30 dias sai do aparelho.
  useEffect(() => {
    limparVencidas();
  }, []);

  useEffect(() => {
    document.title = TITULOS[rota.tela];
  }, [rota.tela]);

  return (
    <MotionConfig reducedMotion="user">
      {rota.tela === "livre" && <UsoLivre criarCanal={criarCanal} />}
      {rota.tela === "criar" && <CriarAtividade />}
      {rota.tela === "pais" && <PaginaDosPais />}
      {rota.tela === "atividade" && <PaginaDaAtividade key={rota.fragmento} atividade={rota.atividade} criarCanal={criarCanal} />}
      {rota.tela === "link_invalido" && <LinkInvalido motivo={rota.motivo} />}
    </MotionConfig>
  );
}
