import re
import uuid

import pytest

from pyvis_motor import registro
from pyvis_motor.concepcoes import POR_ID
from pyvis_motor.registro import (
    hash_do_codigo,
    montar_entrega,
    montar_evento,
    registravel,
    resumo,
    sortear_condicoes,
    validar_evento,
)

SUJEITO = "3f2b8c1e-5d4a-4b7e-9c2d-1a2b3c4d5e6f"
CODIGO = 'nota = 7\nif nota >= 6:\n    print("Passou, Ana")\n'
CONTEXTO = {
    "sala": "TURMA8A",
    "sujeito": SUJEITO,
    "atividade": "aula3",
    "programa": 0,
    "condicao": "prever",
    "code_hash": hash_do_codigo(CODIGO),
}

EXTRAS_VALIDOS = {
    "Session.Start": {},
    "Run.Program": {"ms": 120},
    "Step": {"passo": 3, "ms": 900},
    "Prediction": {
        "ponto": "p1",
        "formato": "alternativas",
        "resposta": {"alternativa": "a2"},
        "certa": False,
        "concepcao": "C01",
        "testadas": ["C01", "C07"],
        "ms": 5300,
    },
    "Prediction.Skip": {"ponto": "p2", "formato": "livre", "ms": 800},
    "Feedback.Layer": {"ponto": "p1", "camada": 2, "concepcao": "C01"},
    "Error": {"erro": "NameError"},
}


def evento(tipo, ts=1_760_000_000_000, **extras):
    base = {"v": 1, "ts": ts, **CONTEXTO, "tipo": tipo}
    base.update(EXTRAS_VALIDOS[tipo] if not extras else extras)
    return base


def sujeito(k):
    return str(uuid.UUID(int=k * 7919 + 1, version=4))


# --- code_hash ---------------------------------------------------------------


def test_hash_tem_16_hex_e_e_igual_em_toda_versao():
    assert re.fullmatch(r"[0-9a-f]{16}", CONTEXTO["code_hash"])
    # Valor fixo: o mesmo no 3.11, no 3.14 e no Pyodide.
    assert hash_do_codigo("x = 1\n") == "8ff436def1451285"


def test_hash_ignora_espacos_comentarios_e_o_conteudo_dos_textos():
    outro = '# da Bia\nnota = 7\r\n\r\nif nota>=6:   # passou?\r\n  print( "Passou, Maria" )\r\n'
    assert hash_do_codigo(outro) == hash_do_codigo(CODIGO)


def test_hash_muda_quando_o_programa_muda():
    assert hash_do_codigo(CODIGO.replace("6", "5")) != hash_do_codigo(CODIGO)
    assert hash_do_codigo(CODIGO.replace("    print", "print")) != hash_do_codigo(CODIGO)


def test_hash_de_codigo_quebrado_tambem_funciona():
    assert hash_do_codigo('print("Olá Maria)\n') == hash_do_codigo('print("Oi Bia)\n')
    assert re.fullmatch(r"[0-9a-f]{16}", hash_do_codigo('x = """sem fim\n'))


# --- validar_evento ------------------------------------------------------------


@pytest.mark.parametrize("tipo", registro.TIPOS)
def test_eventos_validos_de_cada_tipo(tipo):
    assert validar_evento(evento(tipo)) == []


def test_inicio_da_sessao_pode_vir_sem_programa():
    inicio = evento("Session.Start")
    inicio.update(programa=None, condicao=None, code_hash=None)
    assert validar_evento(inicio) == []
    passo = evento("Step")
    passo.update(programa=None, condicao=None, code_hash=None)
    assert len(validar_evento(passo)) == 3


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("codigo", CODIGO),
        ("entradas", ["Ana"]),
        ("apelido", "Tucano Azul 7"),
        ("texto", "eu acho que é 5"),
        ("nome", "Maria"),
        ("saida", "Passou, Ana\n"),
        ("Maria Silva", 1),
    ],
)
def test_campo_fora_da_lista_e_recusado(campo, valor):
    problemas = validar_evento({**evento("Prediction"), campo: valor})
    assert problemas
    assert all("Maria" not in p and "Ana" not in p for p in problemas)


