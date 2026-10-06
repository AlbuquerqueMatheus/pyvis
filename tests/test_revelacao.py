"""Nenhum palpite é entregue antes da resposta (2.1 e 2.2), em todo ponto de previsão.

Os pontos testados são os rotulados à mão no corpus, os que a atividade
escolhe e todos os candidatos que o rastro oferece, no corpus, nos 8
exemplos do site e em programas com funções e geradores. Para cada ponto
pendente, com o aluno parado no passo da pergunta (o mais longe que ele
pode ir sem responder):

1. Nenhum campo visível vem do futuro. Cada campo de um passo sai de algum
   passo do rastro (o efeito sai do passo seguinte do quadro, o total de
   voltas sai da saída do laço...). A conferência é feita aqui, sem usar a
   regra de revelação: o que ela deixa aparecer tem de vir de um passo que o
   aluno já alcançou.
2. Os campos que levam a resposta estão escondidos: o efeito, o valor e o
   ramo da decisão (e o que nem foi calculado), o total de voltas e a
   leitura traduzida do range (nas voltas e na variável do for).
3. A narração visível do passo não traz a resposta nem palavras de desfecho.
"""

import copy
import re

import pytest

from analise.cobertura import ler_corpus, resolver_pontos
from pyvis_motor import rastrear
from pyvis_motor.anotar import passo_depois, passos_de_retorno
from pyvis_motor.concepcoes import gerar_modelos, inicios_de_laco
from pyvis_motor.estrutura import Analise
from pyvis_motor.narrador import _mostrar, narrar_resultado
from pyvis_motor.previsao import candidatas, dependencias, montar_atividade
from pyvis_motor.revelacao import aplicar_dependencias, leitura_visivel, visivel
from test_estrutura import EXEMPLOS
from test_narrador import EXEMPLOS_FIXOS
from test_revelacao_basica import DESFECHOS_NO_TEXTO

NUNCA = float("inf")

# Programas com chamadas e geradores: o desfecho de um passo pode vir de bem depois dele.
EXTRAS = {
    "funcao_no_meio": (
        "def dobro(n):\n    r = n * 2\n    return r\n\ntotal = 0\nfor i in range(3):\n    total = total + dobro(i)\n"
        "print(total)\n",
        [],
    ),
    "gerador": (
        "def contagem(n):\n    i = 0\n    while i < n:\n        yield i\n        i += 1\n\nsoma = 0\n"
        "for v in contagem(4):\n    soma += v\n    print(soma)\n",
        [],
    ),
    "recursao": ("def fat(n):\n    if n <= 1:\n        return 1\n    return n * fat(n - 1)\n\nx = fat(4)\nprint(x)\n", []),
    "while_com_funcao": (
        "def falta(v):\n    return v < 10\n\nv = 1\nwhile falta(v):\n    v = v * 3\nprint(v)\n",
        [],
    ),
    "aninhados": (
        "total = 0\nfor i in range(1, 4):\n    for j in range(i):\n        total += j\n    print(i, total)\n", []
    ),
    "int_do_input": ('idade = int(input("Idade? "))\nprint(idade + 1)\n', ["12"]),
    "input_puro": ('pontos = input("Pontos: ")\nprint(pontos * 2)\n', ["4"]),
    "input_no_if": ('resposta = input("Quer jogar? ")\nif resposta == "s":\n    vidas = 3\nelse:\n    vidas = 0\n'
                    "print(vidas)\n", ["s"]),
    "curto_circuito": ("lista = [3, 4, 5]\ni = 0\nwhile i < len(lista) and lista[i] > 0:\n    i = i + 1\nprint(i)\n", []),
}


