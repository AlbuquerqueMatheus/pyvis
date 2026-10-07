import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";

type Props = {
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
  /** 'alerta' para uma confirmação (alertdialog); 'painel' para uma tela inteira no celular. */
  tipo?: "alerta" | "painel";
};

const FOCAVEIS = "button:not(:disabled), [href], input:not(:disabled), select, textarea, [tabindex]:not([tabindex='-1'])";

/**
 * Uma janela por cima da página. O foco entra nela, fica preso nela (Tab) e
 * volta para quem abriu; Esc fecha. As setas da linha do tempo não andam
 * enquanto ela está aberta (Controles ignora teclas dentro de [role=dialog]).
 */
export function Dialogo({ titulo, aoFechar, children, tipo = "painel" }: Props) {
  const idTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const fecharRef = useRef(aoFechar);
  fecharRef.current = aoFechar;

  useEffect(() => {
    const antes = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const elemento = caixa.current;
    // Numa confirmação, o foco começa no botão que não apaga nada.
    const inicial = elemento?.querySelector<HTMLElement>("[data-foco-inicial]") ?? elemento?.querySelector<HTMLElement>(FOCAVEIS) ?? elemento;
    inicial?.focus({ preventScroll: true });
    // A página atrás não rola enquanto a janela está aberta (no celular, ela ocupa a tela).
    const rolagem = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = rolagem;
      antes?.focus({ preventScroll: true });
    };
  }, []);

  function aoTeclar(evento: KeyboardEvent) {
    if (evento.key === "Escape") {
      evento.stopPropagation();
      fecharRef.current();
      return;
    }
    if (evento.key !== "Tab" || !caixa.current) return;
    const focaveis = [...caixa.current.querySelectorAll<HTMLElement>(FOCAVEIS)];
    if (focaveis.length === 0) return;
    const primeiro = focaveis[0];
    const ultimo = focaveis[focaveis.length - 1];
    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primeiro.focus();
    }
  }

  const tamanho = tipo === "alerta" ? "max-w-md" : "max-w-2xl max-sm:h-full max-sm:max-h-none max-sm:rounded-none";
  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && fecharRef.current()}>
      <div
        ref={caixa}
        role={tipo === "alerta" ? "alertdialog" : "dialog"}
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={aoTeclar}
        className={`flex max-h-[90vh] w-full flex-col overflow-hidden rounded-xl bg-white shadow-xl outline-none ${tamanho}`}
      >
        <div className="flex items-center justify-between gap-3 border-b border-gray-200 px-4 py-3">
          <h2 id={idTitulo} className="text-lg font-bold text-primaria">
            {titulo}
          </h2>
          {tipo === "painel" && (
            <button
              type="button"
              onClick={() => fecharRef.current()}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-xl text-gray-700 hover:bg-gray-100 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
              aria-label="Fechar"
            >
              ✕
            </button>
          )}
        </div>
        <div className="overflow-y-auto p-4">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
