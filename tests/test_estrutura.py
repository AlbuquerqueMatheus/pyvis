import json
import re
import sys
from pathlib import Path

import pytest

from pyvis_motor import analisar, rastrear
from pyvis_motor.rastreador import calcular_voltas

EXEMPLOS_TS = Path(__file__).resolve().parent.parent / "frontend" / "src" / "exemplos.ts"


def comandos_de(codigo):
    return analisar(codigo)["comandos"]


def linhas_dos_passos(resultado):
    return [p["linha"] for p in resultado["passos"] if p["evento"] == "linha"]


# --- analisar(): comandos, faixas e mapa de linhas ---


def test_tipos_dos_comandos():
    codigo = (
        "x = 1\n"
        "x += 1\n"
        "print(x)\n"
        "len('a')\n"
        "def f():\n"
        "    return 1\n"
        "for i in range(2):\n"
        "    if i:\n"
        "        break\n"
        "    elif i > 5:\n"
        "        continue\n"
        "while False:\n"
        "    pass\n"
        "import math\n"
        "y: int = 2\n"
    )
    tipos = [c["tipo"] for c in comandos_de(codigo)]
    assert tipos == [
        "atrib", "aug", "print", "expr", "def", "return", "for", "if", "break", "elif",
        "continue", "while", "outro", "outro", "atrib",
    ]


def test_ids_sao_a_posicao_na_lista():
    comandos = comandos_de("a = 1\nif a:\n    b = 2\nc = 3\n")
    assert [c["id"] for c in comandos] == [0, 1, 2, 3]
    assert [c["pai"] for c in comandos] == [None, None, 1, None]


def test_faixas_de_if_elif_else():
    codigo = "n = 5\nif n > 10:\n    a = 1\nelif n > 3:\n    a = 2\nelse:\n    a = 3\n"
    se, senao_se = comandos_de(codigo)[1], comandos_de(codigo)[3]
    assert se["linhas"] == [2, 7]
    assert se["cabecalho"] == [2, 2]
    assert se["corpo"] == [3, 3]
    assert se["orelse"] == [4, 7]
    assert senao_se["tipo"] == "elif" and senao_se["pai"] == 1
    assert senao_se["orelse"] == [6, 7]  # começa na linha do else:


def test_else_dentro_de_outro_bloco_nao_e_elif():
    comandos = comandos_de("x = 1\nif x:\n    y = 1\nelse:\n    if x > 2:\n        y = 2\n")
    assert [c["tipo"] for c in comandos] == ["atrib", "if", "atrib", "if", "atrib"]
    assert comandos[1]["orelse"] == [4, 6]


def test_cabecalho_em_varias_linhas_e_comentario_antes_do_corpo():
    codigo = "if (1 >\n        0):\n    # comentário\n    x = 1\n"
    se = comandos_de(codigo)[0]
    assert se["cabecalho"] == [1, 2]
    assert se["corpo"] == [4, 4]


def test_acento_antes_dos_dois_pontos_nao_atrapalha():
    codigo = 'nome = "João"\nif nome == "João": print("olá")\nfor letra in "ção":\n    x = letra\n'
    comandos = comandos_de(codigo)
    assert comandos[1]["cabecalho"] == [2, 2]
    assert comandos[1]["corpo_mesma_linha"] is True
    assert comandos[3]["cabecalho"] == [3, 3]
    assert comandos[3]["corpo_mesma_linha"] is False


def test_decorador_faz_parte_do_cabecalho_da_funcao():
    codigo = "def d(f):\n    return f\n@d\ndef g(a,\n      b):\n    return a\n"
    g = comandos_de(codigo)[2]
    assert g["linhas"] == [3, 6]
    assert g["cabecalho"] == [3, 5]
    assert g["corpo"] == [6, 6]


def test_linha_para_comando_cobre_as_linhas_de_um_comando_longo():
    analise = analisar("lista = [\n    1,\n    2,\n]\nprint(lista)\n")
    assert analise["linha_para_comando"] == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1}


