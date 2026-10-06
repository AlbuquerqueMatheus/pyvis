"""API do worker (pyvis_motor/api.py): tudo entra e sai como JSON, e o último rastro fica no Python."""

import json
import re

import pytest

import pyvis_motor
from pyvis_motor import api, registro
from pyvis_motor.revelacao import visivel
from test_narrador import EXEMPLOS_FIXOS

SUJEITO = "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f"
CONTEXTO = {
    "sala": "TURMA8A",
    "sujeito": SUJEITO,
    "atividade": "aula3",
    "programa": 0,
    "condicao": "prever",
    "code_hash": "0123456789abcdef",
}


def pedir(acao, dados=None, **extra):
    resposta = json.loads(api.executar_json(json.dumps({"acao": acao, "dados": dados, **extra})))
    assert set(resposta) <= {"ok", "resultado", "erro", "id"}
    return resposta


def resultado_de(acao, dados=None):
    resposta = pedir(acao, dados)
    assert resposta["ok"], resposta
    return resposta["resultado"]


def esquecer():
    api.ultimo.update(codigo=None, entradas=[], resultado=None, atividade=None, pontos={})


# --- Rastrear ------------------------------------------------------------------------


def test_rastrear_devolve_o_resultado_anotado_e_narrado():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    assert resultado["versao"] == 2 and resultado["erro"] is None
    assert resultado["saida"] == "A soma é 10\n"
    for passo in resultado["passos"]:
        assert {"efeito", "narracao", "proximo_no_quadro"} <= set(passo)
        assert passo["narracao"]["curta"] and passo["narracao"]["partes_curta"]
    for comando in resultado["estrutura"]["comandos"]:
        assert set(comando["leitura"]) == {"literal", "traduzida", "traduzida_depende_de"}
    assert api.ultimo["codigo"] == codigo and api.ultimo["resultado"] is not None


def test_rastrear_com_entradas_e_erro_do_aluno():
    resultado = resultado_de("rastrear", {"codigo": "idade = int(input('Idade: '))\nprint(idade + 1)\n", "entradas": ["10"]})
    assert resultado["saida"].endswith("11\n")
    # O erro no código do aluno vem dentro do Resultado; a resposta continua ok.
    resultado = resultado_de("rastrear", {"codigo": "print(1 / 0)\n"})
    assert resultado["erro"]["tipo"] == "ZeroDivisionError"


def test_limite_de_passos():
    resultado = resultado_de("rastrear", {"codigo": "while True:\n    pass\n", "limite": 300})
    assert resultado["erro"]["tipo"] == "LimiteDePassos"
    assert len(resultado["passos"]) <= 302


def test_mesma_semente_repete_os_sorteios():
    codigo = "import random\nprint(random.randint(1, 1000), random.randint(1, 1000))\n"
    primeira = resultado_de("rastrear", {"codigo": codigo, "semente": 42})
    segunda = resultado_de("rastrear", {"codigo": codigo, "semente": 42})
    assert primeira["semente"] == 42 and primeira["saida"] == segunda["saida"]


@pytest.mark.parametrize(
    "dados, motivo",
    [
        ({"codigo": 5}, "codigo precisa ser texto"),
        ({"codigo": "x = 1", "entradas": [3]}, "cada entrada precisa ser texto"),
        ({"codigo": "x = 1", "limite": 0}, "limite precisa ser um inteiro"),
        ({"codigo": "x = 1", "limite": 10_001}, "limite precisa ser um inteiro"),
        ({"codigo": "x = 1", "limite": True}, "limite precisa ser um inteiro"),
        ({"codigo": "x = 1", "semente": "7"}, "semente precisa ser um inteiro"),
        ({"codigo": "x = 1", "outra": 1}, "TypeError"),
        ({}, "TypeError"),
    ],
)
def test_parametros_invalidos_viram_erro(dados, motivo):
    resposta = pedir("rastrear", dados)
    assert resposta["ok"] is False and motivo in resposta["erro"]


