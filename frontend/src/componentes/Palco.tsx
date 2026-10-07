import { useCallback, useEffect, useId, useMemo, useReducer, useRef, useState, type ReactNode } from "react";
import { anteriorNoQuadro, cenaDoEditor, pilulaDaVolta, retornosVisiveis, type Balao, type CenaDoEditor, type Revelacao } from "../motor/cena";
import {
  PALCO_VAZIO,
  balaoDoPalco,
  destinoPermitido,
  ondeOlhar,
  palco,
  passoResolvido,
  pontosDoPasso,
  type Camada,
} from "../motor/palco";
import { ErroDoMotor } from "../motor/ponte";
import { aplicarAtividade, narracaoVisivel } from "../motor/revelacao";
import type { Atividade, ConfigDaAtividade, ErroDoAluno, Evento, Faixa, Formato, Modo, RespostaDoAluno } from "../motor/tipos";
import type { Motor } from "../motor/useMotor";
import { BalaoPrevisao, RASCUNHO_VAZIO, type Rascunho } from "./BalaoPrevisao";
import { CaixaErro } from "./CaixaErro";
import { Controles } from "./Controles";
import { Editor } from "./Editor";
import { Narracao } from "./Narracao";
import { PainelDetetive } from "./PainelDetetive";
import { rolarAcimaDaBarra } from "./rolar";
import { useTelaGrande } from "./useTelaGrande";
import { Variaveis, primeiraMudanca, texto } from "./Variaveis";

/** O que o palco conta para o diário (2.5). Quem monta o Evento completo é a página da atividade. */
export type RegistroDoPalco =
  | { tipo: "Run.Program"; ms: number }
  | { tipo: "Step"; passo: number }
  | {
      tipo: "Prediction";
      ponto: string;
      formato: Formato;
      resposta: NonNullable<Evento["resposta"]>;
      certa: boolean;
      /** Só quando o palpite foi diferente e um modelo só explica: nunca vai para a tela. */
      concepcao: string | null;
      testadas: string[];
      ms: number;
    }
  | { tipo: "Prediction.Skip"; ponto: string; formato: Formato; ms: number }
  | { tipo: "Feedback.Layer"; ponto: string; camada: Camada; concepcao: string | null }
  | { tipo: "Error"; erro: string };

type Props = {
  motor: Motor;
  codigo: string;
  /** Sem ela, o código é só para ler (o programa de uma atividade). */
  aoMudarCodigo?: (codigo: string) => void;
  entradas: string;
  aoMudarEntradas?: (entradas: string) => void;
  /** A atividade decide a tela: no Assistir não há palpites; no Prever, há. */
  modo: Modo;
  formato: Formato;
  /** O resto da configuração da atividade (max_pontos, palpite_inicial, semente...). */
  config?: Omit<ConfigDaAtividade, "modo" | "formato">;
  /** A semente do programa (a da atividade); sem ela, rodar de novo repete a da última vez. */
  semente?: number;
  /** O que fica acima do editor (os exemplos e o modo, no uso livre). */
  barra?: ReactNode;
  aoRegistrar?: (registro: RegistroDoPalco) => void;
};

/** Um passo a cada 1,5 s no autoplay: dá tempo de ler a frase do narrador. */
export const INTERVALO_MS = 1500;

/** Um pedido que não voltou vira uma caixa de erro como as do programa. */
function erroDoPedido(erro: unknown): ErroDoAluno {
  if (erro instanceof ErroDoMotor && erro.tipo !== "Motor") {
    return { tipo: erro.tipo, linha: null, mensagem: erro.message, original: "" };
  }
  const original = erro instanceof Error ? erro.message : String(erro);
  return { tipo: "Motor", linha: null, mensagem: "O PyVis não conseguiu rodar este programa. Tente de novo.", original };
}

/** A última linha com código: o balão do fim do programa fica preso nela. */
function ultimaLinha(codigo: string): number {
  const linhas = codigo.split("\n");
  for (let n = linhas.length; n >= 1; n--) if (linhas[n - 1].trim() !== "") return n;
  return 1;
}

/**
 * Depois de abrir uma camada, o que ela mostra fica à vista. A caixinha contornada por 'Onde olhar'
 * ou 'Me mostra' pode estar fora da tela (no celular, embaixo da barra fixa da linha do tempo): no
 * centro, ela fica acima da barra. Sem caixinha, rola o texto da camada, que no celular abria
 * embaixo da barra (e o toque parecia não fazer nada).
 */