def test_linha_com_dois_comandos_fica_com_o_primeiro():
    analise = analisar("if True: x = 1\na = 1; b = 2\n")
    assert analise["linha_para_comando"] == {1: 0, 2: 2}


@pytest.mark.parametrize(
    "linha, esperado",
    [
        ("total = total + n", {"nome": "total", "contador": False}),
        ("total += n", {"nome": "total", "contador": False}),
        ("conta = conta + 1", {"nome": "conta", "contador": True}),
        ("conta += 1", {"nome": "conta", "contador": True}),
        ("conta = 1 + conta", {"nome": "conta", "contador": True}),
        ("vidas = vidas - 1", {"nome": "vidas", "contador": True}),
        ("produto = produto * n", {"nome": "produto", "contador": False}),
        ("conta += 1.0", {"nome": "conta", "contador": False}),
        ("total = n + 1", None),
        ("total = 1 - total", None),
        ("lista[0] += 1", None),
        ("total = total / 2", None),
    ],
)
def test_acumulador_dentro_do_laco(linha, esperado):
    comandos = comandos_de(f"for n in range(3):\n    {linha}\n")
    assert comandos[1]["acumulador"] == esperado


def test_acumulador_so_conta_dentro_de_laco():
    comandos = comandos_de("total = 0\ntotal = total + 1\nwhile total < 3:\n    total += 1\n")
    assert [c["acumulador"] for c in comandos] == [None, None, None, {"nome": "total", "contador": True}]


def test_funcao_dentro_de_laco_nao_herda_o_laco():
    comandos = comandos_de("for i in range(2):\n    def f(x):\n        x += 1\n        return x\n")
    assert comandos[2]["acumulador"] is None


def test_analisar_e_json():
    json.dumps(analisar("for i in range(3):\n    print(i)\n")["comandos"])


@pytest.mark.parametrize("fim", ["\r\n", "\r"])
def test_fim_de_linha_do_windows_e_do_mac_antigo(fim):
    codigo = fim.join(["x = 1", "if x > 1:", "    y = 1", "elif x == 1:", "    y = 2", ""])
    assert [c["tipo"] for c in comandos_de(codigo)] == ["atrib", "if", "atrib", "elif", "atrib"]
    resultado = rastrear(codigo)
    assert resultado["erro"] is None
    assert linhas_dos_passos(resultado) == [1, 2, 4, 5]


# --- Os 6 casos em que a sonda dos revisores achou passos errados ---


def test_caso1_comando_em_varias_linhas_fica_numa_linha_so():
    codigo = "lista = [\n    1,\n    2,\n]\ntotal = (len(lista) +\n         sum(lista))\nprint(lista,\n      total)\n"
    resultado = rastrear(codigo)
    # O Python avisa 2, 3, 1 para a lista: o passo é um só, na primeira linha.
    assert linhas_dos_passos(resultado) == [1, 5, 7]
    assert [p["comando"] for p in resultado["passos"]] == [0, 1, 2, None]
    assert resultado["passos"][1]["globais"]["lista"]["tipo"] == "list"
    assert "total" not in resultado["passos"][1]["globais"]  # o estado é o de antes do comando


def test_caso2_if_com_corpo_na_mesma_linha():
    codigo = "x = 5\nif x > 3: y = 1\nelse: y = 2\nprint(y)\n"
    resultado = rastrear(codigo)
    se = resultado["estrutura"]["comandos"][1]
    assert se["corpo_mesma_linha"] is True
    assert linhas_dos_passos(resultado) == [1, 2, 4]
    decisao = resultado["passos"][1]["_decisao_bruta"]
    assert (decisao["texto"], decisao["valor"]) == ("5 > 3", True)


def test_caso3_chamada_dentro_da_condicao():
    codigo = "def dobro(n):\n    return n * 2\nx = 3\nif dobro(x) > 5:\n    print('grande')\n"
    resultado = rastrear(codigo)
    passos = resultado["passos"]
    se = next(p for p in passos if p["linha"] == 4)
    assert se["_decisao_bruta"]["texto"] is None  # chamada do aluno: o avaliador não arrisca
    corpo = passos[se["proximo_no_quadro"]]
    assert corpo["linha"] == 5  # o próximo passo do mesmo quadro, não o de dentro de dobro
    assert passos[se["i"] + 1]["funcao"] == "dobro"
    assert corpo["retorno"]["valor"]["valor"] == "6"