def test_narracao_de_reserva_quando_o_narrador_falha():
    original = api.narrar_resultado

    def quebrado(resultado, codigo):
        raise RuntimeError("defeito")

    api.narrar_resultado = quebrado
    try:
        resultado = api.rastrear("x = 2\nprint(x)\n")
    finally:
        api.narrar_resultado = original
    assert [p["narracao"]["curta"] for p in resultado["passos"]] == ["Roda a linha 1.", "Roda a linha 2.", "O programa terminou."]
    assert all("efeito" in p for p in resultado["passos"])
    assert all(c["leitura"]["traduzida_depende_de"] == [] for c in resultado["estrutura"]["comandos"])
    json.dumps(resultado, allow_nan=False)


# --- Atividade e correção --------------------------------------------------------------


def test_preparar_antes_de_rodar_da_erro():
    esquecer()
    resposta = pedir("preparar_atividade", {"config": {"modo": "prever"}})
    assert resposta == {"ok": False, "erro": "ValueError: rode o programa antes de preparar a atividade"}


def test_corrigir_ponto_desconhecido():
    esquecer()
    resposta = pedir("corrigir", {"ponto_id": "p1", "resposta": {"texto": "4"}})
    assert resposta["ok"] is False and "ponto desconhecido" in resposta["erro"]


def test_fluxo_completo_com_alternativas():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado = resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    atividade = resultado_de("preparar_atividade", {"config": {"modo": "prever", "semente": 3}})
    assert atividade["versao"] == 1 and atividade["modo"] == "prever"
    # O print final é a mesma pergunta do palpite antes de rodar: não volta no passo a passo.
    assert [p["tipo"] for p in atividade["pontos"]] == ["voltas", "valor", "valor"]
    assert atividade["palpite_inicial"]["resposta"]["texto"] == "A soma é 10"
    # Nada interno atravessa a ponte.
    for ponto in [atividade["palpite_inicial"], *atividade["pontos"]]:
        assert not [chave for chave in ponto if chave.startswith("_")]

    # A página aplica as dependências na cópia dela; o resultado aqui não mudou.
    assert not any("depende_de" in passo for passo in resultado["passos"])
    voltas = atividade["pontos"][0]
    for i, campos in atividade["depende_de_por_passo"].items():
        resultado["passos"][int(i)]["depende_de"] = campos
    entrada = resultado["passos"][voltas["passo"]]
    saida = entrada["volta"]["total_visivel_desde"]
    assert not visivel(entrada, "volta.total", set(), saida)
    assert visivel(entrada, "volta.total", {voltas["id"]}, saida)

    por_texto = {a["texto"]: a["id"] for a in voltas["alternativas"]}
    certa = resultado_de("corrigir", {"ponto_id": voltas["id"], "resposta": {"alternativa": por_texto["4"]}})
    assert certa["certa"] and certa["concepcao"] is None
    errada = resultado_de("corrigir", {"ponto_id": voltas["id"], "resposta": {"alternativa": por_texto["5"]}})
    assert errada["certa"] is False and errada["concepcao"] == "C01"
    assert errada["feedback"] and errada["mensagem"] == "Seu palpite: 5. O laço deu 4 voltas."
    assert not re.search(r"\bC\d\d\b", json.dumps(errada["feedback"], ensure_ascii=False))


