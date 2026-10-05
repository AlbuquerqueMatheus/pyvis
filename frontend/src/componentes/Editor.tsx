import { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { RangeSetBuilder } from "@codemirror/state";
import { Decoration, EditorView } from "@codemirror/view";

type Props = {
  codigo: string;
  aoMudar: (codigo: string) => void;
  linhaAtual: number | null;
  linhaComErro: number | null;
};

const linhaAtualDeco = Decoration.line({ class: "cm-linha-atual" });
const linhaErroDeco = Decoration.line({ class: "cm-linha-erro" });

function destacarLinhas(linhaAtual: number | null, linhaComErro: number | null) {
  return EditorView.decorations.of((view) => {
    const builder = new RangeSetBuilder<Decoration>();
    const total = view.state.doc.lines;
    const linha = linhaComErro ?? linhaAtual;
    if (linha && linha >= 1 && linha <= total) {
      builder.add(view.state.doc.line(linha).from, view.state.doc.line(linha).from, linhaComErro ? linhaErroDeco : linhaAtualDeco);
    }
    return builder.finish();
  });
}

export function Editor({ codigo, aoMudar, linhaAtual, linhaComErro }: Props) {
  const extensoes = useMemo(
    () => [python(), destacarLinhas(linhaAtual, linhaComErro), EditorView.lineWrapping],
    [linhaAtual, linhaComErro],
  );

  return (
    <div className="overflow-hidden rounded-xl border border-gray-300 bg-white text-base">
      <CodeMirror
        value={codigo}
        onChange={aoMudar}
        extensions={extensoes}
        height="320px"
        basicSetup={{ highlightActiveLine: false, highlightActiveLineGutter: false, foldGutter: false }}
        aria-label="Seu código Python"
      />
    </div>
  );
}
