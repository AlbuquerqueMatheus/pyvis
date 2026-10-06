import ast
import contextlib
import io
import json
import random
import re

import pytest

from analise.cobertura import CORPUS, criterio, ler_corpus, main, medir, resolver_pontos, resumo_por_tipo
from pyvis_motor import rastrear
from pyvis_motor.concepcoes import (
    AJUDANTES,
    CATALOGO,
    POR_ID,
    TIPOS_DE_PONTO,
    alvo_do_ponto,
    catalogo_publico,
    diagnosticar,
    feedback_do_modelo,
    gerar_modelos,
    inicios_de_laco,
    normalizar,
    observaveis,
    ocorrencia_do_passo,
    rastrear_leve,
)
from pyvis_motor.estrutura import Analise
from pyvis_motor.narrador import _mostrar
from pyvis_motor.rastreador import calcular_voltas

IDS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
CORPUS_LIDO = ler_corpus()


def ponto(pid, tipo, comando, nome=None, ocorrencia=1):
    return {"id": pid, "tipo": tipo, "alvo": {"comando": comando, "nome": nome}, "ocorrencia": ocorrencia}


def bloco_do_ponto(codigo, tipo, linha, nome=None, ocorrencia=1, entradas=(), **opcoes):
    comando = None if linha is None else Analise(codigo).linha_para_comando[linha]
    resultado = gerar_modelos(codigo, entradas, [ponto("p", tipo, comando, nome, ocorrencia)], 0, **opcoes)
    return resultado["por_ponto"]["p"]


def concepcoes_de(bloco):
    return {c for alternativa in bloco["alternativas"] for c in alternativa["concepcoes"]}


def textos_para_o_aluno(feedback):
    return [feedback["regra"], feedback["resolvido"], feedback["resumo"]]


# --- Catálogo ------------------------------------------------------------------


def test_catalogo_tem_as_8_concepcoes_na_ordem():
    assert [c["id"] for c in CATALOGO] == IDS
    for concepcao in CATALOGO:
        assert set(concepcao) >= {"id", "regra_para_aluno", "camadas", "transformar", "regra_rastro", "observavel_em",
                                  "padrao_ast", "referencias"}
        assert set(concepcao["camadas"]) == {"onde", "regra", "resolvido"}
        # Cada concepção é um programa transformado ou uma regra sobre o rastro, nunca as duas coisas.
        assert (concepcao["transformar"] is None) != (concepcao["regra_rastro"] is None)
        if concepcao["transformar"] is not None:
            assert issubclass(concepcao["transformar"], ast.NodeTransformer)
        assert concepcao["observavel_em"] and set(concepcao["observavel_em"]) <= set(TIPOS_DE_PONTO)
        assert concepcao["referencias"]


@pytest.mark.parametrize("concepcao", CATALOGO, ids=IDS)
def test_regra_para_aluno_tem_ate_12_palavras(concepcao):
    assert len(concepcao["regra_para_aluno"].split()) <= 12


@pytest.mark.parametrize("concepcao", CATALOGO, ids=IDS)
def test_textos_para_o_aluno_sem_aposta_nem_rotulo_tecnico(concepcao):
    textos = [concepcao["regra_para_aluno"], concepcao["crenca"], concepcao["camadas"]["regra"],
              concepcao["camadas"]["resolvido"]]
    for texto in textos:
        assert "apost" not in texto.lower()
        assert not re.search(r"\bC0\d\b", texto)
        assert not any(c["nome"] in texto for c in CATALOGO)


def test_catalogo_publico_vira_json_sem_funcoes():
    publico = catalogo_publico()
    json.dumps(publico)
    assert [c["id"] for c in publico] == IDS
    assert all("transformar" not in c and "padrao_ast" not in c for c in publico)


def test_observaveis_por_tipo_e_por_programa():
    assert "C01" in observaveis("voltas") and "C04" not in observaveis("voltas")
    assert observaveis("valor", "x = 1\nx = x + 1\n") == ["C04"]
    assert observaveis("saida", "for i in range(3):\n    print(i)\n") == ["C01", "C02"]
    assert observaveis("saida", "isto não compila(") == []


# --- Programas positivos e negativos para cada concepção ----------------------

FOR_3 = "for i in range(3):\n    print(i)\n"
ENERGIA = (
    "energia = 10\ndistancia = 0\nwhile energia > 0:\n    energia = energia - 3\n"
    "    distancia = distancia + 1\n    print(distancia, energia)\nprint('fim')\n"
)
BOLO = "bolo = 10\ncortes = 0\nwhile bolo > 1:\n    bolo = bolo / 2\n    cortes = cortes + 1\nprint(cortes)\n"
NOTA = 'n = 7\nif n > 5:\n    t = "grande"\nelse:\n    t = "pequeno"\nprint(t)\n'