def test_fluxo_com_resposta_livre_e_evento():
    codigo = 'pontos = input("Pontos: ")\nprint(pontos * 2)\n'
    resultado_de("rastrear", {"codigo": codigo, "entradas": ["4"]})
    atividade = resultado_de("preparar_atividade", {"config": {"formato": "livre", "palpite_inicial": False}})
    ponto = atividade["pontos"][0]
    assert ponto["formato"] == "livre" and "alternativas" not in ponto and ponto["sensivel_a_tipo"]

    certa = resultado_de("corrigir", {"ponto_id": ponto["id"], "resposta": {"texto": "4", "tipo_escolhido": "texto"}})
    assert certa["certa"] and certa["valor_normalizado"] == "4"
    errada = resultado_de("corrigir", {"ponto_id": ponto["id"], "resposta": {"texto": "4", "tipo_escolhido": "numero"}})
    assert errada["certa"] is False and errada["valor_certo"] and not errada["tipo_certo"]
    assert errada["concepcao"] == "C03" and errada["valor_normalizado"] == 4
    assert errada["mensagem"].endswith("O valor é esse, mas é texto, não número.")

    evento = resultado_de(
        "montar_evento",
        {
            "tipo": "Prediction",
            "contexto": CONTEXTO,
            "ts": 1_760_000_000_000,
            "campos": {
                "ponto": ponto["id"],
                "formato": "livre",
                "resposta": {"valor_normalizado": errada["valor_normalizado"], "tipo_escolhido": "texto"},
                "certa": errada["certa"],
                "concepcao": errada["concepcao"],
                "testadas": errada["testadas"],
            },
        },
    )
    assert resultado_de("validar_evento", {"evento": evento}) == []


def test_resposta_malformada_vira_erro():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    atividade = resultado_de("preparar_atividade", {"config": {"formato": "livre"}})
    resposta = pedir("corrigir", {"ponto_id": atividade["pontos"][0]["id"], "resposta": {"texto": 4}})
    assert resposta["ok"] is False and resposta["erro"].startswith("ValueError")


def test_config_invalida_vira_erro():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    assert pedir("preparar_atividade", {"config": {"modo": "estudo"}})["ok"] is False
    assert pedir("preparar_atividade", {"config": [1]})["erro"] == "ValueError: config precisa ser um objeto"


def test_rodar_de_novo_apaga_a_atividade_anterior():
    codigo, entradas, _ = EXEMPLOS_FIXOS["for"]
    resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    atividade = resultado_de("preparar_atividade")
    assert atividade["pontos"] and api.ultimo["pontos"]
    resultado_de("rastrear", {"codigo": "x = 1\n"})
    assert api.ultimo["atividade"] is None and api.ultimo["pontos"] == {}
    assert pedir("corrigir", {"ponto_id": "p2", "resposta": {"texto": "4"}})["ok"] is False


def test_assistir_nao_tem_pontos():
    codigo, entradas, _ = EXEMPLOS_FIXOS["maior"]
    resultado_de("rastrear", {"codigo": codigo, "entradas": entradas})
    atividade = resultado_de("preparar_atividade", {"config": {"modo": "assistir"}})
    assert atividade["pontos"] == [] and atividade["depende_de_por_passo"] == {}


# --- Sala, apelido e diário ------------------------------------------------------------------


def test_apelidos():
    apelido = resultado_de("gerar_apelido", {"semente": SUJEITO})
    assert apelido == resultado_de("gerar_apelido", {"semente": SUJEITO})
    assert resultado_de("validar_apelido", {"apelido": apelido}) is True
    assert resultado_de("validar_apelido", {"apelido": "Maria Silva"}) is False
    assert resultado_de("validar_apelido", {"apelido": resultado_de("gerar_apelido")}) is True
    sugestoes = resultado_de("sugerir_apelidos", {"semente": SUJEITO, "quantidade": 3})
    assert len(sugestoes) == 3 and sugestoes[0] == apelido and len(set(sugestoes)) == 3


def test_higienizar_e_code_hash():
    codigo = 'nome = "Ana"  # minha irmã\nprint(nome)\n'
    higienizado = resultado_de("higienizar", {"codigo": codigo})
    assert "Ana" not in higienizado and "irmã" not in higienizado and "<texto>" in higienizado
    assert resultado_de("code_hash", {"codigo": codigo}) == registro.hash_do_codigo(codigo)
    assert re.fullmatch(r"[0-9a-f]{16}", resultado_de("code_hash", {"codigo": codigo}))
    assert pedir("code_hash", {"codigo": None})["ok"] is False


