"""Regra de revelação (revelacao.py): o que de um passo já pode aparecer.

Os testes contrafactuais rodam o mesmo código com entradas diferentes: até o
passo testado tudo é igual, só o desfecho muda. Com o palpite pendente, a
frase e os campos visíveis têm de ser os mesmos nas duas execuções; se não
forem, a tela entregaria a resposta.
"""

import re

import pytest

from pyvis_motor.narrador import _mostrar
from pyvis_motor.revelacao import (
    DESFECHO,
    DESFECHO_DO_CABECALHO,
    aplicar_dependencias,
    desfecho,
    leitura_visivel,
    montar,
    narracao_visivel,
    relacionados,
    visivel,
)
from test_narrador import EXEMPLOS_FIXOS, PROGRAMAS, narrado

CAMPOS = [
    "efeito",
    "decisao",
    "decisao.texto",
    "decisao.valor",
    "decisao.ramo",
    "volta",
    "volta.n",
    "volta.total",
    "volta.saindo",
    "leitura.traduzida",
    "retorno",
]
TUDO_PENDENTE = {campo: ["p"] for campo in ("efeito", "decisao", "volta", "leitura.traduzida", "retorno")}


def sintetico(**extra):
    """Um passo mínimo, só com o que a regra lê."""
    passo = {"i": 3, "comando": 1, "desfecho_visivel_desde": 3, "decisao": None, "volta": None}
    passo.update(extra)
    return passo


def visiveis(passo, respondidos, passo_atual):
    return {campo for campo in CAMPOS if visivel(passo, campo, respondidos, passo_atual)}


# --- Campos relacionados ---


def test_relacionados():
    assert relacionados("efeito", "efeito")
    assert relacionados("decisao", "decisao.valor")
    assert relacionados("decisao.valor", "decisao")
    assert relacionados("efeito.saida_nova", "efeito")
    assert not relacionados("decisao.valor", "decisao.ramo")
    assert not relacionados("volta", "voltas")
    assert not relacionados("efeito", "decisao")


def test_desfecho_no_cabecalho_do_laco_inclui_a_volta():
    volta = {"laco": 1, "n": 2, "total": 3, "total_visivel_desde": 9, "saindo": False}
    assert desfecho(sintetico(volta=volta)) == DESFECHO_DO_CABECALHO
    assert desfecho(sintetico(volta=volta, comando=4)) == DESFECHO
    assert desfecho(sintetico()) == DESFECHO


# --- Regras de visivel() ---


def test_nada_de_um_passo_que_ainda_nao_chegou():
    passo = sintetico(decisao={"ramo_visivel_desde": 4}, volta={"laco": 0, "total_visivel_desde": 5})
    assert visiveis(passo, set(), 2) == set()


def test_sem_palpite_o_desfecho_aparece_no_proprio_passo():
    passo = sintetico()
    assert visiveis(passo, set(), 3) == set(CAMPOS)


def test_desfecho_espera_as_funcoes_que_o_comando_chamou():
    passo = sintetico(desfecho_visivel_desde=7, decisao={"ramo_visivel_desde": 7})
    for atual in range(3, 7):
        assert visiveis(passo, set(), atual) == {
            "decisao.texto",
            "volta",
            "volta.n",
            "volta.total",
            "volta.saindo",
            "leitura.traduzida",
            "retorno",
        }
    assert visiveis(passo, set(), 7) == set(CAMPOS)


def test_desfecho_sem_indice_nunca_aparece():
    passo = sintetico(desfecho_visivel_desde=None)
    assert not visivel(passo, "efeito", set(), 100)
    assert not visivel(passo, "decisao.valor", set(), 100)
    assert visivel(passo, "decisao.texto", set(), 100)


def test_ramo_so_depois_da_decisao():
    passo = sintetico(decisao={"ramo_visivel_desde": 4})
    assert visivel(passo, "decisao.valor", set(), 3)
    assert visivel(passo, "decisao.texto", set(), 3)
    assert not visivel(passo, "decisao.ramo", set(), 3)
    assert not visivel(passo, "decisao", set(), 3)  # o todo espera a parte mais lenta
    assert visivel(passo, "decisao.ramo", set(), 4)
    assert not visivel(sintetico(decisao={"ramo_visivel_desde": None}), "decisao.ramo", set(), 100)


