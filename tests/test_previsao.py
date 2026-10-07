"""Palpites gerados do rastro (previsao.py): pontos, densidade, alternativas e correção.

O que cada ponto esconde antes da resposta é conferido em test_revelacao.py.
"""

import json
import re

import pytest

from analise.cobertura import ler_corpus, resolver_pontos
from pyvis_motor import rastrear
from pyvis_motor.anotar import passo_depois, passos_de_retorno
from pyvis_motor.concepcoes import POR_ID
from pyvis_motor.estrutura import Analise
from pyvis_motor.narrador import _mostrar, narrar_resultado
from pyvis_motor.previsao import (
    DISTANCIA,
    MAX_ALTERNATIVAS,
    MAX_PONTOS,
    candidatas,
    corrigir,
    dependencias,
    montar_atividade,
    preparar_atividade,
    publico,
)
from pyvis_motor.registro import validar_evento
from test_narrador import EXEMPLOS_FIXOS

PROIBIDAS = re.compile(r"apost|\bC\d{2}\b", re.IGNORECASE)
CORPUS_LIDO = ler_corpus()
CHAVES_DO_PONTO = {"id", "passo", "tipo", "alvo", "ocorrencia", "pergunta", "resposta", "formato", "sensivel_a_tipo",
                   "concepcoes_observaveis", "testadas", "explicacao", "elogio"}
CHAVES_DA_ALTERNATIVA = {"id", "texto", "tipo_valor", "certa", "concepcao", "origem", "feedback"}


def narrado(codigo, entradas=(), semente=1, **opcoes):
    return narrar_resultado(rastrear(codigo, list(entradas), semente=semente, **opcoes), codigo)


def montar(codigo, entradas=(), semente=1, **config):
    resultado = narrado(codigo, entradas, semente)
    completa = montar_atividade(resultado, codigo, entradas, {"modo": "prever", **config})
    return resultado, completa["atividade"], completa["pontos"]


def todos(atividade):
    return ([atividade["palpite_inicial"]] if atividade["palpite_inicial"] else []) + atividade["pontos"]


def textos_para_o_aluno(ponto):
    yield ponto["pergunta"]
    yield ponto["explicacao"]
    yield ponto["elogio"]
    for alternativa in ponto.get("alternativas", []):
        feedback = alternativa["feedback"]
        if feedback:
            yield from (feedback["regra"], feedback["resolvido"], feedback["resumo"])


# --- Os pontos dos exemplos -----------------------------------------------------------

# (palpite antes de rodar, [(tipo, passo, nome, resposta, textos das alternativas na ordem)])
ESPERADOS = {
    "variaveis": ("Ana vai fazer 13 anos", [("valor", 2, "idade", "13", ["14", "12", "13"])]),
    "if": (
        "Situação: aprovado",
        [("decisao", 1, None, "Verdadeiro", ["Verdadeiro: entra no if", "Falso: vai para o else"])],
    ),
    # O print final igual ao palpite antes de rodar não vira outra pergunta; com 3 linhas
    # ou mais (ou com input), não há palpite antes de rodar nas alternativas.
    "for": (
        "A soma é 10",
        [
            ("voltas", 1, None, "4", ["5", "4", "6", "3"]),
            ("valor", 4, "total", "3", ["4", "3", "2", "1"]),
            ("valor", 7, "numero", "4", ["5", "3", "4"]),
        ],
    ),
    "while": (
        None,
        [
            ("valor", 3, "energia", "2", ["3", "2", "1"]),
            ("decisao", 10, None, "Falso", ["Verdadeiro: dá mais uma volta", "Falso: sai do laço"]),
        ],
    ),
    "listas": (
        None,
        [("voltas", 3, None, "3", ["3", "5", "4", "2"]), ("valor", 7, "fruta", '"uva"', ['"banana"', '"manga"', '"uva"'])],
    ),
    "maior": (
        "O maior é 9",
        [
            ("voltas", 2, None, "4", ["5", "4", "6", "3"]),
            ("decisao", 5, None, "Verdadeiro", ["Verdadeiro: entra no if", "Falso: não entra no if"]),
            ("valor", 9, "n", "7", ["6", "8", "7", "2"]),
        ],
    ),
    "input": (None, [("valor", 1, "idade", "11", ["11", "10", "12"])]),
    "erro": (None, []),
}


