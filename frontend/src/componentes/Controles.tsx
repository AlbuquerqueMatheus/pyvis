type Props = {
  passo: number;
  total: number;
  fim: boolean;
  irPara: (passo: number) => void;
};

const botao =
  "rounded-lg bg-secundaria px-3 py-2 font-medium text-white transition hover:bg-primaria disabled:cursor-default disabled:opacity-40";

export function Controles({ passo, total, fim, irPara }: Props) {
  if (total === 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <button className={botao} onClick={() => irPara(0)} disabled={passo === 0} aria-label="Primeiro passo">
          ⏮
        </button>
        <button className={botao} onClick={() => irPara(passo - 1)} disabled={passo === 0}>
          ◀ Voltar
        </button>
        <button className={botao} onClick={() => irPara(passo + 1)} disabled={passo === total - 1}>
          Avançar ▶
        </button>
        <button className={botao} onClick={() => irPara(total - 1)} disabled={passo === total - 1} aria-label="Último passo">
          ⏭
        </button>
        <span className="ml-auto text-sm text-gray-600">
          Passo {passo + 1} de {total}
          {fim && " (fim do programa)"}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={total - 1}
        value={passo}
        onChange={(e) => irPara(Number(e.target.value))}
        aria-label="Linha do tempo da execução"
        className="w-full accent-destaque"
      />
    </div>
  );
}
