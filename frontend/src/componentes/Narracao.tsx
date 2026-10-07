import { useEffect, useRef, useState } from "react";
import type { Revelacao } from "../motor/cena";
import { narracaoVisivel } from "../motor/revelacao";
import type { Passo } from "../motor/tipos";

type Props = {
  passo: Passo | undefined;
  revelacao: Revelacao;
  /** Muda a cada vez que o aluno anda na linha do tempo: só então o leitor de tela fala. */
  movimento: number;
};

/** A frase do passo, sempre montada pela regra de revelação (nunca a frase inteira crua). */
export function Narracao({ passo, revelacao, movimento }: Props) {
  const [detalhes, setDetalhes] = useState(false);
  const curta = passo ? narracaoVisivel(passo, revelacao.respondidos, revelacao.alcancado, "curta").trim() : "";
  const longa = passo ? narracaoVisivel(passo, revelacao.respondidos, revelacao.alcancado, "longa").trim() : "";

  // O anúncio só muda quando o aluno anda; uma revelação no mesmo passo não fala por cima.
  const [anuncio, setAnuncio] = useState("");
  const ultimoMovimento = useRef(movimento);
  useEffect(() => {
    if (ultimoMovimento.current === movimento) return;
    ultimoMovimento.current = movimento;
    setAnuncio(detalhes ? longa : curta);
  }, [movimento, detalhes, curta, longa]);

  if (!curta) return null;
  return (
    <section aria-label="Narrador" className="rounded-xl border-l-4 border-secundaria bg-white p-3 shadow-sm">
      <p className="text-lg leading-snug">{curta}</p>
      {longa && longa !== curta && (
        <>
          <button
            type="button"
            className="mt-1 min-h-11 rounded-lg px-2 text-sm font-semibold text-secundaria underline-offset-2 hover:underline focus-visible:outline-3 focus-visible:outline-destaque"
            aria-expanded={detalhes}
            aria-controls="narracao-longa"
            onClick={() => setDetalhes(!detalhes)}
          >
            {detalhes ? "Menos detalhes" : "Mais detalhes"}
          </button>
          {detalhes && (
            <p id="narracao-longa" className="text-gray-700">
              {longa}
            </p>
          )}
        </>
      )}
      <div aria-live="polite" className="sr-only">
        {anuncio}
      </div>
    </section>
  );
}
