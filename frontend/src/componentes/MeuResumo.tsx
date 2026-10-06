import { useEffect, useId, useMemo, useState } from "react";
import type { AtividadeLink, Entrega, Evento, Resumo } from "../motor/tipos";
import type { Motor } from "../motor/useMotor";
import type { SalaGuardada } from "../sala/armazenamento";
import { arquivoDaEntrega, baixarArquivo, copiarTexto, type ArquivoDaEntrega } from "../sala/arquivos";
import { TextoComCodigo } from "./PainelDetetive";

type Props = {
  atividade: AtividadeLink;
  sala: SalaGuardada;
  pedir: Motor["pedir"];
  aoVoltar: () => void;
  aoApagar: () => void;
};

export const TITULO_ENTENDIDAS = "Ideias que você já entendeu";
export const TITULO_REVISAR = "Ideias para revisar";

const botaoPrimario =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-green-700 px-5 py-3 text-lg font-bold text-white shadow transition hover:bg-green-800 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50";

/** Na reserva de um evento estragado no aparelho, a entrega leva só os que o motor aceita. */
async function soValidos(pedir: Motor["pedir"], eventos: Evento[]): Promise<Evento[]> {
  const problemas = await Promise.all(eventos.map((evento) => pedir("validar_evento", { evento })));
  return eventos.filter((_, k) => problemas[k].length === 0);
}

type EstadoDaEntrega = { estado: "parado" | "montando" } | { estado: "pronta"; arquivo: ArquivoDaEntrega; baixou: boolean } | { estado: "erro" };