# (concepção, código, tipo, linha, nome, entradas, texto da alternativa esperada)
POSITIVOS = [
    ("C01", "for i in range(1, 4):\n    print(i)\n", "voltas", 1, None, (), "4"),
    ("C01", FOR_3, "voltas", 1, None, (), "4"),
    ("C01", "for i in range(3, 0, -1):\n    print(i)\n", "voltas", 1, None, (), "4"),
    ("C01", "s = 0\nfor i in range(1, 4):\n    s = s + i\nprint(s)\n", "saida", 4, None, (), "10"),
    ("C02", FOR_3, "saida", 2, None, (), "1"),
    ("C02", "for i in range(3):\n    for j in range(i):\n        print(i, j)\n", "saida", 3, None, (), "1 1"),
    ("C03", "a = input()\nb = input()\nc = a + b\n", "valor", 3, "c", ("2", "3"), "5"),
    ("C03", 'r = input()\nif r == "7":\n    print("ok")\n', "decisao", 2, None, ("7",), "Falso"),
    ("C04", "x = 1\nx = x + 1\n", "valor", 2, "x", (), "1"),
    ("C04", "x = 'a'\nx += 'b'\n", "valor", 2, "x", (), '"a"'),
    ("C05", NOTA, "saida", 6, None, (), "pequeno"),
    ("C05", 'n = 5\nif n > 8:\n    t = "a"\nelif n > 3:\n    t = "b"\nelse:\n    t = "c"\nprint(t)\n', "saida", 8, None,
     (), "c"),
    ("C06", ENERGIA, "saida", None, None, (), "1 7\n2 4\n3 1\nfim"),
    ("C06", BOLO, "saida", 6, None, (), "3"),
    ("C07", "l = [10, 20, 30]\nx = l[1]\n", "valor", 2, "x", (), "10"),
    ("C07", "l = [5, 8]\nif l[1] > 6:\n    print('alto')\n", "decisao", 2, None, (), "Falso"),
    ("C08", "x = 7 / 2\n", "valor", 1, "x", (), "3"),
    ("C08", "x = 5\nx /= 2\nprint(x)\n", "saida", 3, None, (), "2"),
    ("C08", BOLO, "voltas", 3, None, (), "3"),
]

# (concepção, código, tipo, linha, nome, entradas): a concepção não pode gerar alternativa.
NEGATIVOS = [
    ("C01", "for x in [1, 2, 3]:\n    print(x)\n", "voltas", 1, None, ()),
    ("C01", "for i in range(0, 11, 2):\n    print(i)\n", "voltas", 1, None, ()),  # 11 + 1 não muda nada
    ("C01", "s = 0\nfor i in range(1, 4):\n    s = s + i\n", "valor", 3, "s", ()),  # 1ª volta igual
    ("C02", "for i in range(1, 4):\n    print(i)\n", "saida", 2, None, ()),
    ("C02", FOR_3, "voltas", 1, None, ()),  # a quantidade de voltas não muda
    ("C03", "n = int(input())\nprint(n + 1)\n", "valor", 1, "n", ("4",)),
    ("C03", "nome = input()\nprint('Oi', nome)\n", "saida", 2, None, ("Rex",)),
    ("C03", "p = input().split()\nprint(p)\n", "saida", 2, None, ("1 2",)),
    ("C04", "x = 1\n", "valor", 1, "x", ()),  # a variável ainda não existia
    ("C04", "x = 1\nx = x + 1\nprint(x)\n", "saida", 3, None, ()),  # não é observável na saída
    ("C05", "n = 7\nif n > 5:\n    t = 1\nprint(t)\n", "saida", 4, None, ()),
    ("C05", NOTA.replace("n = 7", "n = 3"), "saida", 6, None, ()),  # o if não entrou: o else roda de qualquer jeito
    ("C06", "c = 5\nwhile c > 0:\n    print(c)\n    c = c - 1\nprint('fim')\n", "saida", None, None, ()),
    ("C06", "r = 0\nwhile input() != 'sair':\n    r = r + 1\n    print(r)\n", "saida", 4, None, ("a", "sair")),
    ("C07", "l = [1, 2]\nx = l[0]\ny = l[-1]\nprint(x, y)\n", "saida", 4, None, ()),
    ("C07", "d = {1: 'um', 2: 'dois'}\nx = d[2]\n", "valor", 2, "x", ()),
    ("C08", "x = 7 // 2\nprint(x)\n", "saida", 2, None, ()),
    ("C08", "x = 14 / 2\n", "valor", 1, "x", ()),  # 7 contra 7.0 não é distrator
]


