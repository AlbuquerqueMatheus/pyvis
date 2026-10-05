import { useState } from "react";
import { Editor } from "./componentes/Editor";
import { Controles } from "./componentes/Controles";
import { Variaveis } from "./componentes/Variaveis";
import { CaixaErro } from "./componentes/CaixaErro";
import { EXEMPLOS } from "./exemplos";
import { useMotor } from "./motor/useMotor";
import type { Resultado } from "./motor/tipos";

const STATUS = {
  carregando: "Preparando o Python...",
  pronto: "Python pronto!",
  executando: "Executando...",
  falhou: "Não foi possível carregar o Python. Recarregue a página.",
};

export default function App() {
  const motor = useMotor();
  const [codigo, setCodigo] = useState(EXEMPLOS[0].codigo);
  const [entradas, setEntradas] = useState("");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [passoAtual, setPassoAtual] = useState(0);

  const passos = resultado?.passos ?? [];
  const passo = passos[passoAtual];
  const anterior = passos[passoAtual - 1];
  const noUltimo = passoAtual === passos.length - 1;
  const erroVisivel = resultado?.erro && (noUltimo || passos.length === 0) ? resultado.erro : null;

  function mudarCodigo(novo: string) {
    setCodigo(novo);
    setResultado(null); // os passos gravados não valem mais para o código novo
  }

  function escolherExemplo(indice: number) {
    mudarCodigo(EXEMPLOS[indice].codigo);
    setEntradas(EXEMPLOS[indice].entradas ?? "");
  }

  function executar() {
    const linhas = entradas.split("\n").filter((l) => l !== "");
    motor.executar(codigo, linhas, (novo) => {
      setResultado(novo);
      setPassoAtual(0);
    });
  }

  function irPara(indice: number) {
    setPassoAtual(Math.max(0, Math.min(passos.length - 1, indice)));
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between bg-primaria px-4 py-3 text-white shadow">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-destaque font-bold text-primaria">Py</div>
          <h1 className="text-xl font-bold">PyVis</h1>
        </div>
        <span className="text-sm" aria-live="polite">
          {motor.aviso ?? STATUS[motor.estado]}
        </span>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 p-4 lg:grid-cols-2">
        <section className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="exemplos" className="font-semibold">
              Exemplos:
            </label>
            <select
              id="exemplos"
              className="rounded-lg border border-gray-300 bg-white px-2 py-1.5"
              onChange={(e) => escolherExemplo(Number(e.target.value))}
            >
              {EXEMPLOS.map((exemplo, i) => (
                <option key={exemplo.titulo} value={i}>
                  {exemplo.titulo}
                </option>
              ))}
            </select>
          </div>

          <Editor
            codigo={codigo}
            aoMudar={mudarCodigo}
            linhaAtual={passo && passo.evento === "linha" ? passo.linha : null}
            linhaComErro={erroVisivel?.linha ?? null}
          />

          <details className="rounded-xl bg-white p-3 shadow-sm" open={entradas !== ""}>
            <summary className="cursor-pointer font-semibold">Respostas para o input() (uma por linha)</summary>
            <textarea
              value={entradas}
              onChange={(e) => {
                setEntradas(e.target.value);
                setResultado(null);
              }}
              rows={3}
              className="mt-2 w-full rounded-lg border border-gray-300 p-2 font-mono"
              aria-label="Respostas para o input()"
            />
          </details>

          <button
            onClick={executar}
            disabled={motor.estado !== "pronto"}
            className="rounded-xl bg-green-600 px-4 py-3 text-lg font-bold text-white shadow transition hover:bg-green-700 disabled:opacity-50"
          >
            ▶ Executar
          </button>

          {resultado && <Controles passo={passoAtual} total={passos.length} fim={passo?.evento === "fim"} irPara={irPara} />}
        </section>

        <section className="flex min-w-0 flex-col gap-4">
          {erroVisivel && <CaixaErro erro={erroVisivel} />}

          <div className="rounded-xl bg-white p-4 shadow-sm">
            <h2 className="mb-3 font-bold text-primaria">Variáveis</h2>
            {passo ? (
              <>
                <Variaveis variaveis={passo.globais} anteriores={anterior?.globais} />
                {passo.funcao && (
                  <div className="mt-4 rounded-lg border border-dashed border-secundaria p-3">
                    <h3 className="mb-2 text-sm font-semibold">Dentro da função {passo.funcao}</h3>
                    <Variaveis variaveis={passo.locais} anteriores={anterior?.funcao === passo.funcao ? anterior.locais : undefined} />
                  </div>
                )}
              </>
            ) : (
              <p className="text-gray-500">Clique em Executar para ver o programa rodando passo a passo.</p>
            )}
          </div>

          <div className="rounded-xl bg-gray-900 p-4 shadow-sm">
            <h2 className="mb-2 text-xs uppercase tracking-wider text-gray-400">Saída</h2>
            <pre className="min-h-16 whitespace-pre-wrap font-mono text-green-300">
              {resultado ? (noUltimo || !passo ? resultado.saida : passo.saida) : ""}
            </pre>
          </div>
        </section>
      </main>
    </div>
  );
}