def test_total_de_voltas_so_na_saida_do_laco():
    passo = sintetico(comando=2, volta={"laco": 0, "n": 1, "total": 3, "total_visivel_desde": 10, "saindo": False})
    assert visivel(passo, "volta.n", set(), 3)
    assert not visivel(passo, "volta.total", set(), 9)
    assert not visivel(passo, "volta", set(), 9)
    assert visivel(passo, "volta.total", set(), 10)
    parado = sintetico(volta={"laco": 0, "n": 1, "total": None, "total_visivel_desde": None, "saindo": False})
    assert not visivel(parado, "volta.total", set(), 100)


def test_palpite_pendente_esconde_o_campo_e_os_de_dentro():
    passo = sintetico(depende_de={"decisao": ["p1"]}, decisao={"ramo_visivel_desde": 3})
    assert not visivel(passo, "decisao.texto", set(), 3)
    assert not visivel(passo, "decisao.valor", set(), 3)
    assert not visivel(passo, "efeito", set(), 3)  # a decisão faz parte do desfecho
    assert visivel(passo, "volta.n", set(), 3)
    assert visiveis(passo, {"p1"}, 3) == set(CAMPOS)


def test_palpite_num_campo_de_dentro_esconde_o_de_fora():
    passo = sintetico(depende_de={"efeito.saida_nova": ["p1"]})
    assert not visivel(passo, "efeito", set(), 3)
    assert not visivel(passo, "decisao.valor", set(), 3)
    assert visivel(passo, "decisao.texto", set(), 3)


@pytest.mark.parametrize("pendente", list(DESFECHO))
def test_campos_do_desfecho_se_escondem_juntos(pendente):
    passo = sintetico(depende_de={pendente: ["p1"]}, decisao={"ramo_visivel_desde": 3})
    for campo in DESFECHO + ("decisao",):
        assert not visivel(passo, campo, set(), 3), campo
    assert visiveis(passo, set(), 3) >= {"decisao.texto", "volta.n", "volta.total", "leitura.traduzida", "retorno"}


def test_cabecalho_do_laco_esconde_volta_e_desfecho_juntos():
    volta = {"laco": 1, "n": 2, "total": 3, "total_visivel_desde": 3, "saindo": False}
    for pendente in ("efeito", "decisao.valor", "volta.n", "volta.saindo", "volta.total"):
        passo = sintetico(volta=volta, decisao={"ramo_visivel_desde": 3}, depende_de={pendente: ["p"]})
        assert visiveis(passo, set(), 3) == {"decisao.texto", "leitura.traduzida", "retorno"}, pendente
    # No corpo do laço, o número da volta é só o presente: não se junta ao desfecho.
    corpo = sintetico(volta=dict(volta, laco=0), depende_de={"volta.n": ["p"]})
    assert visivel(corpo, "efeito", set(), 3)
    assert not visivel(corpo, "volta.n", set(), 3)


def test_todos_os_pontos_precisam_de_resposta():
    passo = sintetico(depende_de={"efeito": ["a", "b"]})
    assert not visivel(passo, "efeito", {"a"}, 3)
    assert visivel(passo, "efeito", {"a", "b"}, 3)


# --- montar() e narracao_visivel() ---


def test_montar_troca_a_parte_escondida_pelo_oculto():
    partes = [
        {"texto": "x recebe 1", "campos": []},
        {"texto": ": variável nova.", "campos": ["efeito"], "oculto": "."},
        {"texto": " Fim.", "campos": ["retorno"]},
    ]
    assert montar(partes, sintetico(), set(), 3) == "x recebe 1: variável nova. Fim."
    assert montar(partes, sintetico(depende_de={"efeito": ["p"]}), set(), 3) == "x recebe 1. Fim."
    assert montar(partes, sintetico(depende_de={"retorno": ["p"]}), set(), 3) == "x recebe 1: variável nova."
    assert montar(partes, sintetico(), set(), 2) == "x recebe 1."


@pytest.mark.parametrize("nome, codigo, entradas, limite", PROGRAMAS, ids=[p[0] for p in PROGRAMAS])
def test_sem_palpites_no_fim_a_frase_montada_e_a_completa(nome, codigo, entradas, limite):
    resultado = narrado(codigo, entradas, limite=limite)
    ultimo = len(resultado["passos"]) - 1
    for passo in resultado["passos"]:
        for versao in ("curta", "longa"):
            assert narracao_visivel(passo, set(), ultimo, versao).strip() == passo["narracao"][versao]