function rolarAteACamada(camada: Camada, contornou: boolean) {
  setTimeout(() => {
    const contorno = contornou ? document.querySelector<HTMLElement>("[data-contorno]") : null;
    if (contorno) contorno.scrollIntoView?.({ block: "center", behavior: "smooth" });
    else rolarAcimaDaBarra(document.querySelector<HTMLElement>(`[data-camada="${camada}"]`), "smooth");
  }, 0);
}

function agora() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

/** 'linha 5', 'linhas 4 e 5', 'linhas 4 a 7': as linhas que a decisão pulou. */
export function textoDosPulados(pulados: Faixa[]): string {
  const partes = pulados.map(([ini, fim]) => (ini === fim ? `${ini}` : fim === ini + 1 ? `${ini} e ${fim}` : `${ini} a ${fim}`));
  const uma = pulados.length === 1 && pulados[0][0] === pulados[0][1];
  return `${uma ? "linha" : "linhas"} ${partes.join(", ")}`;
}

/** O balão da decisão como no editor ('7 >= 6 → Verdadeiro'). Só para os olhos: o narrador diz o mesmo. */
function BalaoDaDecisao({ balao }: { balao: Balao }) {
  return (
    <span className="cm-balao" aria-hidden="true" data-balao="decisao">
      {balao.trechos.map((trecho, n) => (
        <span key={n} className={trecho.naoCalculado ? "cm-balao-nao-calculado" : undefined} title={trecho.naoCalculado ? "nem foi calculado" : undefined}>
          {trecho.texto}
        </span>
      ))}
      {balao.valor !== null && (
        <strong className={balao.valor ? "cm-balao-verdadeiro" : "cm-balao-falso"}>
          {`${balao.trechos.length > 0 ? " → " : ""}${balao.valor ? "Verdadeiro" : "Falso"}`}
        </strong>
      )}
    </span>
  );
}

/**
 * No celular, a aba Passos mostra a linha atual em cima: o balão fica logo abaixo dela. A cena
 * é a mesma do editor (que fica na outra aba): o balão da decisão e as linhas puladas também.
 */
function TrechoAtual({ codigo, cena }: { codigo: string; cena: CenaDoEditor }) {
  // Sem linha atual (o fim do programa), o narrador já diz que terminou.
  const faixa = cena.atual ?? (cena.erro !== null ? ([cena.erro, cena.erro] as const) : null);
  if (!faixa) return null;
  const linhas = codigo.split("\n").slice(faixa[0] - 1, faixa[1]);
  const erro = cena.atual === null;
  return (
    <div className="overflow-x-auto rounded-xl bg-white p-2 shadow-sm" aria-label={`Linha ${faixa[0]} do código`}>
      {linhas.map((linha, n) => (
        <div key={n} className={`flex gap-3 whitespace-pre px-2 font-mono ${erro ? "cm-linha-erro" : "cm-linha-atual"}`}>
          <span aria-hidden="true" className="select-none text-gray-500">
            {faixa[0] + n}
          </span>
          <span>{linha}</span>
        </div>
      ))}
      {cena.balao && (
        <div className="mt-1 pl-6">
          <BalaoDaDecisao balao={cena.balao} />
        </div>
      )}
      {cena.pulados.length > 0 && (
        <p aria-hidden="true" data-pulados className="trecho-pulado mt-1 rounded px-2 text-sm">
          ↷ pulado: {textoDosPulados(cena.pulados)}
        </p>
      )}
    </div>
  );
}

/**
 * O palco de um programa: editor, linha do tempo, narrador, caixinhas e saída,
 * mais o balão de palpite e o Detetive no modo Prever. A atividade decide a
 * tela (spec 2.6): o modo liga só os recursos da etapa, e cada passo tem no
 * máximo um balão e uma caixinha animada. Abaixo do lg, a tela vira duas abas
 * (Código e Passos) com a linha do tempo fixa embaixo.
 */
