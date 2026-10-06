from pyvis_motor import rastrear


def valor(passo, nome):
    return passo["globais"][nome]


def test_grava_um_passo_por_linha_e_o_fim():
    resultado = rastrear("x = 1\ny = x + 1\n")
    assert [p["linha"] for p in resultado["passos"]] == [1, 2, 2]
    assert resultado["passos"][-1]["evento"] == "fim"
    assert resultado["erro"] is None


def test_cada_passo_mostra_o_estado_antes_da_linha_rodar():
    passos = rastrear("x = 1\nx = 2\n")["passos"]
    assert passos[0]["globais"] == {}
    assert valor(passos[1], "x") == {"tipo": "int", "valor": "1", "h": valor(passos[1], "x")["h"]}
    assert valor(passos[2], "x")["valor"] == "2"


def test_lista_e_copiada_em_cada_passo():
    passos = rastrear("nums = [1]\nnums.append(2)\nnums.append(3)\n")["passos"]
    tamanhos = [len(valor(p, "nums")["itens"]) for p in passos if "nums" in p["globais"]]
    assert tamanhos == [1, 2, 3]


def test_loop_for_repete_as_linhas():
    passos = rastrear("total = 0\nfor i in range(3):\n    total = total + i\n")["passos"]
    assert [p["linha"] for p in passos] == [1, 2, 3, 2, 3, 2, 3, 2, 2]
    assert valor(passos[-1], "total")["valor"] == "3"


def test_print_aparece_na_saida_do_passo():
    resultado = rastrear("print('oi')\nprint('tchau')\n")
    assert resultado["passos"][1]["saida"] == "oi\n"
    assert resultado["saida"] == "oi\ntchau\n"


def test_input_usa_as_entradas_digitadas_antes():
    resultado = rastrear("nome = input('Nome? ')\nprint('Olá', nome)\n", entradas=["Ana"])
    assert resultado["saida"] == "Nome? Ana\nOlá Ana\n"


def test_input_sem_entrada_vira_erro():
    resultado = rastrear("input()\n")
    assert resultado["erro"]["tipo"] == "EOFError"


def test_loop_infinito_para_no_limite():
    resultado = rastrear("while True:\n    pass\n", limite=50)
    assert resultado["erro"]["tipo"] == "LimiteDePassos"
    assert len(resultado["passos"]) == 51


def test_erro_traz_linha_e_mensagem_em_portugues():
    resultado = rastrear("pontos = 10\nprint(ponto)\n")
    erro = resultado["erro"]
    assert erro["tipo"] == "NameError"
    assert erro["linha"] == 2
    assert "`ponto`" in erro["mensagem"]
    assert resultado["passos"][-1]["evento"] == "linha"


def test_erro_de_sintaxe_nao_executa_nada():
    resultado = rastrear("if True\n    print(1)\n")
    assert resultado["passos"] == []
    assert resultado["erro"]["tipo"] == "SyntaxError"
    assert resultado["erro"]["linha"] == 1


def test_variaveis_de_funcao_aparecem_como_locais():
    passos = rastrear("def dobro(n):\n    r = n * 2\n    return r\nx = dobro(4)\n")["passos"]
    dentro = [p for p in passos if p["funcao"] == "dobro"]
    assert dentro[-1]["locais"]["r"]["valor"] == "8"
    assert "dobro" in passos[-1]["globais"]


def test_try_except_do_aluno_continua_normalmente():
    resultado = rastrear("try:\n    1 / 0\nexcept ZeroDivisionError:\n    x = 1\n")
    assert resultado["erro"] is None
    assert resultado["passos"][-1]["evento"] == "fim"


def test_rastreador_nao_fica_ligado_depois():
    import sys

    rastrear("x = 1\n")
    assert sys.gettrace() is None


# --- Contrato v2: quadros, retorno, semente e limite ---

import json
import random

from pyvis_motor.rastreador import LIMITE_PADRAO, calcular_voltas


def test_resultado_segue_o_contrato_v2():
    resultado = rastrear("x = 1\nprint(x)\n", semente=7)
    assert list(resultado) == ["versao", "semente", "deterministico", "passos", "saida", "erro", "estrutura"]
    assert resultado["versao"] == 2
    assert resultado["semente"] == 7
    assert resultado["deterministico"] is True
    assert [c["tipo"] for c in resultado["estrutura"]["comandos"]] == ["atrib", "print"]
    chaves = ["i", "linha", "comando", "evento", "quadro", "profundidade", "funcao"]
    chaves += ["globais", "locais", "saida", "proximo_no_quadro"]
    for indice, passo in enumerate(resultado["passos"]):
        assert list(passo)[: len(chaves)] == chaves
        assert passo["i"] == indice
    json.dumps(resultado)  # o worker manda o resultado como JSON


