// O diário da sala neste aparelho (spec 2.5). A página guarda tudo na memória,
// com uma cópia no localStorage para não perder nada ao recarregar. Regras:
// - só dentro de uma sala: o uso livre e a tela do professor não guardam nada;
// - uma chave por sala, com o sujeito (um número aleatório), o apelido e os eventos;
// - a sala que fica 30 dias sem uso é apagada quando o PyVis abre;
// - todo acesso ao localStorage fica em try/catch: no modo anônimo, com os
//   dados do site bloqueados ou com a cota cheia, a atividade segue na memória.

import type { Evento } from "../motor/tipos";

export const PREFIXO = "pyvis:sala:";
export const VALIDADE_MS = 30 * 24 * 60 * 60 * 1000;
/** Teto de eventos por sala: o diário nunca cresce sem limite no aparelho. */
export const MAX_EVENTOS = 5000;

// UUID v4 em minúsculas, o formato que registro.py aceita.
const PADRAO_SUJEITO = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export type SalaGuardada = {
  v: 1;
  sala: string;
  sujeito: string;
  apelido: string;
  /** Último uso, em ms (Date.now()): a validade conta a partir dele. */
  atualizado: number;
  eventos: Evento[];
};

export type Armazenamento = Pick<Storage, "getItem" | "setItem" | "removeItem" | "key" | "length">;

/** O localStorage, ou null quando o navegador nem deixa olhar para ele. */
export function armazenamentoDoNavegador(): Armazenamento | null {
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

export function chaveDaSala(sala: string): string {
  return PREFIXO + sala;
}

export function venceEm(registro: SalaGuardada): number {
  return registro.atualizado + VALIDADE_MS;
}

function pareceSala(dado: unknown): dado is SalaGuardada {
  if (typeof dado !== "object" || dado === null) return false;
  const sala = dado as Record<string, unknown>;
  return (
    sala.v === 1 &&
    typeof sala.sala === "string" &&
    typeof sala.sujeito === "string" &&
    PADRAO_SUJEITO.test(sala.sujeito) &&
    typeof sala.apelido === "string" &&
    typeof sala.atualizado === "number" &&
    Number.isFinite(sala.atualizado) &&
    Array.isArray(sala.eventos)
  );
}

function lerChave(chave: string, armazenamento: Armazenamento): SalaGuardada | null {
  try {
    const texto = armazenamento.getItem(chave);
    if (texto === null) return null;
    const dado: unknown = JSON.parse(texto);
    return pareceSala(dado) ? dado : null;
  } catch {
    return null;
  }
}

function remover(chave: string, armazenamento: Armazenamento): boolean {
  try {
    armazenamento.removeItem(chave);
    return true;
  } catch {
    return false;
  }
}

function chavesDoPyvis(armazenamento: Armazenamento): string[] {
  const chaves: string[] = [];
  try {
    for (let k = 0; k < armazenamento.length; k++) {
      const chave = armazenamento.key(k);
      if (chave?.startsWith(PREFIXO)) chaves.push(chave);
    }
  } catch {
    // sem acesso: nada a listar
  }
  return chaves;
}

/** A sala guardada neste aparelho. Uma vencida ou estragada é apagada e conta como nenhuma. */
export function lerSala(sala: string, armazenamento = armazenamentoDoNavegador(), agora = Date.now()): SalaGuardada | null {
  if (!armazenamento || !sala) return null;
  const chave = chaveDaSala(sala);
  const registro = lerChave(chave, armazenamento);
  if (registro && registro.sala === sala && venceEm(registro) > agora) return registro;
  remover(chave, armazenamento); // tirar uma chave que não existe não faz nada
  return null;
}

/** Guarda a cópia; false quando o aparelho não deixou (a página segue com a memória). */
export function guardarSala(registro: SalaGuardada, armazenamento = armazenamentoDoNavegador()): boolean {
  if (!armazenamento) return false;
  try {
    armazenamento.setItem(chaveDaSala(registro.sala), JSON.stringify(registro));
    return true;
  } catch {
    return false;
  }
}

export function apagarSala(sala: string, armazenamento = armazenamentoDoNavegador()): boolean {
  return armazenamento ? remover(chaveDaSala(sala), armazenamento) : false;
}

/** Todas as salas guardadas aqui (a página dos pais mostra a lista). */
export function salasGuardadas(armazenamento = armazenamentoDoNavegador(), agora = Date.now()): SalaGuardada[] {
  if (!armazenamento) return [];
  return chavesDoPyvis(armazenamento)
    .map((chave) => lerChave(chave, armazenamento))
    .filter((registro): registro is SalaGuardada => registro !== null && venceEm(registro) > agora)
    .sort((a, b) => a.sala.localeCompare(b.sala));
}

/** Apaga tudo o que o PyVis guardou neste aparelho. Devolve quantas salas saíram. */
export function apagarTudo(armazenamento = armazenamentoDoNavegador()): number {
  if (!armazenamento) return 0;
  return chavesDoPyvis(armazenamento).filter((chave) => remover(chave, armazenamento)).length;
}

/** A limpeza ao abrir: some com as salas vencidas e com as que não dá para ler. */
export function limparVencidas(armazenamento = armazenamentoDoNavegador(), agora = Date.now()): number {
  if (!armazenamento) return 0;
  let apagadas = 0;
  for (const chave of chavesDoPyvis(armazenamento)) {
    const registro = lerChave(chave, armazenamento);
    if (registro && chaveDaSala(registro.sala) === chave && venceEm(registro) > agora) continue;
    if (remover(chave, armazenamento)) apagadas++;
  }
  return apagadas;
}

/** O sujeito do diário: um UUID v4 aleatório, um por sala (nunca o nome do aluno). */
export function novoSujeito(): string {
  const cripto = globalThis.crypto;
  if (typeof cripto.randomUUID === "function") return cripto.randomUUID();
  // Fora de https (um teste na rede da escola) não há randomUUID: monta o v4 à mão.
  const bytes = cripto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
