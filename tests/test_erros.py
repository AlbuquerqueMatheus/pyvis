import pytest

from pyvis_motor import rastrear


@pytest.mark.parametrize(
    "codigo, tipo, trecho",
    [
        ("print(10 / 0)", "ZeroDivisionError", "dividir por zero"),
        ("l = [1, 2]\nprint(l[5])", "IndexError", "posição"),
        ("'idade: ' + 12", "TypeError", "transforme o número com str"),
        ("'5' - 2", "TypeError", "int() ou float()"),
        ("int('abc')", "ValueError", "inteiros"),
        ("d = {}\nd['x']", "KeyError", "'x'"),
        ("for i in range(3)\n    print(i)", "SyntaxError", "dois-pontos"),
        ("if True:\nprint(1)", "IndentationError", "próxima linha começa mais à direita"),
        ("print('oi)", "SyntaxError", "aspas"),
        ("print((1)", "SyntaxError", "não fechou"),
        ("  x = 1\n", "IndentationError", "espaços sobrando"),
        ("if True:\n    x = 1\n  y = 2\n", "IndentationError", "não bate"),
        ("bonus = 5\nprint(bonu)", "NameError", "Confira se o nome"),
        ("x = 1\nx.dobro()", "AttributeError", "depois do ponto"),
    ],
)
def test_mensagens_amigaveis(codigo, tipo, trecho):
    erro = rastrear(codigo)["erro"]
    assert erro["tipo"] == tipo
    assert trecho in erro["mensagem"] + " " + erro["detalhe"]
    # A caixa de erro mostra a mensagem; o resto fica em 'Mais detalhes'.
    assert len(erro["mensagem"].split()) <= 12, erro["mensagem"]


def test_espaco_sobrando_no_comeco_tem_texto_proprio():
    erro = rastrear("  nome = 'Ana'\nprint(nome)\n")["erro"]
    assert erro["mensagem"] == "Esta linha começa com espaços sobrando."
    assert "dois-pontos" not in erro["mensagem"] + erro["detalhe"]


def test_nome_errado_sugere_o_parecido():
    erro = rastrear("bonus = 5\nprint(bonu)")["erro"]
    assert erro["mensagem"] == "`bonu` ainda não existe. Você quis dizer `bonus`?"


def test_nome_sem_parecido_nao_sugere():
    erro = rastrear("print(xyz)")["erro"]
    assert "Você quis dizer" not in erro["mensagem"]


def test_variavel_local_antes_de_receber_valor():
    codigo = "total = 0\ndef soma(n):\n    total = total + n\n    return total\nsoma(1)\n"
    erro = rastrear(codigo)["erro"]
    assert erro["tipo"] == "UnboundLocalError"
    assert erro["linha"] == 3
    assert erro["mensagem"] == "Dentro da função, `total = ...` cria outra `total`, só da função."
    assert erro["detalhe"] == "Para usar a de fora, passe-a como parâmetro e devolva com return."
    assert "Você quis dizer" not in erro["mensagem"]


def test_nome_que_falta_dentro_de_modulo_importado():
    erro = rastrear("from math import raiz\n")["erro"]
    assert erro["tipo"] == "ImportError"
    assert erro["mensagem"] == "Esse módulo não tem `raiz`."
    assert erro["detalhe"] == "Confira se o nome está escrito certo."


def test_input_sem_resposta_tem_mensagem_amigavel():
    erro = rastrear("a = input()\n")["erro"]
    assert erro["tipo"] == "EOFError"
    assert erro["mensagem"].startswith("O programa pediu mais respostas")
