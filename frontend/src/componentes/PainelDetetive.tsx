import { useId } from "react";
import { trechosDeCodigo, type Camada } from "../motor/palco";
import type { Correcao, Ponto } from "../motor/tipos";

/** Texto do motor com o código (entre crases) em fonte de código. */
export function TextoComCodigo({ texto }: { texto: string }) {
  return (
    <>
      {trechosDeCodigo(texto).map((trecho, n) =>
        trecho.codigo ? (
          <code key={n} className="rounded bg-white/70 px-1 font-mono text-[0.95em] text-primaria">
            {trecho.texto}
          </code>
        ) : (
          <span key={n}>{trecho.texto}</span>
        ),
      )}
    </>
  );
}

type Props = {
  ponto: Ponto;
  correcao: Correcao;
  camadas: readonly Camada[];
  /** Depois de dois palpites diferentes do Python, 'Me mostra' vem em destaque, sem custo nenhum. */
  oferecerMeMostra: boolean;
  /** A caixinha que 'Onde olhar' contorna (já calculada pela página). */
  destacar: string | null;
  /** 'Onde olhar' levaria para depois de uma pergunta ainda aberta: a camada diz que vem depois. */
  ondeAdiante?: boolean;
  /** A frase longa do narrador no passo da pergunta: a camada 2 quando nenhum modelo explica o palpite. */
  narracao?: string;
  aoAbrir: (camada: Camada) => void;
};

const CAMADAS: { camada: Camada; icone: string; rotulo: string }[] = [
  { camada: 1, icone: "🔍", rotulo: "Onde olhar" },
  { camada: 2, icone: "📏", rotulo: "A regra" },
  { camada: 3, icone: "👀", rotulo: "Me mostra" },
];

/**
 * O Detetive (spec 2.3): quando o palpite foi diferente, a ideia provável por
 * trás dele e três camadas que o aluno abre se quiser. Quando nenhum modelo
 * explica o palpite, ele diz que não sabe e mostra o que a linha fez de
 * verdade, sem inventar uma ideia. Nada aqui mostra o id ou o nome técnico da concepção.
 */
export function PainelDetetive({ ponto, correcao, camadas, oferecerMeMostra, destacar, ondeAdiante = false, narracao = "", aoAbrir }: Props) {
  const base = useId();
  const feedback = correcao.feedback;
  // Sem modelo, a camada 2 é o narrador (o que a linha faz); sem os dois, ela não aparece.
  const disponiveis = CAMADAS.filter(({ camada }) => camada !== 2 || feedback !== null || narracao !== "");
  const adiante = ponto.tipo === "voltas" ? "Você vai ver isso no fim do laço, depois da próxima pergunta." : "Você vai ver isso depois da próxima pergunta.";
  const textos: Record<Camada, string> = {
    1: ondeAdiante ? adiante : destacar ? `Olhe a caixinha \`${destacar}\` neste passo.` : "Olhe a linha destacada neste passo.",
    2: feedback?.regra ?? narracao,
    3: feedback?.resolvido ?? (ponto.alvo.comando === null ? "Veja a tela no fim do programa." : "Veja o passo com o resultado."),
  };
  return (
    <section aria-label="Detetive" className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3">
      <p className="mb-1 text-xs font-bold uppercase tracking-wide text-amber-900">
        <span aria-hidden="true">🔎 </span>Detetive
      </p>
      {feedback ? (
        <p>
          <TextoComCodigo texto={feedback.resumo ?? feedback.regra} />
        </p>
      ) : (
        <>
          {/* Sem modelo, o Detetive não inventa uma ideia: diz que não sabe e mostra o que a linha fez. */}
          {!correcao.valor_certo && <p>Não sei bem o que levou a esse palpite.</p>}
          {!correcao.mensagem.includes(correcao.explicacao) && (
            <p>
              <TextoComCodigo texto={correcao.explicacao} />
            </p>
          )}
        </>
      )}
      <div className="mt-2 flex flex-wrap gap-2">
        {disponiveis.map(({ camada, icone, rotulo }) => {
          const aberta = camadas.includes(camada);
          const destaque = camada === 3 && oferecerMeMostra && !aberta;
          return (
            <button
              key={camada}
              type="button"
              aria-expanded={aberta}
              aria-controls={`${base}-${camada}`}
              onClick={() => aoAbrir(camada)}
              className={`inline-flex min-h-11 items-center gap-1.5 rounded-lg border-2 px-3 py-1.5 text-sm font-semibold transition focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque ${
                destaque
                  ? "border-primaria bg-primaria text-white hover:bg-secundaria"
                  : aberta
                    ? "border-secundaria bg-white text-primaria"
                    : "border-amber-400 bg-white text-amber-950 hover:border-secundaria"
              }`}
            >
              <span aria-hidden="true">{icone}</span>
              {rotulo}
            </button>
          );
        })}
      </div>
      {oferecerMeMostra && !camadas.includes(3) && <p className="mt-2 text-sm text-gray-800">Tudo bem ver o passo resolvido.</p>}
      {disponiveis.map(({ camada }) => (
        // scroll-mb: no celular, o texto que abre fica acima da barra fixa da linha do tempo (Palco rola até ele).
        <p
          key={camada}
          id={`${base}-${camada}`}
          data-camada={camada}
          hidden={!camadas.includes(camada)}
          className="mt-2 border-l-4 border-secundaria pl-2 max-lg:scroll-mb-48"
        >
          <TextoComCodigo texto={textos[camada]} />
        </p>
      ))}
    </section>
  );
}
