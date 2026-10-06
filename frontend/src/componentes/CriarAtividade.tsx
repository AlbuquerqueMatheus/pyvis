import { useId, useMemo, useRef, useState, type ReactNode } from "react";
import { EXEMPLOS, exemploPorId } from "../exemplos";
import { CENA_VAZIA } from "../motor/cena";
import type { AtividadeLink, Formato, ProgramaDoLink } from "../motor/tipos";
import { baixarArquivo, copiarTexto } from "../sala/arquivos";
import {
  LIMITE_DO_CHAT,
  MAX_CODIGO,
  MAX_ENTRADA,
  MAX_ENTRADAS,
  MAX_PROGRAMAS,
  PADRAO_ATIVIDADE,
  PADRAO_SALA,
  SEMENTE_MAXIMA,
  arquivoDaAtividade,
  idPadrao,
  linkDaAtividade,
  normalizarSala,
  novaSala,
  novaSemente,
} from "../sala/link";
import { Cabecalho } from "./Cabecalho";
import { Editor } from "./Editor";
import { Escolha, type Opcao } from "./Escolha";

type ProgramaEmEdicao =
  | { chave: number; tipo: "exemplo"; ex: string; entradas: string }
  | { chave: number; tipo: "codigo"; codigo: string; entradas: string };

type ModoSimples = "assistir" | "prever";

const MODOS: Opcao<ModoSimples>[] = [
  { valor: "assistir", rotulo: "Assistir" },
  { valor: "prever", rotulo: "Prever" },
];
const FORMATOS: Opcao<Formato>[] = [
  { valor: "alternativas", rotulo: "Alternativas (10 a 12 anos)" },
  { valor: "livre", rotulo: "Resposta livre (13 a 17 anos)" },
];

const botaoPrimario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-primaria px-4 py-2 font-semibold text-white transition hover:bg-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-40";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-40";
const botaoPequeno =
  "inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border-2 border-gray-300 bg-white px-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-30";
const campoDeTexto =
  "min-h-11 rounded-lg border-2 border-gray-300 px-3 py-1.5 focus-visible:border-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

function linhas(texto: string): string[] {
  return texto
    .split("\n")
    .map((linha) => linha.replace(/\r$/, ""))
    .filter((linha) => linha !== "");
}

function mesmas(a: string[], b: string[]) {
  return a.length === b.length && a.every((item, k) => item === b[k]);
}

/** O programa como vai no link: um exemplo só leva entradas se o professor trocou as dele. */
function paraOLink(programa: ProgramaEmEdicao): ProgramaDoLink {
  const entradas = linhas(programa.entradas);
  if (programa.tipo === "exemplo") {
    const doExemplo = linhas(exemploPorId(programa.ex)?.entradas ?? "");
    return mesmas(entradas, doExemplo) ? { ex: programa.ex } : { ex: programa.ex, entradas };
  }
  return entradas.length > 0 ? { codigo: programa.codigo, entradas } : { codigo: programa.codigo };
}

type Rascunho = {
  programas: ProgramaEmEdicao[];
  modo: ModoSimples;
  estudo: boolean;
  formato: Formato;
  sala: string;
  id: string;
  semente: string;
};

/** A atividade do rascunho, ou o que falta para ela existir. */
export function montarAtividade(rascunho: Rascunho): { atividade: AtividadeLink | null; problemas: string[] } {
  const problemas: string[] = [];
  if (rascunho.programas.length === 0) problemas.push("Escolha pelo menos um programa.");
  if (rascunho.programas.length > MAX_PROGRAMAS) problemas.push(`Use no máximo ${MAX_PROGRAMAS} programas.`);
  rascunho.programas.forEach((programa, k) => {
    if (programa.tipo === "codigo" && programa.codigo.trim() === "") problemas.push(`O programa ${k + 1} está vazio.`);
    if (programa.tipo === "codigo" && programa.codigo.length > MAX_CODIGO) problemas.push(`O programa ${k + 1} é grande demais.`);
    const entradas = linhas(programa.entradas);
    if (entradas.length > MAX_ENTRADAS || entradas.some((entrada) => entrada.length > MAX_ENTRADA)) problemas.push(`As entradas do programa ${k + 1} passaram do limite.`);
  });
  const sala = normalizarSala(rascunho.sala);
  if (!PADRAO_SALA.test(sala)) problemas.push("O código da sala precisa de 2 a 16 letras, números ou hífen.");
  if (!PADRAO_ATIVIDADE.test(rascunho.id)) problemas.push("O nome da atividade usa só letras sem acento, números, - e _ (até 32).");
  const semente = Number(rascunho.semente);
  if (!/^\d{1,10}$/.test(rascunho.semente) || semente > SEMENTE_MAXIMA) problemas.push(`A semente é um número inteiro de 0 a ${SEMENTE_MAXIMA}.`);
  if (problemas.length > 0) return { atividade: null, problemas };
  return {
    atividade: {
      v: 1,
      id: rascunho.id,
      programas: rascunho.programas.map(paraOLink),
      modo: rascunho.estudo ? "estudo" : rascunho.modo,
      formato: rascunho.formato,
      sala,
      semente,
    },
    problemas,
  };
}

