import { AnimatePresence, motion } from "motion/react";
import type { Valor, Variaveis as Vars } from "../motor/tipos";

function texto(valor: Valor): string {
  if (valor.itens) {
    const abre = valor.tipo === "tuple" ? "(" : valor.tipo === "set" ? "{" : "[";
    const fecha = valor.tipo === "tuple" ? ")" : valor.tipo === "set" ? "}" : "]";
    return abre + valor.itens.map(texto).join(", ") + (valor.cortado ? ", ..." : "") + fecha;
  }
  if (valor.pares) return "{" + valor.pares.map(([c, v]) => `${texto(c)}: ${texto(v)}`).join(", ") + "}";
  return valor.valor ?? "";
}

const igual = (a?: Valor, b?: Valor) => JSON.stringify(a) === JSON.stringify(b);

function Caixa({ valor, mudou }: { valor: Valor; mudou: boolean }) {
  return (
    <motion.div
      key={texto(valor)}
      initial={mudou ? { scale: 0.6, backgroundColor: "#fefcbf" } : false}
      animate={{ scale: 1, backgroundColor: mudou ? "#fefcbf" : "#ffffff" }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className={`min-w-12 rounded-lg border-2 px-3 py-1.5 text-center font-mono ${mudou ? "border-destaque" : "border-gray-300"}`}
    >
      {texto(valor)}
    </motion.div>
  );
}

function Lista({ valor, anterior }: { valor: Valor; anterior?: Valor }) {
  return (
    <div className="flex flex-wrap">
      <AnimatePresence initial={false}>
        {valor.itens!.map((item, i) => {
          const novoOuMudou = anterior !== undefined && !igual(item, anterior.itens?.[i]);
          return (
            <motion.div
              key={i}
              layout
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.6 }}
              className="-ml-0.5 flex flex-col items-center first:ml-0"
            >
              <Caixa valor={item} mudou={novoOuMudou} />
              <span className="text-xs text-gray-500">{i}</span>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {valor.itens!.length === 0 && <div className="rounded-lg border-2 border-dashed border-gray-300 px-3 py-1.5 text-gray-400">vazia</div>}
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

export function Variaveis({ variaveis, anteriores }: { variaveis: Vars; anteriores?: Vars }) {
  const nomes = Object.keys(variaveis).filter((nome) => variaveis[nome].tipo !== "function");
  if (nomes.length === 0) return <p className="text-gray-500">Nenhuma variável ainda.</p>;
  return (
    <div className="flex flex-wrap gap-4">
      <AnimatePresence initial={false}>
        {nomes.map((nome) => {
          const valor = variaveis[nome];
          const anterior = anteriores?.[nome];
          return (
            <motion.div
              key={nome}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col gap-1"
            >
              <span className="font-mono font-semibold">
                {nome} <span className="text-xs font-normal text-gray-500">({NOMES_DOS_TIPOS[valor.tipo] ?? valor.tipo})</span>
              </span>
              {valor.tipo === "list" && valor.itens ? (
                <Lista valor={valor} anterior={anterior} />
              ) : (
                <Caixa valor={valor} mudou={anteriores !== undefined && !igual(valor, anterior)} />
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
