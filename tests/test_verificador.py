"""Verificador do Praticar: recusa o exercício ruim (escrito à mão como um modelo de linguagem erraria)."""

import ast
import hashlib

import pytest

from pyvis_motor import api, gerador, verificador

PALAVRA_DE_JOGO = "a" + "posta"  # montada em pedaços, como em frontend/src/textos.test.ts
CONTEXTO = "Um robô roda um programa curto."


def exercicio(tema, nivel, codigo, contexto=CONTEXTO):
    return {"tema": tema, "nivel": nivel, "codigo": codigo, "contexto": contexto, "entradas": []}


# Os 16 exercícios ruins do protótipo (gerador-prototipo/adversario.py), com o motivo que os recusa.
# Os temas while/for/funcoes do protótipo viram Laços e Condições. Três passavam no protótipo:
# o enunciado que mentia (aqui o contexto não pode perguntar nem passar de 12 palavras), o dado
# pessoal e as 11 operações em Variáveis 1.
ADVERSARIOS = [
    ("laço infinito", "lacos", 1,
     'vidas = 3\nwhile vidas > 0:\n    print("Jogando...")\n    vidas = vidas + 1\nprint("Fim")\n', CONTEXTO,
     "nao_termina"),
    ("input() sem entradas", "variaveis", 2, 'nome = input("Nome do pet: ")\nprint("Olá,", nome)\n', CONTEXTO,
     "proibido:input"),
    ("random sem semente", "variaveis", 1, 'import random\ndado = random.randint(1, 6)\nprint("O dado deu", dado)\n',
     CONTEXTO, "proibido:import"),
    ("gabarito errado (10 + 5 * 2)", "variaveis", 1, "moedas = 10\nmoedas = moedas + 5\nmoedas = moedas * 2\nprint(moedas)\n",
     CONTEXTO, "acima_do_nivel:multiplicacao"),
    ("compreensão de lista no nível 1", "variaveis", 1, "dobros = [n * 2 for n in range(3)]\nprint(dobros)\n", CONTEXTO,
     "proibido:compreensao"),
    ("recursão", "condicoes", 1,
     "def contar(n):\n    if n == 0:\n        return 0\n    return n + contar(n - 1)\n\nprint(contar(3))\n", CONTEXTO,
     "proibido:funcao"),
    ("erro de sintaxe", "condicoes", 1, 'pontos = 10\nif pontos > 5\n    print("Ganhou!")\n', CONTEXTO, "erro_de_sintaxe"),
    ("import os", "variaveis", 1, "import os\nprint(os.getcwd())\n", CONTEXTO, "proibido:import"),
    ("0.1 + 0.2", "variaveis", 3, "preco = 0.1\ntaxa = 0.2\ntotal = preco + taxa\nprint(total)\n", CONTEXTO,
     "decimal_ambiguo"),
    ("500 linhas de saída", "lacos", 2, 'for i in range(500):\n    print("Estrela", i)\n', CONTEXTO, "saida_longa"),
    ("divisão por zero sem querer", "variaveis", 2, "pedacos = 8\namigos = 0\ncada = pedacos // amigos\nprint(cada)\n",
     CONTEXTO, "erro_ao_rodar:ZeroDivisionError"),
    ("variável usada antes de existir", "variaveis", 1, 'print("Pontos:", pontos)\npontos = 10\n', CONTEXTO,
     "erro_ao_rodar:NameError"),
    ("resposta não depende do if", "condicoes", 1,
     'pontos = 70\nif pontos >= 50:\n    print("Fim da fase")\nelse:\n    print("Fim da fase")\n', CONTEXTO,
     "resposta_nao_depende_do_conceito"),
    ("contexto pergunta (o enunciado que mentia)", "lacos", 2,
     "total = 0\nfor i in range(1, 5):\n    total = total + i\nprint(total)\n",
     "O robô soma as moedas de 1 até 5. Quanto vale total?", "contexto_com_pergunta"),
    ("dado pessoal no texto", "variaveis", 1,
     'nome = "Joana Silva"\ntelefone = "11 98765-4321"\nprint(nome, telefone)\n', CONTEXTO, "dado_pessoal:texto:telefone"),
    ("11 operações em Variáveis 1", "variaveis", 1, "a = 7\nb = 3\nc = a * b - b * b + a - b * a + b * 9 - a * 2 + b\nprint(c)\n",
     CONTEXTO, "acima_do_orcamento:operacoes"),
]


