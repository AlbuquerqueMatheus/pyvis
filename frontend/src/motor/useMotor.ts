import { useCallback, useEffect, useRef, useState } from "react";
import type { Resultado } from "./tipos";

const TEMPO_MAXIMO_MS = 10000;

export type EstadoDoMotor = "carregando" | "pronto" | "executando" | "falhou";

/** Cuida do worker com Python: carregar, executar e reiniciar se travar. */
export function useMotor() {
  const [estado, setEstado] = useState<EstadoDoMotor>("carregando");
  const [aviso, setAviso] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const relogioRef = useRef<number | undefined>(undefined);
  const aoTerminarRef = useRef<((r: Resultado) => void) | null>(null);

  const iniciar = useCallback(() => {
    const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = ({ data }) => {
      if (data.tipo === "pronto") {
        setEstado("pronto");
      } else if (data.tipo === "falha") {
        setEstado("falhou");
      } else if (data.tipo === "resultado") {
        clearTimeout(relogioRef.current);
        setEstado("pronto");
        aoTerminarRef.current?.(data.resultado);
      }
    };
    workerRef.current = worker;
  }, []);

  useEffect(() => {
    iniciar();
    return () => workerRef.current?.terminate();
  }, [iniciar]);

  const executar = useCallback(
    (codigo: string, entradas: string[], aoTerminar: (r: Resultado) => void) => {
      aoTerminarRef.current = aoTerminar;
      setAviso(null);
      setEstado("executando");
      relogioRef.current = window.setTimeout(() => {
        // Programa pesado demais: descarta o Python e prepara outro do zero.
        workerRef.current?.terminate();
        setAviso("O programa demorou demais e foi parado.");
        setEstado("carregando");
        iniciar();
      }, TEMPO_MAXIMO_MS);
      workerRef.current?.postMessage({ codigo, entradas });
    },
    [iniciar],
  );

  return { estado, aviso, executar };
}