def test_falta_campo_comum_ou_obrigatorio():
    sem_sala = evento("Run.Program")
    del sem_sala["sala"]
    assert validar_evento(sem_sala) == ["falta o campo sala"]
    palpite = evento("Prediction")
    del palpite["certa"]
    assert validar_evento(palpite) == ["falta o campo certa"]
    assert validar_evento({"tipo": "Step"})


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("v", 2), ("v", True), ("v", "1"), ("v", 1.0),
        ("ts", -1), ("ts", 1.5), ("ts", "2026-10-05"), ("ts", True),
        ("sala", "Turma da Maria"), ("sala", "8"), ("sala", "TURMA8A" * 3), ("sala", "TURMÁ8"), ("sala", 8),
        ("sala", "-8A"),
        ("sala", "Tucano Azul 7"),
        ("sujeito", "maria"), ("sujeito", SUJEITO.upper()), ("sujeito", str(uuid.uuid1())), ("sujeito", SUJEITO + "\n"),
        ("atividade", "aula da Maria"), ("atividade", ""), ("atividade", "a" * 33),
        ("programa", -1), ("programa", 100), ("programa", "0"), ("programa", True),
        ("condicao", "estudo"), ("condicao", "Prever"), ("condicao", ["prever"]),
        ("code_hash", "abc"), ("code_hash", CONTEXTO["code_hash"].upper()), ("code_hash", CODIGO),
        ("tipo", "Chat"), ("tipo", "prediction"),
        ("ponto", "p0"), ("ponto", "x1"), ("ponto", "p1234"), ("ponto", 1),
        ("formato", "texto"),
        ("certa", 1), ("certa", "sim"),
        ("concepcao", "range-inclui-fim"), ("concepcao", "C1"),
        ("testadas", "C01"), ("testadas", ["C01", "C01"]), ("testadas", ["Maria"]),
        ("ms", -5), ("ms", 12.5),
    ],
)
def test_valor_invalido_e_recusado_sem_repetir_o_valor(campo, valor):
    problemas = validar_evento({**evento("Prediction"), campo: valor})
    assert problemas
    texto = repr(valor) if not isinstance(valor, str) else valor
    assert all(texto not in p for p in problemas if len(texto) > 3)


@pytest.mark.parametrize(
    "tipo, campo, valor",
    [
        ("Prediction", "camada", 1),
        ("Prediction", "erro", "NameError"),
        ("Step", "resposta", {"alternativa": "a1"}),
        ("Step", "certa", True),
        ("Run.Program", "ponto", "p1"),
        ("Session.Start", "ms", 10),
        ("Feedback.Layer", "resposta", {"alternativa": "a1"}),
        ("Error", "ms", 10),
    ],
)
def test_campo_de_outro_tipo_e_recusado(tipo, campo, valor):
    assert validar_evento({**evento(tipo), campo: valor})


@pytest.mark.parametrize("camada", [0, 4, True, "1"])
def test_camada_vai_de_1_a_3(camada):
    assert validar_evento({**evento("Feedback.Layer"), "camada": camada})


@pytest.mark.parametrize("erro, ok", [("ZeroDivisionError", True), ("LimiteDePassos", True), ("TempoEsgotado", True),
                                      ("Outro", True), ("ErroDaMaria", False), ("_IncompleteInputError", False)])
def test_erro_so_com_nome_conhecido(erro, ok):
    assert (validar_evento({**evento("Error"), "erro": erro}) == []) is ok


def test_apelido_nao_entra_em_nenhum_campo_de_texto():
    for tipo in registro.TIPOS:
        base = evento(tipo)
        for campo, valor in base.items():
            if isinstance(valor, str):
                assert validar_evento({**base, campo: "Tucano Azul 7"}), (tipo, campo)


def test_evento_que_nao_e_objeto():
    assert validar_evento(["Prediction"]) == ["o evento precisa ser um objeto"]
    assert validar_evento(None)


# --- resposta do palpite ---------------------------------------------------------


