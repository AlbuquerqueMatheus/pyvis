import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CriarCanal } from "../motor/ponte";
import type { AtividadeLink, ContextoDoEvento } from "../motor/tipos";
import { useMotor } from "../motor/useMotor";
import type { SalaGuardada } from "../sala/armazenamento";
import { abrirPrograma, codificarAtividade } from "../sala/link";
import { useDiario } from "../sala/useDiario";
import { Cabecalho } from "./Cabecalho";
import { Dialogo } from "./Dialogo";
import { Entrada } from "./Entrada";
import { MeuResumo } from "./MeuResumo";
import { Palco, type RegistroDoPalco } from "./Palco";

type Condicao = "prever" | "assistir";

type Props = { atividade: AtividadeLink; criarCanal?: CriarCanal };

const botaoDoCabecalho =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-white/70 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-white/10 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-40";
const botaoPerigo =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-red-700 px-4 py-2 font-semibold text-white transition hover:bg-red-800 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

/** O contexto comum de todos os eventos do aluno nesta atividade (o programa entra depois). */
function contextoDaSala(sala: SalaGuardada, atividade: AtividadeLink): ContextoDoEvento {
  return { sala: sala.sala, sujeito: sala.sujeito, atividade: atividade.id, programa: null, condicao: null, code_hash: null };
}

/**
 * Uma atividade aberta por link (spec 2.5): a entrada na sala, os programas
 * em sequência (cada um em Prever ou Assistir, como o link e o sorteio do
 * estudo decidem), 'Meu resumo' e 'Sair e apagar deste aparelho', sempre à vista.
 * Cada coisa que o palco conta vira um evento conferido pelo motor e guardado no diário da sala.
 */
