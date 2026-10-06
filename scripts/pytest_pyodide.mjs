// Roda os testes do motor (tests/test_*.py) dentro do Pyodide, no Node,
// para conferir o motor no mesmo Python que roda no navegador.
// O pytest não vem no Pyodide (instalar exigiria rede), então um mini-pytest
// importa cada arquivo de teste e chama as funções test_*, com
// pytest.mark.parametrize, pytest.mark.skipif e pytest.raises.
// Uso: depois de `npm ci` em frontend/, `node scripts/pytest_pyodide.mjs`.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const { loadPyodide } = await import(join(raiz, "frontend/node_modules/pyodide/pyodide.mjs"));
const pyodide = await loadPyodide();
pyodide.FS.mkdirTree("/repo");
pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: raiz }, "/repo");
pyodide.setStdout({ batched: (linha) => console.log(linha) });
pyodide.setStderr({ batched: (linha) => console.error(linha) });

const MINI_PYTEST = String.raw`
import contextlib, gc, importlib, inspect, itertools, os, re, sys, traceback, types

sys.dont_write_bytecode = True
os.chdir("/repo")
sys.path[:0] = ["/repo", "/repo/tests"]


class Pulado(Exception):
    pass


class Marca:
    def parametrize(self, nomes, valores, ids=None):
        if isinstance(nomes, str):
            nomes = [nome.strip() for nome in nomes.split(",") if nome.strip()]
        valores = [v if len(nomes) > 1 else (v,) for v in valores]

        def decorar(funcao):
            funcao.__dict__.setdefault("parametros", []).insert(0, (list(nomes), valores))
            return funcao

        return decorar

    def skipif(self, condicao, reason=""):
        def decorar(funcao):
            if condicao:
                funcao.pular = reason or "skipif"
            return funcao

        return decorar


class InfoDoErro:
    value = None


@contextlib.contextmanager
def raises(tipo, match=None):
    info = InfoDoErro()
    try:
        yield info
    except tipo as erro:
        info.value = erro
        if match is not None and not re.search(match, str(erro)):
            raise AssertionError(f"{erro!r} não casa com {match!r}") from erro
    else:
        raise AssertionError(f"não levantou {getattr(tipo, '__name__', tipo)}")


def skip(reason=""):
    raise Pulado(reason)


pytest = types.ModuleType("pytest")
pytest.mark = Marca()
pytest.raises = raises
pytest.skip = skip
sys.modules["pytest"] = pytest


def casos(funcao):
    grupos = getattr(funcao, "parametros", [])
    if not grupos:
        yield "", {}
        return
    for combinacao in itertools.product(*[[(nomes, v) for v in valores] for nomes, valores in grupos]):
        argumentos = {}
        for nomes, valor in combinacao:
            argumentos.update(zip(nomes, valor))
        yield "[" + "-".join(repr(v)[:30] for v in argumentos.values()) + "]", argumentos


passaram = falharam = pulados = 0
for arquivo in sorted(os.listdir("tests")):
    if not (arquivo.startswith("test_") and arquivo.endswith(".py")):
        continue
    modulo = importlib.import_module(arquivo[:-3])
    gc.freeze()  # como no worker: o que já foi carregado fica fora da coleta do fim de cada execução
    for nome, funcao in list(vars(modulo).items()):
        if not (nome.startswith("test") and inspect.isfunction(funcao) and funcao.__module__ == modulo.__name__):
            continue
        for sufixo, argumentos in casos(funcao):
            rotulo = f"tests/{arquivo}::{nome}{sufixo}"
            faltando = [p for p in inspect.signature(funcao).parameters if p not in argumentos]
            if getattr(funcao, "pular", None) or faltando:
                pulados += 1
                motivo = funcao.pular if getattr(funcao, "pular", None) else f"fixture sem suporte: {faltando}"
                print(f"PULADO {rotulo} ({motivo})")
                continue
            try:
                funcao(**argumentos)
            except Pulado as motivo:
                pulados += 1
                print(f"PULADO {rotulo} ({motivo})")
            except BaseException:
                falharam += 1
                print(f"FALHOU {rotulo}")
                traceback.print_exc()
            else:
                passaram += 1

print(f"Pyodide {sys.version.split()[0]}: {passaram} passaram, {falharam} falharam, {pulados} pulados")
falharam + (passaram == 0)
`;

const falhas = pyodide.runPython(MINI_PYTEST);
process.exit(falhas ? 1 : 0);
