import { useEffect, useId, useRef, useState } from "react";
import type { CriarCanal } from "../motor/ponte";
import type { CatalogoPraticar, ExercicioGerado, Formato, ItemDaSerie, NivelDePraticar, TemaDePraticar } from "../motor/tipos";
import { useMotor } from "../motor/useMotor";
import { fragmentoDePraticar, type PedidoDePraticar } from "../rotas";
import { copiarTexto } from "../sala/arquivos";
import { Cabecalho } from "./Cabecalho";
import { Escolha, type Opcao } from "./Escolha";
import { Palco } from "./Palco";

/** Quantos exercícios tem uma série: poucos, para terminar. */
export const TAMANHO_DA_SERIE = 5;
/** O motor aceita no máximo 500 chaves em `excluir` (praticar.MAX_EXCLUIDOS). */
const MAX_EXCLUIDOS = 500;
/** Quantas sementes novas a página tenta até achar uma série sem nada já visto (ver montar). */
const TENTATIVAS_DE_SEMENTE = 8;

const FORMATOS: Opcao<Formato>[] = [
  { valor: "alternativas", rotulo: "Alternativas" },
  { valor: "livre", rotulo: "Resposta livre" },
];

const botaoPrimario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-primaria px-4 py-2 font-semibold text-white transition hover:bg-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-40";
const botaoSecundario =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800 transition hover:border-secundaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-40";
const botaoDeTexto =
  "inline-flex min-h-11 items-center rounded px-1 text-sm font-semibold text-secundaria underline decoration-2 underline-offset-2 hover:text-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";
const cartao =
  "flex min-h-11 cursor-pointer flex-col justify-center gap-0.5 rounded-xl border-2 border-gray-300 bg-white px-3 py-2 text-primaria transition hover:border-secundaria has-[:checked]:border-primaria has-[:checked]:bg-primaria has-[:checked]:text-white has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-destaque";
const titulo2 = "text-xl font-bold text-primaria focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque";

/** Uma série: o tema, o nível e a semente decidem os exercícios (o mesmo link, a mesma série para a turma). */
type Serie = { tema: TemaDePraticar; nivel: NivelDePraticar; semente: number; formato: Formato; familia?: string };

/**
 * O que o link do professor abre, comparado com a tela:
 * - "mesma": a série da tela, inteira (ela saiu da semente sem nada excluído);
 * - "sem_trocas": a série como começou ('Outro exercício' trocou algum);
 * - null: nenhum link reproduz a série (ela precisou pular exercícios já vistos).
 */
type Reproducao = "mesma" | "sem_trocas" | null;

type Fase =
  | { tipo: "escolher" }
  | { tipo: "montando" }
  | { tipo: "sem_serie"; motivo: "vazio" | "acabou" | "falhou" }
  | { tipo: "serie"; itens: ItemDaSerie[]; indice: number }
  | { tipo: "fim" };

const TEXTOS_SEM_SERIE: Record<"vazio" | "acabou" | "falhou", [string, string]> = {
  vazio: ["Ainda não há exercícios aqui.", "Que tal outro tema?"],
  acabou: ["Você já viu todos os exercícios daqui.", "Que tal outro tema?"],
  falhou: ["Os exercícios não abriram.", "Tente de novo ou escolha outro tema."],
};

/** Uma semente nova para a série (0 a 2³² - 1, como o motor aceita). */
function novaSemente(): number {
  return globalThis.crypto.getRandomValues(new Uint32Array(1))[0];
}

/** O link pede uma série que o catálogo conhece? Senão, a página abre a escolha. */
function serieDoPedido(pedido: PedidoDePraticar, catalogo: CatalogoPraticar): Serie | null {
  const tema = catalogo.temas.find((t) => t.id === pedido.tema);
  if (!tema || pedido.semente === undefined || !tema.niveis.some((n) => n.nivel === pedido.nivel)) return null;
  const familia = pedido.familia && Object.hasOwn(catalogo.familias, pedido.familia) && catalogo.familias[pedido.familia].tema === tema.id ? pedido.familia : undefined;
  return { tema: tema.id, nivel: pedido.nivel!, semente: pedido.semente, formato: pedido.formato ?? "alternativas", familia };
}

/** As chaves já vistas deste tema e nível ("familia@versao:nivel:semente"), as mais novas por último. */
function vistosDaSerie(vistos: string[], serie: Serie, catalogo: CatalogoPraticar): string[] {
  const doTema = vistos.filter((chave) => {
    const [familia, resto = ""] = chave.split("@");
    return Object.hasOwn(catalogo.familias, familia) && catalogo.familias[familia].tema === serie.tema && resto.split(":")[1] === String(serie.nivel);
  });
  return doTema.slice(-MAX_EXCLUIDOS);
}