@pytest.mark.parametrize("nome", list(ESPERADOS))
def test_pontos_dos_exemplos(nome):
    codigo, entradas, _ = EXEMPLOS_FIXOS[nome]
    _, atividade, _ = montar(codigo, entradas)
    inicial = atividade["palpite_inicial"]["resposta"]["texto"] if atividade["palpite_inicial"] else None
    obtidos = [
        (p["tipo"], p["passo"], p["alvo"].get("nome"), p["resposta"]["texto"], [a["texto"] for a in p["alternativas"]])
        for p in atividade["pontos"]
    ]
    assert (inicial, obtidos) == ESPERADOS[nome]


def test_for_pergunta_as_voltas_com_o_distrator_do_range():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    _, atividade, _ = montar(codigo, entradas)
    voltas = atividade["pontos"][0]
    assert voltas["pergunta"] == "Quantas voltas o laço vai dar?"
    cinco = next(a for a in voltas["alternativas"] if a["texto"] == "5")
    assert cinco["origem"] == "modelo" and cinco["concepcao"] == "C01" and cinco["feedback"]["regra"]
    assert voltas["testadas"] == ["C01"]
    assert voltas["elogio"] == "Isso! O range para antes do último número."
    assert voltas["explicacao"] == "O laço deu 4 voltas. Ele foi de 1 até 4."
    total = atividade["pontos"][1]
    assert total["pergunta"] == "Depois desta linha, quanto vale total?"
    assert total["explicacao"] == "O Python guardou 3 em total porque total valia 1 e numero valia 2."
    regra = next(a for a in total["alternativas"] if a["origem"] == "regra")
    assert regra["concepcao"] is None and regra["feedback"] is None


# --- Propriedades no corpus e nos exemplos ---------------------------------------------

PROGRAMAS = [(f"corpus:{p['nome']}", p["codigo"], p["entradas"], p["semente"]) for p in CORPUS_LIDO]
PROGRAMAS += [(f"fixo:{nome}", c, e, 1) for nome, (c, e, _) in EXEMPLOS_FIXOS.items()]


def resposta_do_rastro(resultado, ponto):
    """A resposta certa calculada aqui, direto do rastro anotado (sem previsao.py)."""
    passos = resultado["passos"]
    if ponto["alvo"]["comando"] is None:
        return resultado["saida"].removesuffix("\n")
    passo = passos[ponto["passo"]]
    if ponto["tipo"] == "voltas":
        return str(passo["volta"]["total"])
    if ponto["tipo"] == "decisao":
        return "Verdadeiro" if passo["decisao"]["ramo"] == "corpo" else "Falso"
    if ponto["tipo"] == "saida":
        return passo["efeito"]["saida_nova"].removesuffix("\n")
    depois = passos[passo_depois(passo, passos_de_retorno(passos))[0]]
    nome = ponto["alvo"]["nome"]
    estado = depois["locais"] if passo["funcao"] is not None and nome in depois["locais"] else depois["globais"]
    return _mostrar(estado[nome])


