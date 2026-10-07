"""Esconde do código do aluno os módulos que falam com o navegador.

No Pyodide, `import js` dá acesso à página e à rede. Enquanto o programa do
aluno roda, esses módulos (e o próprio motor) somem de sys.modules e um
buscador no começo de sys.meta_path recusa o import com uma mensagem amigável.
Ao terminar, tudo volta como estava, porque o próprio Pyodide e o motor
precisam deles. O que o aluno trocou no interpretador (sys.meta_path, o limite
de recursão, sys.stdout) também volta.

Isto não é a proteção principal: dentro do mesmo interpretador, a
introspecção (gc.get_objects(), sys._getframe()) ainda alcança o que está
escondido. A proteção de verdade é rodar o executor numa origem separada, sem
dados e sem rede (spec 1.1), que fica para a publicação do site.
"""

import contextlib
import importlib.abc
import sys

# _pyodide_core traz create_proxy, to_js e run_sync; pyvis_motor é o próprio motor
# (o aluno não pode trocar as funções que corrigem os palpites dele).
BLOQUEADOS = frozenset(
    {"js", "pyodide", "pyodide_js", "_pyodide", "_pyodide_core", "micropip", "pyodide_http", "pyvis_motor"}
)
MENSAGEM = "Esse módulo não está disponível no PyVis."


def bloqueado(nome):
    return nome.partition(".")[0] in BLOQUEADOS


class _Buscador(importlib.abc.MetaPathFinder):
    def find_spec(self, nome, caminho=None, alvo=None):
        if bloqueado(nome):
            # Um ModuleNotFoundError comum: para o aluno, o módulo simplesmente não existe aqui.
            raise ModuleNotFoundError(MENSAGEM, name=nome)
        return None


@contextlib.contextmanager
def isolar():
    """Liga o bloqueio só durante o exec do aluno."""
    escondidos = {nome: modulo for nome, modulo in sys.modules.items() if bloqueado(nome)}
    buscadores = list(sys.meta_path)
    recursao = sys.getrecursionlimit()
    saidas = (sys.stdout, sys.stderr, sys.stdin)
    digitos = sys.get_int_max_str_digits() if hasattr(sys, "get_int_max_str_digits") else None
    for nome in escondidos:
        del sys.modules[nome]
    sys.meta_path.insert(0, _Buscador())
    try:
        yield
    finally:
        # O aluno pode ter mexido em sys.meta_path ou sys.modules: volta tudo ao normal.
        sys.meta_path[:] = buscadores
        for nome in [nome for nome in sys.modules if bloqueado(nome)]:
            del sys.modules[nome]
        sys.modules.update(escondidos)
        sys.setrecursionlimit(recursao)
        sys.stdout, sys.stderr, sys.stdin = saidas
        if digitos is not None:
            sys.set_int_max_str_digits(digitos)
