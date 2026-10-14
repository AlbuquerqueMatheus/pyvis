"""Banco de sementes do Praticar: cada semente gera de novo e passa na conferência, em todo Python.

Este teste roda também dentro do Pyodide (scripts/pytest_pyodide.mjs): é ele
que garante que o banco gravado no CPython vale no navegador.
"""

import ast
from pathlib import Path

import pytest

from pyvis_motor import gerador, verificador
from pyvis_motor.banco import BANCO, IMPRESSOES
from pyvis_motor.familias import FAMILIAS

ARQUIVO = Path(__file__).resolve().parent.parent / "pyvis_motor" / "banco.py"


def _familia_e_nivel(chave):
    familia_e_versao, nivel = chave.split(":")
    familia, versao = familia_e_versao.split("@")
    return familia, int(versao), int(nivel)


def test_banco_py_so_tem_docstring_e_dois_literais():
    corpo = ast.parse(ARQUIVO.read_text(encoding="utf-8")).body
    assert len(corpo) == 3 and isinstance(corpo[0], ast.Expr)
    assert [comando.targets[0].id for comando in corpo[1:]] == ["BANCO", "IMPRESSOES"]
    assert ast.literal_eval(corpo[1].value) == BANCO
    assert ast.literal_eval(corpo[2].value) == IMPRESSOES


def test_chaves_do_banco_batem_com_o_catalogo():
    esperadas = {f"{f}@{d['versao']}:{n}" for f, d in FAMILIAS.items() for n in d["niveis"]}
    assert set(BANCO) == esperadas
    for chave, sementes in BANCO.items():
        assert isinstance(sementes, tuple) and len(sementes) == 40, chave
        assert list(sementes) == sorted(set(sementes)), chave  # as primeiras que passaram, em ordem
        assert all(type(s) is int and 0 <= s <= gerador.SEMENTE_MAXIMA for s in sementes)


@pytest.mark.parametrize("chave", sorted(BANCO))
def test_cada_item_do_banco_gera_de_novo_e_passa(chave):
    familia, versao, nivel = _familia_e_nivel(chave)
    assert FAMILIAS[familia]["versao"] == versao
    codigos = set()
    for semente in BANCO[chave]:
        exercicio = gerador.gerar(familia, nivel, semente)
        conferencia = verificador.verificar(exercicio)
        assert conferencia["ok"], (chave, semente, conferencia["motivos"])
        codigos.add(exercicio["codigo"])
    assert len(codigos) == len(BANCO[chave])  # programas distintos


@pytest.mark.parametrize("chave", sorted(BANCO))
def test_familia_publicada_nao_muda_sem_subir_a_versao(chave):
    # O link do professor guarda familia@versao e a semente: as mesmas sementes
    # precisam gerar os mesmos contextos e códigos (inclusive as LISTAS).
    familia, _, nivel = _familia_e_nivel(chave)
    assert set(IMPRESSOES) == set(BANCO)
    assert gerador.impressao(familia, nivel, BANCO[chave]) == IMPRESSOES[chave], (
        f"{chave}: mudou a família publicada sem subir a versao"
    )


def test_impressao_muda_quando_o_texto_muda():
    dados = FAMILIAS["robo_energia"]
    sementes = BANCO[f"robo_energia@{dados['versao']}:1"][:5]
    antes = gerador.impressao("robo_energia", 1, sementes)
    esqueletos = dados["niveis"][1]
    trocados = tuple(dict(e, contexto=e["contexto"] + " Pronto.") for e in esqueletos)
    dados["niveis"][1] = trocados
    try:
        assert gerador.impressao("robo_energia", 1, sementes) != antes
    finally:
        dados["niveis"][1] = esqueletos
    assert gerador.impressao("robo_energia", 1, sementes) == antes


def test_banco_usa_todos_os_esqueletos():
    for chave, sementes in BANCO.items():
        familia, _, nivel = _familia_e_nivel(chave)
        usados = {gerador.gerar(familia, nivel, s)["esqueleto"] for s in sementes}
        assert usados == {e["id"] for e in FAMILIAS[familia]["niveis"][nivel]}, chave