@pytest.mark.parametrize("nome, codigo, entradas, semente", PROGRAMAS)
def test_densidade_e_formato_dos_pontos(nome, codigo, entradas, semente):
    resultado, atividade, internos = montar(codigo, entradas, semente)
    json.dumps(atividade)
    pontos = atividade["pontos"]
    assert len(pontos) <= MAX_PONTOS
    assert [p["passo"] for p in pontos] == sorted(p["passo"] for p in pontos)
    assert [p["id"] for p in todos(atividade)] == [f"p{k}" for k in range(1, len(todos(atividade)) + 1)]
    assert set(internos) == {p["id"] for p in todos(atividade)}
    for a, b in zip(pontos, pontos[1:]):
        assert b["passo"] - a["passo"] >= DISTANCIA, nome
    pares = [(p["tipo"], p["alvo"]["comando"]) for p in pontos]
    assert len(pares) == len(set(pares)), nome
    for ponto in todos(atividade):
        assert set(ponto) == CHAVES_DO_PONTO | ({"alternativas"} if ponto["formato"] == "alternativas" else set())
        assert ponto["resposta"]["texto"] == resposta_do_rastro(resultado, ponto), (nome, ponto["id"])
        assert ponto["resposta"]["tipo_valor"] in ("numero", "texto", "bool", "lista")
        alternativas = ponto["alternativas"]
        assert 2 <= len(alternativas) <= MAX_ALTERNATIVAS
        if ponto["tipo"] == "decisao":
            assert len(alternativas) == 2 and alternativas[0]["texto"].startswith("Verdadeiro")
        assert [a for a in alternativas if a["certa"]] == [
            next(a for a in alternativas if a["texto"].startswith(ponto["resposta"]["texto"]) and a["certa"])
        ]
        assert len({a["texto"] for a in alternativas}) == len(alternativas)
        assert len({a["id"] for a in alternativas}) == len(alternativas)
        for alternativa in alternativas:
            assert set(alternativa) == CHAVES_DA_ALTERNATIVA
            assert re.fullmatch(r"p\d+a\d", alternativa["id"])
            if alternativa["origem"] == "correta":
                assert alternativa["certa"] and alternativa["concepcao"] is None
            elif alternativa["origem"] == "regra":
                assert alternativa["concepcao"] is None and alternativa["feedback"] is None
            else:
                assert alternativa["origem"] == "modelo"
                assert alternativa["concepcao"] is None or alternativa["concepcao"] in ponto["testadas"]
                assert (alternativa["feedback"] is None) == (alternativa["concepcao"] is None)
        assert set(ponto["testadas"]) <= set(POR_ID)
        assert set(ponto["concepcoes_observaveis"]) <= set(POR_ID)
        for texto in textos_para_o_aluno(ponto):
            assert texto and not PROIBIDAS.search(texto), (nome, texto)
        assert len(ponto["pergunta"].split()) <= 12
        assert len(ponto["elogio"].split()) <= 12


@pytest.mark.parametrize("nome, codigo, entradas, semente", PROGRAMAS)
def test_um_ponto_nunca_fica_dentro_de_outro(nome, codigo, entradas, semente):
    resultado, atividade, _ = montar(codigo, entradas, semente)
    passos = resultado["passos"]
    retornos = passos_de_retorno(passos)
    for ponto in atividade["pontos"]:
        if ponto["tipo"] == "voltas":
            continue
        fim = passo_depois(passos[ponto["passo"]], retornos)[0]
        for outro in atividade["pontos"]:
            assert not ponto["passo"] < outro["passo"] < fim, (nome, ponto["id"], outro["id"])
    comandos = resultado["estrutura"]["comandos"]
    whiles = [p["alvo"]["comando"] for p in atividade["pontos"]
              if p["tipo"] in ("voltas", "decisao") and comandos[p["alvo"]["comando"]]["tipo"] == "while"]
    assert len(whiles) == len(set(whiles))  # quantas voltas e se entra: um entrega o outro


def test_corpus_quase_todo_ponto_rotulado_e_candidato():
    """Os candidatos acham os pontos que o professor marcaria (fora atribuições de valor escrito no código)."""
    achados = rotulados = 0
    for programa in CORPUS_LIDO:
        analise = Analise(programa["codigo"])
        resultado = narrado(programa["codigo"], programa["entradas"], programa["semente"])
        lista, _ = candidatas(resultado, analise)
        chaves = {(c["tipo"], c["comando"], c["ocorrencia"], c["nome"]) for c in lista}
        for ponto in resolver_pontos(programa, analise):
            if ponto["alvo"]["comando"] is None:
                continue
            rotulados += 1
            achados += (ponto["tipo"], ponto["alvo"]["comando"], ponto["ocorrencia"], ponto["alvo"]["nome"]) in chaves
    assert rotulados >= 150
    assert achados / rotulados >= 0.95


def test_corpus_todo_programa_ganha_pontos_e_muitos_tem_modelo():
    com_modelo = total = 0
    for programa in CORPUS_LIDO:
        _, atividade, _ = montar(programa["codigo"], programa["entradas"], programa["semente"])
        assert atividade["pontos"], programa["nome"]
        assert atividade["cobertura"]["total"] == len(todos(atividade))
        com_modelo += atividade["cobertura"]["pontos_com_modelo"]
        total += atividade["cobertura"]["total"]
    assert com_modelo / total >= 0.4


