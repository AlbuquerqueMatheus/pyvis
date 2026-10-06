import { useId } from "react";

export type Opcao<T extends string> = { valor: T; rotulo: string };

type Props<T extends string> = { legenda: string; opcoes: Opcao<T>[]; valor: T; aoMudar: (valor: T) => void; desabilitada?: boolean };

/** Botões de escolha única com cara de chave (radio de verdade por baixo, para o teclado e o leitor de tela). */
export function Escolha<T extends string>({ legenda, opcoes, valor, aoMudar, desabilitada = false }: Props<T>) {
  const nome = useId();
  return (
    <fieldset className="flex flex-wrap items-center gap-2" disabled={desabilitada}>
      <legend className="float-left mr-1 font-semibold">{legenda}</legend>
      <div className="flex flex-wrap rounded-lg border-2 border-secundaria bg-white p-0.5">
        {opcoes.map((opcao) => (
          <label
            key={opcao.valor}
            className="flex min-h-11 cursor-pointer items-center gap-1 rounded-md px-3 text-sm font-semibold text-primaria has-[:checked]:bg-primaria has-[:checked]:text-white has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque"
          >
            <input type="radio" name={nome} value={opcao.valor} checked={valor === opcao.valor} onChange={() => aoMudar(opcao.valor)} className="sr-only" />
            {/* A escolhida também tem marca em texto, não só a cor. */}
            <span aria-hidden="true">{valor === opcao.valor ? "●" : "○"}</span>
            {opcao.rotulo}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
