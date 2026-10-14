"""Catálogo da área Praticar: os arquivos de famílias são só dados, no formato fechado do gerador."""

import ast
import copy
from pathlib import Path

import pytest

from pyvis_motor import familias, familias_condicoes, familias_lacos, familias_variaveis, gerador
from pyvis_motor.familias import FAMILIAS, LISTAS, NIVEIS, TEMAS

MOTOR = Path(__file__).resolve().parent.parent / "pyvis_motor"
MODULOS = {"variaveis": familias_variaveis, "condicoes": familias_condicoes, "lacos": familias_lacos}


def literal_de(texto):
    """O valor de FAMILIAS quando o arquivo só tem docstring, comentários e FAMILIAS = <literal>.

    Qualquer outro comando, ou um valor que não seja literal, é ValueError.
    """
    corpo = ast.parse(texto).body
    if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant):
        corpo = corpo[1:]
    if len(corpo) != 1 or not isinstance(corpo[0], ast.Assign):
        raise ValueError("o arquivo precisa ter um comando só: FAMILIAS = {...}")
    if [getattr(alvo, "id", None) for alvo in corpo[0].targets] != ["FAMILIAS"]:
        raise ValueError("o único comando é FAMILIAS = {...}")
    return ast.literal_eval(corpo[0].value)


@pytest.mark.parametrize("tema", sorted(MODULOS))
def test_arquivo_de_familias_so_tem_docstring_e_um_literal(tema):
    texto = (MOTOR / f"familias_{tema}.py").read_text(encoding="utf-8")
    assert literal_de(texto) == MODULOS[tema].FAMILIAS
    assert "versao" in ast.get_docstring(ast.parse(texto))  # o aviso das versões congeladas


@pytest.mark.parametrize("texto", [
    '"""Doc."""\nFAMILIAS = {}\nimport os\n',
    "FAMILIAS = {'a': len('x')}\n",
    "FAMILIAS = {'a': (lambda: 1)}\n",
    "def f():\n    pass\nFAMILIAS = {}\n",
    "OUTRA = {}\n",
    "FAMILIAS = OUTRA = {}\n",
])
def test_conferencia_de_literal_recusa_codigo(texto):
    with pytest.raises(ValueError):
        literal_de(texto)


def test_familias_py_so_tem_dados_e_a_juncao():
    arvore = ast.parse((MOTOR / "familias.py").read_text(encoding="utf-8"))
    for comando in arvore.body[1:]:
        if isinstance(comando, ast.ImportFrom):
            assert comando.module in ("familias_condicoes", "familias_lacos", "familias_variaveis")
            continue
        assert isinstance(comando, ast.Assign)
        nome = comando.targets[0].id
        if nome == "FAMILIAS":
            assert isinstance(comando.value, ast.Dict) and all(chave is None for chave in comando.value.keys)
        else:
            ast.literal_eval(comando.value)


def test_familias_juntam_os_tres_temas_sem_repetir_id():
    separadas = [m.FAMILIAS for m in MODULOS.values()]
    assert sum(len(f) for f in separadas) == len(FAMILIAS)
    for modulo in separadas:
        for familia, dados in modulo.items():
            assert FAMILIAS[familia] is dados


@pytest.mark.parametrize("familia", sorted(FAMILIAS))
def test_cada_familia_tem_formato_valido(familia):
    tema = FAMILIAS[familia]["tema"]
    assert familia in MODULOS[tema].FAMILIAS  # cada família mora no arquivo do seu tema
    assert gerador.problemas(familia, FAMILIAS[familia], tema) == []


def test_temas_e_niveis_tem_nome_de_conteudo():
    assert [tema["id"] for tema in TEMAS] == ["variaveis", "condicoes", "lacos"]
    for tema in TEMAS:
        assert set(tema) == {"id", "nome", "descricao", "niveis"}
        assert tuple(sorted(tema["niveis"])) == NIVEIS
        for nome in tema["niveis"].values():
            # O nível aparece pelo conteúdo, nunca pelo número.
            assert nome and not any(c.isdigit() for c in nome)
        assert tema["descricao"].endswith(".")