@pytest.mark.parametrize("nome, tema, nivel, codigo, contexto, motivo", ADVERSARIOS)
def test_exercicio_ruim_e_recusado(nome, tema, nivel, codigo, contexto, motivo):
    conferencia = verificador.verificar(exercicio(tema, nivel, codigo, contexto))
    assert not conferencia["ok"], nome
    assert motivo in conferencia["motivos"], (nome, conferencia["motivos"])


def test_sao_os_16_do_prototipo():
    assert len(ADVERSARIOS) == 16


# A mutação em cada tema: um exercício em que o conceito do tema não muda a resposta é recusado,
# e um exercício sem o conceito do tema também. (O único dos 16 era o if de Condições.)
MUTACOES = [
    ("o limite do while não importa", "lacos", 1, 'i = 0\nwhile i < 3:\n    i = i + 1\nprint("fim")\n',
     "resposta_nao_depende_do_conceito"),
    ("o range não importa", "lacos", 2, 'total = 0\nfor i in range(1, 4):\n    total = 5\nprint(total)\n',
     "resposta_nao_depende_do_conceito"),
    ("trocar o valor atribuído não muda a saída", "variaveis", 1, 'x = 5\ny = x + 1\nprint("Bip pronto")\n',
     "resposta_nao_depende_do_conceito"),
    ("Variáveis sem atribuição", "variaveis", 1, 'print("Bip", 1 + 2)\n', "conceito_do_tema_ausente"),
    ("Laços sem laço", "lacos", 1, 'x = 1\nx = x + 1\nprint("Bip", x)\n', "conceito_do_tema_ausente"),
    ("Condições sem if", "condicoes", 1, 'x = 1\nx = x + 1\nprint("Bip", x)\n', "conceito_do_tema_ausente"),
]


@pytest.mark.parametrize("nome, tema, nivel, codigo, motivo", MUTACOES)
def test_conceito_do_tema_precisa_mudar_a_resposta(nome, tema, nivel, codigo, motivo):
    assert motivo in verificador.verificar(exercicio(tema, nivel, codigo))["motivos"], nome


def test_mutacao_aceita_quando_o_conceito_importa():
    # Os pares dos casos acima, com o conceito mudando a resposta.
    assert verificador.verificar(exercicio("lacos", 1, WHILE_SIMPLES))["ok"]
    assert verificador.verificar(exercicio("variaveis", 1, 'x = 5\ny = x + 1\nprint("Bip", y)\n'))["ok"]


def test_contexto_com_mais_de_12_palavras():
    codigo = 'energia = 50\nenergia = energia - 5\nprint("Bip tem", energia)\n'
    longo = "O robô Bip andou pela sala inteira e gastou um pouco da energia dele."
    assert "contexto_longo" in verificador.verificar(exercicio("variaveis", 1, codigo, longo))["motivos"]
    assert verificador.verificar(exercicio("variaveis", 1, codigo, "O robô Bip andou pela sala."))["ok"]


def test_onze_operacoes_estouram_o_orcamento_mesmo_so_com_soma():
    # Sem *, a escada deixa passar: quem recusa é o orçamento.
    codigo = "a = 7\nb = 3\nc = a + b - b + a - b + a + b - a + b - a + b\nprint(c)\n"
    motivos = verificador.verificar(exercicio("variaveis", 1, codigo))["motivos"]
    assert motivos == ["acima_do_orcamento:operacoes"]


# --- A escada é por tema ------------------------------------------------------------------

IF_ELIF = "x = 1\nif x > 0:\n    y = 1\nelif x < 0:\n    y = 2\nelse:\n    y = 3\nprint(y)\n"
IF_E = "x = 1\nz = 2\nif x > 0 and z > 1:\n    y = 1\nelse:\n    y = 3\nprint(y)\n"
IF_OU = "x = 1\nz = 2\nif x > 0 or z > 1:\n    y = 1\nelse:\n    y = 3\nprint(y)\n"
WHILE_SIMPLES = "i = 0\nwhile i < 3:\n    i = i + 1\nprint(i)\n"
WHILE_COMPOSTO = "i = 0\nz = 5\nwhile i < 3 and z > 0:\n    i = i + 1\n    z = z - 1\nprint(i)\n"