def test_narracao_visivel_sem_narracao():
    assert narracao_visivel(sintetico(), set(), 3) == ""


# --- aplicar_dependencias() e leitura_visivel() ---


def test_aplicar_dependencias_aceita_indices_em_texto():
    codigo, entradas, _ = EXEMPLOS_FIXOS["if"]
    resultado = narrado(codigo, entradas)
    aplicar_dependencias(resultado, {"1": {"decisao.valor": ["p1"]}, 2: {"efeito": ["p2"]}})
    assert resultado["passos"][1]["depende_de"] == {"decisao.valor": ["p1"]}
    assert resultado["passos"][2]["depende_de"] == {"efeito": ["p2"]}
    assert "depende_de" not in resultado["passos"][0]
    assert narracao_visivel(resultado["passos"][1], set(), 1) == "nota >= 6? 7 >= 6"
    assert narracao_visivel(resultado["passos"][1], {"p1"}, 1) == "nota >= 6? 7 >= 6, Verdadeiro: entra no if."
    aplicar_dependencias(resultado, {})
    assert all("depende_de" not in passo for passo in resultado["passos"])


def test_leitura_traduzida_pendente_vale_para_os_passos_do_comando():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = narrado(codigo, entradas)
    comando = resultado["estrutura"]["comandos"][1]
    comando["leitura"]["traduzida_depende_de"] = ["q", "p"]
    aplicar_dependencias(resultado, {1: {"leitura.traduzida": ["p"]}})
    cabecalhos = [passo for passo in resultado["passos"] if passo["comando"] == 1]
    assert [passo["depende_de"] for passo in cabecalhos] == [{"leitura.traduzida": ["p", "q"]}] + [
        {"leitura.traduzida": ["q", "p"]}
    ] * (len(cabecalhos) - 1)
    assert all("depende_de" not in passo for passo in resultado["passos"] if passo["comando"] != 1)
    primeiro = cabecalhos[0]
    assert narracao_visivel(primeiro, set(), 1) == "Para cada numero em range(1, 5). Volta 1: numero recebe 1."
    assert narracao_visivel(primeiro, {"p", "q"}, 1) == "Para cada numero de 1 até 4. Volta 1: numero recebe 1."
    assert leitura_visivel(comando, {"p"}) == "para cada numero em range(1, 5)"
    assert leitura_visivel(comando, {"p", "q"}) == "para cada numero de 1 até 4"


# --- Contrafactuais: mesmo presente, futuro diferente, mesma tela ---

# (código, entradas A, entradas B, passo, depende_de do passo, passo_atual até onde conferir)
CONTRAFACTUAIS = [
    ("x = input()\n", ["a"], ["b"], 0, {"efeito": ["p"]}, None),
    ("x = int(input())\n", ["5"], ["abc"], 0, {"efeito": ["p"]}, None),
    ("print(input())\n", ["a"], ["b"], 0, {"efeito": ["p"]}, None),
    (
        "if input() == 's':\n    print('sim')\nelse:\n    print('não')\n",
        ["s"],
        ["n"],
        0,
        {"decisao.valor": ["p"]},
        None,
    ),
    ("if input() == 's':\n    print('sim')\nelse:\n    print('não')\n", ["s"], ["n"], 0, {"efeito": ["p"]}, None),
    ("if input() == 's':\n    x = 1\n", ["s"], ["n"], 0, {"decisao.ramo": ["p"]}, None),
    ("while input() != 'fim':\n    pass\n", ["fim"], ["a", "fim"], 0, {"decisao.valor": ["p"]}, None),
    ("while input() != 'fim':\n    pass\n", ["fim"], ["a", "fim"], 0, {"volta.total": ["p"]}, None),
    ("while input() != 'fim':\n    pass\n", ["fim"], ["a", "fim"], 0, {"volta.n": ["p"]}, None),
    ("for letra in input():\n    pass\n", ["ab"], [""], 0, {"efeito": ["p"]}, None),
    ("for letra in input():\n    pass\n", ["ab"], ["b"], 0, {"efeito": ["p"]}, None),
    ("for letra in input():\n    pass\n", ["ab"], ["a"], 0, {"volta.total": ["p"]}, None),
    ("n = 0\nfor letra in input():\n    n += 1\nprint(n)\n", ["ab"], ["abc"], 1, {"volta.total": ["p"]}, None),
    # Uma chamada no comando: o desfecho espera a função acabar, mesmo sem palpite.
    ("def pergunta():\n    return input() == 's'\nif pergunta():\n    x = 1\n", ["s"], ["n"], 1, {}, 3),
    (
        "def pergunta():\n    return input() == 's'\nif pergunta():\n    x = 1\n",
        ["s"],
        ["n"],
        2,
        {"efeito": ["p"]},
        None,
    ),
    ("def f():\n    return input()\nx = f()\n", ["a"], ["b"], 1, {}, 3),
    ("def f():\n    print(input())\nf()\n", ["a"], ["b"], 1, {}, 3),
    ("def f(s):\n    return s * 2\nprint(f(input()))\n", ["a"], ["bc"], 1, {}, 3),
]