def test_tipos_variados_e_prioridade_ao_acumulador():
    codigo = "soma = 0\nfor n in range(4, 7):\n    soma += n\n    dobro = n * 2\nprint(soma)\n"
    _, atividade, _ = montar(codigo, palpite_inicial=False)
    tipos = [p["tipo"] for p in atividade["pontos"]]
    assert set(tipos) >= {"voltas", "valor", "saida"}
    assert any(p["alvo"].get("nome") == "soma" for p in atividade["pontos"])


# --- Configuração ----------------------------------------------------------------------


def test_assistir_nao_tem_pontos_e_limpa_as_dependencias():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = narrado(codigo, entradas)
    prever = preparar_atividade(resultado, codigo, entradas, {"modo": "prever"})
    assert prever["depende_de_por_passo"] and any("depende_de" in p for p in resultado["passos"])
    assert resultado["estrutura"]["comandos"][1]["leitura"]["traduzida_depende_de"]
    assistir = preparar_atividade(resultado, codigo, entradas, {"modo": "assistir"})
    assert assistir["pontos"] == [] and assistir["palpite_inicial"] is None
    assert assistir["depende_de_por_passo"] == {} and assistir["traduzida_depende_de"] == {}
    assert not any("depende_de" in p for p in resultado["passos"])
    assert all(c["leitura"]["traduzida_depende_de"] == [] for c in resultado["estrutura"]["comandos"])


def test_preparar_de_novo_da_o_mesmo_resultado():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    resultado = narrado(codigo, entradas)
    primeira = preparar_atividade(resultado, codigo, entradas, {"modo": "prever"})
    segunda = preparar_atividade(resultado, codigo, entradas, {"modo": "prever"})
    primeira.pop("tempo_ms")
    segunda.pop("tempo_ms")
    assert primeira == segunda


def test_depende_de_por_passo_e_o_que_ficou_no_resultado():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado, atividade, _ = montar(codigo, entradas)
    copia = {str(p["i"]): p["depende_de"] for p in resultado["passos"] if "depende_de" in p}
    assert atividade["depende_de_por_passo"] == copia
    assert atividade["traduzida_depende_de"] == {"1": ["p2", "p4"]}
    assert copia["1"] == {"volta.total": ["p2"], "leitura.traduzida": ["p2", "p4"]}
    assert copia["7"] == {"efeito": ["p4"], "leitura.traduzida": ["p2", "p4"]}


def test_formato_livre():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    _, atividade, internos = montar(codigo, entradas, formato="livre", palpite_inicial=False)
    formatos = {p["tipo"]: p["formato"] for p in atividade["pontos"]}
    assert formatos == {"voltas": "livre", "decisao": "alternativas", "valor": "livre", "saida": "livre"}
    for ponto in atividade["pontos"]:
        assert ("alternativas" in ponto) == (ponto["formato"] == "alternativas")
        assert "_modelos" in internos[ponto["id"]]


def test_valor_que_e_lista_ou_booleano_e_sempre_de_alternativas():
    codigo = "achou = False\nfor n in [1, 5]:\n    achou = n > 3\nlista = [1]\nlista = lista + [2]\n"
    _, atividade, _ = montar(codigo, formato="livre", palpite_inicial=False, max_pontos=20)
    formatos = {(p["tipo"], p["resposta"]["tipo_valor"]): p["formato"] for p in atividade["pontos"]}
    assert formatos[("valor", "bool")] == "alternativas"
    assert formatos[("valor", "lista")] == "alternativas"


def test_maximo_de_pontos_e_palpite_inicial():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    _, atividade, _ = montar(codigo, entradas, max_pontos=2, palpite_inicial=False)
    assert len(atividade["pontos"]) == 2 and atividade["palpite_inicial"] is None
    assert atividade["pontos"][0]["id"] == "p1"
    _, atividade, _ = montar(codigo, entradas, max_pontos=0)
    assert atividade["pontos"] == [] and atividade["palpite_inicial"]["id"] == "p1"


@pytest.mark.parametrize(
    "config",
    [{"modo": "estudo"}, {"modo": "prever", "formato": "aberto"}, {"modo": "prever", "max_pontos": -1},
     {"modo": "prever", "max_pontos": "6"}],
)
def test_configuracao_invalida(config):
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    with pytest.raises(ValueError):
        preparar_atividade(narrado(codigo, entradas), codigo, entradas, config)