@pytest.mark.parametrize("codigo, conceito", [(IF_ELIF, "elif"), (IF_E, "e_ou_nao"), (IF_OU, "e_ou_nao")])
def test_lacos_1_recusa_elif_e_and_or(codigo, conceito):
    # O protótipo tinha uma escada só, acumulada: Laços 1 aceitava elif e and/or. Aqui não.
    motivos = verificador.verificar(exercicio("lacos", 1, codigo))["motivos"]
    assert f"acima_do_nivel:{conceito}" in motivos


def test_escada_de_cada_tema():
    assert verificador.verificar(exercicio("lacos", 1, WHILE_SIMPLES))["ok"]
    assert verificador.fora_da_escada(ast.parse(WHILE_COMPOSTO), "lacos", 1) == [
        "acima_do_nivel:while_composto"
    ]
    assert verificador.verificar(exercicio("lacos", 3, WHILE_COMPOSTO))["ok"]
    # Condição composta só no while: num if, Laços 3 continua recusando.
    assert "acima_do_nivel:e_ou_nao" in verificador.verificar(exercicio("lacos", 3, IF_E))["motivos"]
    assert verificador.verificar(exercicio("condicoes", 3, IF_E))["ok"]
    assert "acima_do_nivel:elif" in verificador.verificar(exercicio("condicoes", 1, IF_ELIF))["motivos"]
    assert verificador.verificar(exercicio("condicoes", 2, IF_ELIF))["ok"]
    # Variáveis não tem if, e Condições 1 não tem *.
    assert "acima_do_nivel:if" in verificador.verificar(exercicio("variaveis", 3, IF_ELIF))["motivos"]
    conta = "x = 4\ny = x * 2\nif y > 5:\n    z = 1\nelse:\n    z = 2\nprint(z)\n"
    assert "acima_do_nivel:multiplicacao" in verificador.verificar(exercicio("condicoes", 1, conta))["motivos"]


def test_escada_cobre_todo_tema_e_nivel_e_cresce():
    for tema, nivel in verificador.temas_e_niveis():
        assert (tema, nivel) in verificador.ESCADA and (tema, nivel) in verificador.ORCAMENTO
        if nivel > 1:
            assert verificador.PERMITIDOS[(tema, nivel - 1)] < verificador.PERMITIDOS[(tema, nivel)]
    # Pré-requisitos: Laços pede Condições 1, que pede Variáveis 1, e nada acima.
    assert verificador.PERMITIDOS[("variaveis", 1)] < verificador.PERMITIDOS[("lacos", 1)]
    assert "multiplicacao" not in verificador.PERMITIDOS[("lacos", 3)]
    assert "resto" in verificador.PERMITIDOS[("condicoes", 2)]


@pytest.mark.parametrize("codigo, motivo", [
    ('nome = "Bip"\nprint(f"Oi {nome}")\n', "proibido:fstring"),
    ("x = {1: 2}\nprint(x)\n", "proibido:dicionario"),
    ("x = {1, 2}\nprint(x)\n", "proibido:conjunto"),
    ("x = 1\nwhile True:\n    x = x + 1\n    break\nprint(x)\n", "proibido:while_true"),
    ('print(eval("1 + 1"))\n', "proibido:nome_proibido"),
    ("x = __name__\nprint(x)\n", "proibido:nome_proibido"),
    ("f = lambda: 1\nprint(f())\n", "proibido:funcao"),
    ("try:\n    x = 1\nexcept Exception:\n    x = 2\nprint(x)\n", "proibido:try"),
    ("global x\nx = 1\nprint(x)\n", "proibido:global"),
    ('print("a".upper())\n', "proibido:metodo"),
    ("print(abs(-3))\n", "proibido:funcao_fora_da_lista"),
    ('print("a", end="")\n', "proibido:argumento_nomeado"),
    ("x = 2 ** 3\nprint(x)\n", "proibido:potencia"),
    ("class A:\n    pass\nprint(1)\n", "proibido:classe"),
    # O % com texto é interpolação, como a f-string: não é o resto da divisão.
    ('copos = 7\ncopos = copos - 2\nprint("Restam %d copos" % copos)\n', "proibido:formatacao_de_texto"),
    ('molde = "Robo %s"\nnome = "Bip"\nprint(molde % nome)\n', "proibido:formatacao_de_texto"),
    ('nome = "Bip"\nprint(("Robo " + "%s") % nome)\n', "proibido:formatacao_de_texto"),
])
def test_sempre_proibidos(codigo, motivo):
    for tema, nivel in (("variaveis", 3), ("lacos", 3)):
        assert motivo in verificador.verificar(exercicio(tema, nivel, codigo))["motivos"]


