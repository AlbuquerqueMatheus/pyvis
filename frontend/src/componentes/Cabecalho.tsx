import type { ReactNode } from "react";
import type { EstadoDoMotor } from "../motor/useMotor";

export const STATUS: Record<EstadoDoMotor, string> = {
  carregando: "Preparando o Python...",
  pronto: "Python pronto!",
  ocupado: "Executando...",
  falhou: "Não foi possível carregar o Python. Recarregue a página.",
};

type Props = {
  /** O estado do Python; sem ele (telas que não rodam código), o cabeçalho não mostra status. */
  estado?: EstadoDoMotor;
  subtitulo?: string;
  /** A marca leva ao uso livre. Numa atividade ela não é link: um toque não tira o aluno da aula. */
  linkParaInicio?: boolean;
  /** Uma segunda linha (o apelido e os botões da sala). */
  children?: ReactNode;
  /** Preso no alto da tela grande ('Sair e apagar' sempre à vista). No celular a tela é curta e ele rola. */
  fixo?: boolean;
};

export function Cabecalho({ estado, subtitulo, linkParaInicio = false, children, fixo = false }: Props) {
  const marca = (
    <>
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destaque font-bold text-primaria" aria-hidden="true">
        Py
      </span>
      <span className="flex flex-col leading-tight">
        <span className="text-xl font-bold">PyVis</span>
        {subtitulo && <span className="text-sm text-blue-100">{subtitulo}</span>}
      </span>
    </>
  );
  return (
    // z-[55]: acima do balão de palpite preso ao código (50), abaixo das janelas (60).
    <header className={`bg-primaria px-4 py-3 text-white shadow ${fixo ? "lg:sticky lg:top-0 lg:z-[55]" : ""}`}>
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <h1 className="m-0">
          {linkParaInicio ? (
            <a href="#" className="flex items-center gap-3 rounded-lg focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque" aria-label="PyVis: ir para o início">
              {marca}
            </a>
          ) : (
            <span className="flex items-center gap-3">{marca}</span>
          )}
        </h1>
        {estado && (
          <span className="text-right text-sm" aria-live="polite">
            {STATUS[estado]}
          </span>
        )}
      </div>
      {children && <div className="mx-auto mt-2 flex max-w-7xl flex-wrap items-center gap-2">{children}</div>}
    </header>
  );
}
