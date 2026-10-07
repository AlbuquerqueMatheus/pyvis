import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { comAspas } from "../motor/palco";
import type { Correcao, Ponto, RespostaDoAluno } from "../motor/tipos";
import { TextoComCodigo } from "./PainelDetetive";
import { rolarAcimaDaBarra } from "./rolar";

/** O que o aluno já escolheu ou digitou: fica na página para não se perder se o balão mudar de lugar. */
export type Rascunho = { alternativa: string | null; texto: string };
export const RASCUNHO_VAZIO: Rascunho = { alternativa: null, texto: "" };

type Props = {
  ponto: Ponto;
  /** null enquanto a pergunta está aberta; depois, o retorno do Python. */
  correcao: Correcao | null;
  /** O palpite antes de rodar ('O que vai aparecer na tela?'). */
  inicial: boolean;
  /** Recado de uma resposta que não deu para ler (a pergunta continua aberta). */
  aviso: string | null;
  ocupado: boolean;
  rascunho: Rascunho;
  aoMudarRascunho: (rascunho: Rascunho) => void;
  aoResponder: (resposta: RespostaDoAluno) => void;
  aoPular: () => void;
  aoContinuar: () => void;
  /** Muda quando o aluno tenta passar sem responder: o foco volta para a pergunta. */
  atencao: number;
  /** O Detetive, quando o palpite foi diferente do Python. */
  detetive?: ReactNode;
  /** No fluxo da página (celular, aba Passos) em vez de preso à linha no editor. */
  embutido?: boolean;
};

const botaoPrimario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-primaria px-4 py-2 font-semibold text-white transition hover:bg-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-default disabled:opacity-40";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

function campoDeTexto(alvo: EventTarget) {
  return alvo instanceof HTMLElement && (alvo.tagName === "TEXTAREA" || (alvo.tagName === "INPUT" && (alvo as HTMLInputElement).type !== "radio"));
}

/** Num aparelho de toque não há Shift+Enter: lá o Enter da caixa de texto só pula linha. */
function telaDeToque() {
  return typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches;
}

/** Respostas curtas lado a lado; as médias só quando a tela é larga. */
function colunas(textos: string[]) {
  const maior = Math.max(0, ...textos.map((texto) => texto.length));
  return maior <= 6 ? "grid-cols-2" : maior <= 14 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1";
}

function focar(elemento: HTMLElement | null | undefined) {
  elemento?.focus({ preventScroll: true });
}

/**
 * O balão do modo Prever (spec 2.2). Pergunta com alternativas (teclas 1 a 4
 * escolhem, Enter confirma) ou com resposta livre (dois botões grandes,
 * 'número' e 'texto'; o texto ganha aspas sozinho). 'Pular' fica sempre à
 * vista. Depois da resposta: ✓ e o elogio, ou ✗, o que o Python fez e o
 * Detetive. Só o retorno é aria-live; nada de placar.
 */