# --- Textos --------------------------------------------------------------------------------


@pytest.mark.parametrize("contexto, codigo, motivo", [
    (f"O robô fez uma {PALAVRA_DE_JOGO}.", 'x = 1\nx = x + 1\nprint("Bip", x)\n', "palavra_proibida:contexto:" + PALAVRA_DE_JOGO),
    ("O robô ganhou um Prêmio.", 'x = 1\nx = x + 1\nprint("Bip", x)\n', "palavra_proibida:contexto:ganhou"),
    (CONTEXTO, 'x = 1\nx = x + 1\nprint("Medalha", x)\n', "palavra_proibida:texto:medalha"),
    (CONTEXTO, 'vidas = 1\nvidas = vidas + 1\nprint("Bip", vidas)\n', "palavra_proibida:nome:vidas"),
    (CONTEXTO, 'x = "ab"\nx = x + "cd"\nprint(x, "de dano")\n', "palavra_proibida:texto:dano"),
    (CONTEXTO, 'x = "Pa" + "çoca"\nx = x + "!"\nprint(x)\n', "texto_com_acento"),
    (CONTEXTO, 'x = "bip@robo.com"\nx = x + "!"\nprint(x)\n', "dado_pessoal:texto:email"),
    (CONTEXTO, 'x = "123.456.789-09"\nx = x + "!"\nprint(x)\n', "dado_pessoal:texto:cpf"),
    ("Ligue para (11) 98765-4321 depois.", 'x = 1\nx = x + 1\nprint("Bip", x)\n', "dado_pessoal:contexto:telefone"),
    ("Qual é o valor de x no fim", 'x = 1\nx = x + 1\nprint("Bip", x)\n', "contexto_com_pergunta"),
])
def test_textos_recusados(contexto, codigo, motivo):
    motivos = verificador.verificar(exercicio("variaveis", 1, codigo, contexto))["motivos"]
    if motivo == "contexto_com_pergunta":
        # Sem ponto de interrogação, a frase passa: o critério é o sinal, não o jeito de perguntar.
        assert motivo not in motivos
        motivos = verificador.verificar(exercicio("variaveis", 1, codigo, contexto + "?"))["motivos"]
    assert motivo in motivos


def test_resto_com_numeros_continua_sendo_resto():
    codigo = "copos = 7\nsobra = copos % 2\nprint(sobra)\n"
    assert verificador.fora_da_escada(ast.parse(codigo), "variaveis", 2) == []
    assert verificador.fora_da_escada(ast.parse(codigo), "variaveis", 1) == ["acima_do_nivel:resto"]


@pytest.mark.parametrize("palavra", [
    "ganha", "ganhe", "ganhando", "perde", "venceu", "matou", "mata", "tiro", "bomba", "sangue", "batalha",
    "luta", "sortudo", "chefoes", "pontuou", "derrotou", "atirou", "explodiu", "campeao", "placar",
])
def test_flexoes_das_palavras_proibidas(palavra):
    contexto = f"O robô {palavra} agora."
    assert verificador.motivos_de_texto(contexto, ast.parse("x = 1\n")) == [f"palavra_proibida:contexto:{palavra}"]


@pytest.mark.parametrize("palavra", ["morro", "tomate", "parte", "vencimento", "batata", "pontes", "bombom"])
def test_palavras_parecidas_passam(palavra):
    assert verificador.motivos_de_texto(f"O robô viu o {palavra}.", ast.parse("x = 1\n")) == []


