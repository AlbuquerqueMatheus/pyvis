import type { ErroDoAluno } from "../motor/tipos";

export function CaixaErro({ erro }: { erro: ErroDoAluno }) {
  return (
    <div role="alert" className="rounded-xl border-2 border-red-300 bg-red-50 p-3">
      <p className="font-semibold text-red-800">
        Ops! {erro.linha ? `Problema na linha ${erro.linha}` : "Problema no programa"}
      </p>
      <p className="mt-1">{erro.mensagem}</p>
      {erro.original && (
        <details className="mt-2 text-sm text-gray-600">
          <summary className="cursor-pointer">Mensagem original do Python</summary>
          <code className="font-mono">{erro.original}</code>
        </details>
      )}
    </div>
  );
}