def test_codigo_diferente_do_rastreado():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = narrado(codigo, entradas)
    with pytest.raises(ValueError):
        preparar_atividade(resultado, "x = 1\n", entradas, {"modo": "prever"})


def test_mesma_semente_mesma_ordem_e_sementes_diferentes_mudam_a_ordem():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]

    def ordem(semente):
        _, atividade, _ = montar(codigo, entradas, semente=semente)
        return [[a["texto"] for a in p["alternativas"]] for p in todos(atividade)]

    assert ordem(5) == ordem(5)
    assert len({json.dumps(ordem(semente)) for semente in range(6)}) > 1


def test_orcamento_esgotado_fica_so_com_distratores_de_regra():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    _, atividade, _ = montar(codigo, entradas, orcamento_ms=0)
    assert atividade["completa"] is False
    assert atividade["pontos"]
    origens = {a["origem"] for p in todos(atividade) for a in p["alternativas"]}
    assert origens == {"correta", "regra"}
    _, inteira, _ = montar(codigo, entradas)
    assert inteira["completa"] is True and inteira["tempo_ms"] < 2000


def test_programa_nao_deterministico_nao_tem_modelo():
    codigo = "import time\nhora = 10\nfor i in range(1, 3):\n    hora = hora + i\nprint(hora)\n"
    _, atividade, _ = montar(codigo)
    assert atividade["pontos"]
    assert all(a["origem"] != "modelo" for p in todos(atividade) for a in p["alternativas"])


def test_erro_de_sintaxe_e_programa_vazio():
    for codigo in ("for i in range(3)\n    print(i)\n", ""):
        _, atividade, internos = montar(codigo)
        assert atividade["pontos"] == [] and atividade["palpite_inicial"] is None and internos == {}


def test_programa_com_erro_so_tem_pontos_antes_do_erro_e_sem_palpite_inicial():
    codigo = "x = 2\nx = x * 5\nprint(x)\ny = x / 0\nprint(y)\n"
    resultado, atividade, _ = montar(codigo)
    assert resultado["erro"]["tipo"] == "ZeroDivisionError"
    assert atividade["palpite_inicial"] is None
    assert atividade["pontos"] and all(p["passo"] < 3 for p in atividade["pontos"])


def test_programa_que_estoura_o_limite():
    codigo = "n = 0\nwhile True:\n    n = n + 1\n"
    resultado = narrado(codigo, limite=50)
    atividade = preparar_atividade(resultado, codigo, [], {"modo": "prever"})
    assert atividade["palpite_inicial"] is None
    assert all(p["passo"] < len(resultado["passos"]) - 1 for p in atividade["pontos"])


def test_ponto_publico_sem_o_que_fica_no_python():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    _, atividade, internos = montar(codigo, entradas)
    for pid, ponto in internos.items():
        assert {"_modelos", "_alternativas"} <= set(ponto)
        assert not any(chave.startswith("_") for chave in publico(ponto))
    assert "_modelos" not in json.dumps(atividade)


# --- Dependências ----------------------------------------------------------------------


def test_dependencias_por_tipo_de_ponto():
    codigo = "lista = [3, 4]\ni = 0\nwhile i < len(lista) and lista[i] > 0:\n    i = i + 1\nfor k in range(1, 4):\n    pass\n"
    resultado = narrado(codigo)
    passos = resultado["passos"]
    saida_do_while = next(p["i"] for p in passos if p["decisao"] and p["decisao"]["nao_calculado"])
    entrada_do_for = next(p["i"] for p in passos if p["comando"] == 4)
    pontos = [
        {"id": "p1", "passo": 1, "tipo": "valor", "alvo": {"comando": 1, "nome": "i"}},
        {"id": "p2", "passo": saida_do_while, "tipo": "decisao", "alvo": {"comando": 2}},
        {"id": "p3", "passo": entrada_do_for, "tipo": "voltas", "alvo": {"comando": 4}},
        {"id": "p4", "passo": 0, "tipo": "saida", "alvo": {"comando": None}},
    ]
    deps, traduzidas = dependencias(resultado, pontos)
    assert deps == {
        "1": {"efeito": ["p1"]},
        str(saida_do_while): {"decisao.texto": ["p2"], "decisao.valor": ["p2"], "decisao.nao_calculado": ["p2"]},
        str(entrada_do_for): {"volta.total": ["p3"]},
    }
    assert traduzidas == {"4": ["p3"]}


