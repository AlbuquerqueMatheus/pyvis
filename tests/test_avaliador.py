import ast
import builtins
import io
import time
from collections import defaultdict

import pytest

from pyvis_motor import avaliar, rastrear


def condicao(texto, **variaveis):
    escopo = {"__builtins__": builtins, **variaveis}
    return avaliar(ast.parse(texto, mode="eval").body, escopo, escopo)


def marcado(resultado):
    return [resultado["texto"][ini:fim] for ini, fim in resultado["nao_calculado"]]


def rodar_sem_motor(codigo):
    """Roda o programa sem rastreador, para comparar a saída."""
    saida = io.StringIO()
    meus = dict(vars(builtins))
    meus["print"] = lambda *args, **kwargs: print(*args, **{"file": saida, **kwargs})
    exec(compile(codigo, "<aluno>", "exec"), {"__name__": "__main__", "__builtins__": meus})
    return saida.getvalue()


@pytest.mark.parametrize(
    "texto, variaveis, esperado, valor",
    [
        ("nota >= 6", {"nota": 7}, "7 >= 6", True),
        ("nome == 'Ana'", {"nome": "Ana"}, '"Ana" == "Ana"', True),
        ("x % 2 == 0", {"x": 7}, "7 % 2 == 0", False),
        ("numeros[i] > maior", {"numeros": [4, 9], "i": 1, "maior": 4}, "9 > 4", True),
        ("len(l) > 0", {"l": [1, 2, 3]}, "3 > 0", True),
        ("not achou", {"achou": False}, "not False", True),
        ("achou", {"achou": True}, "True", True),
        ("vidas", {"vidas": 0}, "0", False),
        ("x ** 2 > 5", {"x": -3}, "(-3) ** 2 > 5", True),
        ("-x > 0", {"x": -3}, "-(-3) > 0", True),
        ("(a + b) * 2 > 10", {"a": 1, "b": 2}, "(1 + 2) * 2 > 10", False),
        ("not (a > 1 and b > 1)", {"a": 2, "b": 3}, "not (2 > 1 and 3 > 1)", False),
        ("resposta in ['s', 'sim']", {"resposta": "sim"}, '"sim" in ["s", "sim"]', True),
        ("d['a'] == 1", {"d": {"a": 1}}, "1 == 1", True),
        ("l[1:] == [2, 3]", {"l": [1, 2, 3]}, "[2, 3] == [2, 3]", True),
        ("min(l) < max(l)", {"l": [3, 1, 2]}, "1 < 3", True),
        ("abs(x) == 3", {"x": -3}, "3 == 3", True),
        ("x is None", {"x": None}, "None is None", True),
        ("t == (1,)", {"t": (1,)}, "(1,) == (1,)", True),
        ("c == {2, 1}", {"c": {1, 2}}, "{1, 2} == {1, 2}", True),
        ("x in r", {"x": 2, "r": range(3)}, "2 in range(0, 3)", True),
        ("2 ** -1 < 1", {}, "2 ** -1 < 1", True),
    ],
)
def test_texto_com_os_valores(texto, variaveis, esperado, valor):
    resultado = condicao(texto, **variaveis)
    assert resultado["texto"] == esperado
    assert resultado["valor"] is valor
    assert resultado["nao_calculado"] == []
    assert resultado["valor"] == bool(eval(texto, {}, dict(variaveis)))


def test_and_com_lado_esquerdo_falso_nao_calcula_o_direito():
    resultado = condicao("i < len(l) and l[i] > 0", i=3, l=[1, 2, 3])
    assert resultado["texto"] == "3 < 3 and l[i] > 0"
    assert resultado["valor"] is False
    assert marcado(resultado) == ["l[i] > 0"]
    assert resultado["nao_calculado_codigo"] == [[1, 15, 1, 23]]  # posição no código do aluno


def test_or_com_lado_esquerdo_verdadeiro_nao_calcula_o_resto():
    resultado = condicao("x > 0 or y > 0 or z > 0", x=1, y=0, z=0)
    assert resultado["texto"] == "1 > 0 or y > 0 or z > 0"
    assert marcado(resultado) == ["y > 0 or z > 0"]


def test_curto_circuito_preserva_parenteses_do_que_ficou_de_fora():
    resultado = condicao("ok and (a or b)", ok=False, a=1, b=2)
    assert resultado["texto"] == "False and (a or b)"
    assert marcado(resultado) == ["(a or b)"]


def test_comparacao_encadeada_para_no_primeiro_falso():
    resultado = condicao("0 < x < 10 < y", x=-3, y=20)
    assert resultado["texto"] == "0 < -3 < 10 < y"  # y nem foi lido
    assert resultado["valor"] is False
    assert marcado(resultado) == ["< 10 < y"]


def test_comparacao_encadeada_verdadeira_calcula_tudo():
    resultado = condicao("0 < x < 10", x=5)
    assert (resultado["texto"], resultado["valor"], resultado["nao_calculado"]) == ("0 < 5 < 10", True, [])


def test_valor_longo_e_cortado_em_30_caracteres():
    resultado = condicao("l == []", l=list(range(100)))
    assert resultado["valor"] is None or len(resultado["texto"].split(" == ")[0]) <= 30
    resultado = condicao("nome != ''", nome="a" * 100)
    escrito = resultado["texto"].split(" != ")[0]
    assert len(escrito) == 30 and escrito.endswith("…")
    resultado = condicao("len(grande) > 0", grande=list(range(100_000)))
    assert resultado["texto"] == "100000 > 0"
    resultado = condicao("grande", grande=list(range(100_000)))
    assert resultado["texto"].startswith("[0, 1, 2") and len(resultado["texto"]) == 30