function Secao({ numero, titulo, children }: { numero: number; titulo: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm">
      <h2 id={id} className="text-lg font-bold text-primaria">
        <span aria-hidden="true" className="mr-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-primaria text-sm text-white">
          {numero}
        </span>
        {titulo}
      </h2>
      {children}
    </section>
  );
}

/**
 * A tela do professor (spec 2.5): escolhe os programas (exemplos pelo id ou
 * código próprio), as entradas, o modo, o formato das perguntas, a sala e se
 * a atividade é do estudo, e recebe um link para copiar. Nada fica guardado.
 */
export function CriarAtividade() {
  const ids = useId();
  const proximaChave = useRef(1);
  const [programas, setProgramas] = useState<ProgramaEmEdicao[]>([]);
  const [exemploEscolhido, setExemploEscolhido] = useState(EXEMPLOS[2].id);
  const [modo, setModo] = useState<ModoSimples>("prever");
  const [estudo, setEstudo] = useState(false);
  const [formato, setFormato] = useState<Formato>("alternativas");
  const [sala, setSala] = useState(() => novaSala());
  const [id, setId] = useState(() => idPadrao());
  const [semente, setSemente] = useState(() => String(novaSemente()));
  const [copia, setCopia] = useState<"copiado" | "falhou" | null>(null);
  const campoDoLink = useRef<HTMLTextAreaElement>(null);

  const { atividade, problemas } = useMemo(
    () => montarAtividade({ programas, modo, estudo, formato, sala, id, semente }),
    [programas, modo, estudo, formato, sala, id, semente],
  );
  const link = atividade ? linkDaAtividade(atividade) : "";
  const longo = link.length > LIMITE_DO_CHAT;

  function mudar(chave: number, mudanca: Partial<{ codigo: string; entradas: string }>) {
    setProgramas((lista) => lista.map((programa) => (programa.chave === chave ? ({ ...programa, ...mudanca } as ProgramaEmEdicao) : programa)));
    setCopia(null);
  }

  function adicionarExemplo() {
    const exemplo = exemploPorId(exemploEscolhido);
    if (!exemplo) return;
    setProgramas((lista) => [...lista, { chave: proximaChave.current++, tipo: "exemplo", ex: exemplo.id, entradas: exemplo.entradas ?? "" }]);
    setCopia(null);
  }

  function adicionarCodigo() {
    setProgramas((lista) => [...lista, { chave: proximaChave.current++, tipo: "codigo", codigo: "", entradas: "" }]);
    setCopia(null);
  }

  function mover(k: number, para: number) {
    setProgramas((lista) => {
      const nova = [...lista];
      const [tirado] = nova.splice(k, 1);
      nova.splice(para, 0, tirado);
      return nova;
    });
    setCopia(null);
  }

  function remover(k: number) {
    setProgramas((lista) => lista.filter((_, n) => n !== k));
    setCopia(null);
  }

  async function copiar() {
    const deu = await copiarTexto(link);
    if (!deu) campoDoLink.current?.select();
    setCopia(deu ? "copiado" : "falhou");
  }

  function baixarAtividade() {
    if (atividade) {
      const arquivo = arquivoDaAtividade(atividade);
      baixarArquivo(arquivo.nome, arquivo.conteudo);
    }
  }

  return (
    <div className="min-h-screen">
      <Cabecalho subtitulo="Criar atividade (professor)" linkParaInicio />
      <main className="mx-auto flex max-w-4xl flex-col gap-4 p-4">
        <p className="text-gray-800">Monte a atividade e mande o link para a turma. Nada desta tela fica guardado: copie o link antes de sair.</p>

        <Secao numero={1} titulo="Programas">
          {programas.length === 0 && <p className="text-gray-700">Nenhum programa ainda. Escolha um exemplo ou escreva o seu.</p>}
          <ol className="flex flex-col gap-3">
            {programas.map((programa, k) => {
              const exemplo = programa.tipo === "exemplo" ? exemploPorId(programa.ex) : undefined;
              const titulo = exemplo ? exemplo.titulo.replace(/^\d+\.\s*/, "") : "Código próprio";
              const codigo = exemplo ? exemplo.codigo : programa.tipo === "codigo" ? programa.codigo : "";
              const pedeEntradas = programa.tipo === "codigo" || codigo.includes("input(");
              return (
                <li key={programa.chave} className="flex flex-col gap-2 rounded-lg border-2 border-gray-200 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">
                      Programa {k + 1}: {titulo}
                    </span>
                    <span className="ml-auto flex gap-1">
                      <button type="button" className={botaoPequeno} onClick={() => mover(k, k - 1)} disabled={k === 0} aria-label={`Subir o programa ${k + 1}`}>
                        ↑
                      </button>
                      <button
                        type="button"
                        className={botaoPequeno}
                        onClick={() => mover(k, k + 1)}
                        disabled={k === programas.length - 1}
                        aria-label={`Descer o programa ${k + 1}`}
                      >
                        ↓
                      </button>
                      <button type="button" className={botaoPequeno} onClick={() => remover(k)} aria-label={`Tirar o programa ${k + 1}`}>
                        ✕
                      </button>
                    </span>
                  </div>
                  {programa.tipo === "exemplo" ? (
                    <details>
                      <summary className="min-h-11 cursor-pointer content-center text-sm font-semibold text-secundaria">Ver o código</summary>
                      <pre className="overflow-x-auto rounded-lg bg-gray-50 p-2 font-mono text-sm">{codigo}</pre>
                    </details>
                  ) : (
                    <div role="group" aria-label={`Código do programa ${k + 1}`}>
                      <Editor codigo={programa.codigo} aoMudar={(novo) => mudar(programa.chave, { codigo: novo })} cena={CENA_VAZIA} />
                    </div>
                  )}
                  {pedeEntradas && (
                    <label className="flex flex-col gap-1 text-sm">
                      <span className="font-semibold">Respostas para o input() (uma por linha)</span>
                      <textarea
                        value={programa.entradas}
                        onChange={(e) => mudar(programa.chave, { entradas: e.target.value })}
                        rows={2}
                        className="rounded-lg border-2 border-gray-300 p-2 font-mono focus-visible:border-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque"
                      />
                    </label>
                  )}
                </li>
              );
            })}
          </ol>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1">
              <span className="text-sm font-semibold">Exemplo</span>
              <select value={exemploEscolhido} onChange={(e) => setExemploEscolhido(e.target.value)} className={`${campoDeTexto} bg-white`}>
                {EXEMPLOS.map((exemplo) => (
                  <option key={exemplo.id} value={exemplo.id}>
                    {exemplo.titulo}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className={botaoSecundario} onClick={adicionarExemplo} disabled={programas.length >= MAX_PROGRAMAS}>
              + Adicionar exemplo
            </button>
            <button type="button" className={botaoSecundario} onClick={adicionarCodigo} disabled={programas.length >= MAX_PROGRAMAS}>
              + Escrever código próprio
            </button>
          </div>
          <p className="text-sm text-gray-700">Não coloque nomes de alunos no código: quem abre o link vê o código.</p>
        </Secao>

        <Secao numero={2} titulo="Como a turma vai usar">
          <Escolha legenda="Modo:" opcoes={MODOS} valor={modo} aoMudar={setModo} desabilitada={estudo} />
          {!estudo && (
            <p className="text-sm text-gray-700">
              {modo === "prever" ? "O aluno dá palpites antes de ver cada passo." : "O aluno vê o programa rodar, com o narrador."}
            </p>
          )}
          <label className="flex min-h-11 cursor-pointer items-start gap-3">
            <input type="checkbox" checked={estudo} onChange={(e) => setEstudo(e.target.checked)} className="mt-1 h-5 w-5 accent-primaria" />
            <span>
              <span className="font-semibold">Atividade do estudo</span>
              <span className="block text-sm text-gray-700">
                Cada aluno faz metade dos programas em Prever e metade em Assistir. O sorteio muda de aluno para aluno.
              </span>
              {estudo && programas.length === 1 && (
                <span className="block text-sm font-semibold text-red-800">Com um programa só, o sorteio decide se ele é Prever ou Assistir.</span>
              )}
            </span>
          </label>
          {(estudo || modo === "prever") && <Escolha legenda="Perguntas:" opcoes={FORMATOS} valor={formato} aoMudar={setFormato} />}
        </Secao>

        <Secao numero={3} titulo="Sala">
          <div className="flex flex-col gap-1">
            <label htmlFor={`${ids}-sala`} className="font-semibold">
              Código da sala
            </label>
            <p id={`${ids}-sala-dica`} className="text-sm text-gray-700">
              Fale esse código na aula. O aluno digita para entrar.
            </p>
            <div className="flex flex-wrap gap-2">
              <input
                id={`${ids}-sala`}
                value={sala}
                onChange={(e) => setSala(normalizarSala(e.target.value))}
                maxLength={16}
                autoComplete="off"
                spellCheck={false}
                aria-describedby={`${ids}-sala-dica`}
                className={`${campoDeTexto} w-40 font-mono text-lg tracking-widest`}
              />
              <button type="button" className={botaoSecundario} onClick={() => setSala(novaSala())}>
                Sortear outro
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={`${ids}-id`} className="font-semibold">
              Nome da atividade
            </label>
            <p id={`${ids}-id-dica`} className="text-sm text-gray-700">
              Vai em cada resposta e no arquivo de entrega. Sem nomes de alunos.
            </p>
            <input
              id={`${ids}-id`}
              value={id}
              onChange={(e) => setId(e.target.value.trim())}
              maxLength={32}
              autoComplete="off"
              spellCheck={false}
              aria-describedby={`${ids}-id-dica`}
              className={`${campoDeTexto} w-64 font-mono`}
            />
          </div>
          <details>
            <summary className="min-h-11 cursor-pointer content-center font-semibold text-secundaria">Avançado</summary>
            <label htmlFor={`${ids}-semente`} className="mt-1 block font-semibold">
              Semente dos sorteios
            </label>
            <p id={`${ids}-semente-dica`} className="text-sm text-gray-700">
              A mesma semente dá os mesmos números sorteados para toda a turma.
            </p>
            <input
              id={`${ids}-semente`}
              value={semente}
              onChange={(e) => setSemente(e.target.value.trim())}
              inputMode="numeric"
              aria-describedby={`${ids}-semente-dica`}
              className={`${campoDeTexto} mt-1 w-40 font-mono`}
            />
          </details>
        </Secao>

        <Secao numero={4} titulo="Link da atividade">
          {atividade ? (
            <>
              <label htmlFor={`${ids}-link`} className="sr-only">
                Link da atividade
              </label>
              <textarea
                ref={campoDoLink}
                id={`${ids}-link`}
                readOnly
                value={link}
                rows={3}
                onFocus={(e) => e.currentTarget.select()}
                className="w-full break-all rounded-lg border-2 border-gray-300 bg-gray-50 p-2 font-mono text-sm"
              />
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" className={botaoPrimario} onClick={copiar}>
                  Copiar link
                </button>
                <a href={link} target="_blank" rel="noopener" className={botaoSecundario}>
                  Abrir como aluno <span aria-hidden="true">{"↗\uFE0E"}</span>
                </a>
                <span className="text-sm text-gray-700">{link.length} caracteres</span>
              </div>
              <p aria-live="polite" className="text-sm font-semibold">
                {copia === "copiado" && <span className="text-green-800">✓ Link copiado.</span>}
                {copia === "falhou" && <span className="text-red-800">Não deu para copiar sozinho. O link está selecionado: copie com Ctrl+C.</span>}
              </p>
              {longo && (
                <div className="flex flex-col gap-2 rounded-lg border-2 border-destaque bg-orange-50 p-3">
                  <p className="font-semibold">
                    <span aria-hidden="true">⚠ </span>O link é longo e pode não caber no chat do Meet.
                  </p>
                  <p className="text-sm">Mande como arquivo. O aluno abre o PyVis e toca em “Abrir atividade de um arquivo”.</p>
                  <button type="button" className={`${botaoSecundario} self-start`} onClick={baixarAtividade}>
                    Baixar arquivo da atividade
                  </button>
                </div>
              )}
              <p className="rounded-lg bg-blue-50 p-3">
                Na aula, mande o link e fale o código da sala: <strong className="font-mono text-lg tracking-widest">{atividade.sala}</strong>
              </p>
            </>
          ) : (
            <div>
              <p className="font-semibold">Para o link aparecer:</p>
              <ul className="ml-5 list-disc text-gray-800">
                {problemas.map((problema) => (
                  <li key={problema}>{problema}</li>
                ))}
              </ul>
            </div>
          )}
        </Secao>
      </main>
    </div>
  );
}