def test_limite_padrao_continua_1000_e_aceita_outro():
    assert LIMITE_PADRAO == 1000
    assert len(rastrear("while True:\n    pass\n")["passos"]) == 1001
    assert len(rastrear("while True:\n    pass\n", limite=300)["passos"]) == 301


def test_limite_nao_e_engolido_por_except_exception():
    codigo = "for i in range(100):\n    try:\n        x = i\n    except Exception:\n        pass\n"
    resultado = rastrear(codigo, limite=20)
    assert resultado["erro"]["tipo"] == "LimiteDePassos"


def test_limite_engolido_por_except_vazio_ainda_aparece():
    codigo = "try:\n    for i in range(100):\n        x = i\nexcept:\n    y = 1\n"
    resultado = rastrear(codigo, limite=20)
    assert resultado["erro"]["tipo"] == "LimiteDePassos"
    assert len(resultado["passos"]) == 21


def test_quadro_e_profundidade_de_cada_chamada():
    codigo = "def dobro(n):\n    return n * 2\ndef quadruplo(n):\n    return dobro(dobro(n))\nx = quadruplo(1)\n"
    passos = rastrear(codigo)["passos"]
    assert [(p["linha"], p["quadro"], p["profundidade"]) for p in passos] == [
        (1, 0, 0),
        (3, 0, 0),
        (5, 0, 0),
        (4, 1, 1),
        (2, 2, 2),
        (2, 3, 2),
        (5, 0, 0),  # o fim
    ]


def test_retorno_aparece_no_passo_seguinte_sem_passo_proprio():
    codigo = "def dobro(n):\n    return n * 2\nx = dobro(4)\ny = 0\n"
    passos = rastrear(codigo)["passos"]
    assert [p["linha"] for p in passos] == [1, 3, 2, 4, 4]
    assert passos[3]["retorno"] == {
        "funcao": "dobro",
        "valor": {"tipo": "int", "valor": "8", "h": passos[3]["retorno"]["valor"]["h"]},
        "quadro": 1,
        # O estado no momento do return: a saída até ali e as globais que o último comando mudou.
        "saida_ate": 0,
        "mudancas_globais": {},
        "globais_apagadas": [],
    }
    assert passos[3]["retornos"] == [passos[3]["retorno"]]
    assert sum("retorno" in p for p in passos) == 1


def test_retorno_de_funcao_aninhada_mostra_a_de_fora():
    codigo = "def g(n):\n    return n + 1\ndef f(n):\n    return g(n) * 10\nx = f(1)\n"
    passos = rastrear(codigo)["passos"]
    assert passos[-1]["evento"] == "fim"
    assert passos[-1]["retorno"]["funcao"] == "f"
    assert passos[-1]["retorno"]["valor"]["valor"] == "20"
    # g terminou antes, sem passo no meio: o retorno dele não se perde.
    assert [(r["funcao"], r["valor"]["valor"]) for r in passos[-1]["retornos"]] == [("g", "2"), ("f", "20")]


def test_funcao_que_termina_com_erro_nao_tem_retorno():
    codigo = "def f():\n    return 1 / 0\ntry:\n    f()\nexcept ZeroDivisionError:\n    x = 1\n"
    passos = rastrear(codigo)["passos"]
    assert not any("retorno" in p for p in passos)


def test_proximo_no_quadro_pula_os_passos_da_funcao():
    codigo = "def dobro(n):\n    return n * 2\nx = dobro(4)\ny = x\n"
    passos = rastrear(codigo)["passos"]
    chamada = next(p for p in passos if p["linha"] == 3)
    seguinte = passos[chamada["proximo_no_quadro"]]
    assert seguinte["linha"] == 4 and seguinte["quadro"] == chamada["quadro"]
    assert passos[-1]["proximo_no_quadro"] is None
    for passo in passos:
        if passo["proximo_no_quadro"] is not None:
            assert passos[passo["proximo_no_quadro"]]["quadro"] == passo["quadro"]
            assert passo["proximo_no_quadro"] > passo["i"]


def test_gerador_continua_no_mesmo_quadro():
    codigo = "def conta():\n    yield 1\n    yield 2\nfor v in conta():\n    w = v\n"
    passos = rastrear(codigo)["passos"]
    dentro = [p for p in passos if p["funcao"] == "conta"]
    assert [p["linha"] for p in dentro] == [2, 3]
    assert len({p["quadro"] for p in dentro}) == 1
    assert not any("retorno" in p for p in passos)  # yield não é return


