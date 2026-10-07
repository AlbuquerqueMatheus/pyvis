import { useEffect, useMemo, useRef, useState } from "react";
import { ErroDoMotor, Ponte, type Acao, type Acoes, type CriarCanal, type EstadoDoMotor } from "./ponte";

export type { EstadoDoMotor } from "./ponte";

/**
 * A ponte com o Python para os componentes: o estado (para os botões) e os
 * pedidos, que devolvem promessas. `criarCanal` só muda nos testes.
 */
export function useMotor(criarCanal?: CriarCanal) {
  const [estado, setEstado] = useState<EstadoDoMotor>("carregando");
  const ponteRef = useRef<Ponte | null>(null);

  useEffect(() => {
    const ponte = new Ponte(criarCanal);
    ponteRef.current = ponte;
    setEstado(ponte.estado);
    const parar = ponte.observar(setEstado);
    return () => {
      parar();
      ponte.encerrar();
      if (ponteRef.current === ponte) ponteRef.current = null;
    };
  }, [criarCanal]);

  // As funções leem a ponte na hora do pedido: no StrictMode ela é recriada uma vez.
  const pedidos = useMemo(() => {
    function comPonte<T>(pedido: (ponte: Ponte) => Promise<T>): Promise<T> {
      const ponte = ponteRef.current;
      if (ponte) return pedido(ponte);
      // Um filho pode pedir no próprio efeito, que roda antes do efeito que cria a
      // ponte: espera esse commit terminar (a ponte guarda o pedido até o Python carregar).
      return Promise.resolve().then(() => {
        const criada = ponteRef.current;
        return criada ? pedido(criada) : Promise.reject(new ErroDoMotor("Reiniciado", "O Python ainda está carregando."));
      });
    }
    return {
      rastrear: (...args: Parameters<Ponte["rastrear"]>) => comPonte((p) => p.rastrear(...args)),
      prepararAtividade: (...args: Parameters<Ponte["prepararAtividade"]>) => comPonte((p) => p.prepararAtividade(...args)),
      corrigir: (...args: Parameters<Ponte["corrigir"]>) => comPonte((p) => p.corrigir(...args)),
      pedir: (<A extends Acao>(acao: A, dados: Acoes[A]["dados"]) => comPonte((p) => p.pedir(acao, dados))) as Ponte["pedir"],
    };
  }, []);

  return { estado, ...pedidos };
}

export type Motor = ReturnType<typeof useMotor>;
