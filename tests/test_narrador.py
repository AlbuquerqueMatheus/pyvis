"""Narrador: as frases curta e longa de cada passo e a leitura de cada comando.

As fotografias (snapshots) abaixo são as frases completas, com tudo revelado.
O que aparece com um palpite pendente é testado em test_revelacao_basica.py.
"""

import json
import re
from pathlib import Path

import pytest

from pyvis_motor import analisar, rastrear
from pyvis_motor.erros import NOMES_DE_TIPO
from pyvis_motor.narrador import LIMITE_PALAVRAS, contar_palavras, ler_comando, narrar, narrar_resultado
from test_estrutura import EXEMPLOS

CORPUS = Path(__file__).resolve().parent / "corpus"
CAMPOS = {
    "efeito",
    "decisao.texto",
    "decisao.valor",
    "decisao.ramo",
    "volta.n",
    "volta.total",
    "volta.saindo",
    "leitura.traduzida",
    "retorno",
}
PROIBIDAS = re.compile(r"apost|\bC\d{2}\b", re.IGNORECASE)


def narrado(codigo, entradas=(), **opcoes):
    resultado = rastrear(codigo, list(entradas), semente=1, **opcoes)
    return narrar_resultado(resultado, codigo)


def curtas(resultado):
    return [passo["narracao"]["curta"] for passo in resultado["passos"]]


def longas(resultado):
    return [passo["narracao"]["longa"] for passo in resultado["passos"]]


def ler_corpus():
    """Os programas de tests/corpus, com as entradas do cabeçalho '# @entradas: [...]'."""
    if not CORPUS.is_dir():
        return []
    programas = []
    for arquivo in sorted(CORPUS.glob("*.py")):
        codigo = arquivo.read_text(encoding="utf-8")
        achado = re.search(r"^# @entradas:\s*(\[.*\])\s*$", codigo, re.MULTILINE)
        programas.append((arquivo.name, codigo, json.loads(achado.group(1)) if achado else []))
    return programas


CORPUS_LIDO = ler_corpus()