def programas():
    lista = [(f"corpus:{p['nome']}", p["codigo"], p["entradas"], p["semente"], p) for p in ler_corpus()]
    vistos = {codigo for _, codigo, _, _, _ in lista}
    for exemplo in EXEMPLOS:
        if exemplo["codigo"] not in vistos:
            vistos.add(exemplo["codigo"])
            lista.append((f"site:{exemplo['titulo']}", exemplo["codigo"], [e for e in exemplo["entradas"] if e], 1, None))
    for nome, (codigo, entradas, _) in EXEMPLOS_FIXOS.items():
        if codigo not in vistos:
            vistos.add(codigo)
            lista.append((f"fixo:{nome}", codigo, entradas, 1, None))
    lista += [(f"extra:{nome}", codigo, entradas, 1, None) for nome, (codigo, entradas) in EXTRAS.items()]
    return lista


PROGRAMAS = programas()


def narrado(codigo, entradas, semente):
    return narrar_resultado(rastrear(codigo, list(entradas), semente=semente), codigo)


# --- De onde vem o conteúdo de cada campo ------------------------------------


def fontes(passo, retornos):
    """campo -> índice do passo de onde o conteúdo vem; só os campos que o passo tem."""
    j = passo["i"]
    depois = passo_depois(passo, retornos)[0]
    seguinte = depois if depois is not None else j
    tabela = {}
    if "retorno" in passo:
        tabela["retorno"] = j
    if passo.get("efeito") is not None:
        tabela["efeito"] = depois
    decisao = passo.get("decisao")
    if decisao:
        tabela["decisao.texto"] = j
        tabela["decisao.nao_calculado"] = j
        if decisao["valor"] is not None:
            tabela["decisao.valor"] = seguinte
        if decisao["ramo"] != "desconhecido":
            tabela["decisao.ramo"] = seguinte
    volta = passo.get("volta")
    if volta:
        cabecalho = passo["comando"] == volta["laco"]
        tabela["volta.n"] = seguinte if cabecalho else j
        tabela["volta.saindo"] = seguinte if cabecalho else j
        tabela["volta.total"] = NUNCA if volta["total_visivel_desde"] is None else volta["total_visivel_desde"]
    return tabela


class Fontes:
    def __init__(self, resultado):
        retornos = passos_de_retorno(resultado["passos"])
        self.por_passo = [fontes(passo, retornos) for passo in resultado["passos"]]
        # Passos com algum campo (fora o total de voltas, que tem índice próprio) vindo de depois do passo seguinte.
        self.atravessam = [
            j
            for j, tabela in enumerate(self.por_passo)
            if any(fonte > j + 1 for campo, fonte in tabela.items() if campo != "volta.total")
        ]


def sem_futuro(resultado, tabela, i, respondidos):
    """Nada visível no passo i (ou antes) vem de depois de i. Devolve as violações."""
    passos = resultado["passos"]
    violacoes = []
    for j in [i] + [j for j in tabela.atravessam if j < i]:
        for campo, fonte in tabela.por_passo[j].items():
            if fonte > i and visivel(passos[j], campo, respondidos, i):
                violacoes.append((j, campo, fonte))
    return violacoes


# --- O que cada tipo de ponto esconde -----------------------------------------


def campos_da_resposta(passo, tipo):
    if tipo in ("valor", "saida"):
        return ["efeito"]
    if tipo == "decisao":
        campos = ["decisao.texto", "decisao.valor", "decisao.ramo", "efeito"]
        if passo["decisao"]["nao_calculado"]:
            campos.append("decisao.nao_calculado")  # o que nem foi calculado já diz o resultado
        return campos
    return ["volta.total", "volta.n", "volta.saindo", "decisao.valor", "efeito"]


def texto_visivel(passo, respondidos, i, versao):
    """A frase montada sem a parte do retorno, que conta um passado ('dobro devolveu 8')."""
    texto = ""
    for parte in passo["narracao"]["partes_" + versao]:
        if "retorno" in parte["campos"]:
            continue
        if all(visivel(passo, campo, respondidos, i) for campo in parte["campos"]):
            texto += parte["texto"]
        else:
            texto += parte.get("oculto", "")
    return texto.strip()


def presente(passo):
    textos = [_mostrar(valor) for estado in ("globais", "locais") for valor in passo[estado].values()]
    return " ".join(textos) + " " + passo["saida"]