@pytest.mark.parametrize("cid, codigo, tipo, linha, nome, entradas, esperado", POSITIVOS)
def test_concepcao_gera_o_distrator(cid, codigo, tipo, linha, nome, entradas, esperado):
    bloco = bloco_do_ponto(codigo, tipo, linha, nome, entradas=entradas)
    textos = [a["texto"] for a in bloco["alternativas"] if cid in a["concepcoes"]]
    assert textos == [esperado]
    assert bloco["certa"]["texto"] != esperado


@pytest.mark.parametrize("cid, codigo, tipo, linha, nome, entradas", NEGATIVOS)
def test_concepcao_nao_gera_distrator(cid, codigo, tipo, linha, nome, entradas):
    bloco = bloco_do_ponto(codigo, tipo, linha, nome, entradas=entradas)
    assert bloco["certa"] is not None
    assert cid not in concepcoes_de(bloco)


def test_c06_so_vale_para_condicao_sem_efeito_e_corpo_com_dois_comandos():
    padrao = POR_ID["C06"]["padrao_ast"]
    assert padrao(Analise(ENERGIA))
    assert not padrao(Analise("x = 0\nwhile x < 3:\n    x += 1\n"))
    assert not padrao(Analise("x = 0\nwhile x < 3: x += 1; print(x)\n"))
    assert not padrao(Analise("l = [1]\nwhile l.pop():\n    a = 1\n    b = 2\n"))
    assert padrao(Analise("l = [1, 2]\nwhile len(l) > 0:\n    a = l\n    l = []\n"))


def test_c06_nao_cria_passos_nem_muda_a_contagem():
    analise = Analise(ENERGIA)
    arvore = POR_ID["C06"]["transformar"](analise).aplicar(analise.arvore)
    real = rastrear_leve(ENERGIA, analise=analise, limite=1000)
    modelo = rastrear_leve(ENERGIA, (), (), 0, 200, arvore=arvore, extras=AJUDANTES, analise=analise)
    # As 3 primeiras voltas são iguais; na 4ª o modelo para logo depois de energia ficar negativa.
    assert modelo["sequencia"][:14] == real["sequencia"][:14]
    assert modelo["ocorrencias"][3] == real["ocorrencias"][3]  # energia = energia - 3: 4 vezes nos dois
    assert modelo["ocorrencias"][4] == real["ocorrencias"][4] - 1


def test_c03_numero_decimal_e_texto():
    bloco = bloco_do_ponto("a = input()\nb = input()\n", "valor", 1, "a", entradas=("2.5", "x"))
    assert [a["texto"] for a in bloco["alternativas"]] == ["2.5"]
    assert bloco_do_ponto("a = input()\n", "valor", 1, "a", entradas=("nan",))["alternativas"] == []


def test_range_ou_input_do_aluno_nao_vira_modelo():
    assert not POR_ID["C01"]["padrao_ast"](Analise("range = lambda n: [1]\nfor i in range(3):\n    print(i)\n"))
    assert not POR_ID["C02"]["padrao_ast"](Analise("def range(n):\n    return [n]\nfor i in range(3):\n    print(i)\n"))
    assert not POR_ID["C03"]["padrao_ast"](Analise("def input():\n    return 1\nx = input()\n"))
    assert POR_ID["C03"]["padrao_ast"](Analise("x = input()\n"))


def test_c05_cadeia_de_elif_sem_else_nao_e_padrao():
    assert not POR_ID["C05"]["padrao_ast"](Analise("n = 1\nif n > 2:\n    a = 1\nelif n > 0:\n    a = 2\n"))
    assert POR_ID["C05"]["padrao_ast"](Analise("n = 1\nif n > 2:\n    a = 1\nelse:\n    if n > 0:\n        a = 2\n"))


# --- rastrear_leve -------------------------------------------------------------

PROGRAMAS_DIFICEIS = [
    "lista = [\n    1,\n    2,\n]\ntotal = (len(lista) +\n         sum(lista))\nprint(lista,\n      total)\n",
    "x = 5\nif x > 3: y = 1\nelse: y = 2\nprint(y)\n",
    "def dobro(n):\n    return n * 2\nx = 1\nwhile dobro(x) < 8:\n    x = x + 1\nprint(x)\n",
    "for i in range(3): print(i)\nprint('fim')\n",
    "q = [x*x for x in range(4)]\nfor i in range(2):\n    q2 = [y for y in q if y > i]\n",
    "def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\nprint(f(4))\n",
    "def gen():\n    for i in range(3):\n        yield i\nfor v in gen():\n    print(v)\n",
    "for i in range(3):\n    if i == 1:\n        break\n    print(i)\nelse:\n    print('nunca')\n",
    "try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    x = 0\nfinally:\n    y = 2\n",
    "class A:\n    v = 1\n    def m(self):\n        return self.v\nprint(A().m())\n",
    "import random\nfor i in range(3):\n    print(random.randint(1, 6))\n",
]