# Os 8 exemplos do site (o 7, na versão do robô, que não pede o nome do aluno).
EXEMPLOS_FIXOS = {
    "variaveis": (
        'nome = "Ana"\nidade = 12\nidade = idade + 1\nprint(nome, "vai fazer", idade, "anos")\n',
        [],
        [
            'nome recebe "Ana": variável nova.',
            "idade recebe 12: variável nova.",
            "idade recebe idade + 1: vai valer 13.",
            "print escreve na tela: “Ana vai fazer 13 anos”.",
            "O programa terminou.",
        ],
    ),
    "if": (
        'nota = 7\nif nota >= 6:\n    resultado = "aprovado"\nelse:\n    resultado = "recuperação"\nprint("Situação:", resultado)\n',
        [],
        [
            "nota recebe 7: variável nova.",
            "nota >= 6? 7 >= 6, Verdadeiro: entra no if.",
            'resultado recebe "aprovado": variável nova.',
            "print escreve na tela: “Situação: aprovado”.",
            "O programa terminou.",
        ],
    ),
    "for": (
        'total = 0\nfor numero in range(1, 5):\n    total = total + numero\nprint("A soma é", total)\n',
        [],
        [
            "total recebe 0: variável nova.",
            "Para cada numero de 1 até 4. Volta 1: numero recebe 1.",
            "total recebe total + numero: vai valer 1.",
            "Para cada numero de 1 até 4. Volta 2: numero recebe 2.",
            "total recebe total + numero: vai valer 3.",
            "Para cada numero de 1 até 4. Volta 3: numero recebe 3.",
            "total recebe total + numero: vai valer 6.",
            "Para cada numero de 1 até 4. Volta 4: numero recebe 4.",
            "total recebe total + numero: vai valer 10.",
            "Para cada numero de 1 até 4. Acabou: sai do laço.",
            "print escreve na tela: “A soma é 10”.",
            "O programa terminou.",
        ],
    ),
    "while": (
        'energia = 3\nwhile energia > 0:\n    print("Energia:", energia)\n    energia = energia - 1\n'
        'print("O robô descansou!")\n',
        [],
        [
            "energia recebe 3: variável nova.",
            "energia > 0? 3 > 0, Verdadeiro: começa a volta 1.",
            "print escreve na tela: “Energia: 3”.",
            "energia recebe energia - 1: vai valer 2.",
            "energia > 0? 2 > 0, Verdadeiro: começa a volta 2.",
            "print escreve na tela: “Energia: 2”.",
            "energia recebe energia - 1: vai valer 1.",
            "energia > 0? 1 > 0, Verdadeiro: começa a volta 3.",
            "print escreve na tela: “Energia: 1”.",
            "energia recebe energia - 1: vai valer 0.",
            "energia > 0? 0 > 0, Falso: sai do laço.",
            "print escreve na tela: “O robô descansou!”.",
            "O programa terminou.",
        ],
    ),
    "listas": (
        'frutas = ["maçã", "banana"]\nfrutas.append("uva")\nfrutas[0] = "manga"\nfor fruta in frutas:\n    print("Eu gosto de", fruta)\n',
        [],
        [
            'frutas recebe ["maçã", "banana"]: variável nova.',
            'Coloca "uva" no fim de frutas: frutas vai ficar ["maçã", "banana", "uva"].',
            'frutas[0] recebe "manga": frutas vai ficar ["manga", "banana", "uva"].',
            'Para cada fruta em frutas. Volta 1: fruta recebe "manga".',
            "print escreve na tela: “Eu gosto de manga”.",
            'Para cada fruta em frutas. Volta 2: fruta recebe "banana".',
            "print escreve na tela: “Eu gosto de banana”.",
            'Para cada fruta em frutas. Volta 3: fruta recebe "uva".',
            "print escreve na tela: “Eu gosto de uva”.",
            "Para cada fruta em frutas. Acabou: sai do laço.",
            "O programa terminou.",
        ],
    ),
    "maior": (
        'numeros = [4, 9, 2, 7]\nmaior = numeros[0]\nfor n in numeros:\n    if n > maior:\n        maior = n\nprint("O maior é", maior)\n',
        [],
        [
            "numeros recebe [4, 9, 2, 7]: variável nova.",
            "maior recebe numeros[0]: vai valer 4.",
            "Para cada n em numeros. Volta 1: n recebe 4.",
            "n > maior? 4 > 4, Falso: não entra no if.",
            "Para cada n em numeros. Volta 2: n recebe 9.",
            "n > maior? 9 > 4, Verdadeiro: entra no if.",
            "maior recebe n: vai valer 9.",
            "Para cada n em numeros. Volta 3: n recebe 2.",
            "n > maior? 2 > 9, Falso: não entra no if.",
            "Para cada n em numeros. Volta 4: n recebe 7.",
            "n > maior? 7 > 9, Falso: não entra no if.",
            "Para cada n em numeros. Acabou: sai do laço.",
            "print escreve na tela: “O maior é 9”.",
            "O programa terminou.",
        ],
    ),
    "input": (
        'nome = input("Qual é o nome do seu robô? ")\nidade = int(input("Quantos anos o robô tem? "))\nprint("Olá,", nome)\nprint("Daqui a 5 anos ele terá", idade + 5)\n',
        ["Bia", "11"],
        [
            'input devolve texto para nome: chegou "Bia".',
            "input devolve texto, int vira número inteiro: idade vai valer 11.",
            "print escreve na tela: “Olá, Bia”.",
            "print escreve na tela: “Daqui a 5 anos ele terá 16”.",
            "O programa terminou.",
        ],
    ),
    "erro": (
        "pontos = 10\nbonus = 5\ntotal = pontos + bonu\nprint(total)\n",
        [],
        [
            "pontos recebe 10: variável nova.",
            "bonus recebe 5: variável nova.",
            "total recebe pontos + bonu: aqui dá erro.",
        ],
    ),
}

