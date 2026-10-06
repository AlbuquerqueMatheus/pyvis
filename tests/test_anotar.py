import json
import sys

import pytest

from pyvis_motor import rastrear
from pyvis_motor.anotar import anotar
from test_estrutura import EXEMPLOS


def anotado(codigo, entradas=(), **opcoes):
    return anotar(rastrear(codigo, entradas, semente=1, **opcoes))


def passo_na_linha(resultado, linha, vez=0):
    return [p for p in resultado["passos"] if p["linha"] == linha and p["evento"] == "linha"][vez]


def resumo_do_efeito(efeito):
    """O efeito sem os Valores inteiros, para comparar fácil."""
    if efeito is None:
        return None
    mudadas = [(m["nome"], m["escopo"], m["antes"]["valor"], m["depois"]["valor"]) for m in efeito["mudadas"]]
    return efeito["criadas"], mudadas, efeito["saida_nova"]


# --- efeito ---


def test_efeito_compara_com_o_proximo_passo_do_mesmo_quadro():
    resultado = anotado("total = 3\nnumero = 3\ntotal = total + numero\nprint(total)\n")
    efeitos = [resumo_do_efeito(p["efeito"]) for p in resultado["passos"]]
    assert efeitos == [
        (["total"], [], ""),
        (["numero"], [], ""),
        ([], [("total", "global", "3", "6")], ""),
        ([], [], "6\n"),
        None,  # o fim não é comando
    ]
    mudada = resultado["passos"][2]["efeito"]["mudadas"][0]
    assert mudada["antes"]["h"] != mudada["depois"]["h"]  # Valores inteiros, com o resumo h


def test_efeito_de_uma_chamada_inclui_o_que_a_funcao_fez():
    codigo = "def dobro(n):\n    r = n * 2\n    return r\nx = dobro(4)\nprint(x)\n"
    resultado = anotado(codigo)
    chamada = passo_na_linha(resultado, 4)
    assert resumo_do_efeito(chamada["efeito"]) == (["x"], [], "")
    dentro = passo_na_linha(resultado, 2)
    assert dentro["efeito"]["criadas"] == ["r"]  # a variável local da função
    assert dentro["efeito"]["parcial"] is False


def test_efeito_local_e_global_dentro_da_funcao():
    codigo = "t = 0\ndef soma(n):\n    global t\n    t = t + n\n    n = n + 1\n    return n\nsoma(5)\n"
    resultado = anotado(codigo)
    global_ = passo_na_linha(resultado, 4)
    local = passo_na_linha(resultado, 5)
    assert resumo_do_efeito(global_["efeito"]) == ([], [("t", "global", "0", "5")], "")
    assert resumo_do_efeito(local["efeito"]) == ([], [("n", "local", "5", "6")], "")


def test_ultimo_comando_da_funcao_compara_com_o_passo_do_retorno():
    codigo = "def ola(nome):\n    x = 1\n    print('oi', nome)\nola('Ana')\ny = 2\n"
    resultado = anotado(codigo)
    ultimo = passo_na_linha(resultado, 3)
    assert ultimo["proximo_no_quadro"] is None
    # As locais sumiram com a função: só a saída e as globais são comparadas.
    assert ultimo["efeito"]["parcial"] is True
    assert ultimo["efeito"]["saida_nova"] == "oi Ana\n"
    assert ultimo["efeito"]["criadas"] == [] and ultimo["efeito"]["mudadas"] == []


# Quadros que terminam um logo depois do outro, sem passo no meio.
SEM_PASSO_ENTRE_RETORNOS = {
    "recursao": "def contagem(n):\n    if n == 0:\n        print('fim')\n        return\n    print(n)\n    contagem(n - 1)\ncontagem(2)\n",
    "fatorial": "def fat(n):\n    if n <= 1:\n        return 1\n    return n * fat(n - 1)\nr = fat(3)\nprint(r)\n",
    "return_g": "def g(x):\n    return x + 1\ndef f(x):\n    return g(x)\ny = f(1)\n",
    "return_g_vezes": "def dobro(n):\n    return n * 2\ndef quadruplo(n):\n    return dobro(n) * 2\nx = quadruplo(3)\nprint(x)\n",
}


@pytest.mark.parametrize("nome", SEM_PASSO_ENTRE_RETORNOS)
def test_cada_quadro_que_termina_tem_seu_retorno(nome):
    resultado = anotado(SEM_PASSO_ENTRE_RETORNOS[nome])
    assert resultado["erro"] is None
    funcoes = {p["quadro"] for p in resultado["passos"] if p["funcao"] is not None}
    recebidos = [r["quadro"] for p in resultado["passos"] for r in p.get("retornos", [])]
    assert sorted(recebidos) == sorted(funcoes)
    for passo in resultado["passos"]:
        if passo.get("retornos"):
            assert passo["retorno"] is passo["retornos"][-1]  # o do quadro que chamou este
        if passo["evento"] == "linha":
            # Programa sem erro: todo comando, dentro ou fora de função, tem efeito e desfecho.
            assert passo["efeito"] is not None, passo
            assert passo["desfecho_visivel_desde"] is not None