def _sequencia(resultado):
    return [[p["comando"], p["quadro"]] for p in resultado["passos"]]


@pytest.mark.parametrize("codigo", PROGRAMAS_DIFICEIS + [p["codigo"] for p in CORPUS_LIDO[::5]])
def test_rastrear_leve_conta_os_passos_como_o_rastro_completo(codigo):
    completo = rastrear(codigo, semente=3)
    leve = rastrear_leve(codigo, semente=3, limite=1000)
    assert leve["sequencia"] == _sequencia(completo)
    assert leve["saida"] == completo["saida"]


def test_rastrear_leve_nao_tira_fotos():
    leve = rastrear_leve("x = [1, 2]\ny = x\n", alvos=[{"id": "a", "tipo": "valor", "comando": 1, "nome": "y"}])
    assert set(leve) == {"respostas", "antes", "ocorrencias", "passos", "estourou", "sem_tempo", "erro", "saida", "sequencia"}
    assert leve["respostas"]["a"]["texto"] == "[1, 2]"
    assert leve["ocorrencias"] == {0: 1, 1: 1}


def _resposta_do_rastro_completo(resultado, analise, rotulo, comando):
    """A resposta certa calculada do rastro completo, para conferir o alinhamento do leve."""
    passos = resultado["passos"]
    if rotulo["tipo"] == "voltas":
        inicio = inicios_de_laco(passos, analise.comandos)[(comando, rotulo["ocorrencia"])]
        return str(calcular_voltas(resultado)[inicio]["total"])
    if comando is None:
        return resultado["saida"][:-1] if resultado["saida"].endswith("\n") else resultado["saida"]
    passo = [p for p in passos if p["comando"] == comando][rotulo["ocorrencia"] - 1]
    if passo["proximo_no_quadro"] is None:
        return None  # último comando de uma função: o rastro completo não tem o "depois"
    depois = passos[passo["proximo_no_quadro"]]
    if rotulo["tipo"] == "saida":
        texto = depois["saida"][len(passo["saida"]):]
        return texto[:-1] if texto.endswith("\n") else texto
    if rotulo["tipo"] == "decisao":
        corpo = analise.comandos[comando]["corpo"]
        linha = analise.comandos[depois["comando"]]["linhas"][0] if depois["comando"] is not None else None
        return "Verdadeiro" if linha is not None and corpo[0] <= linha <= corpo[1] else "Falso"
    escopo = depois["locais"] if rotulo["nome"] in depois["locais"] else depois["globais"]
    return _mostrar(escopo[rotulo["nome"]])  # "Ana", com as aspas que o aluno vê


@pytest.mark.parametrize("programa", CORPUS_LIDO, ids=[p["nome"] for p in CORPUS_LIDO])
def test_corpus_todo_ponto_rotulado_acontece_e_bate_com_o_rastro_completo(programa):
    codigo, entradas, semente = programa["codigo"], programa["entradas"], programa["semente"]
    analise = Analise(codigo)
    pontos = resolver_pontos(programa, analise)
    resultado = rastrear(codigo, entradas, semente=semente)
    certas = gerar_modelos(codigo, entradas, pontos, semente)["por_ponto"]
    for rotulo, ponto_ in zip(programa["pontos"], pontos):
        certa = certas[ponto_["id"]]["certa"]
        assert certa is not None, f"{programa['nome']}: {rotulo} não acontece"
        esperado = _resposta_do_rastro_completo(resultado, analise, rotulo, ponto_["alvo"]["comando"])
        if esperado is not None:
            assert certa["texto"] == esperado, f"{programa['nome']}: {rotulo}"


def test_capturas_dentro_de_funcao_e_no_fim_do_quadro():
    codigo = "def dobro(x):\n    r = x * 2\n    return r\ndef vazio():\n    a = 1\nvazio()\nprint(dobro(4))\n"
    alvos = [{"id": "r", "tipo": "valor", "comando": 1, "nome": "r"},
             {"id": "a", "tipo": "valor", "comando": 4, "nome": "a"},
             {"id": "s", "tipo": "saida", "comando": 6}]
    leve = rastrear_leve(codigo, alvos=alvos)
    assert leve["respostas"]["r"]["texto"] == "8"
    assert leve["respostas"]["a"]["texto"] == "1"  # fechado no return implícito da função
    assert leve["respostas"]["s"]["texto"] == "8"