# Casos de borda: um por construção ou situação difícil.
CASOS = {
    "funcao": (
        "def dobro(n):\n    r = n * 2\n    return r\nx = dobro(4)\nprint(dobro(x))\n",
        [],
        [
            "Cria a função dobro. Ela só roda quando for chamada.",
            "x recebe dobro(4): vai valer 8.",
            "r recebe n * 2: vai valer 8.",
            "dobro devolve r, que vale 8.",
            "print escreve na tela: “16”.",
            "r recebe n * 2: vai valer 16.",
            "dobro devolve r, que vale 16.",
            "O programa terminou.",
        ],
    ),
    "chamada_na_condicao": (
        "def dobro(n):\n    return n * 2\nx = 3\nif dobro(x) > 5:\n    print('grande')\n",
        [],
        [
            "Cria a função dobro. Ela só roda quando for chamada.",
            "x recebe 3: variável nova.",
            "dobro(x) > 5? Verdadeiro: entra no if.",
            "dobro devolve n * 2, que vale 6.",
            "print escreve na tela: “grande”.",
            "O programa terminou.",
        ],
    ),
    "elif": (
        "n = 1\nif n > 10:\n    a = 1\nelif n > 3:\n    a = 2\nelse:\n    a = 3\n",
        [],
        [
            "n recebe 1: variável nova.",
            "n > 10? 1 > 10, Falso: testa o elif.",
            "n > 3? 1 > 3, Falso: vai para o else.",
            "a recebe 3: variável nova.",
            "O programa terminou.",
        ],
    ),
    "curto_circuito": (
        "l = [1, 2]\ni = 2\nif i < len(l) and l[i] > 0:\n    x = 1\n",
        [],
        [
            "l recebe [1, 2]: variável nova.",
            "i recebe 2: variável nova.",
            "2 < 2 and…, Falso: não entra no if.",
            "O programa terminou.",
        ],
    ),
    "while_else": (
        "x = 0\nwhile x < 2:\n    x += 1\nelse:\n    print('fim')\n",
        [],
        [
            "x recebe 0: variável nova.",
            "x < 2? 0 < 2, Verdadeiro: começa a volta 1.",
            "x recebe x + 1: vai valer 1.",
            "x < 2? 1 < 2, Verdadeiro: começa a volta 2.",
            "x recebe x + 1: vai valer 2.",
            "x < 2? 2 < 2, Falso: vai para o else.",
            "print escreve na tela: “fim”.",
            "O programa terminou.",
        ],
    ),
    "break_continue": (
        "for i in range(10):\n    if i == 1:\n        break\n    continue\n",
        [],
        [
            "Para cada i de 0 até 9. Volta 1: i recebe 0.",
            "i == 1? 0 == 1, Falso: não entra no if.",
            "continue: pula para a próxima volta.",
            "Para cada i de 0 até 9. Volta 2: i recebe 1.",
            "i == 1? 1 == 1, Verdadeiro: entra no if.",
            "break: sai do laço agora.",
            "O programa terminou.",
        ],
    ),
    "try": (
        "try:\n    n = int(input())\nexcept ValueError:\n    n = 0\n",
        ["abc"],
        [
            "try: tenta rodar o bloco.",
            "input devolve texto, int vira número inteiro: aqui dá erro.",
            "Deu erro no try: roda o except.",
            "n recebe 0: variável nova.",
            "O programa terminou.",
        ],
    ),
    "corpo_na_linha": (
        "x = 5\nif x > 3: y = 1\nelse: y = 2\n",
        [],
        [
            "x recebe 5: variável nova.",
            "x > 3? 5 > 3, Verdadeiro: entra no if.",
            "O programa terminou.",
        ],
    ),
    "alvos": (
        "a, b = 1, 2\na, b = b, a\nc = d = 0\nl = [1, 2]\nl[0] += 5\nd = {'a': 1}\nd['b'] = 2\n",
        [],
        [
            "a, b recebem 1, 2: a vale 1 e b vale 2.",
            "a, b recebem b, a: a vale 2 e b vale 1.",
            "c e d recebem 0: c vale 0 e d vale 0.",
            "l recebe [1, 2]: variável nova.",
            "l[0] recebe l[0] + 5: l vai ficar [6, 2].",
            "d recebe {'a': 1}: antes valia 0.",
            'd[\'b\'] recebe 2: d vai ficar {"a": 1, "b": 2}.',
            "O programa terminou.",
        ],
    ),
    "print": (
        "print()\nprint('a', end='')\nprint('um\\ndois')\n",
        [],
        [
            "print escreve na tela: uma linha vazia.",
            "print escreve na tela: “a”.",
            "print escreve na tela: “um / dois”.",
            "O programa terminou.",
        ],
    ),
    "outros": (
        "import random\nclass P:\n    x = 1\np = P()\ndel p\npass\n",
        [],
        [
            "Importa o módulo random.",
            "Cria a classe P.",
            "x recebe 1.",
            "p recebe P(): vai valer um objeto P.",
            "Apaga p.",
            "pass: não faz nada.",
            "O programa terminou.",
        ],
    ),
    "global": (
        "t = 0\ndef soma():\n    global t\n    t = t + 1\nsoma()\n",
        [],
        [
            "t recebe 0: variável nova.",
            "Cria a função soma. Ela só roda quando for chamada.",
            "Chama soma(): t vai valer 1.",
            "t recebe t + 1: vai valer 1.",
            "O programa terminou.",
        ],
    ),
    "gerador": (
        "def conta():\n    yield 1\nfor v in conta():\n    w = v\n",
        [],
        [
            "Cria a função conta. Ela só roda quando for chamada.",
            "Para cada v em conta(). Volta 1: v recebe 1.",
            "yield entrega 1 e pausa a função.",
            "w recebe v: vai valer 1.",
            "Para cada v em conta(). Acabou: sai do laço.",
            "O programa terminou.",
        ],
    ),
    "yield_from": (
        "def g():\n    yield from [1, 2]\nfor x in g():\n    pass\n",
        [],
        [
            "Cria a função g. Ela só roda quando for chamada.",
            "Para cada x em g(). Volta 1: x recebe 1.",
            "yield from entrega os itens de [1, 2], um por vez.",
            "pass: não faz nada.",
            "Para cada x em g(). Volta 2: x recebe 2.",
            "pass: não faz nada.",
            "Para cada x em g(). Acabou: sai do laço.",
            "O programa terminou.",
        ],
    ),
    "ranges": (
        "n = 2\nfor i in range(n):\n    pass\nfor k in range(10, 0, -5):\n    pass\n",
        [],
        [
            "n recebe 2: variável nova.",
            "Para cada i de 0 até n - 1. i recebe 0.",
            "pass: não faz nada.",
            "Para cada i de 0 até n - 1. i recebe 1.",
            "pass: não faz nada.",
            "Para cada i de 0 até n - 1. Sai do laço.",
            "Para cada k em range(10, 0, -5). Volta 1: k recebe 10.",
            "pass: não faz nada.",
            "Para cada k em range(10, 0, -5). Volta 2: k recebe 5.",
            "pass: não faz nada.",
            "Para cada k em range(10, 0, -5). Acabou: sai do laço.",
            "O programa terminou.",
        ],
    ),
    "limite": (
        "x = 0\nwhile True:\n    x += 1\n",
        [],
        [
            "x recebe 0: variável nova.",
            "while True repete até um break. Verdadeiro: começa a volta 1.",
            "x recebe x + 1: vai valer 1.",
            "while True repete até um break. Verdadeiro: começa a volta 2.",
            "x recebe x + 1: vai valer 2.",
            "while True repete até um break. O programa parou aqui.",
        ],
    ),
    "expressoes": (
        "s = 'abc'\nt = s.upper()\nlen(s)\ns + 'd'\n",
        [],
        [
            "s recebe 'abc': variável nova.",
            't recebe s.upper(): vai valer "ABC".',
            "Roda len(s): nada muda.",
            "Calcula s + 'd', mas não guarda o resultado.",
            "O programa terminou.",
        ],
    ),
    "erro_tratado_na_funcao": (
        "def f():\n    return 1 / 0\ntry:\n    f()\nexcept ZeroDivisionError:\n    z = 1\n",
        [],
        [
            "Cria a função f. Ela só roda quando for chamada.",
            "try: tenta rodar o bloco.",
            "Chama f(): aqui dá erro.",
            "f devolve 1 / 0: aqui dá erro.",
            "Deu erro no try: roda o except.",
            "z recebe 1: variável nova.",
            "O programa terminou.",
        ],
    ),
    "exit": (
        "x = 1\nexit()\n",
        [],
        [
            "x recebe 1: variável nova.",
            "exit() encerra o programa aqui.",
        ],
    ),
}


