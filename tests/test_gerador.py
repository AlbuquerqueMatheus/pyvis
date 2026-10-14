"""Gerador do Praticar: o mesmo (família, nível, semente) dá o mesmo exercício em qualquer Python."""

import ast
import hashlib

import pytest

from pyvis_motor import gerador
from pyvis_motor.familias import FAMILIAS, LISTAS


def _familia(regras=(), lacunas=None, versao=1):
    esqueleto = {
        "id": "teste",
        "contexto": "O robô {robo} conta {a} e {b}.",
        "codigo": 'robo = "{robo}"\na = {a}\nb = {b}\nprint(robo, a + b)\n',
        "lacunas": lacunas or {"robo": ("lista", "robos"), "a": ("inteiro", 1, 5, 1), "b": ("inteiro", 1, 5, 1)},
        "regras": regras,
    }
    return {"versao": versao, "tema": "variaveis", "niveis": {1: (esqueleto, dict(esqueleto, id="outro"), dict(esqueleto, id="mais"))}}


def _valores(exercicio):
    """a e b de volta, lidos do código gerado."""
    valores = {}
    for comando in ast.parse(exercicio["codigo"]).body:
        if isinstance(comando, ast.Assign):
            valores[comando.targets[0].id] = comando.value.value
    return valores


def test_versao_publicada_nao_muda():
    # Estes dois exercícios estão em links de professor: se mudarem, a família precisa de versão nova.
    assert gerador.gerar("robo_energia", 1, 0) == {
        "familia": "robo_energia", "versao": 1, "tema": "variaveis", "nivel": 1, "semente": 0,
        "esqueleto": "recarga", "contexto": "Zip carregou a bateria e depois fez uma tarefa.",
        "codigo": 'energia = 25\nenergia = energia + 30\nenergia = energia - 9\nprint("Zip tem", energia, "de energia")\n',
        "entradas": [],
    }
    exercicio = gerador.gerar("pet_lanche", 3, gerador.SEMENTE_MAXIMA)
    assert exercicio["esqueleto"] == "porcoes" and exercicio["contexto"] == "A ração de Mel virou partes iguais, e ele comeu uma."
    assert exercicio["codigo"].startswith("racao = 19\npartes = 4\n")


def test_mesma_entrada_mesmo_exercicio():
    for semente in (0, 1, 77, 123456789):
        assert gerador.gerar("pet_lanche", 2, semente) == gerador.gerar("pet_lanche", 2, semente)


def test_cada_escolha_sai_do_sha256_da_chave_de_texto():
    dados = FAMILIAS["robo_energia"]
    esqueletos = dados["niveis"][1]
    texto = "robo_energia@1:1:5:esqueleto"
    indice = int(hashlib.sha256(texto.encode()).hexdigest()[:12], 16) % len(esqueletos)
    exercicio = gerador.gerar("robo_energia", 1, 5)
    assert exercicio["esqueleto"] == esqueletos[indice]["id"]
    lacuna = next(e for e in esqueletos if e["id"] == exercicio["esqueleto"])["lacunas"]["robo"]
    robos = LISTAS[lacuna[1]]
    robo = robos[int(hashlib.sha256(b"robo_energia@1:1:5:0:robo").hexdigest()[:12], 16) % len(robos)]
    assert robo in exercicio["codigo"] or robo in exercicio["contexto"]


def test_todos_os_esqueletos_aparecem_e_os_programas_variam():
    for familia, dados in FAMILIAS.items():
        for nivel, esqueletos in dados["niveis"].items():
            gerados = [gerador.gerar(familia, nivel, s) for s in range(60)]
            assert {g["esqueleto"] for g in gerados} == {e["id"] for e in esqueletos}
            assert len({g["codigo"] for g in gerados}) >= 30
            for gerado in gerados:
                assert "{" not in gerado["codigo"] and "{" not in gerado["contexto"]
                assert gerado["entradas"] == [] and gerado["tema"] == dados["tema"]


def test_regras_sao_cumpridas_sorteando_de_novo():
    dados = _familia(regras=(("diferentes", "a", "b"), ("menor", "a", "b")))
    for semente in range(80):
        valores = _valores(gerador.montar("teste", dados, 1, semente))
        assert valores["a"] < valores["b"]


def test_regra_impossivel_e_value_error():
    lacunas = {"robo": ("lista", "robos"), "a": ("inteiro", 3, 3, 1), "b": ("inteiro", 1, 2, 1)}
    with pytest.raises(ValueError, match="não cumprem as regras"):
        gerador.montar("teste", _familia(regras=(("menor", "a", "b"),), lacunas=lacunas), 1, 0)


def test_opcao_entra_como_esta_e_inteiro_respeita_passo():
    lacunas = {"robo": ("opcao", ("Bip", "Nino")), "a": ("inteiro", 10, 30, 10), "b": ("inteiro", 1, 1, 1)}
    vistos = set()
    for semente in range(40):
        exercicio = gerador.montar("teste", _familia(lacunas=lacunas), 1, semente)
        valores = _valores(exercicio)
        assert valores["robo"] in ("Bip", "Nino") and valores["a"] in (10, 20, 30) and valores["b"] == 1
        vistos.add(valores["a"])
    assert vistos == {10, 20, 30}


def test_versao_nova_muda_o_sorteio():
    velhos = [gerador.montar("teste", _familia(versao=1), 1, s)["codigo"] for s in range(20)]
    novos = [gerador.montar("teste", _familia(versao=2), 1, s)["codigo"] for s in range(20)]
    assert velhos != novos


@pytest.mark.parametrize("familia, nivel, semente, trecho", [
    ("nao_existe", 1, 0, "família desconhecida"),
    (["robo_energia"], 1, 0, "família desconhecida"),
    ("robo_energia", 0, 0, "nível"),
    ("robo_energia", 4, 0, "nível"),
    ("robo_energia", "1", 0, "nível"),
    ("robo_energia", True, 0, "nível"),
    ("robo_energia", 1, -1, "semente"),
    ("robo_energia", 1, 2**32, "semente"),
    ("robo_energia", 1, 1.0, "semente"),
    ("robo_energia", 1, True, "semente"),
    ("robo_energia", 1, None, "semente"),
])
def test_pedido_invalido(familia, nivel, semente, trecho):
    with pytest.raises(ValueError, match=trecho):
        gerador.gerar(familia, nivel, semente)
