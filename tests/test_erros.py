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
        ("if True:\nprint(1)", "IndentationError", "espaçamento"),
        ("print('oi)", "SyntaxError", "aspas"),
        ("print((1)", "SyntaxError", "não foi fechado"),
    ],
)
def test_mensagens_amigaveis(codigo, tipo, trecho):
    erro = rastrear(codigo)["erro"]
    assert erro["tipo"] == tipo
    assert trecho in erro["mensagem"]


def test_nome_errado_sugere_o_parecido():
    erro = rastrear("bonus = 5\nprint(bonu)")["erro"]
    assert erro["mensagem"].endswith("Você quis dizer `bonus`?")


def test_nome_sem_parecido_nao_sugere():
    erro = rastrear("print(xyz)")["erro"]
    assert "Você quis dizer" not in erro["mensagem"]