def test_caso3_chamada_na_condicao_do_while_conta_as_voltas():
    codigo = "def dobro(n):\n    return n * 2\nx = 1\nwhile dobro(x) < 8:\n    x = x + 1\nprint(x)\n"
    resultado = rastrear(codigo)
    voltas = calcular_voltas(resultado)
    cabecalhos = [v for p, v in zip(resultado["passos"], voltas) if p["linha"] == 4]
    assert [v["n"] for v in cabecalhos] == [1, 2, 3, 3]
    assert cabecalhos[-1]["saindo"] is True
    assert {v["total"] for v in cabecalhos} == {3}


def test_caso4_return_sem_passo_proprio():
    codigo = "def dobro(n):\n    return n * 2\nx = dobro(4)\nprint(x)\n"
    resultado = rastrear(codigo)
    passos = resultado["passos"]
    assert [(p["linha"], p["funcao"]) for p in passos] == [(1, None), (3, None), (2, "dobro"), (4, None), (4, None)]
    assert passos[3]["retorno"]["funcao"] == "dobro"
    assert passos[3]["retorno"]["valor"]["valor"] == "8"


def test_caso4_return_em_funcao_de_uma_linha():
    codigo = "def dobro(n): return n * 2\nx = dobro(4)\n"
    resultado = rastrear(codigo)
    dentro = [p for p in resultado["passos"] if p["funcao"] == "dobro"]
    tipos = resultado["estrutura"]["comandos"]
    assert [tipos[p["comando"]]["tipo"] for p in dentro] == ["return"]  # não é o def
    assert resultado["passos"][-1]["retorno"]["valor"]["valor"] == "8"


def test_caso5_compreensao_e_um_passo_so():
    codigo = (
        "l = [1, 2, 3, 4]\n"
        "q = [n * n for n in l]\n"
        "s = sum(n for n in l)\n"
        "d = {n: n for n in l}\n"
        "c = {n % 2 for n in l}\n"
        "print(q, s, d, c)\n"
    )
    resultado = rastrear(codigo)
    assert linhas_dos_passos(resultado) == [1, 2, 3, 4, 5, 6]
    assert {p["quadro"] for p in resultado["passos"]} == {0}
    for passo in resultado["passos"]:
        assert set(passo["globais"]) <= {"l", "q", "s", "d", "c"}
    assert resultado["saida"] == "[1, 4, 9, 16] 10 {1: 1, 2: 2, 3: 3, 4: 4} {0, 1}\n"


def test_caso5_compreensao_que_chama_funcao():
    codigo = "def dobro(n):\n    return n * 2\nq = [dobro(i) for i in range(3)]\nprint(q)\n"
    resultado = rastrear(codigo)
    passos = resultado["passos"]
    assert [p["linha"] for p in passos if p["funcao"] is None] == [1, 3, 4, 4]
    dentro = [p for p in passos if p["funcao"] == "dobro"]
    assert len(dentro) == 3
    assert all(p["profundidade"] == 1 for p in dentro)
    assert len({p["quadro"] for p in dentro}) == 3


def test_caso6_for_encerrado_por_break():
    codigo = "for i in range(10):\n    if i == 2:\n        break\nprint(i)\n"
    resultado = rastrear(codigo)
    passos = resultado["passos"]
    assert linhas_dos_passos(resultado) == [1, 2, 1, 2, 1, 2, 3, 4]
    voltas = calcular_voltas(resultado)
    print_ = next(p["i"] for p in passos if p["linha"] == 4)
    no_laco = [v for v in voltas if v]
    assert [v["n"] for v in no_laco] == [1, 1, 2, 2, 3, 3, 3]
    assert all(v["total"] == 3 and v["total_visivel_desde"] == print_ for v in no_laco)
    assert not any(v["saindo"] for v in no_laco)  # o break sai sem passar pelo cabeçalho
    assert voltas[print_] is None