@pytest.mark.parametrize(
    "formato, resposta, ok",
    [
        ("alternativas", {"alternativa": "a2"}, True),
        ("alternativas", {"alternativa": 3}, True),
        ("alternativas", {"alternativa": "p3a2"}, True),
        ("alternativas", {"alternativa": "B"}, True),
        ("alternativas", {"alternativa": "Maria"}, False),
        ("alternativas", {"alternativa": ""}, False),
        ("alternativas", {"alternativa": "a2", "valor_normalizado": 5}, False),
        ("alternativas", {"valor_normalizado": 5}, False),
        ("livre", {"valor_normalizado": 5, "tipo_escolhido": "numero"}, True),
        ("livre", {"valor_normalizado": "11", "tipo_escolhido": "texto"}, True),
        ("livre", {"valor_normalizado": [1, 2, 3]}, True),
        ("livre", {"valor_normalizado": True}, True),
        ("livre", {"tipo_escolhido": "texto"}, True),
        ("livre", {"valor_normalizado": "Olá, Maria", "tipo_escolhido": "texto"}, False),
        ("livre", {"valor_normalizado": 11987654321, "tipo_escolhido": "numero"}, False),
        ("livre", {"valor_normalizado": 5, "tipo_escolhido": "lista"}, False),
        ("livre", {"alternativa": "a1"}, False),
        ("livre", {"texto": "5"}, False),
        ("livre", {}, False),
        ("livre", "5", False),
    ],
)
def test_resposta_do_palpite(formato, resposta, ok):
    palpite = {**evento("Prediction"), "formato": formato, "resposta": resposta}
    assert (validar_evento(palpite) == []) is ok


@pytest.mark.parametrize("tipo", ["Prediction", "Prediction.Skip", "Feedback.Layer"])
def test_palpite_e_detetive_so_em_prever(tipo):
    assert validar_evento({**evento(tipo), "condicao": "assistir"}) == [f"{tipo} só acontece na condição prever"]


@pytest.mark.parametrize("tipo", ["Run.Program", "Step", "Error"])
def test_assistir_tem_execucao_passos_e_erros(tipo):
    assert validar_evento({**evento(tipo), "condicao": "assistir"}) == []


def test_concepcao_so_em_palpite_errado():
    certo = {**evento("Prediction"), "certa": True}
    assert validar_evento(certo) == ["concepcao só vale para palpite errado (o certo usa testadas)"]
    certo["concepcao"] = None
    assert validar_evento(certo) == []


@pytest.mark.parametrize(
    "valor, ok",
    [
        (None, True), (True, True), (0, True), (-3, True), (7.5, True), (9_999_999, True),
        (10_000_000, False), (10**400, False), (float("nan"), False), (float("inf"), False),
        ("11", True), ("1 2 3", True), ("[1, 2]", True), ("3.5\n7", True), ("", True),
        ("Ana", False), ("ok 1", False), ("Ç", False), ("11987654321", False), ("x" * 61, False),
        ("1" * 7, True), ("9" * 60, False),
        ([1, [2, 3]], True), ([[[1]]], False), (list(range(21)), False), (["Ana"], False),
        ({"a": 1}, False), ((1, 2), False), (b"1", False),
    ],
)
def test_registravel(valor, ok):
    assert registravel(valor) is ok


# --- montar_evento e montar_entrega ---------------------------------------------


def test_montar_evento_pega_so_o_contexto_seguro():
    contexto = {**CONTEXTO, "apelido": "Tucano Azul 7", "codigo": CODIGO, "entradas": ["Ana"]}
    feito = montar_evento("Run.Program", contexto, ts=1_760_000_000_000, ms=40)
    assert feito == {"v": 1, "ts": 1_760_000_000_000, **CONTEXTO, "tipo": "Run.Program", "ms": 40}


def test_montar_evento_tira_resposta_com_letras_e_esconde_erro_do_aluno():
    palpite = montar_evento(
        "Prediction", CONTEXTO, ts=1, ponto="p1", formato="livre", certa=False, concepcao=None,
        resposta={"valor_normalizado": "Olá, Maria", "tipo_escolhido": "texto"},
    )
    assert palpite["resposta"] == {"tipo_escolhido": "texto"}
    assert "concepcao" not in palpite
    erro = montar_evento("Error", CONTEXTO, ts=1, erro="ErroDaMaria")
    assert erro["erro"] == "Outro"


def test_montar_evento_sem_ts_usa_o_relogio():
    feito = montar_evento("Step", CONTEXTO, passo=1)
    assert feito["ts"] > 1_700_000_000_000