# --- Fotografias das frases curtas ---


@pytest.mark.parametrize("nome", list(EXEMPLOS_FIXOS))
def test_curtas_dos_exemplos(nome):
    codigo, entradas, esperado = EXEMPLOS_FIXOS[nome]
    assert curtas(narrado(codigo, entradas)) == esperado


@pytest.mark.parametrize("nome", list(CASOS))
def test_curtas_dos_casos_de_borda(nome):
    codigo, entradas, esperado = CASOS[nome]
    limite = 5 if nome == "limite" else 1000
    assert curtas(narrado(codigo, entradas, limite=limite)) == esperado


# --- Fotografias das frases longas ---


def test_longas_do_if():
    codigo, entradas, _ = EXEMPLOS_FIXOS["if"]
    assert longas(narrado(codigo, entradas)) == [
        "O Python guarda 7 em nota. nota é uma variável nova e vale 7 (número inteiro).",
        "O if testa nota >= 6. Com os valores de agora: 7 >= 6. Deu Verdadeiro, então o bloco do if roda.",
        'O Python guarda "aprovado" em resultado. resultado é uma variável nova e vale "aprovado" (texto).',
        "print escreve na tela o que está entre os parênteses. Os valores aparecem separados por um espaço. "
        'Com os valores de agora: print("Situação:", "aprovado"). Aparece: “Situação: aprovado”.',
        "Não há mais comandos para rodar: o programa terminou.",
    ]