@pytest.mark.parametrize("texto", ["ligue 3333 4444", "ligue 98765 4321", "ligue 9 8765 4321", "ligue 3333-4444"])
def test_telefone_sem_ddd(texto):
    assert "dado_pessoal:contexto:telefone" in verificador.motivos_de_texto(texto, ast.parse("x = 1\n"))


@pytest.mark.parametrize("nome", ["vidas2", "pontosExtras", "minhasVidas", "vidas_extras"])
def test_nome_com_palavra_proibida_em_qualquer_formato(nome):
    motivos = verificador.motivos_de_texto(CONTEXTO, ast.parse(f"{nome} = 3\nprint({nome})\n"))
    assert any(m.startswith("palavra_proibida:nome:") for m in motivos), nome


def test_palavra_proibida_e_por_palavra_inteira_e_sem_acento():
    arvore = ast.parse('x = "tesouro"\nprint(x)\n')
    assert verificador.motivos_de_texto("O robô achou um tesouro no jardim.", arvore) == []
    assert verificador.motivos_de_texto("O robô levou um PRÊMIO.", arvore) == ["palavra_proibida:contexto:premio"]


# --- O que volta -----------------------------------------------------------------------------


def test_exercicio_gerado_passa_com_medidas_concepcoes_e_chave():
    gerado = gerador.gerar("robo_energia", 1, 0)
    conferencia = verificador.verificar(gerado)
    assert conferencia["ok"] and conferencia["motivos"] == []
    assert set(conferencia) == {"ok", "motivos", "medidas", "concepcoes", "pontos", "so_decisao", "chave"}
    assert conferencia["so_decisao"] is False
    assert conferencia["pontos"] >= 1 and conferencia["concepcoes"] == ["C04"]
    assert set(conferencia["medidas"]) == {"linhas", "passos", "voltas", "operacoes", "variaveis", "aninhamento"}
    # A chave é o sha256 do próprio código (ast.dump muda entre versões do Python).
    assert conferencia["chave"] == hashlib.sha256(gerado["codigo"].encode()).hexdigest()[:16]
    assert verificador.conferir_rapido(gerado) == []


def test_nao_mexe_no_ultimo_rastro_da_api():
    api.rastrear("x = 41\nprint(x + 1)\n")
    antes = dict(api.ultimo)
    verificador.verificar(gerador.gerar("pet_lanche", 2, 3))
    assert api.ultimo == antes and api.ultimo["codigo"] == "x = 41\nprint(x + 1)\n"


def test_conferencia_rapida_nao_roda_o_programa():
    infinito = exercicio("lacos", 1, "i = 0\nwhile i < 3:\n    print(i)\nprint(i)\n")
    assert verificador.conferir_rapido(infinito) == []
    assert "nao_termina" in verificador.verificar(infinito)["motivos"]
    assert verificador.conferir_rapido(exercicio("variaveis", 1, "x = (1\n")) == ["erro_de_sintaxe"]


@pytest.mark.parametrize("ruim", [
    None,
    {"tema": "funcoes", "nivel": 1, "codigo": "x = 1\n"},
    {"tema": "variaveis", "nivel": 4, "codigo": "x = 1\n"},
    {"tema": "variaveis", "nivel": True, "codigo": "x = 1\n"},
    {"tema": "variaveis", "nivel": 1, "codigo": 5},
    {"tema": "variaveis", "nivel": 1, "codigo": "x = 1\n", "entradas": ["3"]},
])
def test_exercicio_mal_formado(ruim):
    with pytest.raises(ValueError):
        verificador.verificar(ruim)


def test_so_decisao_marca_o_cara_ou_coroa():
    # Só "o if vai entrar?" nas alternativas: o banco limita quantos itens são assim.
    so_sim_ou_nao = 'chuva = 3\nregar = False\nif chuva < 5:\n    regar = True\nprint("Regador ligado:", regar)\n'
    conferencia = verificador.verificar(exercicio("condicoes", 1, so_sim_ou_nao))
    assert conferencia["ok"] and conferencia["so_decisao"] is True
    com_numero = 'chuva = 3\nif chuva < 5:\n    copos = 4\nelse:\n    copos = 2\nprint("Copos:", copos)\n'
    assert verificador.verificar(exercicio("condicoes", 1, com_numero))["so_decisao"] is False