export function BalaoPrevisao(props: Props) {
  const { ponto, correcao, inicial, aviso, ocupado, rascunho, aoMudarRascunho, aoResponder, aoPular, aoContinuar, atencao, detetive, embutido } = props;
  const base = useId();
  const raiz = useRef<HTMLElement>(null);
  const continuar = useRef<HTMLButtonElement>(null);
  const alternativas = ponto.formato === "alternativas" ? (ponto.alternativas ?? []) : null;
  const respondendo = correcao === null;

  // A pergunta pega o foco quando abre, quando o aluno tenta passar sem responder
  // e quando um aviso chega (o campo ficou desabilitado durante a correção).
  useEffect(() => {
    if (!respondendo) return;
    const elemento = raiz.current;
    // Com alternativas, o foco fica no balão, não na 1ª opção: as setas, que andam na linha do
    // tempo, marcariam outra opção sem o aluno perceber. Ele escolhe com 1 a 4, clique ou Tab.
    const campo = alternativas ? elemento?.querySelector<HTMLElement>("input:checked") : elemento?.querySelector<HTMLElement>("input, textarea");
    focar(campo ?? elemento);
    if (embutido) elemento?.scrollIntoView?.({ block: "nearest" });
  }, [ponto.id, respondendo, atencao, embutido, aviso]);

  // O retorno chegou: o foco vai para 'Continuar' (o texto do retorno é anunciado pela região viva).
  // No fluxo da página, o botão rola para fora de baixo da linha do tempo fixa (a margem do scroll-mb).
  useEffect(() => {
    if (respondendo) return;
    focar(continuar.current);
    if (embutido) rolarAcimaDaBarra(continuar.current);
  }, [respondendo, embutido]);

  function confirmar() {
    if (alternativas && rascunho.alternativa) aoResponder({ alternativa: rascunho.alternativa });
  }

  function escolher(id: string) {
    aoMudarRascunho({ ...rascunho, alternativa: id });
  }

  function aoTeclar(evento: KeyboardEvent<HTMLElement>) {
    if (!respondendo || !alternativas || ocupado) return;
    if (/^[1-9]$/.test(evento.key) && !campoDeTexto(evento.target)) {
      const alternativa = alternativas[Number(evento.key) - 1];
      if (!alternativa) return;
      evento.preventDefault();
      escolher(alternativa.id);
      focar(raiz.current?.querySelector<HTMLElement>(`input[value="${alternativa.id}"]`));
    } else if (evento.key === "Enter" && rascunho.alternativa && evento.target instanceof HTMLInputElement && evento.target.type === "radio") {
      evento.preventDefault();
      confirmar();
    }
  }

  const titulo = inicial ? (respondendo ? "Antes de rodar" : "Seu palpite antes de rodar") : "Palpite";
  const fonte = ponto.tipo === "decisao" ? "" : "font-mono";
  return (
    <section
      ref={raiz}
      data-balao="previsao"
      role="dialog"
      aria-labelledby={`${base}-pergunta`}
      tabIndex={-1}
      onKeyDown={aoTeclar}
      className={`balao-previsao relative rounded-xl border-2 border-secundaria bg-white p-3 text-base text-gray-900 shadow-lg ${
        // Preso ao código na tela grande, o balão não passa da coluna do código.
        embutido ? "w-full max-lg:scroll-mb-48" : "w-[min(34rem,calc(100vw-2rem))] lg:w-[min(34rem,calc(50vw-4rem))]"
      }`}
    >
      {embutido && !inicial && <span aria-hidden="true" className="balao-seta" />}
      <p className="text-xs font-bold uppercase tracking-wide text-secundaria">
        <span aria-hidden="true">? </span>
        {titulo}
      </p>
      <h2 id={`${base}-pergunta`} className="mt-0.5 text-lg font-bold leading-snug text-primaria">
        {ponto.pergunta}
      </h2>

      {respondendo && alternativas && (
        <fieldset className="mt-2" disabled={ocupado}>
          <legend className="sr-only">{ponto.pergunta}</legend>
          <div className={`grid gap-2 ${colunas(alternativas.map((a) => a.texto))}`}>
            {alternativas.map((alternativa, n) => {
              const marcada = rascunho.alternativa === alternativa.id;
              return (
                <label
                  key={alternativa.id}
                  className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border-2 px-2.5 py-1.5 transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque ${
                    marcada ? "border-primaria bg-blue-50" : "border-gray-300 bg-white hover:border-secundaria"
                  }`}
                >
                  <input
                    type="radio"
                    name={`${base}-alternativas`}
                    value={alternativa.id}
                    checked={marcada}
                    onChange={() => escolher(alternativa.id)}
                    className="sr-only"
                  />
                  <kbd aria-hidden="true" className="rounded border border-gray-400 bg-gray-50 px-1.5 text-xs text-gray-700">
                    {n + 1}
                  </kbd>
                  <span className={`min-w-0 flex-1 whitespace-pre-line break-words ${fonte}`}>{alternativa.texto}</span>
                  <span aria-hidden="true" className={marcada ? "text-primaria" : "text-gray-400"}>
                    {marcada ? "●" : "○"}
                  </span>
                </label>
              );
            })}
          </div>
          <p className="mt-1 text-xs text-gray-600 max-lg:hidden">
            Teclas 1 a {alternativas.length} escolhem. Enter confirma.
          </p>
        </fieldset>
      )}

      {respondendo && !alternativas && (
        <RespostaLivre ponto={ponto} inicial={inicial} rascunho={rascunho} aoMudarRascunho={aoMudarRascunho} aoResponder={aoResponder} ocupado={ocupado} base={base} />
      )}

      <div role="status" aria-live="polite" className="empty:hidden">
        {respondendo && aviso && (
          <p className="mt-2 rounded-lg bg-amber-50 px-2 py-1 text-amber-950">
            <span aria-hidden="true">⚠ </span>
            {aviso}
          </p>
        )}
        {correcao && <Retorno correcao={correcao} />}
      </div>

      {correcao && !correcao.certa && detetive}

      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        {respondendo ? (
          <>
            <button type="button" className={botaoSecundario} onClick={aoPular} disabled={ocupado}>
              Pular <span aria-hidden="true">↷</span>
            </button>
            {alternativas && (
              <button type="button" className={botaoPrimario} onClick={confirmar} disabled={!rascunho.alternativa || ocupado}>
                Confirmar
              </button>
            )}
          </>
        ) : (
          <button ref={continuar} type="button" className={`${botaoPrimario} max-lg:scroll-mb-48`} onClick={aoContinuar}>
            Continuar <span aria-hidden="true">▶</span>
          </button>
        )}
      </div>
    </section>
  );
}

/** ✓ ou ✗ sempre com texto ao lado: nada indicado só pela cor. */
function Retorno({ correcao }: { correcao: Correcao }) {
  return (
    <div className="mt-2">
      {correcao.certa ? (
        <p className="font-bold text-green-800">
          <span aria-hidden="true">✓ </span>Certo!
        </p>
      ) : (
        <p className="font-bold text-red-800">
          <span aria-hidden="true">✗ </span>Não foi isso.
        </p>
      )}
      <p className="whitespace-pre-line">
        <TextoComCodigo texto={correcao.mensagem} />
      </p>
    </div>
  );
}

type PropsLivre = {
  ponto: Ponto;
  inicial: boolean;
  rascunho: Rascunho;
  aoMudarRascunho: (rascunho: Rascunho) => void;
  aoResponder: (resposta: RespostaDoAluno) => void;
  ocupado: boolean;
  base: string;
};

/** Resposta livre: valor (número ou texto), número de voltas ou o que aparece na tela. */
function RespostaLivre({ ponto, inicial, rascunho, aoMudarRascunho, aoResponder, ocupado, base }: PropsLivre) {
  const texto = rascunho.texto;
  const vazio = texto.trim() === "";
  const mudar = (novo: string) => aoMudarRascunho({ ...rascunho, texto: novo });
  const id = `${base}-livre`;
  const campo = "mt-1 w-full rounded-lg border-2 border-gray-300 px-2 py-1.5 font-mono focus-visible:border-secundaria focus-visible:outline-3 focus-visible:outline-destaque";

  if (ponto.tipo === "valor") {
    const botao =
      "flex min-h-14 flex-col items-center justify-center rounded-lg border-2 border-primaria bg-white px-2 py-1 text-primaria transition hover:bg-blue-50 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-default disabled:opacity-40";
    return (
      <div className="mt-2">
        <label htmlFor={id} className="text-sm font-semibold">
          Seu palpite
        </label>
        <input
          id={id}
          value={texto}
          onChange={(e) => mudar(e.target.value)}
          disabled={ocupado}
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          className={campo}
          aria-describedby={`${id}-dica`}
        />
        <p id={`${id}-dica`} className="mt-1 text-sm text-gray-700">
          É número ou texto?
        </p>
        <div className="mt-1 grid grid-cols-2 gap-2">
          <button type="button" className={botao} disabled={vazio || ocupado} onClick={() => aoResponder({ texto, tipo_escolhido: "numero" })}>
            <span className="text-lg font-bold">número</span>
            <span className="sr-only">: </span>
            <span className="max-w-full truncate font-mono text-sm text-gray-800">{vazio ? " " : texto.trim()}</span>
          </button>
          <button type="button" className={botao} disabled={vazio || ocupado} onClick={() => aoResponder({ texto, tipo_escolhido: "texto" })}>
            <span className="text-lg font-bold">texto</span>
            <span className="sr-only">: </span>
            <span className="max-w-full truncate font-mono text-sm text-gray-800">{vazio ? " " : comAspas(texto)}</span>
          </button>
        </div>
      </div>
    );
  }

  const linhas = ponto.tipo === "saida";
  const enviar = () => {
    if (!vazio && !ocupado) aoResponder({ texto });
  };
  return (
    <div className="mt-2">
      <label htmlFor={id} className="text-sm font-semibold">
        Seu palpite
      </label>
      <div className="flex items-start gap-2">
        {linhas ? (
          <textarea
            id={id}
            value={texto}
            rows={inicial ? 3 : 1}
            onChange={(e) => mudar(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && (!telaDeToque() || e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                enviar();
              }
            }}
            disabled={ocupado}
            spellCheck={false}
            className={campo}
            aria-describedby={inicial ? `${id}-dica` : undefined}
          />
        ) : (
          <input
            id={id}
            value={texto}
            inputMode="numeric"
            onChange={(e) => mudar(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                enviar();
              }
            }}
            disabled={ocupado}
            autoComplete="off"
            className={`${campo} max-w-32`}
          />
        )}
        <button type="button" className={`${botaoPrimario} mt-1 shrink-0`} disabled={vazio || ocupado} onClick={enviar}>
          Confirmar
        </button>
      </div>
      {inicial && (
        <p id={`${id}-dica`} className="mt-1 text-xs text-gray-600">
          Uma linha da tela em cada linha.
        </p>
      )}
    </div>
  );
}