# --- Correção da resposta livre -----------------------------------------------------


def ponto_de(codigo, entradas=(), tipo=None, nome=None, **config):
    _, atividade, internos = montar(codigo, entradas, **{"formato": "livre", **config})
    for ponto in internos.values():
        if (tipo is None or ponto["tipo"] == tipo) and (nome is None or ponto["alvo"].get("nome") == nome):
            return ponto
    raise AssertionError("ponto não escolhido")


def test_numero_certo_e_errado():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "valor", "total")
    certa = corrigir(ponto, {"texto": " 3 ", "tipo_escolhido": "numero"})
    assert certa["certa"] and certa["legivel"] and certa["valor_certo"] and certa["tipo_certo"]
    assert certa["mensagem"] == ponto["elogio"] and certa["valor_normalizado"] == 3
    assert certa["testadas"] == ponto["testadas"]
    errada = corrigir(ponto, {"texto": "4", "tipo_escolhido": "numero"})
    assert not errada["certa"] and errada["concepcao"] is None and errada["feedback"] is None
    assert errada["mensagem"] == "Seu palpite: 4. O Python guardou 3."
    assert errada["explicacao"] == "O Python guardou 3 em total porque total valia 1 e numero valia 2."
    antigo = corrigir(ponto, {"texto": "1", "tipo_escolhido": "numero"})
    assert antigo["concepcao"] == "C04" and antigo["feedback"]["regra"]


def test_voltas_com_diagnostico_do_range():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "voltas")
    assert corrigir(ponto, {"texto": "4"})["certa"]
    errada = corrigir(ponto, {"texto": "5"})
    assert errada["concepcao"] == "C01" and errada["mensagem"] == "Seu palpite: 5. O laço deu 4 voltas."
    assert "range" in errada["feedback"]["regra"]
    assert not corrigir(ponto, {"texto": "quatro"})["legivel"]


ENTRADA = 'idade = input("Idade do robô: ")\nprint("ok")\n'


def test_input_texto_contra_numero_e_o_botao_decide():
    ponto = ponto_de(ENTRADA, ["11"], "valor", "idade")
    assert ponto["sensivel_a_tipo"] and ponto["resposta"] == {"texto": '"11"', "tipo_valor": "texto"}
    texto = corrigir(ponto, {"texto": "11", "tipo_escolhido": "texto"})
    assert texto["certa"] and texto["palpite"] == '"11"' and texto["valor_normalizado"] == "11"
    com_aspas = corrigir(ponto, {"texto": '"11"', "tipo_escolhido": "texto"})
    assert com_aspas["certa"]
    numero = corrigir(ponto, {"texto": "11", "tipo_escolhido": "numero"})
    assert not numero["certa"] and numero["valor_certo"] and not numero["tipo_certo"]
    assert numero["concepcao"] == "C03" and numero["feedback"]["regra"].startswith("O `input` devolve texto")
    assert numero["mensagem"] == 'Seu palpite: 11. O Python guardou "11". O valor é esse, mas é texto, não número.'
    # Sem marcar 'número', o mesmo palpite não vira 'o input devolve número'.
    sem_botao = corrigir(ponto, {"texto": "11"})
    assert not sem_botao["certa"] and sem_botao["concepcao"] is None


def test_numero_contra_texto():
    codigo = 'idade = int(input("Idade: "))\nprint("ok")\n'
    ponto = ponto_de(codigo, ["11"], "valor", "idade")
    texto = corrigir(ponto, {"texto": "11", "tipo_escolhido": "texto"})
    assert not texto["certa"] and texto["valor_certo"] and not texto["tipo_certo"]
    assert texto["mensagem"].endswith("O valor é esse, mas é número, não texto.")