def test_decisao_com_corpo_na_mesma_linha_usa_o_avaliador():
    codigo = "x = 5\nif x > 3: y = 1\nif x > 9: y = 2\n"
    alvos = [{"id": "a", "tipo": "decisao", "comando": 1}, {"id": "b", "tipo": "decisao", "comando": 3}]
    respostas = rastrear_leve(codigo, alvos=alvos)["respostas"]
    assert (respostas["a"]["texto"], respostas["b"]["texto"]) == ("Verdadeiro", "Falso")


def test_saida_inteira_so_quando_o_programa_termina():
    alvos = [{"id": "t", "tipo": "saida", "comando": None}]
    assert rastrear_leve("print(1)\nprint(2)\n", alvos=alvos)["respostas"]["t"]["texto"] == "1\n2"
    assert rastrear_leve("print(1)\nx = 1 / 0\n", alvos=alvos)["respostas"]["t"] is None


def test_limite_de_passos_do_rastreio_leve():
    leve = rastrear_leve("while True:\n    x = 1\n", limite=50)
    assert leve["estourou"] is True
    assert len(leve["sequencia"]) == 51


def test_mesma_semente_mesmos_sorteios_e_random_do_motor_intacto():
    codigo = "import random\nprint(random.randint(1, 100), random.random())\n"
    random.seed(5)
    antes = random.random()
    random.seed(5)
    leve = rastrear_leve(codigo, semente=42)
    assert random.random() == antes
    assert leve["saida"] == rastrear(codigo, semente=42)["saida"]
    assert rastrear_leve(codigo, semente=42)["saida"] == leve["saida"]


def test_rastreio_leve_respeita_o_bloqueio_de_modulos():
    leve = rastrear_leve("import js\n")
    assert leve["erro"] == "ModuleNotFoundError"
    bloco = bloco_do_ponto("import pyodide\nfor i in range(2):\n    print(i)\n", "voltas", 2)
    assert bloco["certa"] is None  # o programa para no import
    assert rastrear_leve("import json\nprint(json.dumps(1))\n")["saida"] == "1\n"


# --- gerar_modelos ---------------------------------------------------------------


def test_cada_transformacao_roda_uma_vez_por_programa():
    codigo = "s = 0\nfor i in range(1, 4):\n    s = s + i\n    print(s)\nprint('fim', s)\n"
    analise = Analise(codigo)
    pontos = [ponto("a", "voltas", 1), ponto("b", "saida", 3, ocorrencia=1), ponto("c", "saida", 3, ocorrencia=3),
              ponto("d", "valor", 2, "s", 2), ponto("e", "saida", 4)]
    resultado = gerar_modelos(codigo, (), pontos, 0)
    assert resultado["concepcoes"]["C01"]["execucoes"] == 1
    assert resultado["concepcoes"]["C04"]["execucoes"] == 0  # regra sobre o rastro: não roda o programa
    for cid in ("C02", "C03", "C05", "C06", "C07", "C08"):
        assert resultado["concepcoes"][cid]["execucoes"] == 0  # o programa não tem a construção
    assert analise.comandos[1]["tipo"] == "for"
    json.dumps(resultado)


def test_alternativa_igual_a_certa_e_descartada():
    bloco = bloco_do_ponto("s = 0\nfor i in range(1, 4):\n    s = s + i\n", "valor", 3, "s", ocorrencia=1)
    assert bloco["descartadas"]["iguais"] == 1  # o range com o fim dá o mesmo na 1ª volta
    assert bloco["sem_modelo"]["C01"] == "igual_a_certa"
    assert [a["concepcoes"] for a in bloco["alternativas"]] == [["C04"]]


def test_duas_concepcoes_com_a_mesma_resposta_viram_uma_alternativa_sem_diagnostico():
    codigo = "for i in range(3):\n    for j in range(i):\n        print(i, j)\n"
    bloco = bloco_do_ponto(codigo, "voltas", 2, ocorrencia=2)
    assert bloco["certa"]["texto"] == "1"
    assert len(bloco["alternativas"]) == 1
    alternativa = bloco["alternativas"][0]
    assert alternativa["concepcoes"] == ["C01", "C02"]
    assert alternativa["concepcao"] is None and alternativa["feedback"] is None
    assert alternativa["origem"] == "modelo" and alternativa["certa"] is False
    assert bloco["descartadas"]["repetidas"] == 1


def test_modelo_que_estoura_o_limite_fica_sem_alternativa():
    # Com o else rodando junto, n volta a 0 e o laço nunca termina.
    codigo = "n = 0\nwhile n != 3:\n    if n < 3:\n        n = n + 3\n    else:\n        n = n - 3\nprint(n)\n"
    bloco = bloco_do_ponto(codigo, "saida", 7, limite=50)
    assert bloco["certa"]["texto"] == "3"
    assert bloco["sem_modelo"]["C05"] == "estouro"
    assert "C05" not in concepcoes_de(bloco)


