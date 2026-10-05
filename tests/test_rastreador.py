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
    assert valor(passos[1], "x") == {"tipo": "int", "valor": "1"}
    assert valor(passos[2], "x") == {"tipo": "int", "valor": "2"}


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
