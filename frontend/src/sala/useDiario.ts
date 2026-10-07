import { useCallback, useEffect, useRef, useState } from "react";
import type { ContextoDoEvento, Evento, TipoDeEvento } from "../motor/tipos";
import type { Motor } from "../motor/useMotor";
import {
  MAX_EVENTOS,
  apagarSala,
  armazenamentoDoNavegador,
  chaveDaSala,
  guardarSala,
  lerSala,
  type Armazenamento,
  type SalaGuardada,
} from "./armazenamento";

export type Diario = {
  /** A sala em que o aluno entrou, ou null (ainda não entrou, ou apagou). */
  sala: SalaGuardada | null;
  /** false quando o aparelho não deixou guardar: tudo fica só nesta página. */
  guardado: boolean;
  /** A sala foi apagada em outra aba (pela página dos pais, por exemplo). */
  apagadaDeFora: boolean;
  entrar(dados: { sala: string; sujeito: string; apelido: string }): SalaGuardada;
  /**
   * Pede ao motor o evento (registro.montar_evento confere cada campo) e só
   * então guarda. Um evento inválido não entra. Os eventos ficam na ordem em
   * que foram pedidos, mesmo quando o contexto ainda está a caminho.
   */
  registrar(tipo: TipoDeEvento, contexto: ContextoDoEvento | Promise<ContextoDoEvento>, campos?: Record<string, unknown>): Promise<void>;
  apagar(): void;
};

/**
 * O diário de uma sala (spec 2.5): memória da página com cópia no aparelho.
 * Fora de uma sala (antes de `entrar`), nada é guardado.
 */
export function useDiario(salaInicial: string, pedir: Motor["pedir"], armazenamento: Armazenamento | null = armazenamentoDoNavegador()): Diario {
  const [sala, setSala] = useState<SalaGuardada | null>(() => lerSala(salaInicial, armazenamento));
  const [guardado, setGuardado] = useState(armazenamento !== null);
  const [apagadaDeFora, setApagadaDeFora] = useState(false);
  const atual = useRef(sala);
  const fila = useRef<Promise<void>>(Promise.resolve());
  // Muda a cada 'apagar': um evento que estava a caminho não ressuscita a sala.
  const geracao = useRef(0);

  const trocar = useCallback((nova: SalaGuardada | null) => {
    atual.current = nova;
    setSala(nova);
  }, []);

  // Apagada em outra aba: esta também esquece.
  useEffect(() => {
    function aoMudar(evento: StorageEvent) {
      const minha = atual.current;
      if (!minha || (evento.key !== null && evento.key !== chaveDaSala(minha.sala))) return;
      if (evento.key === null ? lerSala(minha.sala, armazenamento) !== null : evento.newValue !== null) return;
      geracao.current++;
      trocar(null);
      setApagadaDeFora(true);
    }
    window.addEventListener("storage", aoMudar);
    return () => window.removeEventListener("storage", aoMudar);
  }, [armazenamento, trocar]);

  const entrar = useCallback(
    (dados: { sala: string; sujeito: string; apelido: string }) => {
      const nova: SalaGuardada = { v: 1, ...dados, atualizado: Date.now(), eventos: [] };
      trocar(nova);
      setGuardado(guardarSala(nova, armazenamento));
      setApagadaDeFora(false);
      return nova;
    },
    [armazenamento, trocar],
  );

  const acrescentar = useCallback(
    (evento: Evento) => {
      const minha = atual.current;
      if (!minha) return;
      // Outra aba da mesma sala pode ter guardado eventos: parte do que está no aparelho.
      const noAparelho = lerSala(minha.sala, armazenamento);
      const base = noAparelho && noAparelho.sujeito === minha.sujeito && noAparelho.eventos.length >= minha.eventos.length ? noAparelho : minha;
      if (base.eventos.length >= MAX_EVENTOS) return;
      const nova = { ...base, atualizado: Date.now(), eventos: [...base.eventos, evento] };
      trocar(nova);
      setGuardado(guardarSala(nova, armazenamento));
    },
    [armazenamento, trocar],
  );

  const registrar = useCallback(
    (tipo: TipoDeEvento, contexto: ContextoDoEvento | Promise<ContextoDoEvento>, campos?: Record<string, unknown>) => {
      const minhaGeracao = geracao.current;
      const ts = Date.now();
      // Se a vez deste evento nunca chegar (a sala foi apagada), a falha do contexto não fica solta.
      Promise.resolve(contexto).catch(() => {});
      const vez = fila.current.then(async () => {
        if (minhaGeracao !== geracao.current || !atual.current) return;
        try {
          const evento = await pedir("montar_evento", { tipo, contexto: await contexto, ts, campos: campos ?? {} });
          if (minhaGeracao === geracao.current) acrescentar(evento);
        } catch {
          // o motor recusou o evento (ou não respondeu): ele não é guardado
        }
      });
      fila.current = vez;
      return vez;
    },
    [pedir, acrescentar],
  );

  const apagar = useCallback(() => {
    geracao.current++;
    const minha = atual.current;
    if (minha) apagarSala(minha.sala, armazenamento);
    trocar(null);
  }, [armazenamento, trocar]);

  return { sala, guardado, apagadaDeFora, entrar, registrar, apagar };
}