def conferir(nome, codigo, resultado, tabela, ponto, resposta, respondidos):
    """Todas as conferências de um ponto pendente; `resposta` é o texto da resposta certa."""
    i = ponto["passo"]
    passo = resultado["passos"][i]
    tipo = ponto["tipo"]
    rotulo = (nome, ponto["id"], tipo, i)
    assert ponto["id"] not in respondidos

    assert sem_futuro(resultado, tabela, i, respondidos) == [], rotulo

    for campo in campos_da_resposta(passo, tipo):
        assert not visivel(passo, campo, respondidos, i), (rotulo, campo)
    comando = resultado["estrutura"]["comandos"][ponto["alvo"]["comando"]]
    if tipo in ("voltas", "valor") and comando["tipo"] == "for":
        leitura = comando["leitura"]
        if leitura["traduzida"] != leitura["literal"]:
            assert leitura_visivel(comando, respondidos) == leitura["literal"], rotulo
            for anterior in resultado["passos"][: i + 1]:
                if anterior["comando"] == comando["id"]:
                    assert not visivel(anterior, "leitura.traduzida", respondidos, i), rotulo

    textos = [texto_visivel(passo, respondidos, i, versao) for versao in ("curta", "longa")]
    assert all(textos), rotulo
    for texto in textos:
        assert not DESFECHOS_NO_TEXTO.search(texto), (rotulo, texto)
        if tipo == "decisao":
            # No elif, "as condições de cima deram Falso" é o passado, não a resposta.
            sem_passado = texto.replace("As condições de cima deram Falso", "")
            for palavra in ("Verdadeiro", "Falso"):
                if palavra not in codigo:
                    assert palavra not in sem_passado, (rotulo, texto)
        if tipo == "voltas":
            assert not re.search(rf"\b{re.escape(resposta)} voltas?\b", texto), (rotulo, texto)
        certa = ponto.get("resposta")
        if tipo == "valor" and isinstance(certa, dict) and certa.get("tipo_valor") in ("numero", "texto"):
            # Na resposta livre, os botões número/texto fazem parte da resposta: a frase não pode dizer o tipo.
            assert not re.search(r"devolve texto|vira número|em número", texto), (rotulo, texto)
    # A resposta só pode aparecer se já está no código ou no presente (o valor de uma caixinha).
    ja_visto = codigo + " " + presente(passo)
    if tipo in ("valor", "saida") and len(resposta) >= 2:
        for pedaco in [resposta] + resposta.split("\n"):
            if len(pedaco) >= 2 and pedaco not in ja_visto:
                for texto in textos:
                    assert pedaco not in texto, (rotulo, pedaco, texto)


def aplicar(resultado, pontos):
    deps, traduzidas = dependencias(resultado, pontos)
    for comando in resultado["estrutura"]["comandos"]:
        comando["leitura"]["traduzida_depende_de"] = list(traduzidas.get(str(comando["id"]), []))
    aplicar_dependencias(resultado, deps)


# --- Os testes ---------------------------------------------------------------------


@pytest.mark.parametrize("nome, codigo, entradas, semente, programa", PROGRAMAS)
def test_pontos_da_atividade_nao_entregam_a_resposta(nome, codigo, entradas, semente, programa):
    resultado = narrado(codigo, entradas, semente)
    atividade = montar_atividade(resultado, codigo, entradas, {"modo": "prever"})["atividade"]
    tabela = Fontes(resultado)
    respondidos = set()
    if atividade["palpite_inicial"]:
        respondidos.add(atividade["palpite_inicial"]["id"])  # perguntado antes de rodar, corrigido no fim
    for ponto in atividade["pontos"]:
        conferir(nome, codigo, resultado, tabela, ponto, ponto["resposta"]["texto"], respondidos)
        respondidos.add(ponto["id"])