type OpcaoEmCartao<T> = { valor: T; nome: string; descricao?: string };

/** Escolha única em cartões grandes (radio de verdade por baixo, como a Escolha). */
function Cartoes<T extends string | number>({ legenda, opcoes, valor, aoMudar, colunas }: { legenda: string; opcoes: OpcaoEmCartao<T>[]; valor: T; aoMudar: (valor: T) => void; colunas: string }) {
  const nome = useId();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 font-semibold">{legenda}</legend>
      <div className={`grid gap-2 ${colunas}`}>
        {opcoes.map((opcao) => (
          <label key={opcao.valor} className={cartao}>
            <input
              type="radio"
              name={nome}
              value={opcao.valor}
              checked={valor === opcao.valor}
              onChange={() => aoMudar(opcao.valor)}
              aria-labelledby={`${nome}-${opcao.valor}`}
              aria-describedby={opcao.descricao ? `${nome}-${opcao.valor}-d` : undefined}
              className="sr-only"
            />
            <span className="flex items-center gap-1 font-bold">
              {/* A escolhida também tem marca em texto, não só a cor. */}
              <span aria-hidden="true">{valor === opcao.valor ? "●" : "○"}</span>
              <span id={`${nome}-${opcao.valor}`}>{opcao.nome}</span>
            </span>
            {opcao.descricao && (
              <span id={`${nome}-${opcao.valor}-d`} className="text-sm">
                {opcao.descricao}
              </span>
            )}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** O link desta série para o professor mandar à turma; sem área de transferência, o link fica à vista. */
function LinkDaSerie({ serie, reproducao }: { serie: Serie; reproducao: "mesma" | "sem_trocas" }) {
  const campo = useRef<HTMLInputElement>(null);
  const [copia, setCopia] = useState<"copiado" | "falhou" | null>(null);
  const link = `${window.location.href.split("#")[0]}${fragmentoDePraticar(serie)}`;

  async function copiar() {
    setCopia((await copiarTexto(link)) ? "copiado" : "falhou");
  }

  useEffect(() => {
    if (copia === "falhou") campo.current?.select();
  }, [copia]);

  return (
    <div className="flex flex-col gap-1">
      <button type="button" className={`${botaoDeTexto} self-start`} onClick={copiar}>
        Para o professor: copiar o link desta série
      </button>
      <p aria-live="polite" className="text-sm font-semibold">
        {copia === "copiado" && (
          <span className="text-green-800">
            {reproducao === "mesma" ? "✓ Link copiado. Quem abrir verá a mesma série." : "✓ Link copiado. Ele abre esta série como começou, antes das trocas."}
          </span>
        )}
        {copia === "falhou" && <span className="text-red-800">Não deu para copiar sozinho. Copie o link abaixo.</span>}
      </p>
      {copia === "falhou" && (
        <input
          ref={campo}
          readOnly
          value={link}
          aria-label="Link desta série"
          onFocus={(e) => e.currentTarget.select()}
          className="min-h-11 w-full rounded-lg border-2 border-gray-300 bg-gray-50 px-2 font-mono text-sm"
        />
      )}
    </div>
  );
}

/**
 * A área Praticar: o aluno escolhe um tema e o que praticar nele, e recebe uma
 * série curta de programas gerados pelo motor (praticar.py) para dar palpites
 * no Prever. Tudo vem do catálogo do motor: nenhum tema ou família fica escrito
 * aqui. Nada é guardado: o que o aluno já viu fica só na memória da página.
 * Sem placar e sem nada automático: o aluno decide quando seguir.
 */
export function Praticar({ pedido, criarCanal }: { pedido: PedidoDePraticar; criarCanal?: CriarCanal }) {
  const motor = useMotor(criarCanal);
  const { pedir } = motor;
  const [catalogo, setCatalogo] = useState<CatalogoPraticar | null>(null);
  const [falhaNoCatalogo, setFalhaNoCatalogo] = useState(false);
  const [tema, setTema] = useState<string | undefined>(pedido.tema);
  const [nivel, setNivel] = useState<NivelDePraticar | undefined>(pedido.nivel);
  const [formato, setFormato] = useState<Formato>(pedido.formato ?? "alternativas");
  const [serie, setSerie] = useState<Serie | null>(null);
  const [reproducao, setReproducao] = useState<Reproducao>(null);
  const [fase, setFase] = useState<Fase>({ tipo: "escolher" });
  const [exercicio, setExercicio] = useState<{ chave: string; dados: ExercicioGerado | null } | null>(null);
  const [troca, setTroca] = useState<"buscando" | "trocado" | "acabou" | "falhou" | null>(null);
  // Tudo o que já apareceu nesta visita (chaves de ItemDaSerie): volta em `excluir`, nunca é guardado.
  const vistos = useRef<string[]>([]);
  // Respostas atrasadas do motor (de uma série que o aluno já trocou) são descartadas.
  const pedidoAtual = useRef(0);
  // O mesmo para 'Outro exercício': depois de 'Próximo' (ou de outra série), a troca pedida antes não vale mais.
  const trocaAtual = useRef(0);
  // Depois de uma ação do aluno, o foco vai para o título novo (senão cai no body e o leitor de tela se perde).
  const titulo = useRef<HTMLHeadingElement>(null);
  const focar = useRef(false);

  useEffect(() => {
    if (focar.current && titulo.current) {
      focar.current = false;
      titulo.current.focus();
    }
  });

  function marcarVistos(itens: ItemDaSerie[]) {
    const novos = itens.map((item) => item.chave).filter((chave) => !vistos.current.includes(chave));
    vistos.current = [...vistos.current, ...novos];
  }

  function pedirSerie(nova: Serie, excluir: string[]) {
    return pedir("montar_serie", {
      tema: nova.tema,
      nivel: nova.nivel,
      semente: nova.semente,
      quantidade: TAMANHO_DA_SERIE,
      ...(nova.familia ? { familia: nova.familia } : {}),
      excluir,
    });
  }

  /**
   * Monta a série e diz se o link a reproduz. O link só leva tema, nível e
   * semente, então a série da tela precisa ser a da semente sem nada excluído.
   * Quando o aluno já viu exercícios daqui ('Mais 5', ou o mesmo tema de novo),
   * a página sorteia outra semente até achar uma série sem nada visto. Se não
   * achar (o aluno já viu quase tudo), pula os vistos e fica sem link.
   */
  async function montar(pedida: Serie, cat: CatalogoPraticar) {
    const vez = ++pedidoAtual.current;
    trocaAtual.current++;
    setSerie(pedida);
    setFase({ tipo: "montando" });
    setTroca(null);
    try {
      const vistosAqui = vistosDaSerie(vistos.current, pedida, cat);
      let nova = pedida;
      let itens = await pedirSerie(nova, []);
      let fiel = true;
      for (let tentativa = 1; itens.some((item) => vistosAqui.includes(item.chave)); tentativa++) {
        if (tentativa >= TENTATIVAS_DE_SEMENTE) {
          itens = await pedirSerie(nova, vistosAqui);
          fiel = false;
          break;
        }
        nova = { ...pedida, semente: novaSemente() };
        itens = await pedirSerie(nova, []);
      }
      if (vez !== pedidoAtual.current) return;
      marcarVistos(itens);
      setSerie(nova);
      setReproducao(fiel ? "mesma" : null);
      // O endereço vira o link da série: recarregar a página volta para ela. Sem link, volta à escolha.
      window.history.replaceState(null, "", fragmentoDePraticar(fiel ? nova : { ...nova, semente: undefined }));
      // Sem nada excluído e sem itens: este tema ainda não tem exercícios neste nível.
      setFase(itens.length > 0 ? { tipo: "serie", itens, indice: 0 } : { tipo: "sem_serie", motivo: vistosAqui.length > 0 ? "acabou" : "vazio" });
    } catch {
      if (vez === pedidoAtual.current) setFase({ tipo: "sem_serie", motivo: "falhou" });
    }
  }

  // O catálogo vem do motor. Um link de série que ele reconhece já abre o primeiro exercício.
  useEffect(() => {
    let vivo = true;
    pedir("catalogo_praticar", {}).then(
      (lido) => {
        if (!vivo) return;
        setCatalogo(lido);
        const doLink = serieDoPedido(pedido, lido);
        if (doLink) montar(doLink, lido);
      },
      () => vivo && setFalhaNoCatalogo(true),
    );
    return () => {
      vivo = false;
    };
    // O pedido só é lido ao abrir: outro link recria a página (App usa o pedido como key).
  }, [pedir]);

  const item = fase.tipo === "serie" ? fase.itens[fase.indice] : null;

  useEffect(() => {
    if (!item) return;
    let vivo = true;
    pedir("gerar_exercicio", { familia: item.familia, nivel: item.nivel, semente: item.semente }).then(
      (dados) => vivo && setExercicio({ chave: item.chave, dados }),
      () => vivo && setExercicio({ chave: item.chave, dados: null }),
    );
    return () => {
      vivo = false;
    };
  }, [item, pedir]);

  function comecar(nova: Serie) {
    if (!catalogo) return;
    focar.current = true;
    montar(nova, catalogo);
  }

  function escolherOutroTema() {
    pedidoAtual.current++;
    trocaAtual.current++;
    focar.current = true;
    if (serie) {
      setTema(serie.tema);
      setNivel(serie.nivel);
      setFormato(serie.formato);
    }
    setSerie(null);
    setFase({ tipo: "escolher" });
    window.history.replaceState(null, "", fragmentoDePraticar({}));
  }

  function proximo() {
    if (fase.tipo !== "serie") return;
    focar.current = true;
    trocaAtual.current++;
    setTroca(null);
    if (fase.indice < fase.itens.length - 1) setFase({ ...fase, indice: fase.indice + 1 });
    else setFase({ tipo: "fim" });
  }

  // 'Outro exercício': o próximo da mesma série que ainda não apareceu toma o lugar deste.
  async function outro() {
    if (fase.tipo !== "serie" || !serie || !catalogo || troca === "buscando") return;
    const vez = ++trocaAtual.current;
    const indice = fase.indice;
    setTroca("buscando");
    try {
      const [novo] = await pedir("montar_serie", {
        tema: serie.tema,
        nivel: serie.nivel,
        semente: serie.semente,
        quantidade: 1,
        ...(serie.familia ? { familia: serie.familia } : {}),
        excluir: vistosDaSerie(vistos.current, serie, catalogo),
      });
      // O aluno já seguiu (Próximo, outra série): esta resposta não vale mais e não aparece.
      if (vez !== trocaAtual.current) return;
      if (!novo) {
        setTroca("acabou");
        return;
      }
      marcarVistos([novo]);
      focar.current = true;
      // O título continua "Exercício k de 5": o aviso diz ao leitor de tela que o exercício mudou.
      setTroca("trocado");
      setReproducao((agora) => (agora === "mesma" ? "sem_trocas" : agora));
      setFase((agora) =>
        agora.tipo === "serie" && agora.indice === indice ? { ...agora, itens: agora.itens.map((antigo, k) => (k === indice ? novo : antigo)) } : agora,
      );
    } catch {
      if (vez === trocaAtual.current) setTroca("falhou");
    }
  }

  const temaDaSerie = serie && catalogo ? catalogo.temas.find((t) => t.id === serie.tema) : undefined;
  const nomeDoNivel = temaDaSerie?.niveis.find((n) => n.nivel === serie?.nivel)?.nome;

  let conteudo;
  if (!catalogo) {
    conteudo = (
      <main className="mx-auto max-w-xl p-4">
        <p aria-live="polite" className="rounded-xl bg-white p-4 shadow-sm">
          {falhaNoCatalogo || motor.estado === "falhou" ? "Não deu para abrir os exercícios. Recarregue a página." : "Preparando..."}
        </p>
      </main>
    );
  } else if (fase.tipo === "escolher") {
    const temaEscolhido = catalogo.temas.find((t) => t.id === tema) ?? catalogo.temas[0];
    const nivelEscolhido = temaEscolhido?.niveis.find((n) => n.nivel === nivel) ?? temaEscolhido?.niveis[0];
    conteudo = (
      <main className="mx-auto flex max-w-3xl flex-col gap-5 p-4">
        <div>
          <h2 ref={titulo} tabIndex={-1} className={`${titulo2} text-2xl`}>
            Praticar
          </h2>
          <p className="mt-1 text-gray-800">Programas curtos para você dar palpites. Escolha o tema e comece.</p>
        </div>
        {temaEscolhido && nivelEscolhido ? (
          <>
            <Cartoes
              legenda="Tema:"
              opcoes={catalogo.temas.map((t) => ({ valor: t.id, nome: t.nome, descricao: t.descricao }))}
              valor={temaEscolhido.id}
              aoMudar={setTema}
              colunas="sm:grid-cols-3"
            />
            <Cartoes
              legenda="O que praticar:"
              opcoes={temaEscolhido.niveis.map((n) => ({ valor: n.nivel, nome: n.nome }))}
              valor={nivelEscolhido.nivel}
              aoMudar={setNivel}
              colunas="sm:grid-cols-3"
            />
            <Escolha legenda="Perguntas:" opcoes={FORMATOS} valor={formato} aoMudar={setFormato} />
            <button
              type="button"
              className={`${botaoPrimario} self-start text-lg`}
              onClick={() => comecar({ tema: temaEscolhido.id, nivel: nivelEscolhido.nivel, semente: novaSemente(), formato })}
            >
              Começar ▶
            </button>
          </>
        ) : (
          <p className="rounded-xl bg-white p-4 shadow-sm">Ainda não há exercícios por aqui.</p>
        )}
      </main>
    );
  } else if (fase.tipo === "montando") {
    conteudo = (
      <main className="mx-auto max-w-xl p-4">
        <p aria-live="polite" className="rounded-xl bg-white p-4 shadow-sm">
          Preparando...
        </p>
      </main>
    );
  } else if (fase.tipo === "sem_serie" || fase.tipo === "fim") {
    const fim = fase.tipo === "fim";
    conteudo = (
      <main className="mx-auto flex max-w-xl flex-col gap-4 p-4">
        <div className="rounded-xl bg-white p-4 shadow-sm" role={fim ? undefined : "status"}>
          <h2 ref={titulo} tabIndex={-1} className={titulo2}>
            {fim ? "Por hoje é isso." : TEXTOS_SEM_SERIE[fase.motivo][0]}
          </h2>
          <p className="mt-1 text-gray-800">{fim ? "Quer praticar mais? Você escolhe." : TEXTOS_SEM_SERIE[fase.motivo][1]}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {fim && serie && (
            <button type="button" className={botaoPrimario} onClick={() => comecar({ ...serie, semente: novaSemente() })}>
              Mais 5 deste tema
            </button>
          )}
          {!fim && fase.motivo === "falhou" && serie && (
            <button type="button" className={botaoPrimario} onClick={() => comecar(serie)}>
              Tentar de novo
            </button>
          )}
          <button type="button" className={botaoSecundario} onClick={escolherOutroTema}>
            Escolher outro tema
          </button>
          <a href="#" className={botaoSecundario}>
            Voltar ao início
          </a>
        </div>
      </main>
    );
  } else {
    const atual = fase.itens[fase.indice];
    const ultimo = fase.indice === fase.itens.length - 1;
    const pronto = exercicio && exercicio.chave === atual.chave ? exercicio : null;
    const aviso =
      troca === "buscando"
        ? "Procurando outro exercício..."
        : troca === "trocado"
          ? "Exercício trocado."
          : troca === "acabou"
            ? "Não há outro exercício agora. Siga com este ou escolha outro tema."
            : troca === "falhou"
              ? "Não deu para trocar agora. Tente de novo."
              : "";
    conteudo = (
      <main>
        <div className="mx-auto max-w-7xl px-4 pt-4">
          <nav aria-label="Exercícios da série" className="flex flex-col gap-2 rounded-xl bg-white p-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <h2 ref={titulo} tabIndex={-1} className={`${titulo2} text-lg`}>
                Exercício {fase.indice + 1} de {fase.itens.length}
              </h2>
              {temaDaSerie && (
                <span className="text-sm text-gray-700">
                  {temaDaSerie.nome}
                  {nomeDoNivel && ` · ${nomeDoNivel}`}
                </span>
              )}
              <span className="ml-auto" />
              {/* aria-disabled, e não disabled: o botão desabilitado perderia o foco (cairia no body). */}
              <button type="button" className={`${botaoSecundario} aria-disabled:opacity-40`} onClick={outro} aria-disabled={troca === "buscando"}>
                Outro exercício
              </button>
              <button type="button" className={botaoPrimario} onClick={proximo}>
                {ultimo ? "Terminar" : "Próximo ▶"}
              </button>
            </div>
            {pronto?.dados && <p className="text-lg">{pronto.dados.contexto}</p>}
            <p aria-live="polite" className="text-sm font-semibold text-gray-700">
              {aviso}
            </p>
            {serie && reproducao && <LinkDaSerie key={`${fragmentoDePraticar(serie)}:${reproducao}`} serie={serie} reproducao={reproducao} />}
          </nav>
        </div>
        {pronto?.dados ? (
          <Palco key={atual.chave} motor={motor} codigo={pronto.dados.codigo} entradas={pronto.dados.entradas.join("\n")} modo="prever" formato={serie?.formato ?? "alternativas"} />
        ) : (
          <div className="mx-auto max-w-7xl px-4 pt-4">
            <p aria-live="polite" className="rounded-xl bg-white p-4 shadow-sm">
              {pronto ? "Este exercício não abriu. Tente outro." : "Preparando o exercício..."}
            </p>
          </div>
        )}
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <Cabecalho estado={motor.estado} subtitulo="Praticar" linkParaInicio />
      {conteudo}
    </div>
  );
}