def test_longas_do_for():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    frases = longas(narrado(codigo, entradas))
    assert frases[1] == (
        "O for pega um valor de cada vez, de 1 até 4, e guarda em numero. "
        "Volta 1: numero passa a valer 1. Ao todo, o laço dá 4 voltas."
    )
    assert frases[6] == (
        "O Python calcula total + numero e guarda o resultado em total. Com os valores de agora: 3 + 3. "
        "total passa a valer 6 (número inteiro). O valor antigo, 3, sai: uma variável guarda um valor só."
    )
    assert frases[9] == (
        "O for pega um valor de cada vez, de 1 até 4, e guarda em numero. "
        "Não há mais valores: o laço termina e o programa segue depois dele. Ao todo, o laço dá 4 voltas."
    )


def test_longas_da_funcao():
    codigo, entradas, _ = CASOS["funcao"]
    assert longas(narrado(codigo, entradas)) == [
        "O Python guarda a função dobro(n), mas ainda não roda o que está dentro dela. "
        "Isso só acontece quando dobro for chamada.",
        "O Python calcula dobro(4) e guarda o resultado em x. Antes, o Python roda dobro para saber o valor. "
        "x é uma variável nova e vale 8 (número inteiro).",
        "O Python calcula n * 2 e guarda o resultado em r. Com os valores de agora: 4 * 2. "
        "r é uma variável nova e vale 8 (número inteiro).",
        "return termina a função dobro e devolve r para quem chamou. Com os valores de agora: 8. O valor devolvido é 8.",
        "dobro devolveu 8. print escreve na tela o que está entre os parênteses. "
        "Com os valores de agora: print(dobro(8)). Antes, o Python roda dobro. Aparece: “16”.",
        "O Python calcula n * 2 e guarda o resultado em r. Com os valores de agora: 8 * 2. "
        "r é uma variável nova e vale 16 (número inteiro).",
        "return termina a função dobro e devolve r para quem chamou. Com os valores de agora: 16. O valor devolvido é 16.",
        "dobro devolveu 16. Não há mais comandos para rodar: o programa terminou.",
    ]


def test_longas_de_input_e_posicao():
    codigo, entradas, _ = EXEMPLOS_FIXOS["input"]
    frases = longas(narrado(codigo, entradas))
    assert frases[0] == 'O input lê o que foi digitado. Ele sempre devolve texto. Chegou "Bia", que vai para nome.'
    assert frases[1] == (
        "O input lê o que foi digitado. Ele devolve texto, e int transforma esse texto em número inteiro. "
        "idade é uma variável nova e vale 11 (número inteiro)."
    )
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    assert longas(narrado(codigo, entradas))[1] == (
        "O Python calcula numeros[0] e guarda o resultado em maior. numeros[0] é o item na posição 0: "
        "a primeira posição é a 0. maior é uma variável nova e vale 4 (número inteiro)."
    )


def test_longas_de_curto_circuito_e_erro():
    codigo, entradas, _ = CASOS["curto_circuito"]
    assert longas(narrado(codigo, entradas))[2] == (
        "O if testa i < len(l) and l[i] > 0. Com os valores de agora: 2 < 2 and l[i] > 0. "
        "O Python nem calculou l[i] > 0: o resultado já estava decidido. "
        "Deu Falso, então o Python pula o bloco do if."
    )
    codigo, entradas, _ = EXEMPLOS_FIXOS["erro"]
    assert longas(narrado(codigo, entradas))[2] == (
        "O Python calcula pontos + bonu e guarda o resultado em total. Com os valores de agora: 10 + bonu. "
        "Aqui acontece um erro, e o programa para."
    )


def test_longa_usa_os_nomes_de_tipo_de_erros():
    resultado = narrado("x = 5\nnome = 'Ana'\n")
    assert f"({NOMES_DE_TIPO['int']})" in resultado["passos"][0]["narracao"]["longa"]
    assert f"({NOMES_DE_TIPO['str']})" in resultado["passos"][1]["narracao"]["longa"]


def test_texto_com_espaco_e_input_dentro_do_print():
    codigo = 'texto = ""\nfor c in range(2):\n    texto = texto + str(c * 10) + " "\nprint(input("Nome? "))\n'
    frases = curtas(narrado(codigo, ["Bia"]))
    assert frases[2] == 'texto recebe texto + str(c * 10)…: vai valer "0 ".'
    # O input também escreve na tela: a pergunta e o que foi digitado.
    assert frases[6] == "input e print escrevem na tela: “Nome? Bia / Bia”."


# --- Leitura dos comandos ---

