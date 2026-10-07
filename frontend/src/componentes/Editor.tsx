import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import CodeMirror, { ExternalChange } from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { RangeSet, RangeSetBuilder, StateEffect, StateField, type Text } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  GutterMarker,
  WidgetType,
  gutter,
  showTooltip,
  tooltips,
  type DecorationSet,
  type Tooltip,
  type TooltipView,
} from "@codemirror/view";
import type { Balao, CenaDoEditor } from "../motor/cena";

type Props = {
  codigo: string;
  aoMudar: (codigo: string) => void;
  cena: CenaDoEditor;
  /** A linha em que o balão de palpite fica preso (logo abaixo dela), ou null. */
  linhaDoBalao?: number | null;
  /** O conteúdo do balão de palpite (React), desenhado junto da linha. */
  balao?: ReactNode;
  /** Numa atividade, o programa é do professor: dá para ler e rolar, não para mudar. */
  somenteLeitura?: boolean;
};

// O passo a passo chega ao editor por este efeito; as decorações ficam num
// StateField e só são refeitas quando a cena muda, não a cada renderização.
export const irPara = StateEffect.define<CenaDoEditor>();

const linhaAtual = Decoration.line({ class: "cm-linha-atual" });
const linhaErro = Decoration.line({ class: "cm-linha-erro" });
const linhaPulada = Decoration.line({ class: "cm-linha-pulada" });
const naoCalculado = Decoration.mark({ class: "cm-nao-calculado", attributes: { title: "nem foi calculado" } });

// O balão de palpite é um tooltip do CodeMirror preso ao começo da linha: ele
// acompanha a rolagem e troca de lado quando falta espaço. O conteúdo é React,
// desenhado (por portal) num elemento fixo de cada editor; o tooltip só diz onde
// ele fica. Com o mesmo `criar`, o CodeMirror reaproveita o elemento quando a
// linha muda, e o foco e o que o aluno digitou continuam lá.
const ancorar = StateEffect.define<{ pos: number; criar: () => TooltipView } | null>();

const campoDoBalao = StateField.define<Tooltip | null>({
  create: () => null,
  update(tooltip, tr) {
    let atual = tooltip && tr.docChanged ? { ...tooltip, pos: tr.changes.mapPos(tooltip.pos) } : tooltip;
    for (const efeito of tr.effects) {
      if (efeito.is(ancorar)) atual = efeito.value ? { pos: efeito.value.pos, above: false, arrow: true, create: efeito.value.criar } : null;
    }
    return atual;
  },
  provide: (campo) => showTooltip.from(campo),
});

class BalaoWidget extends WidgetType {
  constructor(readonly balao: Balao) {
    super();
  }
  eq(outro: BalaoWidget) {
    return JSON.stringify(outro.balao) === JSON.stringify(this.balao);
  }
  toDOM() {
    // O mesmo conteúdo vai para o narrador; aqui é só para os olhos.
    const balao = document.createElement("span");
    balao.className = "cm-balao";
    balao.setAttribute("aria-hidden", "true");
    balao.dataset.balao = "decisao";
    for (const trecho of this.balao.trechos) {
      const parte = document.createElement("span");
      parte.textContent = trecho.texto;
      if (trecho.naoCalculado) {
        parte.className = "cm-balao-nao-calculado";
        parte.title = "nem foi calculado";
      }
      balao.appendChild(parte);
    }
    if (this.balao.valor !== null) {
      const valor = document.createElement("strong");
      valor.className = this.balao.valor ? "cm-balao-verdadeiro" : "cm-balao-falso";
      // Sem ✓ e ✗: aqui eles pareceriam certo e errado, e Falso não é erro.
      valor.textContent = `${this.balao.trechos.length > 0 ? " → " : ""}${this.balao.valor ? "Verdadeiro" : "Falso"}`;
      balao.appendChild(valor);
    }
    return balao;
  }
}

class RotuloPulado extends WidgetType {
  eq() {
    return true;
  }
  toDOM() {
    const rotulo = document.createElement("span");
    rotulo.className = "cm-rotulo-pulado";
    rotulo.setAttribute("aria-hidden", "true");
    rotulo.textContent = "↷ pulado";
    return rotulo;
  }
}

class MarcaPulado extends GutterMarker {
  eq() {
    return true;
  }
  toDOM() {
    const marca = document.createElement("span");
    marca.textContent = "↷";
    marca.setAttribute("aria-hidden", "true");
    return marca;
  }
}

const marcaPulado = new MarcaPulado();
const rotuloPulado = Decoration.widget({ widget: new RotuloPulado(), side: 1 });

type Desenho = { decoracoes: DecorationSet; margem: RangeSet<GutterMarker> };