export function PaginaDaAtividade({ atividade, criarCanal }: Props) {
  const motor = useMotor(criarCanal);
  const { pedir } = motor;
  const diario = useDiario(atividade.sala, pedir);
  const { registrar } = diario;
  const sala = diario.sala;
  const programas = useMemo(() => atividade.programas.map(abrirPrograma), [atividade]);
  const [indice, setIndice] = useState(0);
  const [condicoes, setCondicoes] = useState<{ sujeito: string; lista: Condicao[] } | null>(null);
  const [falhaNoSorteio, setFalhaNoSorteio] = useState(false);
  const [painel, setPainel] = useState<"resumo" | "apagar" | null>(null);
  const [apagou, setApagou] = useState(false);
  const hashes = useRef(new Map<number, Promise<string>>());
  const sessao = useRef<string | null>(null);
  // Depois de 'Começar', o foco vai para o nome do programa (senão cai no body e o leitor de tela se perde).
  const titulo = useRef<HTMLHeadingElement>(null);
  const focarTitulo = useRef(false);

  const sujeito = sala?.sujeito ?? null;

  // Prever ou Assistir em cada programa. No estudo, o motor sorteia metade de
  // cada (registro.sortear_condicoes), o mesmo sorteio sempre para o mesmo aluno.
  useEffect(() => {
    if (!sujeito) return;
    if (atividade.modo !== "estudo") {
      setCondicoes({ sujeito, lista: atividade.programas.map(() => atividade.modo as Condicao) });
      return;
    }
    let vivo = true;
    setFalhaNoSorteio(false);
    pedir("sortear_condicoes", { sujeito, atividade }).then(
      (lista) => vivo && setCondicoes({ sujeito, lista }),
      () => vivo && setFalhaNoSorteio(true),
    );
    return () => {
      vivo = false;
    };
  }, [sujeito, atividade, pedir]);

  // Cada vez que a página abre a sala é uma sessão nova no diário.
  useEffect(() => {
    if (!sala || sessao.current === sala.sujeito) return;
    sessao.current = sala.sujeito;
    registrar("Session.Start", contextoDaSala(sala, atividade));
  }, [sala, atividade, registrar]);

  const hashDe = useCallback(
    (k: number) => {
      let pedido = hashes.current.get(k);
      if (!pedido) {
        pedido = pedir("code_hash", { codigo: programas[k].codigo });
        hashes.current.set(k, pedido);
        pedido.catch(() => hashes.current.delete(k));
      }
      return pedido;
    },
    [pedir, programas],
  );

  const condicao = condicoes && condicoes.sujeito === sujeito ? (condicoes.lista[indice] ?? null) : null;

  const pronta = condicao !== null;
  useEffect(() => {
    if (!pronta || !focarTitulo.current) return;
    focarTitulo.current = false;
    titulo.current?.focus();
  }, [pronta]);

  // O palco conta o que aconteceu; aqui ganha o contexto da sala e do programa.
  const aoRegistrar = useCallback(
    (registro: RegistroDoPalco) => {
      if (!sala || !condicao) return;
      const { tipo, ...campos } = registro;
      const contexto = hashDe(indice).then((code_hash) => ({ ...contextoDaSala(sala, atividade), programa: indice, condicao, code_hash }));
      registrar(tipo, contexto, campos);
    },
    [sala, condicao, hashDe, indice, atividade, registrar],
  );

  function entrar(dados: { sala: string; sujeito: string; apelido: string }) {
    focarTitulo.current = true;
    diario.entrar(dados);
    setApagou(false);
    // Um link sem sala ganha a que o aluno digitou: recarregar a página volta para a mesma sala.
    if (!atividade.sala) window.history.replaceState(null, "", `#${codificarAtividade({ ...atividade, sala: dados.sala })}`);
  }

  function esquecerSala() {
    sessao.current = null;
    hashes.current.clear();
    setCondicoes(null);
    setIndice(0);
    setPainel(null);
    setApagou(true);
  }

  function apagar() {
    diario.apagar();
    esquecerSala();
  }

  // Apagada em outra aba (a página dos pais): esta aba também sai da sala.
  const apagadaDeFora = diario.apagadaDeFora;
  useEffect(() => {
    if (apagadaDeFora) esquecerSala();
  }, [apagadaDeFora]);

  const rodados = useMemo(
    () => new Set((sala?.eventos ?? []).filter((evento) => evento.tipo === "Run.Program" && evento.atividade === atividade.id).map((evento) => evento.programa)),
    [sala, atividade.id],
  );

  let conteudo;
  if (apagou) {
    conteudo = (
      <main className="mx-auto flex max-w-xl flex-col gap-4 p-4">
        <div role="status" className="rounded-xl border-2 border-green-700/40 bg-green-50 p-4">
          <p className="text-lg font-bold text-green-900">
            <span aria-hidden="true">✓ </span>Pronto! Nada desta sala ficou neste aparelho.
          </p>
          {apagadaDeFora && <p className="mt-1">Os dados foram apagados em outra página.</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={botaoSecundario} onClick={() => setApagou(false)}>
            Entrar de novo
          </button>
          <a href="#" className={botaoSecundario}>
            Ir para o PyVis
          </a>
        </div>
      </main>
    );
  } else if (!sala) {
    conteudo = <Entrada atividade={atividade} pedir={pedir} falhou={motor.estado === "falhou"} aoEntrar={entrar} />;
  } else if (!condicao) {
    conteudo = (
      <main className="mx-auto max-w-xl p-4">
        <p aria-live="polite" className="rounded-xl bg-white p-4 shadow-sm">
          {falhaNoSorteio || motor.estado === "falhou" ? "Não deu para preparar a atividade. Recarregue a página." : "Preparando a atividade..."}
        </p>
      </main>
    );
  } else {
    const programa = programas[indice];
    const ultimo = indice === programas.length - 1;
    const navegacao = (
      <div className="mx-auto max-w-7xl px-4 pt-4">
      <nav aria-label="Programas da atividade" className="flex flex-col gap-1 rounded-xl bg-white p-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">
            Programa {indice + 1} de {programas.length}
          </span>
          {programas.length > 1 && (
            <ol className="flex flex-wrap gap-1">
              {programas.map((outro, k) => (
                <li key={k}>
                  <button
                    type="button"
                    onClick={() => setIndice(k)}
                    aria-current={k === indice ? "step" : undefined}
                    aria-label={`Programa ${k + 1}: ${outro.titulo}${rodados.has(k) ? ", já rodou" : ""}`}
                    className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-0.5 rounded-lg border-2 px-2 font-semibold focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque ${
                      k === indice ? "border-primaria bg-primaria text-white" : "border-gray-300 bg-white text-primaria hover:border-secundaria"
                    }`}
                  >
                    {k + 1}
                    {rodados.has(k) && <span aria-hidden="true">✓</span>}
                  </button>
                </li>
              ))}
            </ol>
          )}
          <span className="ml-auto" />
          {ultimo ? (
            <button type="button" className={botaoSecundario} onClick={() => setPainel("resumo")}>
              Terminei: ver meu resumo
            </button>
          ) : (
            <button type="button" className={botaoSecundario} onClick={() => setIndice(indice + 1)}>
              Próximo programa ▶
            </button>
          )}
        </div>
        <h2 ref={titulo} tabIndex={-1} className="text-lg font-bold text-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque">
          {programa.titulo}
        </h2>
        <p className="text-sm text-gray-700">{condicao === "prever" ? "Aqui você dá palpites antes de ver cada passo." : "Aqui você assiste o programa passo a passo."}</p>
      </nav>
      </div>
    );
    conteudo = (
      <main>
        {!diario.guardado && (
          <p role="status" className="mx-auto max-w-7xl px-4 pt-3 text-sm font-semibold text-red-800">
            <span aria-hidden="true">⚠ </span>Este aparelho não deixa guardar. Entregue antes de fechar a página.
          </p>
        )}
        {navegacao}
        <Palco
          key={indice}
          motor={motor}
          codigo={programa.codigo}
          entradas={programa.entradas}
          modo={condicao}
          formato={atividade.formato}
          semente={atividade.semente}
          aoRegistrar={aoRegistrar}
        />
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <Cabecalho estado={motor.estado} subtitulo={`Atividade ${atividade.id}`} fixo>
        {sala && !apagou && (
          <>
            <span className="rounded-lg bg-white/15 px-2 py-1 text-sm">
              Você é <strong>{sala.apelido}</strong>
              <span className="max-sm:sr-only"> · sala {sala.sala}</span>
            </span>
            <span className="flex flex-wrap gap-2 sm:ml-auto">
              <button type="button" className={botaoDoCabecalho} onClick={() => setPainel("resumo")}>
                Meu resumo
              </button>
              <button type="button" className={botaoDoCabecalho} onClick={() => setPainel("apagar")}>
                Sair e apagar deste aparelho
              </button>
            </span>
          </>
        )}
      </Cabecalho>

      {conteudo}

      {painel === "resumo" && sala && (
        <Dialogo titulo="Meu resumo" aoFechar={() => setPainel(null)}>
          <MeuResumo atividade={atividade} sala={sala} pedir={pedir} aoVoltar={() => setPainel(null)} aoApagar={() => setPainel("apagar")} />
        </Dialogo>
      )}
      {painel === "apagar" && sala && (
        <Dialogo titulo="Sair e apagar deste aparelho?" tipo="alerta" aoFechar={() => setPainel(null)}>
          <p>Seu apelido e suas respostas desta sala somem deste aparelho.</p>
          <p className="mt-2 font-semibold">Ainda não entregou? Entregue antes de apagar.</p>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <button type="button" className={botaoSecundario} onClick={() => setPainel(null)} data-foco-inicial="">
              Cancelar
            </button>
            <button type="button" className={botaoPerigo} onClick={apagar}>
              Sim, apagar
            </button>
          </div>
        </Dialogo>
      )}
    </div>
  );
}