export function Palco({ motor, codigo, aoMudarCodigo, entradas, aoMudarEntradas, modo, formato, config, semente, barra, aoRegistrar }: Props) {
  const telaGrande = useTelaGrande();
  const ids = useId();
  const [estado, despachar] = useReducer(palco, PALCO_VAZIO);
  const [erroDoMotor, setErroDoMotor] = useState<ErroDoAluno | null>(null);
  const [preparando, setPreparando] = useState(false);
  const [corrigindo, setCorrigindo] = useState(false);
  const [aviso, setAviso] = useState<{ ponto: string; texto: string } | null>(null);
  const [rascunho, setRascunho] = useState<{ ponto: string; rascunho: Rascunho } | null>(null);
  const [aba, setAba] = useState<"codigo" | "passos">("codigo");
  const [entradasAbertas, setEntradasAbertas] = useState(Boolean(entradas));
  const campoDeEntradas = useRef<HTMLTextAreaElement>(null);
  // Rodar de novo o mesmo programa repete os mesmos sorteios.
  const ultimaExecucao = useRef<{ codigo: string; entradas: string; semente: number } | null>(null);
  // Muda a cada execução e a cada mudança do programa: respostas atrasadas do Python são descartadas.
  const versao = useRef(0);
  const mostradoEm = useRef(new Map<string, number>());
  const registrarRef = useRef(aoRegistrar);
  registrarRef.current = aoRegistrar;
  const registrar = useCallback((registro: RegistroDoPalco) => registrarRef.current?.(registro), []);

  // Outro programa, outras entradas ou outro modo: a execução anterior não vale mais.
  useEffect(() => {
    versao.current += 1;
    despachar({ tipo: "esquecer" });
    setErroDoMotor(null);
    setAviso(null);
  }, [codigo, entradas, modo, formato]);

  // Entradas que chegam de fora (um exemplo escolhido) abrem ou fecham o campo.
  useEffect(() => {
    if (document.activeElement !== campoDeEntradas.current) setEntradasAbertas(Boolean(entradas));
  }, [entradas]);

  const execucao = estado.execucao;
  const resultado = execucao?.resultado ?? null;
  const atividade = execucao?.atividade ?? null;
  const passos = useMemo(() => resultado?.passos ?? [], [resultado]);
  const total = passos.length;
  const emPassos = estado.fase === "passos" && resultado !== null;
  const passo = emPassos ? passos[estado.passo] : undefined;
  const noUltimo = estado.passo === total - 1;
  const balao = balaoDoPalco(estado);
  const pergunta = balao && !balao.correcao ? balao.ponto : null;

  const revelacao: Revelacao = useMemo(() => ({ respondidos: estado.respondidos, alcancado: estado.alcancado }), [estado.respondidos, estado.alcancado]);
  const cenaCompleta = useMemo(() => cenaDoEditor(emPassos ? resultado : null, estado.passo, revelacao), [emPassos, resultado, estado.passo, revelacao]);
  // Orçamento de atenção: com o balão do palpite aberto, o balão da decisão não aparece.
  const cena = useMemo(() => (balao && cenaCompleta.balao ? { ...cenaCompleta, balao: null } : cenaCompleta), [balao, cenaCompleta]);
  const volta = useMemo(() => (resultado && passo ? pilulaDaVolta(passo, resultado.estrutura.comandos, revelacao) : null), [resultado, passo, revelacao]);
  const retornos = retornosVisiveis(passo, revelacao);
  // Com perguntas abertas, a linha do tempo não mostra o total (ele diria o número de voltas).
  const pontos = pontosDoPasso(atividade);
  const alcance = pontos.some((ponto) => !estado.respondidos.has(ponto.id))
    ? destinoPermitido(pontos, estado.respondidos, estado.passo, Math.max(0, total - 1))
    : undefined;

  // O tempo de cada palpite conta de quando a pergunta apareceu.
  const perguntaId = pergunta?.id ?? null;
  useEffect(() => {
    if (perguntaId && !mostradoEm.current.has(perguntaId)) mostradoEm.current.set(perguntaId, agora());
  }, [perguntaId]);
  const tempoDe = (id: string) => Math.max(0, Math.round(agora() - (mostradoEm.current.get(id) ?? agora())));

  // Cada passo que o aluno dá vai para o diário (não o autoplay, nem a primeira tela de uma execução).
  const ultimoMovimento = useRef({ movimento: estado.movimento, execucao });
  useEffect(() => {
    const anterior = ultimoMovimento.current;
    ultimoMovimento.current = { movimento: estado.movimento, execucao };
    if (anterior.movimento !== estado.movimento && anterior.execucao === execucao && execucao && estado.fase === "passos") {
      registrar({ tipo: "Step", passo: estado.passo });
    }
  }, [estado.movimento, estado.passo, estado.fase, execucao, registrar]);

  // Autoplay: anda sozinho e para no primeiro ponto sem resposta (o reducer cuida disso).
  useEffect(() => {
    if (!estado.tocando) return;
    const relogio = setTimeout(() => despachar({ tipo: "ir", destino: estado.passo + 1, origem: "autoplay" }), INTERVALO_MS);
    return () => clearTimeout(relogio);
  }, [estado.tocando, estado.passo]);

  // Quando o balão fecha com o foco dentro dele, o foco vai para 'Avançar' (não se perde no body).
  const balaoAberto = balao !== null;
  useEffect(() => {
    if (balaoAberto) return;
    const ativo = document.activeElement;
    if (ativo === null || ativo === document.body) document.querySelector<HTMLElement>("[data-avancar]:not(:disabled)")?.focus({ preventScroll: true });
  }, [balaoAberto]);

  const irPara = useCallback((destino: number) => despachar({ tipo: "ir", destino, origem: "aluno" }), []);
  const tocar = useCallback((tocando: boolean) => despachar({ tipo: "tocar", tocando }), []);

  async function executar() {
    const linhas = entradas.split("\n").filter((linha) => linha !== "");
    const ultima = ultimaExecucao.current;
    const repetir = ultima && ultima.codigo === codigo && ultima.entradas === entradas ? ultima.semente : undefined;
    const minha = ++versao.current;
    setErroDoMotor(null);
    setAviso(null);
    const inicio = agora();
    try {
      const novo = await motor.rastrear(codigo, linhas, semente ?? repetir);
      if (minha !== versao.current) return; // o programa mudou enquanto o Python rodava
      ultimaExecucao.current = { codigo, entradas, semente: novo.semente };
      registrar({ tipo: "Run.Program", ms: Math.round(agora() - inicio) });
      if (novo.erro) registrar({ tipo: "Error", erro: novo.erro.tipo });
      let atividadeNova: Atividade | null = null;
      let aplicado = novo;
      if (modo === "prever") {
        setPreparando(true);
        try {
          atividadeNova = await motor.prepararAtividade({ ...config, modo: "prever", formato });
          aplicado = aplicarAtividade(novo, atividadeNova);
        } catch {
          atividadeNova = null; // sem perguntas, o programa ainda roda como no Assistir
        } finally {
          setPreparando(false);
        }
        if (minha !== versao.current) return;
      }
      mostradoEm.current.clear();
      setRascunho(null);
      despachar({ tipo: "rodou", execucao: { resultado: aplicado, atividade: atividadeNova } });
      setAba(atividadeNova?.palpite_inicial ? "codigo" : "passos");
    } catch (erro) {
      if (minha !== versao.current) return;
      despachar({ tipo: "esquecer" });
      setErroDoMotor(erroDoPedido(erro));
      setAba("passos");
      if (erro instanceof ErroDoMotor && erro.tipo === "TempoEsgotado") registrar({ tipo: "Error", erro: "TempoEsgotado" });
    }
  }

  async function responder(resposta: RespostaDoAluno) {
    if (!pergunta || corrigindo) return;
    const ponto = pergunta;
    const minha = versao.current;
    setCorrigindo(true);
    setAviso(null);
    try {
      const correcao = await motor.corrigir(ponto.id, resposta);
      if (minha !== versao.current) return;
      if (!correcao.legivel) {
        // Não deu para ler (um texto no lugar de um número): a pergunta continua aberta e nada é registrado.
        setAviso({ ponto: ponto.id, texto: correcao.mensagem });
        return;
      }
      despachar({ tipo: "respondeu", ponto: ponto.id, correcao });
      // Depois do palpite inicial, o celular vai para os passos (como no Assistir).
      if (estado.fase === "palpite_inicial") setAba("passos");
      const doEvento: NonNullable<Evento["resposta"]> =
        "alternativa" in resposta
          ? { alternativa: resposta.alternativa }
          : {
              valor_normalizado: correcao.valor_normalizado,
              ...(ponto.tipo === "valor" && resposta.tipo_escolhido ? { tipo_escolhido: resposta.tipo_escolhido } : {}),
            };
      registrar({
        tipo: "Prediction",
        ponto: ponto.id,
        formato: ponto.formato,
        resposta: doEvento,
        certa: correcao.certa,
        concepcao: correcao.certa ? null : correcao.concepcao,
        testadas: correcao.testadas,
        ms: tempoDe(ponto.id),
      });
    } catch {
      if (minha !== versao.current) return;
      setAviso({ ponto: ponto.id, texto: "Não deu para conferir agora. Tente de novo." });
    } finally {
      setCorrigindo(false);
    }
  }

  function pular() {
    if (!pergunta || corrigindo) return;
    registrar({ tipo: "Prediction.Skip", ponto: pergunta.id, formato: pergunta.formato, ms: tempoDe(pergunta.id) });
    despachar({ tipo: "pulou", ponto: pergunta.id });
    if (estado.fase === "palpite_inicial") setAba("passos");
  }

  function abrirCamada(camada: Camada) {
    if (!balao?.correcao || !resultado) return;
    const { ponto, correcao } = balao;
    // Cada uso vira um evento (2.3), também quando o aluno abre a mesma camada de novo.
    registrar({ tipo: "Feedback.Layer", ponto: ponto.id, camada, concepcao: correcao.concepcao });
    if (camada === 1) {
      // A linha do tempo vai ao passo e a caixinha certa ganha contorno, se dá para chegar
      // lá sem passar de uma pergunta ainda aberta (senão o Detetive diz que vem depois).
      const onde = ondeOlhar(resultado, ponto, correcao.feedback);
      const livre = destinoPermitido(pontosDoPasso(atividade), estado.respondidos, estado.passo, onde.passo) === onde.passo;
      despachar(livre ? { tipo: "camada", camada, passo: onde.passo, contorno: onde.destacar } : { tipo: "camada", camada });
      if (livre) setAba("passos");
      rolarAteACamada(camada, livre);
    } else if (camada === 3) {
      // O passo resolvido, se dá para chegar nele sem passar de uma pergunta ainda aberta.
      const alvo = passoResolvido(resultado, ponto);
      const livre = destinoPermitido(pontosDoPasso(atividade), estado.respondidos, estado.passo, alvo) === alvo;
      const nome = ponto.tipo === "valor" ? (ponto.alvo.nome ?? null) : null;
      despachar(livre ? { tipo: "camada", camada, passo: alvo, contorno: nome } : { tipo: "camada", camada });
      if (livre) setAba("passos");
      rolarAteACamada(camada, livre);
    } else {
      despachar({ tipo: "camada", camada });
      rolarAteACamada(camada, false);
    }
  }

  // --- O que cada parte da tela mostra ---------------------------------------------

  const valorPendente = pergunta?.tipo === "valor" ? (pergunta.alvo.nome ?? null) : null;
  const naFuncao = Boolean(passo?.funcao) && valorPendente !== null && passo !== undefined && (valorPendente in passo.locais || !(valorPendente in passo.globais));
  const ocultas = valorPendente ? new Set([valorPendente]) : undefined;
  const anterioresLocais = passo?.funcao ? (anteriorNoQuadro(passos, estado.passo)?.locais ?? {}) : undefined;
  // Uma caixinha animada por passo: a da função tem a vez; com o balão aberto, nenhuma.
  const mudouNaFuncao = passo?.funcao ? primeiraMudanca(passo.locais, anterioresLocais, naFuncao ? ocultas : undefined) : null;
  const animadaLocal = balaoAberto ? null : mudouNaFuncao;
  const animadaGlobal = balaoAberto || mudouNaFuncao ? null : undefined;
  const contorno = estado.contorno && estado.contorno.passo === estado.passo ? estado.contorno.nome : null;
  const saida = emPassos && resultado ? (noUltimo || !passo ? resultado.saida : passo.saida) : "";
  const saidaPendente = pergunta?.tipo === "saida" && !balao?.inicial;
  const erroVisivel = erroDoMotor ?? (resultado?.erro && emPassos && (noUltimo || total === 0) ? resultado.erro : null);

  const noEditor = telaGrande || aba === "codigo";
  const onde = balao?.correcao && resultado ? ondeOlhar(resultado, balao.ponto, balao.correcao.feedback) : null;
  // Sem modelo, a camada 2 é o narrador: a frase longa do passo da pergunta (2.3).
  const passoDoPonto = balao && balao.ponto.alvo.comando !== null ? passos[balao.ponto.passo] : undefined;
  const narracaoDoPonto = passoDoPonto ? narracaoVisivel(passoDoPonto, estado.respondidos, estado.alcancado, "longa").trim() : "";
  const rascunhoAtual = balao && rascunho?.ponto === balao.ponto.id ? rascunho.rascunho : RASCUNHO_VAZIO;
  const desenharBalao = (embutido: boolean) =>
    balao && resultado ? (
      <BalaoPrevisao
        key={balao.ponto.id}
        ponto={balao.ponto}
        correcao={balao.correcao}
        inicial={balao.inicial}
        aviso={aviso?.ponto === balao.ponto.id ? aviso.texto : null}
        ocupado={corrigindo}
        rascunho={rascunhoAtual}
        aoMudarRascunho={(novo) => {
          setRascunho({ ponto: balao.ponto.id, rascunho: novo });
          // O aviso era sobre o texto antigo.
          setAviso(null);
        }}
        aoResponder={responder}
        aoPular={pular}
        aoContinuar={() => despachar({ tipo: "continuar" })}
        atencao={estado.atencao}
        embutido={embutido}
        detetive={
          balao.correcao && !balao.correcao.certa ? (
            <PainelDetetive
              ponto={balao.ponto}
              correcao={balao.correcao}
              camadas={estado.camadas}
              oferecerMeMostra={estado.errados >= 2}
              destacar={onde?.destacar ?? null}
              ondeAdiante={onde !== null && destinoPermitido(pontos, estado.respondidos, estado.passo, onde.passo) !== onde.passo}
              narracao={narracaoDoPonto}
              aoAbrir={abrirCamada}
            />
          ) : undefined
        }
      />
    ) : null;

  const controles = emPassos && total > 0 && (
    <Controles
      passo={estado.passo}
      total={total}
      fim={passo?.evento === "fim"}
      volta={volta}
      irPara={irPara}
      tocando={estado.tocando}
      aoTocar={tocar}
      alcance={alcance}
    />
  );
  const narrador = emPassos && <Narracao passo={passo} revelacao={revelacao} movimento={estado.movimento} />;
  const caixinhas = (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="mb-3 font-bold text-primaria">Variáveis</h2>
      {retornos.length > 0 && (
        <ul className="mb-3 flex flex-col items-start gap-1">
          {retornos.map((retorno) => (
            <li key={retorno.quadro} className="inline-flex flex-wrap items-center gap-1 rounded-lg bg-blue-50 px-2 py-1 text-sm">
              <span aria-hidden="true">↩</span>
              <span className="font-mono font-semibold">{retorno.funcao}</span> devolveu{" "}
              <span className="font-mono font-semibold">{texto(retorno.valor)}</span>
            </li>
          ))}
        </ul>
      )}
      {passo ? (
        <>
          <Variaveis
            variaveis={passo.globais}
            anteriores={estado.passo > 0 ? passos[estado.passo - 1].globais : undefined}
            ocultas={naFuncao ? undefined : ocultas}
            contorno={contorno}
            animada={animadaGlobal}
          />
          {passo.funcao && (
            <div className="mt-4 rounded-lg border border-dashed border-secundaria p-3">
              <h3 className="mb-2 text-sm font-semibold">Dentro da função {passo.funcao}</h3>
              <Variaveis variaveis={passo.locais} anteriores={anterioresLocais} ocultas={naFuncao ? ocultas : undefined} contorno={contorno} animada={animadaLocal} />
            </div>
          )}
        </>
      ) : (
        <p className="text-gray-600">
          {estado.fase === "palpite_inicial"
            ? "Primeiro, dê o seu palpite."
            : modo === "prever"
              ? "Clique em Executar. Antes de ver o resultado, você dá palpites."
              : "Clique em Executar para ver o programa rodando passo a passo."}
        </p>
      )}
    </div>
  );
  // No celular, com uma pergunta de valor, as caixinhas vêm antes do narrador: é nelas que o aluno
  // procura a resposta, e embaixo elas ficariam escondidas atrás da linha do tempo fixa.
  const caixinhasAntes = !telaGrande && balao !== null && !balao.inicial && balao.ponto.tipo === "valor";
  const ocupado = motor.estado === "ocupado" || preparando;
  const mostrarCodigo = telaGrande || aba === "codigo";
  const mostrarPassos = telaGrande || aba === "passos";

  return (
    <div className="mx-auto max-w-7xl p-4 max-lg:pb-48">
      {!telaGrande && (
        <div role="tablist" aria-label="Partes da tela" className="sticky top-0 z-30 -mx-4 -mt-4 mb-3 flex gap-2 border-b border-gray-200 bg-fundo px-4 py-2">
          {(["codigo", "passos"] as const).map((nome) => (
            <button
              key={nome}
              type="button"
              role="tab"
              id={`${ids}-aba-${nome}`}
              aria-selected={aba === nome}
              aria-controls={`${ids}-painel-${nome}`}
              onClick={() => setAba(nome)}
              className={`min-h-11 flex-1 rounded-lg border-2 px-3 font-semibold focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque ${
                aba === nome ? "border-primaria bg-primaria text-white" : "border-gray-300 bg-white text-primaria"
              }`}
            >
              {nome === "codigo" ? "Código" : "Passos"}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section
          id={`${ids}-painel-codigo`}
          aria-label="Código"
          role={telaGrande ? undefined : "tabpanel"}
          className={`${mostrarCodigo ? "flex" : "hidden"} min-w-0 flex-col gap-3`}
        >
          {barra}

          <Editor
            codigo={codigo}
            aoMudar={aoMudarCodigo ?? (() => {})}
            cena={cena}
            linhaDoBalao={cena.atual ? cena.atual[1] : ultimaLinha(codigo)}
            balao={emPassos && noEditor ? desenharBalao(false) : null}
            somenteLeitura={!aoMudarCodigo}
          />

          {(aoMudarEntradas || entradas) && (
            <details className="rounded-xl bg-white p-3 shadow-sm" open={entradasAbertas} onToggle={(e) => setEntradasAbertas(e.currentTarget.open)}>
              <summary className="min-h-11 cursor-pointer content-center font-semibold">Respostas para o input() (uma por linha)</summary>
              <p id={`${ids}-aviso-entradas`} className="mt-1 text-sm text-gray-700">
                ⚠ Não use seu nome de verdade.
              </p>
              <textarea
                ref={campoDeEntradas}
                value={entradas}
                onChange={(e) => aoMudarEntradas?.(e.target.value)}
                readOnly={!aoMudarEntradas}
                rows={3}
                className="mt-2 w-full rounded-lg border border-gray-300 p-2 font-mono"
                aria-label="Respostas para o input()"
                aria-describedby={`${ids}-aviso-entradas`}
              />
            </details>
          )}

          {estado.fase === "palpite_inicial" && resultado ? (
            // Na tela grande, o palpite antes de rodar fica ao lado do código (na outra coluna).
            !telaGrande && desenharBalao(true)
          ) : (
            <button
              onClick={executar}
              disabled={motor.estado !== "pronto" || preparando}
              className="min-h-11 rounded-xl bg-green-700 px-4 py-3 text-lg font-bold text-white shadow transition hover:bg-green-800 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50"
            >
              {ocupado ? "Executando..." : "▶ Executar"}
            </button>
          )}
        </section>

        <section
          id={`${ids}-painel-passos`}
          aria-label="Execução"
          role={telaGrande ? undefined : "tabpanel"}
          className={`${mostrarPassos ? "flex" : "hidden"} min-w-0 flex-col gap-4`}
        >
          {/* Na tela grande, a linha do tempo e o narrador ficam no alto desta coluna: à vista sem rolar,
              e o balão preso ao código (na outra coluna) não cobre os botões. */}
          {telaGrande && estado.fase === "palpite_inicial" && resultado && desenharBalao(true)}
          {telaGrande && controles}
          {!telaGrande && emPassos && <TrechoAtual codigo={codigo} cena={cena} />}
          {!telaGrande && emPassos && !noEditor && desenharBalao(true)}
          {caixinhasAntes && caixinhas}
          {narrador}
          {erroVisivel && <CaixaErro erro={erroVisivel} />}
          {!caixinhasAntes && caixinhas}

          <div className="rounded-xl bg-gray-900 p-4 shadow-sm">
            <h2 className="mb-2 text-xs uppercase tracking-wider text-gray-300">Saída</h2>
            <pre className="min-h-16 whitespace-pre-wrap break-words font-mono text-green-300">
              {saida}
              {saidaPendente && (
                <span className="inline-block rounded border-2 border-dashed border-green-300 px-2">
                  <span aria-hidden="true">?</span>
                  <span className="sr-only">o que aparece aqui é o seu palpite</span>
                </span>
              )}
            </pre>
          </div>
        </section>
      </div>

      {!telaGrande && controles && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-200 bg-fundo/95 p-2 shadow-[0_-2px_8px_rgb(0_0_0/0.08)]">{controles}</div>
      )}
    </div>
  );
}