def test_programa_nao_deterministico_nao_gera_modelo():
    codigo = "import time\nfor i in range(3):\n    print(i)\n"
    resultado = gerar_modelos(codigo, (), [ponto("p", "voltas", 1)], 0)
    assert resultado["deterministico"] is False
    assert resultado["por_ponto"]["p"]["alternativas"] == []
    assert resultado["por_ponto"]["p"]["sem_modelo"]["C01"] == "nao_deterministico"


def test_programa_com_random_usa_a_semente_e_gera_modelo():
    codigo = "import random\nn = random.randint(2, 4)\nfor i in range(n):\n    print(i)\n"
    primeiro = gerar_modelos(codigo, (), [ponto("p", "voltas", 2)], 9)["por_ponto"]["p"]
    segundo = gerar_modelos(codigo, (), [ponto("p", "voltas", 2)], 9)["por_ponto"]["p"]
    assert primeiro == segundo
    assert int(primeiro["alternativas"][0]["texto"]) == int(primeiro["certa"]["texto"]) + 1


def test_orcamento_esgotado_nao_gera_modelo():
    bloco = bloco_do_ponto(FOR_3, "voltas", 1, orcamento_ms=0)
    assert bloco["alternativas"] == []
    assert bloco["sem_modelo"]["C01"] == "orcamento"


def test_codigo_que_nao_compila_devolve_pontos_vazios():
    resultado = gerar_modelos("for i in range(3)\n    print(i)\n", (), [ponto("p", "voltas", 0)], 0)
    assert resultado["por_ponto"]["p"]["certa"] is None


def test_ocorrencia_vem_do_passo_do_rastro_completo():
    codigo = "for v in range(2):\n    for i in range(1, 3):\n        print(v, i)\n"
    resultado = rastrear(codigo)
    passos = resultado["passos"]
    terceiro_print = [p["i"] for p in passos if p["comando"] == 2][2]
    assert ocorrencia_do_passo(resultado, terceiro_print, "saida", 2) == 3
    segunda_entrada = inicios_de_laco(passos, resultado["estrutura"]["comandos"])[(1, 2)]
    assert ocorrencia_do_passo(resultado, segunda_entrada, "voltas", 1) == 2
    alvo = alvo_do_ponto({"id": "p", "tipo": "voltas", "passo": segunda_entrada, "alvo": {"comando": 1}}, resultado)
    assert alvo == {"id": "p", "tipo": "voltas", "comando": 1, "ocorrencia": 2, "nome": None}
    pontos = [{"id": "p", "tipo": "voltas", "passo": segunda_entrada, "alvo": {"comando": 1}}]
    bloco = gerar_modelos(codigo, (), pontos, 0, resultado=resultado)["por_ponto"]["p"]
    assert (bloco["certa"]["texto"], [a["texto"] for a in bloco["alternativas"]]) == ("2", ["3"])


# --- Feedback --------------------------------------------------------------------


def test_feedback_do_range_usa_os_valores_do_programa():
    bloco = bloco_do_ponto("for numero in range(1, 5):\n    print(numero)\n", "voltas", 1)
    feedback = bloco["alternativas"][0]["feedback"]
    assert feedback["onde"] == {"passo": None, "destacar": "numero"}
    assert feedback["regra"] == "O `range(1, 5)` para antes do `5`. O `5` nunca entra."
    assert feedback["resolvido"].startswith("O laço dá 4 voltas.")
    assert feedback["resumo"] == (
        "Será que você pensou que o `range(1, 5)` chegava até o `5`? O range para antes do último número."
    )


def test_feedback_fala_do_range_que_veio_antes_do_ponto():
    # ast.walk anda por largura: o range raso lá de baixo não pode passar na frente do aninhado de cima.
    codigo = "if True:\n    for i in range(1, 3):\n        x = i\nprint(x)\nfor k in range(7, 9):\n    pass\n"
    feedback = bloco_do_ponto(codigo, "saida", 4)["alternativas"][0]["feedback"]
    assert feedback["regra"] == "O `range(1, 3)` para antes do `3`. O `3` nunca entra."


def test_feedback_da_atribuicao_mostra_o_valor_antigo():
    bloco = bloco_do_ponto("total = 3\ntotal = total + 3\n", "valor", 2, "total")
    feedback = bloco["alternativas"][0]["feedback"]
    assert feedback["onde"]["destacar"] == "total"
    assert feedback["regra"] == "O `=` troca o valor: `total` valia 3 e passa a valer 6."