function Ideias({ titulo, icone, frases, vazio }: { titulo: string; icone: string; frases: string[]; vazio: string }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="rounded-xl border-2 border-gray-200 p-3">
      <h3 id={id} className="font-bold text-primaria">
        <span aria-hidden="true">{icone} </span>
        {titulo}
      </h3>
      {frases.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1.5">
          {frases.map((frase) => (
            <li key={frase} className="flex gap-2">
              <span aria-hidden="true" className="text-secundaria">
                •
              </span>
              <span>
                <TextoComCodigo texto={frase} />
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-gray-700">{vazio}</p>
      )}
    </section>
  );
}

/**
 * 'Meu resumo' (spec 2.5): primeiro as ideias (as entendidas e as para
 * revisar, com a regra de cada uma, nunca o id), só depois os números. A
 * entrega baixa um arquivo comprimido com o apelido e os eventos desta atividade.
 */
export function MeuResumo({ atividade, sala, pedir, aoVoltar, aoApagar }: Props) {
  const eventos = useMemo(() => sala.eventos.filter((evento) => evento.atividade === atividade.id && evento.sujeito === sala.sujeito), [sala, atividade.id]);
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [entrega, setEntrega] = useState<EstadoDaEntrega>({ estado: "parado" });
  const [copiado, setCopiado] = useState<boolean | null>(null);

  useEffect(() => {
    let vivo = true;
    pedir("resumo", { eventos, atividade: atividade.id }).then(
      (lido) => vivo && setResumo(lido),
      () => vivo && setFalhou(true),
    );
    return () => {
      vivo = false;
    };
  }, [pedir, eventos, atividade.id]);

  async function montar(): Promise<ArquivoDaEntrega> {
    let pacote: Entrega;
    try {
      pacote = await pedir("montar_entrega", { apelido: sala.apelido, eventos });
    } catch {
      pacote = await pedir("montar_entrega", { apelido: sala.apelido, eventos: await soValidos(pedir, eventos) });
    }
    return arquivoDaEntrega(pacote, atividade.id);
  }

  async function entregar() {
    setEntrega({ estado: "montando" });
    setCopiado(null);
    try {
      const arquivo = await montar();
      setEntrega({ estado: "pronta", arquivo, baixou: baixarArquivo(arquivo.nome, arquivo.conteudo) });
    } catch {
      setEntrega({ estado: "erro" });
    }
  }

  async function copiarCodigo() {
    try {
      const arquivo = entrega.estado === "pronta" ? entrega.arquivo : await montar();
      if (entrega.estado !== "pronta") setEntrega({ estado: "pronta", arquivo, baixou: false });
      setCopiado(await copiarTexto(arquivo.codigo));
    } catch {
      setCopiado(false);
    }
  }

  const semPalpites = resumo !== null && resumo.numeros.palpites === 0;
  const numeros = resumo?.numeros;

  return (
    <div className="flex flex-col gap-4">
      <p>
        Você é <strong>{sala.apelido}</strong> na sala <strong className="font-mono">{sala.sala}</strong>.
      </p>

      {resumo ? (
        <>
          <Ideias
            titulo={TITULO_ENTENDIDAS}
            icone="✓"
            frases={resumo.entendidas}
            // Nunca 'nenhuma': um palpite certo numa pergunta sem regra por trás não vira ideia, e ler
            // 'nenhuma' depois de vários acertos soaria como 'você não entendeu nada'.
            vazio={semPalpites ? "As ideias aparecem quando você dá palpites." : "As ideias aparecem aqui quando um palpite mostra uma regra do Python."}
          />
          <Ideias titulo={TITULO_REVISAR} icone="↻" frases={resumo.revisar} vazio="Nada para revisar agora." />
          {numeros && (
            <section className="rounded-xl bg-gray-50 p-3">
              <h3 className="font-bold text-primaria">O que você fez</h3>
              <ul className="mt-1 grid gap-x-4 text-gray-800 sm:grid-cols-2">
                <li>Programas que você rodou: {numeros.programas}</li>
                <li>Palpites que você deu: {numeros.palpites}</li>
                <li>Palpites pulados: {numeros.pulados}</li>
                <li>Explicações que você abriu: {numeros.explicacoes}</li>
              </ul>
            </section>
          )}
        </>
      ) : (
        <p aria-live="polite" className="text-gray-700">
          {falhou ? "Não deu para montar o resumo agora. Tente de novo." : "Montando seu resumo..."}
        </p>
      )}

      <section className="flex flex-col gap-2 rounded-xl border-2 border-green-700/40 bg-green-50 p-3">
        <h3 className="font-bold text-primaria">Entregar ao professor</h3>
        <p className="text-gray-800">O arquivo leva seu apelido e suas respostas. Não leva seu nome nem seu código.</p>
        <button type="button" className={`${botaoPrimario} self-start`} onClick={entregar} disabled={entrega.estado === "montando"}>
          Entregar ao professor
        </button>
        <div aria-live="polite">
          {entrega.estado === "pronta" && entrega.baixou && (
            <div className="rounded-lg bg-white p-3">
              <p className="font-semibold text-green-800">
                <span aria-hidden="true">✓ </span>Pronto! O arquivo foi baixado.
              </p>
              <p className="mt-1 break-all font-mono text-sm">{entrega.arquivo.nome}</p>
              <p className="mt-1">Envie como o professor pediu. Nunca pelo chat do Meet.</p>
            </div>
          )}
          {entrega.estado === "pronta" && !entrega.baixou && copiado === null && <p className="text-red-800">O navegador não baixou o arquivo. Use o código abaixo.</p>}
          {entrega.estado === "erro" && <p className="text-red-800">Não deu para montar o arquivo. Tente de novo.</p>}
        </div>
        <details className="text-sm" open={entrega.estado === "pronta" && !entrega.baixou}>
          <summary className="min-h-11 cursor-pointer content-center font-semibold">Não consegue mandar o arquivo?</summary>
          <p className="text-gray-800">Copie o código da entrega e cole no formulário do professor.</p>
          <button type="button" className={`${botaoSecundario} mt-2`} onClick={copiarCodigo}>
            Copiar código da entrega
          </button>
          <p aria-live="polite" className="mt-1">
            {copiado === true && "✓ Código copiado."}
            {copiado === false && "Não deu para copiar sozinho. Selecione o código e copie."}
          </p>
          {entrega.estado === "pronta" && (
            <textarea
              readOnly
              value={entrega.arquivo.codigo}
              rows={3}
              aria-label="Código da entrega"
              onFocus={(e) => e.currentTarget.select()}
              className="mt-2 w-full rounded-lg border border-gray-300 p-2 font-mono text-xs"
            />
          )}
        </details>
      </section>

      <div className="flex flex-wrap gap-2">
        <button type="button" className={botaoSecundario} onClick={aoVoltar}>
          ◀ Voltar para a atividade
        </button>
        <button type="button" className={`${botaoSecundario} border-red-300 text-red-800`} onClick={aoApagar}>
          Sair e apagar deste aparelho
        </button>
      </div>
      <p className="text-sm text-gray-700">Já entregou? Então pode apagar tudo deste aparelho.</p>
    </div>
  );
}
