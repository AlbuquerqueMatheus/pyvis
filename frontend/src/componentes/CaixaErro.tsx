import type { ErroDoAluno } from "../motor/tipos";
import { TextoComCodigo } from "./PainelDetetive";

export function CaixaErro({ erro }: { erro: ErroDoAluno }) {
  const temMais = Boolean(erro.detalhe || erro.original);
  return (
    <div role="alert" className="rounded-xl border-2 border-red-300 bg-red-50 p-3">
      <p className="font-semibold text-red-800">
        Ops! {erro.linha ? `Problema na linha ${erro.linha}` : "Problema no programa"}
      </p>
      <p className="mt-1">
        <TextoComCodigo texto={erro.mensagem} />
      </p>
      {temMais && (
        <details className="mt-1 text-sm text-gray-700">
          <summary className="flex min-h-11 cursor-pointer items-center">Mais detalhes</summary>
          {erro.detalhe && (
            <p className="mb-2">
              <TextoComCodigo texto={erro.detalhe} />
            </p>
          )}
          {erro.original && (
            <p className="text-gray-600">
              Mensagem original do Python: <code className="font-mono">{erro.original}</code>
            </p>
          )}
        </details>
      )}
    </div>
  );
}
