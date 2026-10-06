import importlib
import sys
import types

import pytest

from pyvis_motor import rastrear
from pyvis_motor.seguranca import isolar

NO_PYODIDE = sys.platform == "emscripten"
MENSAGEM = "Esse módulo não está disponível no PyVis."


@pytest.mark.parametrize(
    "codigo",
    [
        "import js",
        "import pyodide",
        "import pyodide.ffi",
        "from js import document",
        "from pyodide.http import pyfetch",
        "import pyodide_js",
        "import _pyodide",
        "import micropip",
        "import pyodide_http",
        "import importlib\nimportlib.import_module('js')",
        "__import__('pyodide')",
    ],
)
def test_modulos_do_navegador_sao_recusados(codigo):
    resultado = rastrear(codigo + "\n")
    erro = resultado["erro"]
    assert erro["tipo"] == "ModuleNotFoundError"
    assert erro["mensagem"] == MENSAGEM
    assert erro["linha"] == codigo.count("\n") + 1


def test_aluno_pode_tratar_o_import_recusado():
    resultado = rastrear("try:\n    import js\nexcept ImportError:\n    print('sem js')\n")
    assert resultado["erro"] is None
    assert resultado["saida"] == "sem js\n"


def test_motor_continua_funcionando_depois():
    rastrear("import js\n")
    resultado = rastrear("import math\nx = math.sqrt(16)\nprint(x)\n")
    assert resultado["erro"] is None
    assert resultado["saida"] == "4.0\n"
    assert sys.gettrace() is None
    assert not any(type(b).__name__ == "_Buscador" for b in sys.meta_path)


def test_modulos_ja_carregados_somem_durante_o_exec_e_voltam_depois():
    falso = types.ModuleType("pyodide")
    original = sys.modules.get("pyodide")
    sys.modules["pyodide"] = falso
    try:
        resultado = rastrear("import sys\nprint('pyodide' in sys.modules)\nimport pyodide\n")
        assert resultado["saida"] == "False\n"
        assert resultado["erro"]["mensagem"] == MENSAGEM
        assert sys.modules["pyodide"] is falso
    finally:
        if original is None:
            del sys.modules["pyodide"]
        else:
            sys.modules["pyodide"] = original


def test_aluno_mexer_no_meta_path_nao_estraga_o_motor():
    antes = list(sys.meta_path)
    resultado = rastrear("import sys\nsys.meta_path.clear()\nsys.modules['js'] = 1\n")
    assert resultado["erro"] is None
    assert sys.meta_path == antes
    assert sys.modules.get("js") != 1
    importlib.import_module("json")


def test_isolar_restaura_mesmo_com_erro():
    antes = list(sys.meta_path)
    with pytest.raises(ZeroDivisionError):
        with isolar():
            1 / 0
    assert sys.meta_path == antes


def test_modulo_inexistente_tem_mensagem_amigavel():
    erro = rastrear("import numpyy\n")["erro"]
    assert erro["tipo"] == "ModuleNotFoundError"
    assert erro["mensagem"] == MENSAGEM


def test_modulos_comuns_continuam_liberados():
    resultado = rastrear("import math, random, time\nfrom collections import Counter\nprint(Counter('aab')['a'])\n")
    assert resultado["erro"] is None
    assert resultado["saida"] == "2\n"


@pytest.mark.skipif(not NO_PYODIDE, reason="só no Pyodide existe o módulo js de verdade")
def test_no_pyodide_o_js_volta_para_o_motor():
    pyodide_antes = sys.modules["pyodide"]
    resultado = rastrear("import pyodide\n")
    assert resultado["erro"]["mensagem"] == MENSAGEM
    assert sys.modules["pyodide"] is pyodide_antes
    js = importlib.import_module("js")  # o motor (e o próprio Pyodide) continuam podendo usar
    assert hasattr(js, "Object")


@pytest.mark.parametrize("codigo", ["import _pyodide_core", "import pyvis_motor", "from pyvis_motor import previsao"])
def test_nucleo_do_pyodide_e_o_motor_tambem_sao_recusados(codigo):
    assert rastrear(codigo + "\n")["erro"]["mensagem"] == MENSAGEM


def test_perfil_e_rastreador_do_aluno_nao_sobrevivem_ao_exec():
    codigo = "import sys\nchamadas = []\nsys.setprofile(lambda *a: chamadas.append(a))\nx = 1\n"
    resultado = rastrear(codigo)
    assert resultado["erro"] is None
    assert sys.getprofile() is None and sys.gettrace() is None
    codigo = "import sys\nsys.settrace(lambda *a: None)\nx = 1\n"
    rastrear(codigo)
    assert sys.gettrace() is None


def test_aluno_mexer_no_interpretador_nao_estraga_o_motor():
    limite = sys.getrecursionlimit()
    saida = sys.stdout
    rastrear("import sys, io\nsys.setrecursionlimit(60)\nsys.stdout = io.StringIO()\n")
    assert sys.getrecursionlimit() == limite
    assert sys.stdout is saida


def test_finalizador_do_aluno_roda_ainda_isolado():
    # Um __del__ que roda depois do exec estaria fora do bloqueio.
    codigo = (
        "class X:\n    def __del__(self):\n        try:\n            import js\n            print('escapou')\n"
        "        except ImportError:\n            print('bloqueado')\nx = X()\n"
    )
    resultado = rastrear(codigo)
    assert resultado["erro"] is None
    assert resultado["saida"] == "bloqueado\n"  # rodou, e ainda dentro do isolamento
    # Também com um ciclo, que só o coletor de lixo solta.
    ciclo = codigo.replace("x = X()\n", "x = X()\nx.eu = x\n")
    assert rastrear(ciclo)["saida"] == "bloqueado\n"
    # Um ciclo que já sobreviveu a uma coleta está na geração velha: a coleta do fim precisa ser inteira.
    velho = ciclo + "import gc\ngc.collect()\n"
    assert rastrear(velho)["saida"] == "bloqueado\n"


def test_time_sleep_nao_espera():
    import time

    comeco = time.perf_counter()
    resultado = rastrear("import time\nfor i in range(3, 0, -1):\n    print(i)\n    time.sleep(1)\nprint('Já!')\n")
    assert time.perf_counter() - comeco < 1
    assert resultado["erro"] is None and resultado["saida"] == "3\n2\n1\nJá!\n"
    assert rastrear("from time import sleep\nsleep(-1)\n")["erro"]["tipo"] == "ValueError"
    assert time.sleep.__module__ == "time"  # o original voltou