# (código, índice do comando, literal, traduzida ou None quando é igual à literal)
LEITURAS = [
    ("x = 5\n", 0, "x recebe 5", None),
    ("a, b = 1, 2\n", 0, "a, b recebem 1, 2", None),
    ("c = d = 0\n", 0, "c e d recebem 0", None),
    ("x: int = 3\n", 0, "x recebe 3", None),
    ("x += 1\n", 0, "x recebe x + 1", None),
    ("x -= a + b\n", 0, "x recebe x - (a + b)", None),
    ("x += a * b\n", 0, "x recebe x + a * b", None),
    ("if x > 1:\n    pass\nelif x < 0:\n    pass\n", 0, "se x > 1", None),
    ("if x > 1:\n    pass\nelif x < 0:\n    pass\n", 2, "senão, se x < 0", None),
    ("while x < 3:\n    break\n", 0, "enquanto x < 3", None),
    ("while x < 3:\n    break\n", 1, "sai do laço", None),
    ("for i in x:\n    continue\n", 1, "pula para a próxima volta", None),
    ("for i in range(1, 5):\n    pass\n", 0, "para cada i em range(1, 5)", "para cada i de 1 até 4"),
    ("for i in range(3):\n    pass\n", 0, "para cada i em range(3)", "para cada i de 0 até 2"),
    ("for i in range(0, 10, 2):\n    pass\n", 0, "para cada i em range(0, 10, 2)", "para cada i de 0 até 8, de 2 em 2"),
    (
        "for i in range(10, 0, -5):\n    pass\n",
        0,
        "para cada i em range(10, 0, -5)",
        "para cada i de 10 até 5, descendo de 5 em 5",
    ),
    ("for i in range(n):\n    pass\n", 0, "para cada i em range(n)", "para cada i de 0 até n - 1"),
    ("for i in range(1, n + 1):\n    pass\n", 0, "para cada i em range(1, n + 1)", "para cada i de 1 até n"),
    ("for i in range(len(s)):\n    pass\n", 0, "para cada i em range(len(s))", "para cada i de 0 até len(s) - 1"),
    ("for i in range(0):\n    pass\n", 0, "para cada i em range(0)", None),
    ("for i in range(a, b, 2):\n    pass\n", 0, "para cada i em range(a, b, 2)", None),
    ("for c in 'abc':\n    pass\n", 0, "para cada c em 'abc'", None),
    ("print('oi', x)\n", 0, "mostra na tela 'oi', x", None),
    ("print()\n", 0, "mostra uma linha vazia na tela", None),
    ("print('a', end='')\n", 0, "mostra na tela 'a', end=''", None),
    ("len(x)\n", 0, "chama len(x)", None),
    ("x + 1\n", 0, "calcula x + 1", None),
    ("def f(a, b=2):\n    return a\n", 0, "cria a função f(a, b=2)", None),
    ("def f(a, b=2):\n    return a\n", 1, "devolve a", None),
    ("def f():\n    return\n", 1, "sai da função", None),
    ("import math, random\n", 0, "importa math, random", None),
    ("from math import sqrt\n", 0, "importa sqrt de math", None),
    ("class P:\n    pass\n", 0, "cria a classe P", None),
    ("try:\n    pass\nexcept ValueError:\n    pass\n", 0, "tenta rodar o bloco", None),
    ("try:\n    pass\nexcept ValueError:\n    pass\n", 2, "se deu erro no try, roda este bloco", None),
    ("del x, y[0]\n", 0, "apaga x, y[0]", None),
    ("assert x > 0\n", 0, "confere se x > 0", None),
    ("with open('a') as f:\n    pass\n", 0, "with open('a') as f", None),
]


@pytest.mark.parametrize("codigo, indice, literal, traduzida", LEITURAS)
def test_leitura_do_comando(codigo, indice, literal, traduzida):
    comando = analisar(codigo)["comandos"][indice]
    assert ler_comando(comando, codigo) == {
        "literal": literal,
        "traduzida": traduzida or literal,
        "traduzida_depende_de": [],
    }


def test_global_e_raise_tem_leitura():
    codigo = "def f():\n    global t\n    raise ValueError\n"
    comandos = analisar(codigo)["comandos"]
    assert ler_comando(comandos[1], codigo)["literal"] == "usa a variável de fora t"
    assert ler_comando(comandos[2], codigo)["literal"] == "levanta um erro"


@pytest.mark.parametrize("nome", list(EXEMPLOS_FIXOS))
def test_narrar_resultado_grava_a_leitura_de_cada_comando(nome):
    codigo, entradas, _ = EXEMPLOS_FIXOS[nome]
    resultado = narrado(codigo, entradas)
    for comando in resultado["estrutura"]["comandos"]:
        assert comando["leitura"] == ler_comando(comando, codigo)