def test_sete_contra_sete_ponto_zero_e_recado_nao_diagnostico():
    ponto = ponto_de("media = 14 / 2\nprint(media)\n", (), "valor", "media")
    assert ponto["resposta"]["texto"] == "7.0"
    sete = corrigir(ponto, {"texto": "7", "tipo_escolhido": "numero"})
    assert sete["certa"] and sete["concepcao"] is None
    assert sete["mensagem"].endswith("Repare: o Python mostra 7.0, um número decimal.")
    inteiro = ponto_de("media = 14 // 2\nprint(media)\n", (), "valor", "media")
    decimal = corrigir(inteiro, {"texto": "7.0", "tipo_escolhido": "numero"})
    assert decimal["certa"] and decimal["mensagem"].endswith("Repare: o Python mostra 7, um número inteiro.")


def test_texto_ilegivel_como_numero():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "valor", "total")
    for texto in ("abc", "", "   ", "3 +"):
        resposta = corrigir(ponto, {"texto": texto, "tipo_escolhido": "numero"})
        assert not resposta["legivel"] and not resposta["certa"] and resposta["mensagem"]


def test_saida_ignora_espacos_no_fim_e_nao_tira_aspas():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "saida", palpite_inicial=False)
    assert corrigir(ponto, {"texto": "A soma é 10   \n"})["certa"]
    # Espaço sobrando no começo ou no meio não se vê na tela: não pode virar erro.
    assert corrigir(ponto, {"texto": " A soma  é 10"})["certa"]
    assert not corrigir(ponto, {"texto": "A somaé 10"})["certa"]
    assert not corrigir(ponto, {"texto": '"A soma é 10"'})["certa"]
    errada = corrigir(ponto, {"texto": "A soma é 15"})
    assert errada["concepcao"] == "C01"
    assert errada["mensagem"] == "Seu palpite: “A soma é 15”. Na tela apareceu “A soma é 10”."
    assert errada["valor_normalizado"] is None  # texto com letras não sai do aparelho


def test_palpite_inicial_corrige_a_saida_inteira():
    codigo, entradas, _ = EXEMPLOS_FIXOS["while"]
    _, atividade, internos = montar(codigo, entradas, formato="livre")
    inicial = internos["p1"]
    assert atividade["palpite_inicial"]["pergunta"] == "Qual é o seu palpite? O que vai aparecer na tela?"
    assert inicial["alvo"] == {"comando": None} and inicial["passo"] == 0
    certo = "Energia: 3\nEnergia: 2\nEnergia: 1\nO robô descansou!"
    assert corrigir(inicial, {"texto": certo})["certa"]
    errada = corrigir(inicial, {"texto": "Energia: 3"})
    assert errada["mensagem"] == (
        "Seu palpite: “Energia: 3”. No fim, a tela mostrou "
        "“Energia: 3 / Energia: 2 / Energia: 1 / O robô descansou!” A 2ª linha foi “Energia: 2”."
    )
    sem_a_ultima = corrigir(inicial, {"texto": certo.replace("O robô descansou!", "Fim!")})
    assert sem_a_ultima["mensagem"].endswith("A 4ª linha foi “O robô descansou!”")
    a_mais = corrigir(inicial, {"texto": certo + "\nTchau"})
    assert a_mais["mensagem"].endswith("A tela teve só 4 linhas.")


def test_palpite_inicial_nas_alternativas_tem_ate_duas_linhas():
    codigo = 'print("Oi")\nprint("Tchau!")\n'
    _, atividade, internos = montar(codigo)
    inicial = atividade["palpite_inicial"]
    assert inicial["resposta"]["texto"] == "Oi\nTchau!"
    errada = next(a for a in inicial["alternativas"] if not a["certa"])
    mensagem = corrigir(internos[inicial["id"]], {"alternativa": errada["id"]})["mensagem"]
    # Um formato só (“ / ”), sem '!.' e com a linha que mudou.
    assert mensagem.startswith(f"Seu palpite: “{errada['texto'].replace(chr(10), ' / ')}”")
    assert "No fim, a tela mostrou “Oi / Tchau!” " in mensagem and "!”." not in mensagem
    tres = 'print("a")\nprint("b")\nprint("c")\n'
    assert montar(tres)[1]["palpite_inicial"] is None
    assert montar(tres, formato="livre")[1]["palpite_inicial"]["resposta"]["texto"] == "a\nb\nc"


def test_palpite_inicial_nao_aparece_com_input():
    # A tela teria as perguntas do input e o que foi digitado: quem escreve só os prints erraria.
    codigo = 'nome = input("Nome? ")\nprint("Oi", nome)\n'
    for formato in ("alternativas", "livre"):
        assert montar(codigo, ["Bia"], formato=formato)[1]["palpite_inicial"] is None


