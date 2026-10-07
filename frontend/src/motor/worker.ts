// Roda o Python (Pyodide) fora da página principal, para que um programa
// lento ou travado do aluno não congele a tela.
//
// Recebe {id, acao, dados} e responde com o texto JSON que o motor escreve
// ({id, ok, resultado} ou {id, ok: false, erro}); a ponte lê esse texto.
import type { loadPyodide as LoadPyodide } from "pyodide";
import { ACOES as LISTA_DE_ACOES } from "./protocolo";

// Todos os arquivos do motor, como texto: um módulo novo em pyvis_motor/ entra sozinho.
const MOTOR = import.meta.glob("../../../pyvis_motor/*.py", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

const ACOES: ReadonlySet<string> = new Set(LISTA_DE_ACOES);

const pastaPyodide = new URL(`${import.meta.env.BASE_URL}pyodide/`, self.location.origin).href;

const pronto = (async () => {
  const { loadPyodide } = (await import(/* @vite-ignore */ `${pastaPyodide}pyodide.mjs`)) as {
    loadPyodide: typeof LoadPyodide;
  };
  // Semente de hash fixa: conjuntos e textos ficam na mesma ordem (e com o mesmo `h`) a cada carga.
  const pyodide = await loadPyodide({ indexURL: pastaPyodide, env: { PYTHONHASHSEED: "0" } });
  pyodide.FS.mkdirTree("/home/pyodide/pyvis_motor");
  for (const [caminho, texto] of Object.entries(MOTOR)) {
    const nome = caminho.slice(caminho.lastIndexOf("/") + 1);
    pyodide.FS.writeFile(`/home/pyodide/pyvis_motor/${nome}`, texto);
  }
  // gc.freeze: o que existe depois de carregar o motor fica fora das coletas. Assim a coleta
  // inteira no fim de cada execução (que solta os objetos do aluno ainda isolados) custa pouco.
  pyodide.runPython(`
import gc, sys
sys.path.insert(0, "/home/pyodide")
import pyvis_motor.api
gc.freeze()
`);
  return pyodide.runPython("pyvis_motor.api.executar_json") as (pedido: string) => string;
})();

pronto.then(
  () => postMessage({ tipo: "pronto" }),
  (falha) => postMessage({ tipo: "falha", mensagem: String(falha) }),
);

function pedidoValido(dados: unknown): dados is { id: number; acao: string; dados?: unknown } {
  if (typeof dados !== "object" || dados === null) return false;
  const pedido = dados as Record<string, unknown>;
  return Number.isInteger(pedido.id) && typeof pedido.acao === "string" && ACOES.has(pedido.acao);
}

onmessage = async ({ data }: MessageEvent<unknown>) => {
  const executarJson = await pronto;
  if (!pedidoValido(data)) {
    const id = typeof data === "object" && data !== null && Number.isInteger((data as { id?: unknown }).id) ? (data as { id: number }).id : null;
    postMessage(JSON.stringify({ id, ok: false, erro: "pedido inválido" }));
    return;
  }
  let resposta: string;
  try {
    resposta = executarJson(JSON.stringify({ id: data.id, acao: data.acao, dados: data.dados ?? {} }));
  } catch (falha) {
    // O motor já devolve os próprios erros; chegar aqui é defeito do Pyodide.
    resposta = JSON.stringify({ id: data.id, ok: false, erro: `falha do Python: ${String(falha).slice(0, 200)}` });
  }
  postMessage(resposta);
};