def test_leitura_em_varias_linhas():
    codigo = (
        "lista = [\n    1,\n    2,\n]\n"
        "total = (len(lista) +\n         sum(lista))\n"
        "y = 1 + \\\n    2\n"
        "x = (1 +  # um comentário\n     2)\n"
        "s = '''a\nb'''\n"
        "print(lista,\n      total)\n"
    )
    resultado = narrado(codigo)
    assert [c["leitura"]["literal"] for c in resultado["estrutura"]["comandos"]] == [
        "lista recebe [1, 2,]",
        "total recebe len(lista) + sum(lista)",
        "y recebe 1 + 2",
        "x recebe 1 + 2",
        "s recebe 'a\\nb'",
        "mostra na tela lista, total",
    ]
    assert curtas(resultado)[:2] == [
        "lista recebe [1, 2,]: variável nova.",
        "total recebe len(lista) + sum(lista): vai valer 5.",
    ]


def test_acentos_no_codigo():
    # As colunas da AST contam bytes: um acento antes do trecho não pode deslocá-lo.
    codigo = 'preço = 5\nmédia = preço * 2\nif média > preço: print("ótimo")\nnão = ["ç", média]\n'
    assert curtas(narrado(codigo)) == [
        "preço recebe 5: variável nova.",
        "média recebe preço * 2: vai valer 10.",
        "média > preço? 10 > 5, Verdadeiro: entra no if.",
        'não recebe ["ç", média]: vai ficar ["ç", 10].',
        "O programa terminou.",
    ]
    assert "Com os valores de agora: 5 * 2." in narrado(codigo)["passos"][1]["narracao"]["longa"]


def test_fim_de_linha_do_windows():
    codigo, entradas, esperado = EXEMPLOS_FIXOS["maior"]
    windows = codigo.replace("\n", "\r\n")
    resultado = narrado(windows, entradas)
    assert curtas(resultado) == esperado
    assert longas(resultado) == longas(narrado(codigo, entradas))


# --- Propriedades em todos os programas ---


def programas():
    lista = [(f"site:{e['titulo']}", e["codigo"], [x for x in e["entradas"] if x], 1000) for e in EXEMPLOS]
    lista += [(f"fixo:{nome}", c, en, 1000) for nome, (c, en, _) in EXEMPLOS_FIXOS.items()]
    lista += [(f"borda:{nome}", c, en, 5 if nome == "limite" else 1000) for nome, (c, en, _) in CASOS.items()]
    lista += [(f"corpus:{nome}", c, en, 1000) for nome, c, en in CORPUS_LIDO]
    return lista


PROGRAMAS = programas()


def combinacoes(partes):
    """Todas as frases que montar() pode produzir, campo a campo visível ou não."""
    campos = sorted({campo for parte in partes for campo in parte["campos"]})
    for mascara in range(2 ** len(campos)):
        visiveis = {campo for indice, campo in enumerate(campos) if mascara >> indice & 1}
        yield "".join(
            parte["texto"] if set(parte["campos"]) <= visiveis else parte.get("oculto", "") for parte in partes
        )


def textos_do_aluno(resultado):
    for comando in resultado["estrutura"]["comandos"]:
        yield comando["leitura"]["literal"]
        yield comando["leitura"]["traduzida"]
    for passo in resultado["passos"]:
        narracao = passo["narracao"]
        for versao in ("curta", "longa"):
            yield narracao[versao]
            yield from combinacoes(narracao["partes_" + versao])


@pytest.mark.parametrize("nome, codigo, entradas, limite", PROGRAMAS, ids=[p[0] for p in PROGRAMAS])
def test_curta_tem_no_maximo_12_palavras_em_qualquer_revelacao(nome, codigo, entradas, limite):
    resultado = narrado(codigo, entradas, limite=limite)
    for passo in resultado["passos"]:
        for frase in combinacoes(passo["narracao"]["partes_curta"]):
            assert 1 <= contar_palavras(frase) <= LIMITE_PALAVRAS, (nome, passo["i"], frase)


@pytest.mark.parametrize("nome, codigo, entradas, limite", PROGRAMAS, ids=[p[0] for p in PROGRAMAS])
def test_partes_montam_as_frases(nome, codigo, entradas, limite):
    resultado = narrado(codigo, entradas, limite=limite)
    json.dumps(resultado)
    for passo in resultado["passos"]:
        narracao = passo["narracao"]
        assert set(narracao) == {"curta", "longa", "partes_curta", "partes_longa"}
        for versao in ("curta", "longa"):
            partes = narracao["partes_" + versao]
            assert "".join(parte["texto"] for parte in partes).strip() == narracao[versao]
            for parte in partes:
                assert set(parte) <= {"texto", "campos", "oculto"}
                assert set(parte["campos"]) <= CAMPOS, parte
                assert parte["texto"] or parte.get("oculto")
            assert narracao[versao].endswith((".", "?", "!", "…")), (nome, passo["i"], narracao[versao])


