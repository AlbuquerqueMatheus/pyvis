import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import type { AtividadeLink } from "../motor/tipos";
import type { Motor } from "../motor/useMotor";
import { novoSujeito } from "../sala/armazenamento";
import { PADRAO_SALA, normalizarSala } from "../sala/link";
import { IlustracaoApagar, IlustracaoProfessor, IlustracaoSemNome } from "./Ilustracoes";

type Props = {
  atividade: AtividadeLink;
  pedir: Motor["pedir"];
  /** O Python carregou de vez? Sem ele não há apelido. */
  falhou: boolean;
  aoEntrar: (dados: { sala: string; sujeito: string; apelido: string }) => void;
};

/** Quantos apelidos o aluno vê de cada vez, e o máximo que o motor sugere. */
const POR_VEZ = 4;
const MAXIMO = 20;

export const AVISO = ["O professor vê suas respostas desta aula.", "Não pedimos seu nome.", "Você pode apagar tudo deste aparelho."];

const botaoPrimario =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-green-700 px-5 py-3 text-lg font-bold text-white shadow transition hover:bg-green-800 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50";

/**
 * A porta da sala (spec 2.5): o aviso de 3 frases, o apelido gerado (que o
 * aluno pode trocar por outro da lista) e o código da sala que o professor
 * fala na aula. Nada é guardado antes de 'Começar'.
 */
export function Entrada({ atividade, pedir, falhou, aoEntrar }: Props) {
  const ids = useId();
  // Um sujeito novo para esta sala: o apelido sai dele e é sempre o mesmo para ele.
  const [sujeito] = useState(novoSujeito);
  const [apelidos, setApelidos] = useState<string[] | null>(null);
  const [quantos, setQuantos] = useState(POR_VEZ);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let vivo = true;
    pedir("sugerir_apelidos", { semente: sujeito, quantidade: quantos }).then(
      (lista) => {
        if (!vivo) return;
        setApelidos(lista);
        setEscolhido((atual) => atual ?? lista[0]);
      },
      () => {
        // sem resposta, o botão Começar continua desabilitado e o cabeçalho diz o que houve
      },
    );
    return () => {
      vivo = false;
    };
  }, [pedir, sujeito, quantos]);

  function comecar(evento: FormEvent) {
    evento.preventDefault();
    const digitado = normalizarSala(codigo);
    let problema: string | null = null;
    if (digitado === "") problema = "Digite o código da sala.";
    else if (atividade.sala && digitado !== atividade.sala) problema = "Esse não é o código desta sala. Confira com o professor.";
    else if (!PADRAO_SALA.test(digitado)) problema = "O código tem de 2 a 16 letras ou números.";
    setErro(problema);
    if (problema) {
      campo.current?.focus();
      return;
    }
    if (escolhido) aoEntrar({ sala: atividade.sala || digitado, sujeito, apelido: escolhido });
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <section aria-labelledby={`${ids}-aviso`} className="rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <h2 id={`${ids}-aviso`} className="text-xl font-bold text-primaria">
          Antes de começar
        </h2>
        <ul className="mt-3 flex flex-col gap-3">
          {[IlustracaoProfessor, IlustracaoSemNome, IlustracaoApagar].map((Desenho, k) => (
            <li key={k} className="flex items-center gap-4">
              <Desenho />
              <span className="text-lg">{AVISO[k]}</span>
            </li>
          ))}
        </ul>
        <a
          href="#/pais"
          target="_blank"
          rel="noopener"
          className="mt-4 inline-flex min-h-11 items-center rounded px-1 text-secundaria underline decoration-2 underline-offset-2 hover:text-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          Para pais e responsáveis: o que fica guardado
        </a>
      </section>

      <form onSubmit={comecar} noValidate className="flex flex-col gap-5 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <fieldset className="flex flex-col gap-2">
          <legend className="text-lg font-bold text-primaria">Seu apelido nesta sala</legend>
          {apelidos && escolhido ? (
            <>
              <p className="text-gray-700">
                Você vai aparecer como <strong className="rounded-lg bg-destaque/30 px-2 py-0.5 text-xl text-primaria">{escolhido}</strong>
              </p>
              <p className="mt-1 text-sm text-gray-700">Se quiser, troque por outro da lista:</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {apelidos.map((apelido) => (
                  <label
                    key={apelido}
                    className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border-2 border-gray-300 px-3 has-[:checked]:border-primaria has-[:checked]:bg-blue-50 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque"
                  >
                    <input type="radio" name={`${ids}-apelido`} value={apelido} checked={escolhido === apelido} onChange={() => setEscolhido(apelido)} className="sr-only" />
                    <span aria-hidden="true">{escolhido === apelido ? "●" : "○"}</span>
                    {apelido}
                  </label>
                ))}
              </div>
              {apelidos.length < MAXIMO && (
                <button type="button" className={`${botaoSecundario} self-start`} onClick={() => setQuantos((n) => Math.min(MAXIMO, n + POR_VEZ))}>
                  Ver outros apelidos
                </button>
              )}
            </>
          ) : (
            <p className="text-gray-700" aria-live="polite">
              {falhou ? "Não deu para criar o apelido. Recarregue a página." : "Criando seu apelido..."}
            </p>
          )}
        </fieldset>

        <div className="flex flex-col gap-1">
          <label htmlFor={`${ids}-sala`} className="text-lg font-bold text-primaria">
            Código da sala
          </label>
          <p id={`${ids}-dica`} className="text-sm text-gray-700">
            O professor fala o código na aula.
          </p>
          <input
            ref={campo}
            id={`${ids}-sala`}
            value={codigo}
            onChange={(e) => {
              setCodigo(e.target.value);
              setErro(null);
            }}
            maxLength={20}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-invalid={erro ? true : undefined}
            aria-describedby={erro ? `${ids}-dica ${ids}-erro` : `${ids}-dica`}
            className="mt-1 min-h-11 max-w-xs rounded-lg border-2 border-gray-300 px-3 font-mono text-xl uppercase tracking-widest focus-visible:border-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
          />
          {erro && (
            <p id={`${ids}-erro`} role="alert" className="font-semibold text-red-800">
              <span aria-hidden="true">✗ </span>
              {erro}
            </p>
          )}
        </div>

        <button type="submit" className={`${botaoPrimario} self-start`} disabled={!escolhido}>
          Começar ▶
        </button>
      </form>
    </main>
  );
}
