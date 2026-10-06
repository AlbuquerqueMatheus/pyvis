import { useEffect, useState } from "react";

// O mesmo ponto de quebra do `lg:` do Tailwind (64rem). Abaixo dele a tela vira
// duas abas, Código e Passos, com a linha do tempo fixa embaixo.
const CONSULTA = "(min-width: 64rem)";

function consultar(): boolean {
  // Sem matchMedia (testes em jsdom), vale a tela grande.
  return typeof window === "undefined" || typeof window.matchMedia !== "function" || window.matchMedia(CONSULTA).matches;
}

export function useTelaGrande(): boolean {
  const [grande, setGrande] = useState(consultar);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const lista = window.matchMedia(CONSULTA);
    const mudar = () => setGrande(lista.matches);
    mudar();
    lista.addEventListener("change", mudar);
    return () => lista.removeEventListener("change", mudar);
  }, []);
  return grande;
}
