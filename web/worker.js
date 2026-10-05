// Roda o Python (Pyodide) fora da página principal, para que um programa
// lento ou travado do aluno não congele a tela.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

const ARQUIVOS_DO_MOTOR = ["__init__.py", "valores.py", "erros.py", "rastreador.py"];
const PASTA = "/home/pyodide/pyvis_motor";

const pronto = (async () => {
  const pyodide = await loadPyodide();
  pyodide.FS.mkdirTree(PASTA);
  for (const nome of ARQUIVOS_DO_MOTOR) {
    const resposta = await fetch(new URL(`../pyvis_motor/${nome}`, import.meta.url));
    pyodide.FS.writeFile(`${PASTA}/${nome}`, await resposta.text());
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

onmessage = async ({ data }) => {
  const pyodide = await pronto;
  pyodide.globals.set("codigo", data.codigo);
  pyodide.globals.set("entradas", pyodide.toPy(data.entradas));
  const json = pyodide.runPython("json.dumps(pyvis_motor.rastrear(codigo, entradas))");
  postMessage({ tipo: "resultado", resultado: JSON.parse(json) });
};