def test_recursao_guarda_os_retornos_do_mais_fundo_ao_de_fora():
    resultado = anotado(SEM_PASSO_ENTRE_RETORNOS["fatorial"])
    recebe = next(p for p in resultado["passos"] if p.get("retornos"))
    assert [r["valor"]["valor"] for r in recebe["retornos"]] == ["1", "2", "6"]
    assert recebe["retorno"]["valor"]["valor"] == "6"


def test_if_no_fim_da_funcao_recursiva_decide_o_ramo():
    resultado = anotado(SEM_PASSO_ENTRE_RETORNOS["recursao"])
    ramos = [p["decisao"]["ramo"] for p in resultado["passos"] if p["decisao"]]
    assert ramos == ["sai", "sai", "corpo"]


def test_efeito_do_ultimo_comando_para_no_return():
    # O print de fora escreve depois do return: não é efeito do print de dentro.
    resultado = anotado("def estrelas(n):\n    print('*' * n)\nfor i in range(1, 3):\n    print(estrelas(i))\n")
    dentro = [p for p in resultado["passos"] if p["linha"] == 2]
    assert [p["efeito"]["saida_nova"] for p in dentro] == ["*\n", "**\n"]
    assert all(p["efeito"]["parcial"] for p in dentro)
    # `t = f()` acontece depois do return: t não é efeito do return.
    resultado = anotado("def f():\n    v = 5\n    return v\nt = f()\nprint(t)\n")
    ultimo = passo_na_linha(resultado, 3)
    assert ultimo["efeito"]["criadas"] == [] and ultimo["efeito"]["mudadas"] == []
    # Uma global mudada no último comando continua aparecendo.
    resultado = anotado("t = 0\ndef f():\n    global t\n    t = t + 1\nf()\nx = 1\n")
    ultimo = passo_na_linha(resultado, 4)
    assert resumo_do_efeito(ultimo["efeito"]) == ([], [("t", "global", "0", "1")], "")


def test_try_finally_nao_mistura_a_saida_de_fora():
    codigo = "def f():\n    try:\n        return 1\n    finally:\n        print('fim')\nprint(f())\n"
    resultado = anotado(codigo)
    finalmente = passo_na_linha(resultado, 5)
    assert finalmente["efeito"]["saida_nova"] == "fim\n"


def test_comando_que_deu_erro_nao_tem_efeito():
    resultado = anotado("x = 1\ny = x / 0\n")
    assert resultado["passos"][-1]["efeito"] is None
    resultado = anotado("def f():\n    return 1 / 0\ntry:\n    f()\nexcept ZeroDivisionError:\n    z = 1\n")
    dentro = passo_na_linha(resultado, 2)
    assert dentro["efeito"] is None  # a função saiu por um erro: não há estado depois


def test_efeito_mostra_variavel_apagada_e_lista_mudada_por_dentro():
    resultado = anotado("l = [1]\nl.append(2)\ndel l\n")
    mudada = resultado["passos"][1]["efeito"]["mudadas"][0]
    assert (mudada["nome"], mudada["escopo"]) == ("l", "global")
    assert [i["valor"] for i in mudada["antes"]["itens"]] == ["1"]
    assert [i["valor"] for i in mudada["depois"]["itens"]] == ["1", "2"]
    assert resultado["passos"][2]["efeito"]["apagadas"] == ["l"]


# --- decisao ---


def decisoes(resultado):
    return [
        (p["linha"], p["decisao"]["texto"], p["decisao"]["valor"], p["decisao"]["ramo"])
        for p in resultado["passos"]
        if p["decisao"]
    ]


def test_decisao_substitui_a_bruta_e_so_existe_em_if_elif_e_while():
    resultado = anotado("n = 5\nif n > 10:\n    a = 1\nelif n > 3:\n    a = 2\nelse:\n    a = 3\n")
    assert not any("_decisao_bruta" in p for p in resultado["passos"])
    assert decisoes(resultado) == [(2, "5 > 10", False, "orelse"), (4, "5 > 3", True, "corpo")]
    assert [p["decisao"] is None for p in resultado["passos"]] == [True, False, False, True, True]