def caminho(passo, campo):
    valor = passo
    for parte in campo.split("."):
        valor = valor.get(parte) if isinstance(valor, dict) else None
    return valor


@pytest.mark.parametrize("codigo, entradas_a, entradas_b, i, depende_de, ate", CONTRAFACTUAIS)
def test_contrafactual_mesma_tela_enquanto_o_palpite_esta_pendente(codigo, entradas_a, entradas_b, i, depende_de, ate):
    a = narrado(codigo, entradas_a)["passos"][i]
    b = narrado(codigo, entradas_b)["passos"][i]
    # O presente é o mesmo; só o desfecho muda.
    for chave in ("comando", "linha", "profundidade", "saida"):
        assert a[chave] == b[chave]
    assert {n: v["h"] for n, v in a["globais"].items()} == {n: v["h"] for n, v in b["globais"].items()}
    assert {n: v["h"] for n, v in a["locais"].items()} == {n: v["h"] for n, v in b["locais"].items()}
    assert a["narracao"]["curta"] != b["narracao"]["curta"] or a["narracao"]["longa"] != b["narracao"]["longa"]
    a["depende_de"] = b["depende_de"] = depende_de
    for atual in range(i, ate if ate is not None else i + 1):
        for versao in ("curta", "longa"):
            assert narracao_visivel(a, set(), atual, versao) == narracao_visivel(b, set(), atual, versao)
        campos = visiveis(a, set(), atual)
        assert campos == visiveis(b, set(), atual)
        for campo in campos - {"leitura.traduzida"}:
            assert caminho(a, campo) == caminho(b, campo), campo


# --- Varredura: com tudo pendente, nenhum desfecho aparece ---

DESFECHOS_NO_TEXTO = re.compile(
    r"Verdadeiro|entra no|vai para o else|testa o elif|começa a volta|Volta \d|Acabou|sai do laço|dá erro|"
    r"acontece um erro|parou aqui|passa a valer|variável nova|[Cc]hegou|continua valendo|antes valia|que vale|"
    r"devolveu|Deu Falso|Aparece:|aparece na tela|uma linha vazia|Ao todo| fica |muda\.|mudam\.|deixa de existir|"
    r"valor devolvido"
)


@pytest.mark.parametrize("nome, codigo, entradas, limite", PROGRAMAS, ids=[p[0] for p in PROGRAMAS])
def test_com_tudo_pendente_a_frase_nao_traz_desfecho(nome, codigo, entradas, limite):
    resultado = narrado(codigo, entradas, limite=limite)
    comandos = resultado["estrutura"]["comandos"]
    for passo in resultado["passos"]:
        if passo["evento"] != "linha":
            continue
        passo["depende_de"] = TUDO_PENDENTE
        textos = [narracao_visivel(passo, set(), passo["i"], versao) for versao in ("curta", "longa")]
        assert all(textos), (nome, passo["i"])
        if comandos[passo["comando"]]["tipo"] not in ("break",):
            for texto in textos:
                assert not DESFECHOS_NO_TEXTO.search(texto), (nome, passo["i"], texto)
        # Valores novos que não estão no código nem no presente não podem aparecer.
        presente = " ".join(_mostrar(valor) for estado in ("globais", "locais") for valor in passo[estado].values())
        novos = []
        if passo["efeito"]:
            for mudada in passo["efeito"]["mudadas"]:
                novos.append(_mostrar(mudada["depois"]))
            novos += [linha.strip() for linha in passo["efeito"]["saida_nova"].split("\n")]
        for novo in novos:
            if len(novo) >= 3 and novo not in codigo and novo not in presente:
                for texto in textos:
                    assert novo not in texto, (nome, passo["i"], novo, texto)
