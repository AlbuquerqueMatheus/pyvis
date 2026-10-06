import { AnimatePresence, motion } from "motion/react";
import type { Valor, Variaveis as Vars } from "../motor/tipos";

/** 'Ana' (repr do Python) vira "Ana", como no narrador e nas perguntas: aspas diferentes
 * pareceriam valores diferentes justo nas perguntas de texto ou número. */
function comAspasDuplas(representacao: string): string {
  if (representacao.length < 2 || !representacao.startsWith("'") || !representacao.endsWith("'")) return representacao;
  const dentro = representacao.slice(1, -1);
  return dentro.includes('"') || dentro.includes("\\") ? representacao : `"${dentro}"`;
}

export function texto(valor: Valor): string {
  if (valor.tipo === "str" && valor.valor) return comAspasDuplas(valor.valor);
  if (valor.itens) {
    const abre = valor.tipo === "tuple" ? "(" : valor.tipo === "set" ? "{" : "[";
    const fecha = valor.tipo === "tuple" ? ")" : valor.tipo === "set" ? "}" : "]";
    return abre + valor.itens.map(texto).join(", ") + (valor.cortado ? ", …" : "") + fecha;
  }
  if (valor.pares) return "{" + valor.pares.map(([c, v]) => `${texto(c)}: ${texto(v)}`).join(", ") + (valor.cortado ? ", …" : "") + "}";
  return valor.valor ?? "";
}

/** O valor antigo, riscado ao lado do novo: a mudança aparece em texto, não só na cor. */
function Antigo({ valor }: { valor: Valor }) {
  return (
    <del className="font-mono text-gray-600 decoration-2" title="valor antigo">
      <span className="sr-only">antes era </span>
      {texto(valor)}
    </del>
  );
}

function Etiqueta({ children }: { children: string }) {
  return <span className="rounded bg-amber-100 px-1 text-[0.7rem] font-semibold uppercase tracking-wide text-amber-900">{children}</span>;
}

const MOLA = { type: "spring", stiffness: 400, damping: 20 } as const;

function Caixa({ valor, destaque, animar }: { valor: Valor; destaque: boolean; animar: boolean }) {
  return (
    <motion.div
      key={valor.h}
      initial={animar ? { scale: 0.6 } : false}
      animate={{ scale: 1 }}
      transition={MOLA}
      className={`min-w-12 rounded-lg border-2 px-3 py-1.5 text-center font-mono ${
        destaque ? "border-destaque bg-amber-50" : "border-gray-300 bg-white"
      }`}
    >
      {texto(valor)}
    </motion.div>
  );
}

/** O valor depois da linha, escondido enquanto o palpite sobre ele está aberto. */
function CaixaOculta() {
  return (
    <div className="min-w-12 rounded-lg border-2 border-dashed border-secundaria bg-blue-50 px-3 py-1.5 text-center font-mono font-bold text-secundaria">
      <span aria-hidden="true">?</span>
      <span className="sr-only">valor depois desta linha: é o seu palpite</span>
    </div>
  );
}

function Lista({ valor, anterior, animar }: { valor: Valor; anterior?: Valor; animar: boolean }) {
  const antigos = anterior?.itens;
  const itens = valor.itens!;
  // Só um item ganha a animação: o primeiro que mudou ou chegou.
  const animado = animar ? itens.findIndex((item, i) => antigos !== undefined && (antigos[i] === undefined || antigos[i].h !== item.h)) : -1;
  return (
    <div className="flex flex-wrap gap-y-1">
      <AnimatePresence initial={false}>
        {itens.map((item, i) => {
          const antigo = antigos?.[i];
          const novo = antigos !== undefined && antigo === undefined;
          const mudou = antigo !== undefined && antigo.h !== item.h;
          return (
            <motion.div
              key={i}
              initial={novo && i === animado ? { opacity: 0, y: -12 } : false}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="-ml-0.5 flex flex-col items-center first:ml-0"
            >
              <Caixa valor={item} destaque={novo || mudou} animar={mudou && i === animado} />
              <span className="text-xs text-gray-500">{i}</span>
              {mudou && <Antigo valor={antigo} />}
              {novo && <Etiqueta>novo</Etiqueta>}
            </motion.div>
          );
        })}
      </AnimatePresence>
      {valor.cortado && (
        <div className="self-start px-2 py-1.5 font-mono text-gray-600">
          …<span className="sr-only"> e mais itens</span>
        </div>
      )}
      {itens.length === 0 && <div className="rounded-lg border-2 border-dashed border-gray-300 px-3 py-1.5 text-gray-500">vazia</div>}
    </div>
  );
}

const NOMES_DOS_TIPOS: Record<string, string> = {
  int: "inteiro",
  float: "decimal",
  str: "texto",
  bool: "lógico",
  list: "lista",
  tuple: "tupla",
  dict: "dicionário",
  set: "conjunto",
  NoneType: "nada",
};

/** 'Onde olhar' do Detetive: contorno e texto, não só cor. */
function OlheAqui() {
  return (
    <span className="rounded bg-secundaria px-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-white">
      <span aria-hidden="true">◎ </span>olhe aqui
    </span>
  );
}