def test_listas_so_tem_nomes_sem_acento_e_sem_repetir():
    for nome, itens in LISTAS.items():
        assert isinstance(itens, tuple) and len(itens) >= 4, nome
        assert len(set(itens)) == len(itens), nome
        for item in itens:
            assert item.isascii() and item.strip() == item and item, (nome, item)
            assert all(c.isalnum() for c in item), (nome, item)


def test_cada_arquivo_de_tema_tem_um_dicionario():
    # Condições e Laços chegam em outras etapas; até lá o arquivo existe e é um dicionário.
    for modulo in MODULOS.values():
        assert isinstance(modulo.FAMILIAS, dict)
    assert familias.FAMILIAS is FAMILIAS


# --- O formato recusa o que não conhece -----------------------------------------------


def _uma_familia():
    return copy.deepcopy(FAMILIAS["robo_energia"])


def _primeiro(dados):
    esqueletos = list(dados["niveis"][1])
    esqueleto = dict(esqueletos[0])
    esqueletos[0] = esqueleto
    dados["niveis"][1] = tuple(esqueletos)
    return esqueleto


def test_formato_valido_passa():
    assert gerador.problemas("robo_energia", _uma_familia(), "variaveis") == []


def test_tema_errado_e_versao_invalida():
    dados = _uma_familia()
    assert gerador.problemas("robo_energia", dados, "lacos")
    dados["versao"] = 0
    assert any("versao" in p for p in gerador.problemas("robo_energia", dados))
    dados = _uma_familia()
    dados["extra"] = 1
    assert gerador.problemas("robo_energia", dados)
    assert gerador.problemas("Robo Energia", _uma_familia())


def test_chave_desconhecida_no_esqueleto():
    dados = _uma_familia()
    _primeiro(dados)["dica"] = "nao"
    assert any("chaves" in p for p in gerador.problemas("robo_energia", dados))


@pytest.mark.parametrize("lacuna", [
    ("texto", "robos"),
    ("lista", "planetas"),
    ("inteiro", 1, 9),
    ("inteiro", 9, 1, 1),
    ("inteiro", 1, 9, 0),
    ("inteiro", 1.0, 9, 1),
    ("inteiro", True, 9, 1),
    ("opcao", ()),
    ("opcao", ("+", 2)),
    ("opcao", ("maçã", "uva")),
    ["lista", "robos"],
])
def test_tipo_de_lacuna_desconhecido_ou_mal_formado(lacuna):
    dados = _uma_familia()
    _primeiro(dados)["lacunas"] = {**_primeiro(dados)["lacunas"], "robo": lacuna}
    assert gerador.problemas("robo_energia", dados)


def test_marcador_sem_lacuna_e_lacuna_sem_uso():
    dados = _uma_familia()
    esqueleto = _primeiro(dados)
    esqueleto["contexto"] = esqueleto["contexto"] + " {cor}"
    assert any("{cor} não tem lacuna" in p for p in gerador.problemas("robo_energia", dados))
    dados = _uma_familia()
    esqueleto = _primeiro(dados)
    esqueleto["lacunas"] = {**esqueleto["lacunas"], "sobrando": ("inteiro", 1, 2, 1)}
    assert any("sobrando nunca é usada" in p for p in gerador.problemas("robo_energia", dados))


@pytest.mark.parametrize("regras", [
    (("igual", "e", "g"),),
    (("menor", "e", "nao_existe"),),
    (("menor", "e"),),
    (("menor", "robo", "e"),),
    [("menor", "g", "e")],
])
def test_regra_desconhecida_ou_mal_formada(regras):
    dados = _uma_familia()
    _primeiro(dados)["regras"] = regras
    assert gerador.problemas("robo_energia", dados)


def test_menos_de_3_esqueletos_e_id_repetido():
    dados = _uma_familia()
    dados["niveis"][1] = dados["niveis"][1][:2]
    assert any("3 esqueletos" in p for p in gerador.problemas("robo_energia", dados))
    dados = _uma_familia()
    dados["niveis"][2] = (dict(dados["niveis"][2][0], id="gasto"),) + dados["niveis"][2][1:]
    assert any("repetidos" in p for p in gerador.problemas("robo_energia", dados))
    dados = _uma_familia()
    dados["niveis"][4] = dados["niveis"][1]
    assert gerador.problemas("robo_energia", dados)