def test_mesma_semente_repete_o_random():
    codigo = "import random\nx = random.randint(1, 1000000)\nprint(x)\n"
    primeira = rastrear(codigo, semente=42)
    assert rastrear(codigo, semente=42)["saida"] == primeira["saida"]
    assert primeira["deterministico"] is True
    sem_semente = rastrear(codigo)
    assert rastrear(codigo, semente=sem_semente["semente"])["saida"] == sem_semente["saida"]


def test_random_do_motor_volta_ao_estado_anterior():
    estado = random.getstate()
    rastrear("import random\nrandom.random()\n", semente=1)
    assert random.getstate() == estado


def test_relogio_deixa_o_programa_nao_deterministico():
    for codigo in ("import time\n", "from datetime import date\n", "import secrets\n", "import os, time\n"):
        assert rastrear(codigo)["deterministico"] is False, codigo
    assert rastrear("import random\nimport math\n")["deterministico"] is True


def test_decisao_bruta_nos_cabecalhos_de_if_elif_e_while():
    codigo = "n = 5\nif n > 10:\n    a = 1\nelif n > 3:\n    a = 2\nwhile n > 4:\n    n = n - 1\n"
    passos = rastrear(codigo)["passos"]
    brutas = [(p["linha"], p["_decisao_bruta"]) for p in passos if "_decisao_bruta" in p]
    decisoes = [(linha, bruta["texto"], bruta["valor"]) for linha, bruta in brutas]
    assert decisoes == [(2, "5 > 10", False), (4, "5 > 3", True), (6, "5 > 4", True), (6, "4 > 4", False)]
    assert all("_decisao_bruta" not in p for p in passos if p["linha"] in (1, 3, 5, 7))


def test_erro_de_sintaxe_devolve_estrutura_vazia():
    resultado = rastrear("if True\n    print(1)\n", semente=3)
    assert resultado["estrutura"] == {"comandos": []}
    assert resultado["semente"] == 3
    assert resultado["versao"] == 2


def test_nomes_internos_de_compreensao_nao_aparecem():
    codigo = "def f(l):\n    q = [n * 2 for n in l]\n    return q\nr = f([1, 2])\n"
    passos = rastrear(codigo)["passos"]
    for passo in passos:
        assert not any(not nome.isidentifier() for nome in passo["locais"])
        assert "n" not in passo["locais"]


def test_corpo_de_classe_nao_vira_retorno():
    codigo = "class Ponto:\n    x = 1\np = Ponto()\n"
    passos = rastrear(codigo)["passos"]
    assert not any("retorno" in p for p in passos)
    assert [p["funcao"] for p in passos] == [None, "Ponto", None, None]


def test_voltas_de_um_for():
    codigo = "total = 0\nfor n in range(1, 4):\n    total = total + n\nprint(total)\n"
    resultado = rastrear(codigo)
    voltas = calcular_voltas(resultado)
    passos = resultado["passos"]
    linhas = [(p["linha"], v and v["n"], v and v["saindo"]) for p, v in zip(passos, voltas)]
    assert linhas == [
        (1, None, None),
        (2, 1, False),
        (3, 1, False),
        (2, 2, False),
        (3, 2, False),
        (2, 3, False),
        (3, 3, False),
        (2, 3, True),
        (4, None, None),
        (4, None, None),
    ]
    saida_do_laco = next(p["i"] for p in passos if p["linha"] == 4)
    for volta in filter(None, voltas):
        assert volta["total"] == 3
        assert volta["total_visivel_desde"] == saida_do_laco


def test_voltas_recomecam_a_cada_entrada_no_laco():
    codigo = "for i in range(2):\n    for j in range(3):\n        x = j\n"
    resultado = rastrear(codigo)
    voltas = calcular_voltas(resultado)
    internos = [v["n"] for p, v in zip(resultado["passos"], voltas) if p["linha"] == 3]
    assert internos == [1, 2, 3, 1, 2, 3]
    assert {v["total"] for v in voltas if v and v["laco"] == 1} == {3}


def test_laco_que_nao_termina_fica_sem_total():
    resultado = rastrear("while True:\n    x = 1\n", limite=30)
    voltas = calcular_voltas(resultado)
    assert all(v["total"] is None and v["total_visivel_desde"] is None for v in voltas)