def test_voltas_de_um_for_numa_lista_explica_pelos_itens():
    codigo = 'frutas = ["uva", "kiwi", "pera"]\nfor f in frutas:\n    print(f)\n'
    ponto = ponto_de(codigo, (), "voltas")
    assert ponto["explicacao"] == "O laço deu 3 voltas. Uma volta para cada item de frutas: são 3 itens."
    letras = ponto_de('for c in "oi":\n    print(c)\n', (), "voltas")
    assert letras["explicacao"] == 'O laço deu 2 voltas. Uma volta para cada letra de "oi": são 2 letras.'
    # Com break, o número de itens não é o de voltas: a frase ficaria errada.
    com_break = ponto_de('for n in [1, 2, 3, 4]:\n    if n == 2:\n        break\n', (), "voltas")
    assert com_break["explicacao"] == "O laço deu 2 voltas."


def test_onde_olhar_das_voltas_e_a_ultima_volta():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado, atividade, _ = montar(codigo, entradas)
    voltas = atividade["pontos"][0]
    cinco = next(a for a in voltas["alternativas"] if a["texto"] == "5")
    passo = resultado["passos"][cinco["feedback"]["onde"]["passo"]]
    assert passo["comando"] == voltas["alvo"]["comando"] and passo["volta"]["n"] == 4


def test_elogio_da_saida_diz_o_que_foi_lido():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "saida", palpite_inicial=False)
    assert ponto["elogio"] == "Você leu o valor de total na hora do print."


def test_decisao_por_palavra():
    codigo, entradas, _ = EXEMPLOS_FIXOS["if"]
    ponto = ponto_de(codigo, entradas, "decisao")
    assert corrigir(ponto, {"texto": "verdadeiro"})["certa"]
    assert corrigir(ponto, {"texto": "Sim"})["certa"]
    assert corrigir(ponto, {"texto": "Falso"})["mensagem"] == "Seu palpite: Falso. A condição deu Verdadeiro."
    assert not corrigir(ponto, {"texto": "talvez"})["legivel"]


def test_correcao_por_alternativa():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    _, atividade, internos = montar(codigo, entradas)
    voltas = internos["p2"]
    por_texto = {a["texto"]: a for a in voltas["alternativas"]}
    assert corrigir(voltas, {"alternativa": por_texto["4"]["id"]})["certa"]
    modelo = corrigir(voltas, {"alternativa": por_texto["5"]["id"]})
    assert modelo["concepcao"] == "C01" and modelo["feedback"] == por_texto["5"]["feedback"]
    assert modelo["mensagem"] == "Seu palpite: 5. O laço deu 4 voltas."
    regra = corrigir(voltas, {"alternativa": por_texto["6"]["id"]})
    assert not regra["certa"] and regra["concepcao"] is None and regra["feedback"] is None
    assert not corrigir(voltas, {"alternativa": "p9a9"})["legivel"]
    # O Ponto público (sem os modelos) também serve.
    assert corrigir(atividade["pontos"][0], {"alternativa": por_texto["5"]["id"]})["concepcao"] == "C01"


@pytest.mark.parametrize("resposta", [None, "4", {"texto": 4}, {"texto": "4", "tipo_escolhido": "letra"}])
def test_resposta_malformada(resposta):
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "voltas")
    with pytest.raises(ValueError):
        corrigir(ponto, resposta)


def test_correcao_vira_evento_valido():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    ponto = ponto_de(codigo, entradas, "valor", "total")
    correcao = corrigir(ponto, {"texto": "1", "tipo_escolhido": "numero"})
    evento = {
        "v": 1, "ts": 1_760_000_000_000, "sala": "TURMA8A", "sujeito": "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f",
        "atividade": "aula3", "programa": 0, "condicao": "prever", "tipo": "Prediction",
        "code_hash": "0123456789abcdef", "ponto": ponto["id"], "formato": "livre",
        "resposta": {"valor_normalizado": correcao["valor_normalizado"], "tipo_escolhido": "numero"},
        "certa": correcao["certa"], "concepcao": correcao["concepcao"], "testadas": correcao["testadas"],
    }
    assert validar_evento(evento) == []