def test_validar_evento_lista_os_problemas():
    assert resultado_de("validar_evento", {"evento": {"tipo": "Nada"}}) == ["tipo desconhecido"]
    evento = resultado_de("montar_evento", {"tipo": "Run.Program", "contexto": CONTEXTO, "ts": 1, "campos": {"ms": 30}})
    assert resultado_de("validar_evento", {"evento": evento}) == []
    assert pedir("montar_evento", {"tipo": "Run.Program", "contexto": {**CONTEXTO, "sala": "#"}})["ok"] is False


def test_resumo_sorteio_e_entrega():
    apelido = resultado_de("gerar_apelido", {"semente": SUJEITO})
    campos = {"ponto": "p2", "formato": "alternativas", "resposta": {"alternativa": "p2a1"}}
    eventos = [
        resultado_de("montar_evento", {"tipo": "Prediction", "contexto": CONTEXTO, "ts": 1, "campos": {**campos, "certa": False, "concepcao": "C01"}}),
        resultado_de("montar_evento", {"tipo": "Prediction", "contexto": CONTEXTO, "ts": 2, "campos": {**campos, "certa": True, "testadas": ["C04"]}}),
    ]
    resumo = resultado_de("resumo", {"eventos": eventos, "atividade": "aula3"})
    assert resumo["revisar"] == ["O range para antes do último número."]
    assert resumo["entendidas"] == ["Depois do =, a variável guarda só o valor novo."]
    assert resumo["numeros"]["palpites"] == 2

    condicoes = resultado_de("sortear_condicoes", {"sujeito": SUJEITO, "atividade": {"id": "aula3", "modo": "estudo", "programas": [1, 2, 3, 4]}})
    assert sorted(condicoes) == ["assistir", "assistir", "prever", "prever"]

    entrega = resultado_de("montar_entrega", {"apelido": apelido, "eventos": eventos})
    assert entrega["apelido"] == apelido and entrega["eventos"] == eventos
    assert pedir("montar_entrega", {"apelido": "Maria", "eventos": eventos})["ok"] is False


# --- O envelope JSON ---------------------------------------------------------------------


def test_id_volta_na_resposta():
    assert pedir("code_hash", {"codigo": "x = 1"}, id=7)["id"] == 7
    assert pedir("acao_que_nao_existe", {}, id="a1") == {"ok": False, "erro": "ValueError: ação desconhecida: acao_que_nao_existe", "id": "a1"}
    assert "id" not in pedir("code_hash", {"codigo": "x = 1"}, id=[1])


@pytest.mark.parametrize("pedido", ["isso não é json", "[1, 2]", '{"acao": "rastrear", "dados": [1]}', "null"])
def test_pedidos_quebrados(pedido):
    resposta = json.loads(api.executar_json(pedido))
    assert resposta["ok"] is False and resposta["erro"]


def test_erro_inesperado_nao_vaza_detalhes():
    original = api.ACOES["code_hash"]

    def quebrado(codigo):
        raise RuntimeError("caminho/secreto do aluno")

    api.ACOES["code_hash"] = quebrado
    try:
        resposta = pedir("code_hash", {"codigo": "x"})
    finally:
        api.ACOES["code_hash"] = original
    assert resposta == {"ok": False, "erro": "RuntimeError"}


def test_resposta_sem_nan():
    original = api.ACOES["code_hash"]
    api.ACOES["code_hash"] = lambda codigo: float("nan")
    try:
        resposta = pedir("code_hash", {"codigo": "x"})
    finally:
        api.ACOES["code_hash"] = original
    assert resposta["ok"] is False


def test_executar_direto_e_exportado_no_pacote():
    assert pyvis_motor.executar is api.executar and pyvis_motor.executar_json is api.executar_json
    assert pyvis_motor.api is api
    assert api.executar("code_hash", {"codigo": "x = 1"}) == registro.hash_do_codigo("x = 1")
    with pytest.raises(ValueError, match="dados precisa ser um objeto"):
        api.executar("code_hash", "x = 1")
    with pytest.raises(AttributeError):
        pyvis_motor.nao_existe  # noqa: B018