def test_return_dentro_do_laco_encerra_as_voltas():
    codigo = "def acha(l):\n    for x in l:\n        if x > 1:\n            return x\nr = acha([1, 2, 3])\n"
    resultado = rastrear(codigo)
    voltas = calcular_voltas(resultado)
    do_laco = [v for v in voltas if v]
    assert do_laco and all(v["total"] == 2 for v in do_laco)
    assert do_laco[0]["total_visivel_desde"] == len(resultado["passos"]) - 1  # o passo que recebe o retorno


# --- valores.py: resumo curto `h` para a interface comparar ---

from pyvis_motor.valores import converter, variaveis_visiveis


def test_resumo_h_e_estavel_e_curto():
    # O mesmo número em qualquer Python (inclusive no Pyodide): é um crc32, não o hash().
    assert converter(1)["h"] == "ae767cde"
    assert converter("Ana")["h"] == converter("Ana")["h"]
    assert len(converter([1, 2])["h"]) == 8


def test_resumo_h_muda_quando_o_valor_muda():
    assert converter([1, 2])["h"] != converter([1, 3])["h"]
    assert converter([1, 2])["h"] != converter((1, 2))["h"]
    assert converter(1)["h"] != converter(True)["h"]
    assert converter({"a": 1})["h"] != converter({"a": 2})["h"]
    assert converter(list(range(60)))["h"] != converter(list(range(50)))["h"]  # o cortado conta


def test_cada_item_tem_seu_resumo():
    valor = converter({"nomes": ["Ana", "Bia"]})
    chave, lista = valor["pares"][0]
    assert all("h" in item for item in lista["itens"]) and "h" in chave
    assert converter(["Ana", "Bia"])["h"] == lista["h"]


def test_inteiro_enorme_nao_vira_erro_do_aluno():
    # Acima de 4300 dígitos o repr levanta ValueError: o programa é válido e tem de rodar.
    resultado = rastrear("x = 2 ** 20000\nresto = x % 7\nprint(resto)\n")
    assert resultado["erro"] is None and resultado["saida"] == "4\n"
    x = resultado["passos"][1]["globais"]["x"]
    assert x["valor"] == "um número com 6021 dígitos" and x["cortado"] is True
    assert converter(2**20000)["h"] != converter(2**20000 + 1)["h"]
    assert converter(10**99)["valor"] == repr(10**99)  # 100 dígitos ainda aparecem inteiros
    assert converter(10**100)["valor"] == "um número com 101 dígitos"


def test_texto_longo_mostra_o_comeco_e_o_resumo_e_do_texto_inteiro():
    texto = "ab" * 500
    valor = converter(texto)
    assert valor["cortado"] is True
    assert valor["valor"] == repr(texto[:200] + "…")
    assert valor["h"] == converter(texto)["h"]
    # Muda no fim (fora do que aparece): a caixinha ainda sabe que mudou.
    assert converter(texto + "c")["h"] != valor["h"]
    assert "cortado" not in converter("ab" * 100)


def test_texto_enorme_nao_explode_o_rastro():
    codigo = 'texto = "ab" * 500000\nfor i in range(100):\n    n = i\nprint(len(texto))\n'
    import json

    assert len(json.dumps(rastrear(codigo))) < 1_000_000


def test_repr_quebrado_do_aluno_nao_derruba_o_rastreador():
    codigo = "class Chato:\n    def __repr__(self):\n        raise ValueError()\nc = Chato()\nx = 1\n"
    resultado = rastrear(codigo)
    assert resultado["erro"] is None
    assert resultado["passos"][-1]["globais"]["c"]["valor"] == "<Chato>"


def test_nomes_que_nao_sao_identificadores_ficam_de_fora():
    assert variaveis_visiveis({".0": 1, "x": 2, "__name__": "m", 3: 4}) == {"x": converter(2)}


def test_erro_dentro_de_compreensao_nao_vira_retorno_nem_fim():
    codigo = "def f(l):\n    return [1 / x for x in l]\ntry:\n    f([0])\nexcept ZeroDivisionError:\n    y = 1\n"
    passos = rastrear(codigo)["passos"]
    assert not any("retorno" in p for p in passos)
    resultado = rastrear("l = [1, 0]\nq = [1 / x for x in l]\n")
    assert resultado["erro"]["tipo"] == "ZeroDivisionError"
    assert [p["evento"] for p in resultado["passos"]] == ["linha", "linha"]


def test_exit_encerra_sem_erro_e_sem_fim():
    resultado = rastrear("def f():\n    exit()\nf()\nprint(1)\n")
    assert resultado["erro"] is None
    assert resultado["saida"] == ""
    assert resultado["passos"][-1]["evento"] == "linha"