def test_montar_evento_invalido_levanta_erro():
    with pytest.raises(ValueError, match="falta o campo ponto"):
        montar_evento("Prediction.Skip", CONTEXTO, ts=1)
    with pytest.raises(ValueError, match="contexto"):
        montar_evento("Step", CONTEXTO, ts=1, sala="OUTRA")
    with pytest.raises(ValueError):
        montar_evento("Step", {**CONTEXTO, "sala": "Turma da Maria"}, ts=1)


def test_entrega_leva_o_apelido_fora_dos_eventos():
    eventos = [evento("Session.Start"), evento("Prediction")]
    entrega = montar_entrega("Tucano Azul 7", eventos)
    assert entrega == {"v": 1, "apelido": "Tucano Azul 7", "eventos": eventos}
    assert all("apelido" not in e for e in entrega["eventos"])


def test_entrega_recusa_apelido_livre_evento_invalido_e_outro_aluno():
    with pytest.raises(ValueError, match="apelido"):
        montar_entrega("Maria Silva", [])
    with pytest.raises(ValueError, match="evento 1"):
        montar_entrega("Tucano Azul 7", [evento("Step"), {**evento("Step"), "codigo": CODIGO}])
    with pytest.raises(ValueError, match="mais de um aluno"):
        montar_entrega("Tucano Azul 7", [evento("Step"), {**evento("Step"), "sujeito": sujeito(1)}])


# --- resumo ----------------------------------------------------------------------


def palpite(ts, certa, concepcao=None, testadas=None, programa=0, atividade="aula3"):
    feito = {**evento("Prediction", ts=ts), "certa": certa, "programa": programa, "atividade": atividade}
    feito.pop("concepcao")
    feito.pop("testadas")
    if concepcao:
        feito["concepcao"] = concepcao
    if testadas:
        feito["testadas"] = testadas
    return feito


def regra(cid):
    return POR_ID[cid]["regra_para_aluno"]


def test_resumo_separa_ideias_entendidas_e_para_revisar():
    eventos = [
        palpite(1, True, testadas=["C01"]),
        palpite(2, False, concepcao="C03", testadas=["C03"]),
        palpite(3, True, testadas=["C07", "C08"]),
    ]
    feito = resumo(eventos)
    assert feito["entendidas"] == [regra("C01"), regra("C07"), regra("C08")]
    assert feito["revisar"] == [regra("C03")]


def test_resumo_vale_o_palpite_mais_recente():
    errou_e_acertou = [palpite(1, False, concepcao="C01"), palpite(2, True, testadas=["C01"])]
    assert resumo(errou_e_acertou)["entendidas"] == [regra("C01")]
    assert resumo(errou_e_acertou)["revisar"] == []
    acertou_e_errou = [palpite(1, True, testadas=["C01"]), palpite(2, False, concepcao="C01")]
    assert resumo(acertou_e_errou)["revisar"] == [regra("C01")]
    # A ordem do tempo vale mesmo se os eventos chegarem fora de ordem.
    assert resumo(list(reversed(acertou_e_errou)))["revisar"] == [regra("C01")]


def test_erro_sem_ideia_que_explique_nao_vira_ideia():
    # Honestidade diagnóstica: sem concepção, o resumo não inventa uma.
    feito = resumo([palpite(1, False, testadas=["C01"])])
    assert feito["entendidas"] == [] and feito["revisar"] == []
    assert feito["numeros"]["palpites"] == 1


def test_resumo_mostra_ideias_antes_dos_numeros_e_nunca_o_id():
    eventos = [
        evento("Session.Start"),
        evento("Run.Program"),
        palpite(2, True, testadas=["C02"]),
        palpite(3, False, concepcao="C05", programa=1),
        evento("Prediction.Skip"),
        evento("Feedback.Layer"),
        evento("Feedback.Layer"),
    ]
    feito = resumo(eventos)
    assert list(feito) == ["entendidas", "revisar", "numeros"]
    assert feito["numeros"] == {"programas": 2, "palpites": 2, "pulados": 1, "explicacoes": 2}
    texto = " ".join(feito["entendidas"] + feito["revisar"])
    assert not re.search(r"\bC\d{2}\b|apost|range-|input-e", texto, re.IGNORECASE)
    assert all(len(frase.split()) <= 12 for frase in feito["entendidas"] + feito["revisar"])


