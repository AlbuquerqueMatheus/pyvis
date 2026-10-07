import { useEffect } from "react";
import { textoDaVolta, type PilulaDaVolta } from "../motor/cena";

type Props = {
  passo: number;
  total: number;
  fim: boolean;
  volta: PilulaDaVolta | null;
  irPara: (passo: number) => void;
  /** Autoplay: só aparece quando a página sabe tocar e pausar. */
  tocando?: boolean;
  aoTocar?: (tocar: boolean) => void;
  /**
   * Com perguntas ainda abertas: o passo mais longe a que se pode ir agora. O total do
   * rastro diria o futuro (num laço simples, quantas voltas faltam), então ele some e a
   * barra vai só até aqui.
   */
  alcance?: number;
};

// Alvos de toque de 44 px (min-h-11 e min-w-11).
const botao =
  "inline-flex min-h-11 min-w-11 items-center justify-center gap-1 rounded-lg bg-secundaria px-3 py-2 font-medium text-white transition hover:bg-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-default disabled:opacity-40";

/** Teclas que já fazem outra coisa onde o foco está: digitar código, escolher numa lista, responder um palpite. */
function teclaDeOutroLugar(alvo: EventTarget | null) {
  if (!(alvo instanceof HTMLElement)) return false;
  return alvo.isContentEditable || alvo.closest("input, textarea, select, .cm-editor, [role='dialog']") !== null;
}

export function Controles({ passo, total, fim, volta, irPara, tocando = false, aoTocar, alcance }: Props) {
  // Setas do teclado andam na linha do tempo, de qualquer lugar fora do editor.
  useEffect(() => {
    if (total === 0) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.altKey || evento.ctrlKey || evento.metaKey || evento.defaultPrevented) return;
      if (teclaDeOutroLugar(evento.target)) return;
      const destinos: Record<string, number> = { ArrowRight: passo + 1, ArrowLeft: passo - 1 };
      const destino = destinos[evento.key];
      if (destino === undefined) return;
      evento.preventDefault();
      irPara(destino);
    }
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [passo, total, irPara]);

  if (total === 0) return null;
  const ultimo = passo === total - 1;
  const deTotal = alcance === undefined ? ` de ${total}` : "";
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-white p-2 shadow-sm sm:gap-2 sm:p-3">
      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        <button className={botao} onClick={() => irPara(0)} disabled={passo === 0} aria-label="Primeiro passo">
          ⏮
        </button>
        <button className={botao} onClick={() => irPara(passo - 1)} disabled={passo === 0} title="Seta para a esquerda" aria-keyshortcuts="ArrowLeft">
          ◀ <span className="max-sm:sr-only">Voltar</span>
        </button>
        {aoTocar && (
          <button
            className={botao}
            onClick={() => aoTocar(!tocando)}
            disabled={!tocando && ultimo}
            aria-pressed={tocando}
            title={tocando ? "Pausar" : "Tocar: anda sozinho"}
          >
            {tocando ? "⏸" : "▷"} <span className="max-sm:sr-only">{tocando ? "Pausar" : "Tocar"}</span>
          </button>
        )}
        <button
          className={botao}
          onClick={() => irPara(passo + 1)}
          disabled={ultimo}
          title="Seta para a direita"
          aria-keyshortcuts="ArrowRight"
          data-avancar=""
        >
          <span className="max-sm:sr-only">Avançar</span> ▶
        </button>
        <button className={botao} onClick={() => irPara(total - 1)} disabled={ultimo} aria-label="Último passo">
          ⏭
        </button>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2 text-sm text-gray-700">
          {volta && (
            <span
              className="rounded-full border-2 border-secundaria bg-blue-50 px-3 py-0.5 font-semibold text-primaria"
              aria-label={`${textoDaVolta(volta)}, no laço da linha ${volta.linha}`}
              title={`Laço da linha ${volta.linha}`}
            >
              ↻ {textoDaVolta(volta)}
            </span>
          )}
          <span>
            Passo {passo + 1}
            {deTotal}
            {fim && <span className="max-sm:sr-only"> (fim do programa)</span>}
          </span>
        </div>
      </div>
      <input
        type="range"
        min={0}
        max={alcance ?? total - 1}
        value={passo}
        onChange={(e) => irPara(Number(e.target.value))}
        aria-label="Linha do tempo da execução"
        aria-valuetext={`Passo ${passo + 1}${deTotal}`}
        className="h-11 w-full cursor-pointer accent-destaque"
      />
    </div>
  );
}