@pytest.mark.parametrize("nome, codigo, entradas, limite", PROGRAMAS, ids=[p[0] for p in PROGRAMAS])
def test_texto_sem_palavras_proibidas_nem_espacos_sobrando(nome, codigo, entradas, limite):
    resultado = narrado(codigo, entradas, limite=limite)
    for texto in textos_do_aluno(resultado):
        assert not PROIBIDAS.search(texto), (nome, texto)
        # Fora do que é citado (saída e textos do código), as partes se juntam sem espaço sobrando.
        frase = re.sub(r"“[^”]*”|\"[^\"]*\"|'[^']*'", "Q", texto.strip())
        assert "  " not in frase and " ." not in frase and " ," not in frase, (nome, texto)


def test_narrar_um_passo_igual_ao_resultado_inteiro():
    codigo, entradas, _ = CASOS["funcao"]
    inteiro = narrado(codigo, entradas)
    sozinho = rastrear(codigo, entradas, semente=1)
    for passo in sozinho["passos"]:
        assert narrar(passo, sozinho, codigo) == inteiro["passos"][passo["i"]]["narracao"]


def test_narrar_de_novo_nao_muda_nada():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    resultado = narrado(codigo, entradas)
    antes = json.dumps(resultado, sort_keys=True)
    narrar_resultado(resultado, codigo)
    assert json.dumps(resultado, sort_keys=True) == antes


def test_erro_de_sintaxe_nao_quebra():
    codigo = "x = (\n"
    resultado = rastrear(codigo, semente=1)
    assert narrar_resultado(resultado, codigo) is resultado
    assert resultado["passos"] == [] and resultado["estrutura"]["comandos"] == []
    json.dumps(resultado)


def test_codigo_diferente_do_rastreado_levanta_erro():
    resultado = rastrear("x = 1\n", semente=1)
    with pytest.raises(ValueError):
        narrar_resultado(resultado, "x = 1\ny = 2\n")


def test_contar_palavras():
    assert contar_palavras("a  b\nc") == 3
    assert contar_palavras("") == 0


def test_valor_de_objeto_nao_mostra_endereco_de_memoria():
    resultado = narrado("class P:\n    pass\np = P()\n")
    for texto in textos_do_aluno(resultado):
        assert "0x" not in texto


SEM_ERRO_COM_RETORNOS = [
    "def contagem(n):\n    if n == 0:\n        print('fim')\n        return\n    print(n)\n    contagem(n - 1)\ncontagem(2)\n",
    "def fat(n):\n    if n <= 1:\n        return 1\n    return n * fat(n - 1)\nr = fat(3)\nprint(r)\n",
    "def dobro(n):\n    return n * 2\ndef quadruplo(n):\n    return dobro(n) * 2\nx = quadruplo(3)\nprint(x)\n",
    "def g(x):\n    return x + 1\ndef f(x):\n    return g(x)\ny = f(1)\n",
]


@pytest.mark.parametrize("codigo", SEM_ERRO_COM_RETORNOS)
def test_programa_sem_erro_nunca_narra_erro(codigo):
    resultado = narrado(codigo)
    assert resultado["erro"] is None
    for passo in resultado["passos"]:
        assert "erro" not in passo["narracao"]["curta"], passo["narracao"]["curta"]
        assert "erro" not in passo["narracao"]["longa"], passo["narracao"]["longa"]


def test_recursao_narra_cada_retorno():
    resultado = narrado(SEM_ERRO_COM_RETORNOS[1])
    recebe = next(p for p in resultado["passos"] if p.get("retornos"))
    assert recebe["narracao"]["longa"].startswith("fat devolveu 1. fat devolveu 2. fat devolveu 6. ")
    curtas_ = curtas(resultado)
    assert "fat devolve n * fat(n - 1), que vale 2." in curtas_


def test_print_dentro_da_funcao_nao_leva_o_print_de_fora():
    resultado = narrado("def estrelas(n):\n    print('*' * n)\nfor i in range(1, 3):\n    print(estrelas(i))\n")
    dentro = [p["narracao"]["curta"] for p in resultado["passos"] if p["linha"] == 2]
    assert dentro == ["print escreve na tela: “*”.", "print escreve na tela: “**”."]