@pytest.mark.parametrize(
    "texto",
    [
        "f(x) > 1",  # função do aluno
        "nome.upper() == 'A'",  # método
        "str(x) == '1'",  # função fora da lista
        "(y := x) > 0",  # := mudaria uma variável
        "x if x else 0",
        "f'{x}' == '1'",
        "'%s' % x == '1'",
        "outra > 0",  # nome que não existe
        "len(x)",  # len de número dá erro
        "x / 0 > 1",
        "l[10] == 0",
        "d['b'] == 0",
        "10 ** 10 ** 9 > 1",  # travaria a página
        "'a' * 10 ** 8 == ''",
        "1.5 in range(10 ** 12)",
        "max([]) > 0",
        "min(l, key=abs) > 0",
        "[*l] == l",
    ],
)
def test_desiste_do_que_nao_e_seguro(texto):
    resultado = condicao(texto, x=1, l=[1, 2], d={"a": 1}, nome="ana", f=lambda v: v)
    assert resultado == {"texto": None, "valor": None, "nao_calculado": [], "nao_calculado_codigo": []}


def test_desistir_e_rapido():
    inicio = time.perf_counter()
    condicao("10 ** 10 ** 9 > 1 and 2 ** 10 ** 8 > 1")
    condicao("x * x * x > 0", x=10**30000)
    assert time.perf_counter() - inicio < 1


def test_len_que_o_aluno_trocou_nao_e_usado():
    assert condicao("len(l) > 0", l=[1], len=lambda v: 99)["texto"] is None


def test_subclasse_de_tipo_seguro_nao_e_aceita():
    class MeuInt(int):
        def __gt__(self, outro):
            raise RuntimeError("não devia ser chamado")

    assert condicao("x > 1", x=MeuInt(5))["texto"] is None


# --- Nada do programa do aluno pode mudar por causa da anotação ---


class Contador:
    """Um objeto que conta quantas vezes o Python mexeu nele."""

    def __init__(self):
        self.vezes = 0

    def __getitem__(self, indice):
        self.vezes += 1
        return 0

    def __eq__(self, outro):
        self.vezes += 1
        return True

    def __lt__(self, outro):
        self.vezes += 1
        return True

    def __bool__(self):
        self.vezes += 1
        return True

    def __len__(self):
        self.vezes += 1
        return 1

    __hash__ = object.__hash__


@pytest.mark.parametrize(
    "texto",
    [
        "c[0] == 0", "c == 1", "c", "not c", "len(c) > 0", "c in l",
        "l == [1]", "max(l) > 0", "l[0] == 1", "d[1] == 0", "{c} == set()",
    ],
)
def test_objeto_do_aluno_nunca_e_tocado(texto):
    c = Contador()
    resultado = condicao(texto, c=c, l=[c], d={c: 1})
    assert resultado["texto"] is None
    assert c.vezes == 0


def test_map_gerador_e_defaultdict_nao_sao_consumidos():
    numeros = map(int, ["3", "1", "2"])
    gerador = (n for n in range(3))
    contagem = defaultdict(int)
    for texto in ("max(numeros) > 2", "min(gerador) == 0", "contagem['a'] == 0", "len(numeros) > 0", "numeros"):
        resultado = condicao(texto, numeros=numeros, gerador=gerador, contagem=contagem)
        assert resultado["texto"] is None, texto
    assert list(numeros) == [3, 1, 2]
    assert list(gerador) == [0, 1, 2]
    assert dict(contagem) == {}


PROGRAMAS_COM_EFEITO = {
    "map": (
        'numeros = map(int, ["3", "1", "2"])\n'
        "if max(numeros) > 2:\n"
        '    print("grande")\n'
        "print(list(numeros))\n"
    ),
    "gerador": (
        "g = (n * n for n in range(4))\n"
        "while max(g) > 100:\n"
        "    pass\n"
        "print(list(g))\n"
    ),
    "defaultdict": (
        "from collections import defaultdict\n"
        "d = defaultdict(int)\n"
        "if d['a'] == 0 and len(d) == 1:\n"
        "    print('criou a chave uma vez')\n"
        "print(dict(d))\n"
    ),
    "getitem": (
        "class Contador:\n"
        "    def __init__(self):\n"
        "        self.vezes = 0\n"
        "    def __getitem__(self, i):\n"
        "        self.vezes += 1\n"
        "        return i\n"
        "c = Contador()\n"
        "if c[0] == 0:\n"
        "    print(c.vezes)\n"
        "while c[1] == 1 and c.vezes < 3:\n"
        "    pass\n"
        "print(c.vezes)\n"
    ),
    "curto_circuito": (
        "l = [1, 2, 3]\n"
        "i = 3\n"
        "if i < len(l) and l[i] > 0:\n"
        "    print('dentro')\n"
        "print('fora')\n"
    ),
}


@pytest.mark.parametrize("nome", list(PROGRAMAS_COM_EFEITO))
def test_saida_igual_com_e_sem_anotacao(nome):
    codigo = PROGRAMAS_COM_EFEITO[nome]
    resultado = rastrear(codigo)
    assert resultado["erro"] is None
    assert resultado["saida"] == rodar_sem_motor(codigo)
    decisoes = [p["_decisao_bruta"] for p in resultado["passos"] if "_decisao_bruta" in p]
    assert decisoes


def test_curto_circuito_aparece_no_rastro():
    resultado = rastrear(PROGRAMAS_COM_EFEITO["curto_circuito"])
    decisao = next(p["_decisao_bruta"] for p in resultado["passos"] if "_decisao_bruta" in p)
    assert decisao["texto"] == "3 < 3 and l[i] > 0"
    assert decisao["valor"] is False
    assert [decisao["texto"][a:b] for a, b in decisao["nao_calculado"]] == ["l[i] > 0"]