# --- Laços de uma linha só ---


def test_for_de_uma_linha_tem_um_passo_por_volta():
    resultado = rastrear("t = 0\nfor i in range(3): t += i\nprint(t)\n")
    assert linhas_dos_passos(resultado) == [1, 2, 2, 2, 2, 3]
    voltas = calcular_voltas(resultado)
    assert [v["n"] for v in voltas if v] == [1, 2, 3, 3]
    assert resultado["saida"] == "3\n"


def test_while_de_uma_linha():
    resultado = rastrear("x = 0\nwhile x < 3: x += 1\ny = x\n")
    cabecalhos = [p for p in resultado["passos"] if p["linha"] == 2]
    if sys.version_info >= (3, 14):  # o Pyodide; antes disso o Python avisa uma vez a menos
        assert len(cabecalhos) == 4
        assert [p["_decisao_bruta"]["valor"] for p in cabecalhos] == [True, True, True, False]
    else:
        assert len(cabecalhos) >= 2
    assert resultado["passos"][-1]["globais"]["y"]["valor"] == "3"


def test_compreensao_no_cabecalho_do_for_nao_conta_volta():
    resultado = rastrear("l = [1, 2]\nfor x in [y * 2 for y in l]:\n    print(x)\n")
    assert linhas_dos_passos(resultado) == [1, 2, 3, 2, 3, 2]
    assert resultado["saida"] == "2\n4\n"


# --- Os 8 exemplos do menu ---


def ler_exemplos():
    """Lê frontend/src/exemplos.ts: título, código (template literal) e entradas."""
    texto = EXEMPLOS_TS.read_text(encoding="utf-8")
    exemplos = []
    for bloco in re.split(r"\n\s*\{\s*\n", texto)[1:]:
        titulo = re.search(r"titulo:\s*\"([^\"]*)\"", bloco)
        codigo = re.search(r"codigo:\s*`((?:[^`\\]|\\.)*)`", bloco, re.S)
        if not (titulo and codigo):
            continue
        entradas = re.search(r"entradas:\s*(\"(?:[^\"\\]|\\.)*\")", bloco)
        exemplos.append(
            {
                "titulo": titulo.group(1),
                "codigo": codigo.group(1).replace("\\`", "`").replace("\\$", "$").replace("\\\\", "\\"),
                "entradas": json.loads(entradas.group(1)).split("\n") if entradas else [],
            }
        )
    return exemplos


EXEMPLOS = ler_exemplos()


def test_exemplos_foram_lidos():
    assert len(EXEMPLOS) >= 8


@pytest.mark.parametrize("exemplo", EXEMPLOS, ids=[e["titulo"] for e in EXEMPLOS])
def test_exemplo_roda_e_respeita_o_contrato(exemplo):
    resultado = rastrear(exemplo["codigo"], [e for e in exemplo["entradas"] if e], semente=1)
    json.dumps(resultado)
    passos = resultado["passos"]
    comandos = resultado["estrutura"]["comandos"]
    assert passos, exemplo["titulo"]
    if resultado["erro"] is None:
        assert passos[-1]["evento"] == "fim"
    else:
        assert resultado["erro"]["tipo"] == "NameError"  # só o "Encontre o erro"
        assert "erro" in exemplo["titulo"].lower()
    for passo in passos:
        if passo["evento"] == "linha":
            assert passo["linha"] == comandos[passo["comando"]]["linhas"][0]
        assert (passo["funcao"] is None) == (passo["profundidade"] == 0)
    # Dois passos seguidos nunca são o mesmo comando, a não ser num laço que dá outra volta.
    for antes, depois in zip(passos, passos[1:]):
        if antes["comando"] == depois["comando"] and antes["comando"] is not None:
            assert comandos[antes["comando"]]["tipo"] in ("for", "while")
    voltas = calcular_voltas(resultado)
    assert len(voltas) == len(passos)
    # Rodar de novo com a mesma semente dá o mesmo rastro.
    assert rastrear(exemplo["codigo"], [e for e in exemplo["entradas"] if e], semente=1) == resultado