def test_feedback_de_todo_o_corpus_sem_lacuna_rotulo_ou_aposta():
    vistas = set()
    for programa in CORPUS_LIDO:
        analise = Analise(programa["codigo"])
        pontos = resolver_pontos(programa, analise)
        blocos = gerar_modelos(programa["codigo"], programa["entradas"], pontos, programa["semente"])["por_ponto"]
        for bloco in blocos.values():
            for modelo in bloco["modelos"]:
                vistas.add(modelo["concepcao"])
                for texto in textos_para_o_aluno(modelo["feedback"]):
                    assert "{" not in texto and "`?`" not in texto, texto
                    assert "apost" not in texto.lower()
                    assert not re.search(r"\bC0\d\b", texto)
    assert vistas == set(IDS)  # o corpus exercita o feedback de todas as concepções


# --- diagnosticar ------------------------------------------------------------------


def _ponto_de(codigo, tipo, linha, nome=None, entradas=(), ocorrencia=1):
    return {"id": "p", "tipo": tipo, **bloco_do_ponto(codigo, tipo, linha, nome, ocorrencia, entradas)}


def test_diagnostico_de_resposta_livre_depende_do_botao_numero_ou_texto():
    p = _ponto_de("a = input()\nb = input()\nsoma = a + b\n", "valor", 3, "soma", ("4", "5"))
    assert diagnosticar(p, {"texto": "9", "tipo_escolhido": "numero"}) == "C03"
    assert diagnosticar(p, {"texto": "9", "tipo_escolhido": "texto"}) is None
    assert diagnosticar(p, {"texto": "45", "tipo_escolhido": "texto"}) is None  # a certa
    assert diagnosticar(p, {"texto": "10", "tipo_escolhido": "numero"}) is None  # nenhum modelo explica
    assert diagnosticar(p, {"texto": "", "tipo_escolhido": "numero"}) is None
    assert feedback_do_modelo(p, "C03")["regra"].startswith("O `input` devolve texto")


def test_sete_contra_sete_ponto_zero_nao_e_diagnostico():
    p = _ponto_de("x = 14 / 2\n", "valor", 1, "x")
    assert p["certa"]["texto"] == "7.0"
    assert diagnosticar(p, {"texto": "7", "tipo_escolhido": "numero"}) is None


def test_diagnostico_de_voltas_saida_e_decisao():
    p = _ponto_de("for i in range(1, 4):\n    print(i)\n", "voltas", 1)
    assert diagnosticar(p, {"texto": "4"}) == "C01"
    assert diagnosticar(p, {"texto": "quatro"}) is None
    p = _ponto_de(NOTA, "saida", 6)
    assert diagnosticar(p, {"texto": "pequeno  "}) == "C05"
    p = _ponto_de('r = input()\nif r == "7":\n    print("ok")\n', "decisao", 2, entradas=("7",))
    assert diagnosticar(p, {"texto": "não"}) == "C03"
    assert diagnosticar(p, {"texto": "sim"}) is None


def test_diagnostico_exige_um_unico_modelo():
    p = _ponto_de("for i in range(3):\n    for j in range(i):\n        print(i, j)\n", "voltas", 2, ocorrencia=2)
    assert diagnosticar(p, {"texto": "2"}) is None  # C01 e C02 explicam a mesma resposta


def test_diagnostico_por_alternativa_nunca_conta_regra():
    p = {"tipo": "valor", "alternativas": [
        {"id": "a", "texto": "5", "certa": True, "concepcao": None, "origem": "correta"},
        {"id": "b", "texto": "4", "certa": False, "concepcao": "C01", "concepcoes": ["C01"], "origem": "modelo"},
        {"id": "c", "texto": "6", "certa": False, "concepcao": None, "origem": "regra"},
        {"id": "d", "texto": "3", "certa": False, "concepcao": None, "concepcoes": ["C01", "C02"], "origem": "modelo"},
    ]}
    assert diagnosticar(p, {"alternativa": "b"}) == "C01"
    assert diagnosticar(p, {"alternativa": "a"}) is None
    assert diagnosticar(p, {"alternativa": "c"}) is None
    assert diagnosticar(p, {"alternativa": "d"}) is None
    # Resposta livre só com as alternativas (sem `modelos`): também só conta o modelo.
    p["resposta"] = {"texto": "5", "tipo_valor": "numero"}
    assert diagnosticar(p, {"texto": "4"}) == "C01"
    assert diagnosticar(p, {"texto": "6"}) is None


def test_resposta_certa_do_rastro_completo_sem_aspas_tambem_serve():
    p = {"tipo": "valor", "resposta": {"texto": "12", "tipo_valor": "texto"},
         "modelos": [{"concepcao": "C03", "texto": "12", "tipo_valor": "numero"}]}
    assert diagnosticar(p, {"texto": "12", "tipo_escolhido": "texto"}) is None
    assert diagnosticar(p, {"texto": "12", "tipo_escolhido": "numero"}) == "C03"


