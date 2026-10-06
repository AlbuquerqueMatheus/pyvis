// Armazenamentos de mentira para os testes do diário da sala.
import type { Armazenamento } from "../sala/armazenamento";

/** Um localStorage de mentira (um Map), para cada teste começar do zero. */
export function armazenamentoFalso(): Armazenamento & { dados: Map<string, string> } {
  const dados = new Map<string, string>();
  return {
    dados,
    get length() {
      return dados.size;
    },
    key: (k: number) => [...dados.keys()][k] ?? null,
    getItem: (chave: string) => dados.get(chave) ?? null,
    setItem: (chave: string, valor: string) => void dados.set(chave, String(valor)),
    removeItem: (chave: string) => void dados.delete(chave),
  };
}

/** O navegador que não deixa guardar nada (modo anônimo, dados bloqueados, cota cheia). */
export const armazenamentoQueFalha: Armazenamento = {
  get length(): number {
    throw new DOMException("bloqueado", "SecurityError");
  },
  key: () => {
    throw new DOMException("bloqueado", "SecurityError");
  },
  getItem: () => {
    throw new DOMException("bloqueado", "SecurityError");
  },
  setItem: () => {
    throw new DOMException("cheio", "QuotaExceededError");
  },
  removeItem: () => {
    throw new DOMException("bloqueado", "SecurityError");
  },
};
