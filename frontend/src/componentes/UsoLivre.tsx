import { useRef, useState } from "react";
import { EXEMPLOS } from "../exemplos";
import type { Formato, Modo } from "../motor/tipos";
import type { CriarCanal } from "../motor/ponte";
import { useMotor } from "../motor/useMotor";
import { codificarAtividade, lerArquivoDaAtividade } from "../sala/link";
import { Cabecalho } from "./Cabecalho";
import { Escolha, type Opcao } from "./Escolha";
import { Palco } from "./Palco";

const MODOS: Opcao<Modo>[] = [
  { valor: "assistir", rotulo: "Assistir" },
  { valor: "prever", rotulo: "Prever" },
];
const FORMATOS: Opcao<Formato>[] = [
  { valor: "alternativas", rotulo: "Alternativas" },
  { valor: "livre", rotulo: "Resposta livre" },
];

const link = "inline-flex min-h-11 items-center rounded px-1 text-blue-50 underline decoration-2 underline-offset-2 hover:text-white focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

/** A atividade que veio num arquivo (quando o link não coube no chat) vira o link de sempre. */
function AbrirArquivo() {
  const campo = useRef<HTMLInputElement>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function abrir(arquivo: File | undefined) {
    if (!arquivo) return;
    const lido = lerArquivoDaAtividade(await arquivo.text());
    if (campo.current) campo.current.value = "";
    if (lido.tipo !== "atividade") {
      setErro("Esse arquivo não é de uma atividade do PyVis.");
      return;
    }
    setErro(null);
    window.location.hash = codificarAtividade(lido.atividade);
  }

  return (
    <span className="inline-flex flex-col">
      <label className={`${link} cursor-pointer has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque`}>
        <input ref={campo} type="file" accept=".json,application/json" className="sr-only" onChange={(e) => abrir(e.target.files?.[0])} />
        Abrir atividade de um arquivo
      </label>
      {erro && (
        <span role="alert" className="font-semibold text-destaque">
          {erro}
        </span>
      )}
    </span>
  );
}

/** O uso livre do PyVis (fora de um link de atividade): o aluno escolhe o programa e o modo. Nada é guardado. */
export function UsoLivre({ criarCanal }: { criarCanal?: CriarCanal }) {
  const motor = useMotor(criarCanal);
  const [codigo, setCodigo] = useState(EXEMPLOS[0].codigo);
  const [entradas, setEntradas] = useState(EXEMPLOS[0].entradas ?? "");
  // Fora de uma atividade, o padrão é assistir; Prever pede palpites antes de cada passo.
  const [modo, setModo] = useState<Modo>("assistir");
  const [formato, setFormato] = useState<Formato>("alternativas");

  function escolherExemplo(indice: number) {
    setCodigo(EXEMPLOS[indice].codigo);
    setEntradas(EXEMPLOS[indice].entradas ?? "");
  }

  const barra = (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="exemplos" className="font-semibold">
          Exemplos:
        </label>
        <select
          id="exemplos"
          className="min-h-11 min-w-0 max-w-full rounded-lg border border-gray-300 bg-white px-2 py-1.5"
          onChange={(e) => escolherExemplo(Number(e.target.value))}
        >
          {EXEMPLOS.map((exemplo, i) => (
            <option key={exemplo.titulo} value={i}>
              {exemplo.titulo}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Escolha legenda="Modo:" opcoes={MODOS} valor={modo} aoMudar={setModo} />
        {modo === "prever" && <Escolha legenda="Perguntas:" opcoes={FORMATOS} valor={formato} aoMudar={setFormato} />}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen">
      <Cabecalho estado={motor.estado}>
        <nav aria-label="Outras páginas" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          <a href="#/criar" className={link}>
            Professor: criar atividade
          </a>
          {/* Numa aba nova: o código que o aluno escreveu aqui não se perde. */}
          <a href="#/pais" target="_blank" rel="noopener" className={link}>
            Para pais e responsáveis
          </a>
          <AbrirArquivo />
        </nav>
      </Cabecalho>
      <main>
        <Palco
          motor={motor}
          codigo={codigo}
          aoMudarCodigo={setCodigo}
          entradas={entradas}
          aoMudarEntradas={setEntradas}
          modo={modo}
          formato={formato}
          barra={barra}
        />
      </main>
    </div>
  );
}