@pytest.mark.parametrize(
    "tipo, texto, escolhido, chave",
    [
        ("decisao", "Sim", None, ("bool", True)),
        ("decisao", "falso", None, ("bool", False)),
        ("decisao", "talvez", None, None),
        ("voltas", " 4 ", None, ("numero", 4)),
        ("voltas", "4.5", None, None),
        ("saida", "A soma é 10  \n", None, ("saida", "A soma é 10")),
        ("valor", "7", "numero", ("numero", 7)),
        ("valor", "7.0", "numero", ("numero", 7)),
        ("valor", "Rex", "numero", None),
        ("valor", "'Rex'", "texto", ("texto", "Rex")),
        ("valor", "[1, 2]", None, ("lista", "list", (("numero", 1), ("numero", 2)))),
        ("valor", "True", None, ("bool", True)),
        ("valor", "Rex", None, ("texto", "Rex")),
    ],
)
def test_normalizar_resposta_livre(tipo, texto, escolhido, chave):
    assert normalizar(tipo, texto, escolhido) == chave


# --- Corpus e sonda de cobertura -----------------------------------------------------


def test_corpus_tem_de_40_a_60_programas_com_metadados_validos():
    assert 40 <= len(CORPUS_LIDO) <= 60
    tipos = {tipo: 0 for tipo in TIPOS_DE_PONTO}
    rotulos = {cid: 0 for cid in IDS}
    for programa in CORPUS_LIDO:
        assert len(programa["pontos"]) >= 3, programa["nome"]
        resolver_pontos(programa, Analise(programa["codigo"]))  # linha certa e tipo de comando certo
        compile(programa["codigo"], programa["nome"], "exec")
        assert "apost" not in programa["codigo"].lower()
        for rotulo in programa["pontos"]:
            tipos[rotulo["tipo"]] += 1
        for cid in programa["concepcoes"]:
            rotulos[cid] += 1
    assert min(tipos.values()) >= 25, tipos
    assert min(rotulos.values()) >= 3, rotulos


def test_corpus_tem_programas_com_input_e_um_nao_deterministico():
    assert sum(1 for p in CORPUS_LIDO if p["entradas"]) >= 10
    assert any(not gerar_modelos(p["codigo"], p["entradas"], (), 0)["deterministico"] for p in CORPUS_LIDO)


def test_sonda_de_cobertura_no_corpus():
    medicao = medir(CORPUS_LIDO, medir_tempo=False)
    tabela = resumo_por_tipo(medicao)
    assert tabela["total"]["pontos"] == sum(len(p["pontos"]) for p in CORPUS_LIDO)
    assert tabela["total"]["sem_certa"] == 0
    for tipo in TIPOS_DE_PONTO:
        linha = tabela[tipo]
        assert 0 <= linha["dois"] <= linha["um"] <= linha["pontos"]
        assert linha["descartadas"] <= linha["geradas"]
    decisao = criterio(medicao)
    assert decisao["total"] == sum(tabela[t]["pontos"] for t in ("saida", "voltas", "decisao"))
    assert 0 <= decisao["fracao"] <= 1
    json.dumps(medicao)


def test_script_de_cobertura_imprime_a_tabela():
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        assert main(["--corpus", str(CORPUS)]) == 0
    texto = saida.getvalue()
    assert "Pontos rotulados à mão" in texto
    assert "Critério pré-registrado" in texto
    assert all(cid in texto for cid in IDS)


def test_modelo_lento_para_no_prazo_e_marca_incompleto():
    # A C05 roda o else que o programa de verdade nunca roda, e ele é lento.
    codigo = (
        "idade = 12\nif idade >= 10:\n    print('pode jogar')\nelse:\n"
        "    for i in range(100):\n        total = sum(range(300000))\n    print(total)\nprint('fim')\n"
    )
    import time as relogio

    comeco = relogio.perf_counter()
    pontos = [{"id": "p1", "tipo": "saida", "alvo": {"comando": None}, "passo": 0}]
    saida = gerar_modelos(codigo, [], pontos, orcamento_ms=30)
    assert (relogio.perf_counter() - comeco) < 1.0  # sem o prazo, seriam vários segundos
    assert saida["completa"] is False
    assert saida["por_ponto"]["p1"]["sem_modelo"].get("C05") == "orcamento"
    assert saida["por_ponto"]["p1"]["certa"] is not None  # o programa de verdade rodou


def test_rastrear_leve_para_no_prazo():
    import time as relogio

    resultado = rastrear_leve("for i in range(150):\n    x = sum(range(200000))\n", prazo=relogio.perf_counter() + 0.02)
    assert resultado["sem_tempo"] is True and resultado["estourou"] is True
    assert resultado["passos"] < 150