@pytest.mark.parametrize(
    "codigo, esperado",
    [
        ("x = 1\nif x > 0:\n    y = 1\n", [(2, "1 > 0", True, "corpo")]),
        ("x = 1\nif x > 5:\n    y = 1\nz = 2\n", [(2, "1 > 5", False, "sai")]),
        ("x = 1\nif x > 5:\n    y = 1\nelse:\n    y = 2\n", [(2, "1 > 5", False, "orelse")]),
        (
            "x = 2\nwhile x > 0:\n    x -= 1\n",
            [(2, "2 > 0", True, "corpo"), (2, "1 > 0", True, "corpo"), (2, "0 > 0", False, "sai")],
        ),
        (
            "x = 1\nwhile x > 0:\n    x -= 1\nelse:\n    y = 1\n",
            [(2, "1 > 0", True, "corpo"), (2, "0 > 0", False, "orelse")],
        ),
        # O corpo na mesma linha não gera passo: o avaliador decide.
        ("x = 5\nif x > 3: y = 1\nelse: y = 2\n", [(2, "5 > 3", True, "corpo")]),
        ("x = 1\nif x > 3: y = 1\nelse: y = 2\n", [(2, "1 > 3", False, "orelse")]),
        ("x = 1\nif x > 3: y = 1\nz = 0\n", [(2, "1 > 3", False, "sai")]),
        # Um corpo que não gera passo nenhum.
        ("x = 1\nif x:\n    ...\nz = 0\n", [(2, "1", True, "corpo")]),
    ],
)
def test_ramo_pelo_proximo_passo_do_mesmo_quadro(codigo, esperado):
    assert decisoes(anotado(codigo)) == esperado


def test_ramo_com_chamada_na_condicao_vem_do_rastro():
    codigo = (
        "def dobro(n):\n    return n * 2\nx = 3\nif dobro(x) > 5:\n    print('grande')\nelse:\n    print('pequeno')\n"
    )
    resultado = anotado(codigo)
    se = passo_na_linha(resultado, 4)
    assert se["decisao"]["texto"] is None  # o avaliador não arrisca chamar a função
    assert (se["decisao"]["valor"], se["decisao"]["ramo"]) == (True, "corpo")
    corpo = passo_na_linha(resultado, 5)
    assert se["decisao"]["ramo_visivel_desde"] == corpo["i"]
    # O valor só pode aparecer depois que dobro terminou.
    assert se["desfecho_visivel_desde"] == corpo["i"]


def test_if_no_fim_da_funcao_sai_quando_a_funcao_termina():
    codigo = "def f(x):\n    if x > 5:\n        return 1\nr = f(1)\n"
    resultado = anotado(codigo)
    se = passo_na_linha(resultado, 2)
    assert se["proximo_no_quadro"] is None
    assert (se["decisao"]["valor"], se["decisao"]["ramo"]) == (False, "sai")
    assert se["decisao"]["ramo_visivel_desde"] == resultado["passos"][-1]["i"]  # o passo que recebe o retorno


def test_erro_na_condicao_deixa_o_ramo_desconhecido():
    resultado = anotado("x = 0\nif 1 / x > 1:\n    y = 1\n")
    se = resultado["passos"][-1]
    assert se["decisao"]["ramo"] == "desconhecido"
    assert se["decisao"]["valor"] is None
    assert se["decisao"]["ramo_visivel_desde"] is None


def test_limite_no_cabecalho_deixa_o_ramo_desconhecido():
    resultado = anotado("x = 0\nwhile x < 100:\n    x += 1\n", limite=3)
    ultimo = resultado["passos"][-1]
    assert resultado["erro"]["tipo"] == "LimiteDePassos"
    assert ultimo["linha"] == 2
    assert ultimo["decisao"]["ramo"] == "desconhecido"
    assert ultimo["decisao"]["valor"] is None  # o comando nem chegou a rodar
    assert ultimo["efeito"] is None


def test_curto_circuito_continua_marcado():
    resultado = anotado("l = [1, 2]\ni = 2\nif i < len(l) and l[i] > 0:\n    x = 1\n")
    decisao = passo_na_linha(resultado, 3)["decisao"]
    assert decisao["texto"] == "2 < 2 and l[i] > 0"
    assert decisao["texto"][slice(*decisao["nao_calculado"][0])] == "l[i] > 0"
    assert decisao["nao_calculado_codigo"] == [[3, 18, 3, 26]]
    assert decisao["ramo"] == "sai"


def test_while_de_uma_linha():
    resultado = anotado("x = 0\nwhile x < 3: x += 1\ny = x\n")
    cabecalhos = [p["decisao"] for p in resultado["passos"] if p["linha"] == 2]
    assert all(d["ramo"] in ("corpo", "sai") for d in cabecalhos)
    assert cabecalhos[0]["ramo"] == "corpo"
    if sys.version_info >= (3, 14):  # o Pyodide; antes, o Python avisa uma vez a menos
        assert [d["ramo"] for d in cabecalhos] == ["corpo", "corpo", "corpo", "sai"]


# --- volta e desfecho_visivel_desde ---