@pytest.mark.parametrize("nome, codigo, entradas, semente, programa", PROGRAMAS)
def test_todo_candidato_sozinho_nao_entrega_a_resposta(nome, codigo, entradas, semente, programa):
    resultado = narrado(codigo, entradas, semente)
    lista, _ = candidatas(resultado, Analise(codigo))
    tabela = Fontes(resultado)
    for numero, candidata in enumerate(lista, 1):
        ponto = {"id": f"p{numero}", "passo": candidata["passo"], "tipo": candidata["tipo"],
                 "alvo": {"comando": candidata["comando"]}}
        aplicar(resultado, [ponto])
        conferir(nome, codigo, resultado, tabela, ponto, candidata["exibir"], set())


def pontos_rotulados(programa, resultado):
    """Os pontos à mão do corpus, com o passo em que a pergunta aparece e a resposta certa."""
    analise = Analise(programa["codigo"])
    pontos = [p for p in resolver_pontos(programa, analise) if p["alvo"]["comando"] is not None]
    certas = gerar_modelos(programa["codigo"], programa["entradas"], pontos, programa["semente"])["por_ponto"]
    passos = resultado["passos"]
    inicios = inicios_de_laco(passos, resultado["estrutura"]["comandos"])
    for ponto in pontos:
        comando, k = ponto["alvo"]["comando"], ponto["ocorrencia"]
        if ponto["tipo"] == "voltas":
            ponto["passo"] = inicios[(comando, k)]
        else:
            ponto["passo"] = [p["i"] for p in passos if p["comando"] == comando][k - 1]
        ponto["resposta"] = certas[ponto["id"]]["certa"]["texto"]
    return pontos


CORPUS = [p for p in PROGRAMAS if p[4] is not None]


@pytest.mark.parametrize("nome, codigo, entradas, semente, programa", CORPUS)
def test_pontos_rotulados_do_corpus_nao_entregam_a_resposta(nome, codigo, entradas, semente, programa):
    resultado = narrado(codigo, entradas, semente)
    tabela = Fontes(resultado)
    for ponto in pontos_rotulados(programa, resultado):
        aplicar(resultado, [ponto])
        resposta = ponto["resposta"]
        if ponto["tipo"] == "valor":
            resposta = resposta.replace("'", '"')  # a narração mostra textos com aspas duplas
        conferir(nome, codigo, resultado, tabela, ponto, resposta, set())


def test_o_gerador_esconde_o_efeito_do_yield_que_atravessa_o_ponto():
    codigo, entradas = EXTRAS["gerador"]
    resultado = narrado(codigo, entradas, 1)
    passos = resultado["passos"]
    soma = [p["i"] for p in passos if p["linha"] == 9]
    ponto = {"id": "p1", "passo": soma[1], "tipo": "valor", "alvo": {"comando": passos[soma[1]]["comando"]}}
    sem_pontos = copy.deepcopy(resultado)
    tabela = Fontes(sem_pontos)
    # Sem a dependência extra, o efeito do yield (que já foi mostrado) traria a soma de depois.
    assert sem_futuro(sem_pontos, tabela, ponto["passo"], set()) != []
    aplicar(resultado, [ponto])
    assert sem_futuro(resultado, tabela, ponto["passo"], set()) == []
    yields = [j for j, _, _ in sem_futuro(sem_pontos, tabela, ponto["passo"], set())]
    assert all(passos[j]["depende_de"] == {"efeito": ["p1"]} for j in yields if j != ponto["passo"])


def test_conferencia_acha_um_vazamento_de_proposito():
    """A própria conferência funciona: sem depende_de, o efeito do passo do ponto aparece."""
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = narrado(codigo, entradas, 1)
    tabela = Fontes(resultado)
    assert sem_futuro(resultado, tabela, 2, set()) == [(2, "efeito", 3)]
    ponto = {"id": "p1", "passo": 2, "tipo": "valor", "alvo": {"comando": 2}}
    aplicar(resultado, [ponto])
    assert sem_futuro(resultado, tabela, 2, set()) == []
    assert sem_futuro(resultado, tabela, 2, {"p1"}) == [(2, "efeito", 3)]  # respondido, pode aparecer
