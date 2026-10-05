// Roda o Python (Pyodide) fora da página principal, para que um programa
// lento ou travado do aluno não congele a tela.
import type { loadPyodide as LoadPyodide } from "pyodide";
import init from "../../../pyvis_motor/__init__.py?raw";
import valores from "../../../pyvis_motor/valores.py?raw";
import erros from "../../../pyvis_motor/erros.py?raw";
import rastreador from "../../../pyvis_motor/rastreador.py?raw";

const MOTOR: Record<string, string> = {
  "__init__.py": init,
  "valores.py": valores,
  "erros.py": erros,
  "rastreador.py": rastreador,
};

const pastaPyodide = new URL(`${import.meta.env.BASE_URL}pyodide/`, self.location.origin).href;

const pronto = (async () => {
  const { loadPyodide } = (await import(/* @vite-ignore */ `${pastaPyodide}pyodide.mjs`)) as {
    loadPyodide: typeof LoadPyodide;
  };
  const pyodide = await loadPyodide({ indexURL: pastaPyodide });
  pyodide.FS.mkdirTree("/home/pyodide/pyvis_motor");
  for (const [nome, texto] of Object.entries(MOTOR)) {
    pyodide.FS.writeFile(`/home/pyodide/pyvis_motor/${nome}`, texto);
  }
  pyodide.runPython(`
import sys, json
sys.path.insert(0, "/home/pyodide")
import pyvis_motor
`);
  return pyodide;
})();

pronto.then(
  () => postMessage({ tipo: "pronto" }),
  (falha) => postMessage({ tipo: "falha", mensagem: String(falha) }),
);

onmessage = async ({ data }: MessageEvent<{ codigo: string; entradas: string[] }>) => {
  const pyodide = await pronto;
  pyodide.globals.set("codigo", data.codigo);
  pyodide.globals.set("entradas", pyodide.toPy(data.entradas));
  const json = pyodide.runPython("json.dumps(pyvis_motor.rastrear(codigo, entradas))") as string;
  postMessage({ tipo: "resultado", resultado: JSON.parse(json) });
};