def test_volta_vem_de_calcular_voltas():
    resultado = anotado("total = 0\nfor numero in range(1, 5):\n    total = total + numero\nprint(total)\n")
    passos = resultado["passos"]
    print_ = passo_na_linha(resultado, 4)
    voltas = [(p["linha"], p["volta"]["n"], p["volta"]["saindo"]) for p in passos if p["volta"]]
    assert voltas == [(2, 1, False), (3, 1, False), (2, 2, False), (3, 2, False), (2, 3, False), (3, 3, False)] + [
        (2, 4, False),
        (3, 4, False),
        (2, 4, True),
    ]
    for passo in passos:
        if passo["volta"]:
            assert passo["volta"]["laco"] == 1
            assert passo["volta"]["total"] == 4
            assert passo["volta"]["total_visivel_desde"] == print_["i"]
    assert passos[0]["volta"] is None and print_["volta"] is None


def test_desfecho_aparece_junto_com_o_passo_sem_chamadas():
    resultado = anotado("x = 1\nif x:\n    y = 2\n")
    assert [p["desfecho_visivel_desde"] for p in resultado["passos"]] == [0, 1, 2, 3]


def test_desfecho_de_quem_chama_funcao_espera_a_funcao_terminar():
    codigo = "def dobro(n):\n    return n * 2\nx = dobro(4)\nprint(x)\n"
    resultado = anotado(codigo)
    chamada = passo_na_linha(resultado, 3)
    seguinte = passo_na_linha(resultado, 4)
    assert chamada["desfecho_visivel_desde"] == seguinte["i"]
    assert "retorno" in seguinte  # o retorno continua onde estava


def test_for_sobre_gerador_espera_o_gerador():
    codigo = "def conta():\n    yield 1\nfor v in conta():\n    w = v\n"
    resultado = anotado(codigo)
    cabecalho = passo_na_linha(resultado, 3)
    assert cabecalho["desfecho_visivel_desde"] == passo_na_linha(resultado, 4)["i"]


# --- os 6 casos de 1.2 e os exemplos ---


def test_caso1_comando_em_varias_linhas():
    resultado = anotado("lista = [\n    1,\n    2,\n]\ntotal = (len(lista) +\n         sum(lista))\n")
    assert resumo_do_efeito(resultado["passos"][0]["efeito"])[0] == ["lista"]
    assert resultado["passos"][1]["efeito"]["criadas"] == ["total"]


def test_caso5_compreensao_nao_cria_variaveis_internas():
    resultado = anotado("l = [1, 2]\nq = [n * n for n in l]\n")
    assert resultado["passos"][1]["efeito"]["criadas"] == ["q"]


def test_caso6_for_encerrado_por_break():
    resultado = anotado("for i in range(10):\n    if i == 2:\n        break\nprint(i)\n")
    ses = [p for p in resultado["passos"] if p["linha"] == 2]
    assert [p["decisao"]["ramo"] for p in ses] == ["sai", "sai", "corpo"]
    assert {p["volta"]["total"] for p in resultado["passos"] if p["volta"]} == {3}


@pytest.mark.parametrize("exemplo", EXEMPLOS, ids=[e["titulo"] for e in EXEMPLOS])
def test_exemplos_anotados(exemplo):
    resultado = anotado(exemplo["codigo"], [e for e in exemplo["entradas"] if e])
    json.dumps(resultado)
    passos = resultado["passos"]
    for passo in passos:
        assert set(passo) >= {"efeito", "decisao", "volta", "desfecho_visivel_desde"}
        assert "_decisao_bruta" not in passo
        if passo["decisao"] is not None:
            assert passo["decisao"]["ramo"] in ("corpo", "orelse", "sai", "desconhecido")
            desde = passo["decisao"]["ramo_visivel_desde"]
            assert desde is None or desde > passo["i"]
        assert passo["desfecho_visivel_desde"] is None or passo["desfecho_visivel_desde"] >= passo["i"]
        if passo["efeito"] is not None:
            assert (
                passo["saida"] + passo["efeito"]["saida_nova"] == passos[passo["proximo_no_quadro"]]["saida"]
                or passo["efeito"]["parcial"]
            )
    # Anotar de novo não muda nada.
    copia = json.loads(json.dumps(resultado))
    assert anotar(copia) == resultado


def test_anotar_nao_muda_a_execucao():
    codigo = "import random\nl = [random.randint(1, 9) for _ in range(3)]\nprint(l)\n"
    antes = rastrear(codigo, semente=5)
    depois = anotar(rastrear(codigo, semente=5))
    assert depois["saida"] == antes["saida"]
    assert [p["globais"] for p in depois["passos"]] == [p["globais"] for p in antes["passos"]]


def test_erro_de_sintaxe_nao_quebra():
    resultado = anotado("if True\n    x = 1\n")
    assert resultado["passos"] == []