function dentro(doc: Text, linha: number) {
  return Number.isInteger(linha) && linha >= 1 && linha <= doc.lines;
}

/** Converte uma coluna em bytes UTF-8 (como o Python conta) para a posição no texto da linha. */
export function colunaDeBytes(texto: string, bytes: number): number {
  const codificador = new TextEncoder();
  let contados = 0;
  let posicao = 0;
  for (const letra of texto) {
    if (contados >= bytes) break;
    contados += codificador.encode(letra).length;
    posicao += letra.length;
  }
  return posicao;
}

export function desenhar(doc: Text, cena: CenaDoEditor): Desenho {
  const linhas = new Map<number, Decoration>();
  const pontos: { de: number; ate: number; deco: Decoration }[] = [];
  const margem = new RangeSetBuilder<GutterMarker>();

  const puladas = new Set<number>();
  for (const [ini, fim] of cena.pulados) {
    for (let n = ini; n <= fim; n++) if (dentro(doc, n)) puladas.add(n);
  }
  for (const n of puladas) linhas.set(n, linhaPulada);
  if (cena.atual) {
    for (let n = cena.atual[0]; n <= cena.atual[1]; n++) if (dentro(doc, n)) linhas.set(n, linhaAtual);
  }
  if (cena.erro !== null && dentro(doc, cena.erro)) linhas.set(cena.erro, linhaErro);

  // O rótulo 'pulado' vai só na primeira linha de cada faixa esmaecida.
  for (const [ini] of cena.pulados) {
    if (dentro(doc, ini) && linhas.get(ini) === linhaPulada) {
      const fim = doc.line(ini).to;
      pontos.push({ de: fim, ate: fim, deco: rotuloPulado });
    }
  }
  if (cena.balao && dentro(doc, cena.balao.linha)) {
    const fim = doc.line(cena.balao.linha).to;
    pontos.push({ de: fim, ate: fim, deco: Decoration.widget({ widget: new BalaoWidget(cena.balao), side: 2 }) });
  }
  for (const [linha, coluna, linhaFim, colunaFim] of cena.naoCalculado) {
    if (!dentro(doc, linha) || !dentro(doc, linhaFim)) continue;
    const inicio = doc.line(linha);
    const final = doc.line(linhaFim);
    const de = inicio.from + colunaDeBytes(inicio.text, coluna);
    const ate = final.from + colunaDeBytes(final.text, colunaFim);
    if (ate > de) pontos.push({ de, ate, deco: naoCalculado });
  }

  const todas = [
    ...[...linhas].map(([n, deco]) => deco.range(doc.line(n).from)),
    ...pontos.map(({ de, ate, deco }) => (de === ate ? deco.range(de) : deco.range(de, ate))),
  ];
  for (const n of [...puladas].sort((a, b) => a - b)) {
    if (linhas.get(n) === linhaPulada) margem.add(doc.line(n).from, doc.line(n).from, marcaPulado);
  }
  return { decoracoes: Decoration.set(todas, true), margem: margem.finish() };
}

const campoDoPasso = StateField.define<Desenho>({
  create: () => ({ decoracoes: Decoration.none, margem: RangeSet.empty }),
  update(desenho, tr) {
    let atual = tr.docChanged
      ? { decoracoes: desenho.decoracoes.map(tr.changes), margem: desenho.margem.map(tr.changes) }
      : desenho;
    for (const efeito of tr.effects) if (efeito.is(irPara)) atual = desenhar(tr.state.doc, efeito.value);
    return atual;
  },
  provide: (campo) => EditorView.decorations.from(campo, (desenho) => desenho.decoracoes),
});

const margemDoPasso = gutter({
  class: "cm-margem-pulado",
  markers: (view) => view.state.field(campoDoPasso).margem,
  initialSpacer: () => marcaPulado, // a margem já nasce com a largura do ícone: nada pula de lugar
});

// Fixas: o @uiw/react-codemirror reconfigura o editor sempre que estas mudam.
// Os tooltips ficam dentro do editor, em posição absoluta: rolam junto com a página.
const EXTENSOES = [
  python(),
  EditorView.lineWrapping,
  EditorView.contentAttributes.of({ "aria-label": "Seu código Python" }),
  campoDoPasso,
  margemDoPasso,
  campoDoBalao,
  tooltips({ position: "absolute" }),
];
const BASICO = { highlightActiveLine: false, highlightActiveLineGutter: false, foldGutter: false };

