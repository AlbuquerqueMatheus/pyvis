// Desenhos simples do aviso de entrada (spec 2.5): um para cada frase. São
// decoração (aria-hidden); a frase ao lado diz tudo.

import type { ReactNode } from "react";

const traco = { fill: "none", stroke: "currentColor", strokeWidth: 2.5, strokeLinecap: "round", strokeLinejoin: "round" } as const;

function Moldura({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-blue-50 text-primaria" aria-hidden="true">
      <svg viewBox="0 0 48 48" width="40" height="40">
        {children}
      </svg>
    </span>
  );
}

/** O professor olhando as respostas: um quadro com ✓ e um olho. */
export function IlustracaoProfessor() {
  return (
    <Moldura>
      <rect x="5" y="7" width="26" height="20" rx="3" {...traco} />
      <path d="M11 17l4 4 8-8" {...traco} />
      <path d="M22 37c3.5-5 8-7.5 12-7.5S42.5 32 46 37c-3.5 5-8 7.5-12 7.5S25.5 42 22 37z" {...traco} />
      <circle cx="34" cy="37" r="3" fill="currentColor" />
    </Moldura>
  );
}

/** Um crachá de nome riscado: o PyVis não pede o nome. */
export function IlustracaoSemNome() {
  return (
    <Moldura>
      <rect x="7" y="12" width="34" height="24" rx="4" {...traco} />
      <path d="M14 21h12M14 28h18" {...traco} />
      <path d="M6 42L42 6" {...traco} stroke="#c53030" />
    </Moldura>
  );
}

/** Uma lixeira: tudo pode ser apagado do aparelho. */
export function IlustracaoApagar() {
  return (
    <Moldura>
      <path d="M10 13h28M19 13V9h10v4M14 13l2 27h16l2-27" {...traco} />
      <path d="M21 19v15M27 19v15" {...traco} />
    </Moldura>
  );
}
