import { useEffect, useState, type ReactNode } from "react";
import { VALIDADE_MS, apagarSala, apagarTudo, salasGuardadas, venceEm, type SalaGuardada } from "../sala/armazenamento";
import { Cabecalho } from "./Cabecalho";

const DIAS_DE_VALIDADE = Math.round(VALIDADE_MS / (24 * 60 * 60 * 1000));

const botaoPerigo =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-red-700 px-4 py-2 font-semibold text-white transition hover:bg-red-800 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

function data(ms: number) {
  return new Date(ms).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="text-lg font-bold text-primaria">{titulo}</h2>
      <div className="mt-2 flex flex-col gap-2 text-gray-800">{children}</div>
    </section>
  );
}

/**
 * A página para pais e responsáveis (spec 2.5, LGPD art. 14): o que o PyVis
 * guarda, onde, por quanto tempo e como apagar, em linguagem simples. Mostra
 * as salas guardadas neste aparelho e apaga cada uma, ou todas.
 */
export function PaginaDosPais() {
  const [salas, setSalas] = useState<SalaGuardada[]>(() => salasGuardadas());
  const [aviso, setAviso] = useState<string | null>(null);

  // Uma aba da atividade pode guardar ou apagar enquanto esta está aberta.
  useEffect(() => {
    const atualizar = () => setSalas(salasGuardadas());
    window.addEventListener("storage", atualizar);
    return () => window.removeEventListener("storage", atualizar);
  }, []);

  function apagarUma(sala: string) {
    apagarSala(sala);
    setSalas(salasGuardadas());
    setAviso(`A sala ${sala} foi apagada deste aparelho.`);
  }

  function apagarTodas() {
    apagarTudo();
    setSalas(salasGuardadas());
    setAviso("Tudo o que o PyVis guardou neste aparelho foi apagado.");
  }

  return (
    <div className="min-h-screen">
      <Cabecalho subtitulo="Para pais e responsáveis" linkParaInicio />
      <main className="mx-auto flex max-w-3xl flex-col gap-4 p-4">
        <p className="text-lg">
          O PyVis é um site para aprender a programar em Python. Ele mostra o programa rodando passo a passo e pede palpites ao aluno. Tudo roda no navegador deste
          aparelho.
        </p>

        <Secao titulo="O que fica guardado">
          <p>Só nas atividades de uma sala, abertas pelo link do professor. Fora delas, nada é guardado.</p>
          <ul className="ml-5 list-disc">
            <li>Um apelido sorteado, como “Tucano Azul 7”.</li>
            <li>O código da sala e um número aleatório que separa este aluno dos outros.</li>
            <li>O que o aluno fez: se cada palpite foi certo, qual alternativa escolheu ou que número digitou, quais explicações abriu e quanto tempo levou.</li>
          </ul>
        </Secao>

        <Secao titulo="O que nunca fica guardado">
          <ul className="ml-5 list-disc">
            <li>Nome, e-mail, telefone, foto ou escola.</li>
            <li>O código que o aluno escreveu e as respostas que ele digitou para o programa.</li>
            <li>Textos escritos pelo aluno. De um palpite com letras, só fica se estava certo ou não.</li>
          </ul>
        </Secao>

        <Secao titulo="Onde fica e quem vê">
          <p>Fica só neste aparelho, no navegador. O PyVis não manda nada para a internet sozinho.</p>
          <p>
            Os dados só saem quando o aluno toca em “Entregar ao professor”. Isso baixa um arquivo, que o aluno envia ao professor. O professor vê o apelido, não o nome.
          </p>
          <p>Mesmo com apelido, isso é dado pessoal pela LGPD. Dúvidas? Fale com o professor ou com a escola.</p>
        </Secao>

        <Secao titulo="Por quanto tempo">
          <p>Se uma sala ficar {DIAS_DE_VALIDADE} dias sem uso neste aparelho, tudo dela é apagado sozinho.</p>
        </Secao>

        <Secao titulo="Como apagar">
          <p>O aluno pode tocar em “Sair e apagar deste aparelho” durante a atividade. Vocês também podem apagar aqui:</p>
          {salas.length > 0 ? (
            <>
              <ul className="flex flex-col gap-2">
                {salas.map((sala) => (
                  <li key={sala.sala} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 p-3">
                    <span>
                      Sala <strong className="font-mono">{sala.sala}</strong>, apelido <strong>{sala.apelido}</strong>. {sala.eventos.length}{" "}
                      {sala.eventos.length === 1 ? "registro" : "registros"}. Apaga sozinho em{" "}
                      {data(venceEm(sala))}.
                    </span>
                    <button type="button" className={botaoSecundario} onClick={() => apagarUma(sala.sala)} aria-label={`Apagar a sala ${sala.sala}`}>
                      Apagar esta sala
                    </button>
                  </li>
                ))}
              </ul>
              <button type="button" className={`${botaoPerigo} self-start`} onClick={apagarTodas}>
                Apagar tudo do PyVis deste aparelho
              </button>
            </>
          ) : (
            <p className="font-semibold">Neste aparelho não há nada guardado pelo PyVis.</p>
          )}
          <p aria-live="polite" className="font-semibold text-green-800">
            {aviso && (
              <>
                <span aria-hidden="true">✓ </span>
                {aviso}
              </>
            )}
          </p>
          <p className="text-sm text-gray-700">Limpar os dados de navegação deste site no navegador também apaga tudo.</p>
        </Secao>

        <a
          href="#"
          className="inline-flex min-h-11 items-center self-start rounded-lg bg-primaria px-4 font-semibold text-white focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          Ir para o PyVis
        </a>
      </main>
    </div>
  );
}