/** Rola só a caixa do editor (nunca a página) até as linhas [linha, fim] aparecerem. */
function mostrarLinhas(view: EditorView, linha: number, fim: number) {
  const de = view.state.doc.line(linha).from;
  const ate = view.state.doc.line(fim).from;
  view.requestMeasure({
    read: () => {
      const topo = view.lineBlockAt(de).top + view.documentPadding.top;
      const ultimo = view.lineBlockAt(ate);
      const base = ultimo.top + ultimo.height + view.documentPadding.top;
      return { topo, base, rolagem: view.scrollDOM.scrollTop, altura: view.scrollDOM.clientHeight };
    },
    write: ({ topo, base, rolagem, altura }) => {
      if (altura <= 0) return; // escondido (a aba do código no celular)
      const margem = 8;
      if (topo - margem < rolagem) view.scrollDOM.scrollTop = Math.max(0, topo - margem);
      else if (base + margem > rolagem + altura) view.scrollDOM.scrollTop = Math.min(topo - margem, base + margem - altura);
    },
  });
}

export function Editor({ codigo, aoMudar, cena, linhaDoBalao = null, balao, somenteLeitura = false }: Props) {
  const viewRef = useRef<EditorView | null>(null);
  const cenaRef = useRef(cena);
  const aoMudarRef = useRef(aoMudar);
  aoMudarRef.current = aoMudar;
  cenaRef.current = cena;

  // O elemento do balão de palpite: o mesmo durante toda a vida do editor.
  const recipiente = useMemo(() => {
    const div = document.createElement("div");
    div.className = "cm-balao-previsao";
    return div;
  }, []);
  const criarBalao = useCallback((): TooltipView => ({ dom: recipiente, offset: { x: 0, y: 2 }, resize: false }), [recipiente]);
  const ancora = balao ? linhaDoBalao : null;
  const ancoraRef = useRef(ancora);
  ancoraRef.current = ancora;

  const prender = useCallback(
    (view: EditorView, linha: number | null) => {
      const valida = linha !== null && dentro(view.state.doc, linha) ? linha : null;
      const atual = view.state.field(campoDoBalao);
      const pos = valida === null ? null : view.state.doc.line(valida).from;
      if ((atual === null && pos === null) || (atual !== null && atual.pos === pos)) return;
      view.dispatch({ effects: ancorar.of(pos === null ? null : { pos, criar: criarBalao }) });
    },
    [criarBalao],
  );

  const mudou = useCallback((novo: string) => aoMudarRef.current(novo), []);
  const criado = useCallback(
    (view: EditorView) => {
      viewRef.current = view;
      view.dispatch({ effects: irPara.of(cenaRef.current) });
      prender(view, ancoraRef.current);
    },
    [prender],
  );

  // Antes dos efeitos dos filhos: o balão já está na página quando ele pega o foco.
  useLayoutEffect(() => {
    if (viewRef.current) prender(viewRef.current, ancora);
  }, [ancora, codigo, prender]);

  // Código que vem de fora (um exemplo escolhido) entra já. O @uiw/react-codemirror
  // espera uma pausa na digitação para isso, e o passo a passo cairia no texto antigo.
  useEffect(() => {
    const view = viewRef.current;
    if (!view || view.state.doc.toString() === codigo) return;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: codigo },
      annotations: ExternalChange.of(true),
      effects: irPara.of(cenaRef.current),
    });
  }, [codigo]);

  useEffect(() => {
    viewRef.current?.dispatch({ effects: irPara.of(cena) });
  }, [cena]);

  // A linha atual (e o balão logo abaixo dela) fica sempre à vista dentro do editor.
  const linhaAtual = cena.atual?.[0] ?? null;
  const fimAtual = cena.atual?.[1] ?? null;
  useEffect(() => {
    const view = viewRef.current;
    if (!view || linhaAtual === null || fimAtual === null || !dentro(view.state.doc, linhaAtual) || !dentro(view.state.doc, fimAtual)) return;
    mostrarLinhas(view, linhaAtual, fimAtual);
  }, [linhaAtual, fimAtual]);

  return (
    <div className="editor-pyvis rounded-xl border border-gray-300 bg-white text-base">
      <CodeMirror
        value={codigo}
        onChange={mudou}
        onCreateEditor={criado}
        extensions={EXTENSOES}
        // Do tamanho do código (até 320 px): num programa curto, o balão do palpite e o
        // código cabem juntos na tela, e ninguém escolhe sem ver o programa.
        minHeight="7.5rem"
        maxHeight="320px"
        basicSetup={BASICO}
        // Tab sai do editor (senão o teclado fica preso nele e o Tab estraga o código com espaços).
        // Para recuar, o Enter depois de ':' já põe os espaços, e Ctrl+] / Ctrl+[ mudam o recuo.
        indentWithTab={false}
        readOnly={somenteLeitura}
      />
      {balao ? createPortal(balao, recipiente) : null}
    </div>
  );
}