def test_resumo_ignora_invalido_ideia_sem_frase_e_outra_atividade():
    eventos = [
        {**palpite(1, False, concepcao="C01"), "codigo": CODIGO},
        palpite(2, False, concepcao="C99"),
        palpite(3, False, concepcao="C03", atividade="outra"),
        palpite(4, True, testadas=["C04"]),
    ]
    feito = resumo(eventos, atividade="aula3")
    assert feito["entendidas"] == [regra("C04")]
    assert feito["revisar"] == []
    assert feito["numeros"]["palpites"] == 2
    assert resumo(eventos)["revisar"] == [regra("C03")]


def test_resumo_com_frases_proprias_e_vazio():
    assert resumo([palpite(1, True, testadas=["C01"])], regras={"C01": "Regra um."})["entendidas"] == ["Regra um."]
    vazio = resumo([])
    assert vazio == {"entendidas": [], "revisar": [], "numeros": {"programas": 0, "palpites": 0, "pulados": 0,
                                                                   "explicacoes": 0}}


def test_titulos_do_resumo():
    assert registro.TITULO_ENTENDIDAS == "Ideias que você já entendeu"
    assert registro.TITULO_REVISAR == "Ideias para revisar"


# --- sortear_condicoes -------------------------------------------------------------


def atividade(n, modo="estudo", semente=2026, ident="aula3"):
    return {"v": 1, "id": ident, "programas": [{"ex": f"ex{k + 1}"} for k in range(n)], "modo": modo,
            "formato": "alternativas", "sala": "TURMA8A", "semente": semente}


def test_sorteio_e_deterministico_e_igual_em_toda_versao():
    assert sortear_condicoes(SUJEITO, atividade(4)) == sortear_condicoes(SUJEITO, atividade(4))
    # Valores fixos: sha256, o mesmo no 3.11, no 3.14 e no Pyodide.
    assert sortear_condicoes(SUJEITO, atividade(4)) == ["prever", "assistir", "prever", "assistir"]
    assert sortear_condicoes(SUJEITO, atividade(5)) == ["prever", "assistir", "prever", "assistir", "assistir"]


@pytest.mark.parametrize("n", range(1, 9))
def test_sorteio_balanceado_dentro_do_aluno(n):
    for k in range(50):
        condicoes = sortear_condicoes(sujeito(k), atividade(n))
        assert len(condicoes) == n
        assert set(condicoes) <= {"prever", "assistir"}
        assert abs(condicoes.count("prever") - condicoes.count("assistir")) == n % 2


def test_cada_programa_cai_nas_duas_condicoes_entre_alunos():
    alunos = [sujeito(k) for k in range(400)]
    sorteios = [sortear_condicoes(s, atividade(5)) for s in alunos]
    for posicao in range(5):
        prever = sum(c[posicao] == "prever" for c in sorteios)
        assert 0.35 < prever / len(alunos) < 0.65
    total = sum(c.count("prever") for c in sorteios)
    assert 0.45 < total / (5 * len(alunos)) < 0.55  # o programa do meio também é balanceado


def test_sorteio_muda_com_a_semente_e_com_a_atividade():
    alunos = [sujeito(k) for k in range(30)]
    base = [sortear_condicoes(s, atividade(4)) for s in alunos]
    assert [sortear_condicoes(s, atividade(4, semente=7)) for s in alunos] != base
    assert [sortear_condicoes(s, atividade(4, ident="aula4")) for s in alunos] != base


@pytest.mark.parametrize("modo", ["prever", "assistir"])
def test_fora_do_estudo_todos_seguem_o_modo(modo):
    assert sortear_condicoes(SUJEITO, atividade(3, modo=modo)) == [modo] * 3


@pytest.mark.parametrize("ruim", [{"programas": [], "modo": "estudo"}, {"programas": [{"ex": "ex1"}], "modo": "jogo"},
                                  {"programas": [{"ex": "ex1"}]}, {"modo": "estudo"}])
def test_sorteio_com_atividade_invalida(ruim):
    with pytest.raises(ValueError):
        sortear_condicoes(SUJEITO, ruim)