function visiveis(variaveis: Vars): string[] {
  return Object.keys(variaveis).filter((nome) => variaveis[nome].tipo !== "function");
}

/** O primeiro nome que chegou ou mudou desde `anteriores` (fora os escondidos pelo palpite), ou null. */
export function primeiraMudanca(variaveis: Vars, anteriores: Vars | undefined, ocultas?: ReadonlySet<string>): string | null {
  if (anteriores === undefined) return null;
  for (const nome of visiveis(variaveis)) {
    if (ocultas?.has(nome)) continue;
    const anterior = anteriores[nome];
    if (anterior === undefined || anterior.h !== variaveis[nome].h) return nome;
  }
  return null;
}

type Props = {
  variaveis: Vars;
  /** Os valores do passo anterior; sem eles, nada aparece como novo ou mudado. */
  anteriores?: Vars;
  /**
   * Nomes cujo valor depois da linha é a pergunta do palpite: a caixinha mostra
   * o valor de agora e um '?' no lugar do próximo (ou só o '?', se é nova).
   */
  ocultas?: ReadonlySet<string>;
  /** A caixinha que o Detetive mandou olhar. */
  contorno?: string | null;
  /**
   * O único nome que pode ganhar o destaque animado neste passo (orçamento de
   * atenção); null: nenhum. Sem a prop, vale o primeiro que mudou ou chegou.
   */
  animada?: string | null;
};

export function Variaveis({ variaveis, anteriores, ocultas, contorno, animada }: Props) {
  const nomes = visiveis(variaveis);
  // Uma variável que a linha vai criar ainda não existe: ganha só o '?'.
  const futuras = [...(ocultas ?? [])].filter((nome) => !(nome in variaveis));
  if (nomes.length === 0 && futuras.length === 0) return <p className="text-gray-500">Nenhuma variável ainda.</p>;

  // Comparar o resumo `h` é barato: nada de comparar o valor inteiro a cada passo.
  const mudancas = new Map<string, { nova: boolean; mudou: boolean }>();
  for (const nome of nomes) {
    const anterior = anteriores?.[nome];
    mudancas.set(nome, {
      nova: anteriores !== undefined && anterior === undefined,
      mudou: anterior !== undefined && anterior.h !== variaveis[nome].h,
    });
  }
  // Orçamento de atenção: uma caixinha animada por passo, no máximo.
  const escolhida = animada === undefined ? primeiraMudanca(variaveis, anteriores, ocultas) : animada;
  const animar = (nome: string) => {
    const mudanca = mudancas.get(nome)!;
    return escolhida !== null && nome === escolhida && !ocultas?.has(nome) && (mudanca.nova || mudanca.mudou);
  };

  return (
    <div className="flex flex-wrap gap-4">
      <AnimatePresence initial={false}>
        {nomes.map((nome) => {
          const valor = variaveis[nome];
          const oculto = ocultas?.has(nome) ?? false;
          const anterior = anteriores?.[nome];
          const { nova, mudou } = mudancas.get(nome)!;
          const lista = valor.tipo === "list" && valor.itens !== undefined;
          const anima = animar(nome);
          const contornada = contorno === nome;
          return (
            <motion.div
              key={nome}
              initial={anima && nova ? { opacity: 0, scale: 0.8 } : false}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className={`flex flex-col gap-1 rounded-lg ${contornada ? "p-1.5 outline-3 outline-offset-2 outline-secundaria" : ""}`}
              data-variavel={nome}
              data-destaque-animado={anima ? "" : undefined}
              data-contorno={contornada ? "" : undefined}
            >
              <span className="flex flex-wrap items-center gap-1.5 font-mono font-semibold">
                {nome}
                {/* O tipo também responde o palpite (texto ou número?): fica escondido junto. */}
                {!oculto && <span className="text-xs font-normal text-gray-500">({NOMES_DOS_TIPOS[valor.tipo] ?? valor.tipo})</span>}
                {!oculto && nova && <Etiqueta>nova</Etiqueta>}
                {!oculto && mudou && <Etiqueta>mudou</Etiqueta>}
                {contornada && <OlheAqui />}
              </span>
              {oculto ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Caixa valor={valor} destaque={false} animar={false} />
                  <span aria-hidden="true" className="text-gray-500">
                    →
                  </span>
                  <span className="sr-only">depois desta linha:</span>
                  <CaixaOculta />
                </div>
              ) : lista ? (
                <>
                  <Lista valor={valor} anterior={anterior?.itens ? anterior : undefined} animar={anima} />
                  {mudou && !anterior!.itens && <Antigo valor={anterior!} />}
                </>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <Caixa valor={valor} destaque={nova || mudou} animar={anima} />
                  {mudou && <Antigo valor={anterior!} />}
                </div>
              )}
            </motion.div>
          );
        })}
        {futuras.map((nome) => (
          <div key={`?${nome}`} className="flex flex-col gap-1" data-variavel={nome}>
            <span className="font-mono font-semibold">{nome}</span>
            <CaixaOculta />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
