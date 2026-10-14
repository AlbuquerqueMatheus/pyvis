"""As ações da área Praticar: o catálogo, a série de exercícios e o exercício.

A série sai só do banco (banco.py): sementes que já passaram na conferência
completa. A mesma (tema, nível, semente da série) dá sempre a mesma série,
em qualquer aparelho: é assim que o link do professor dá a mesma série para
a turma inteira. A ordem vem do sha256 de (semente da série, chave do item);
as famílias do tema se alternam e, dentro de cada família, os esqueletos
também (o mesmo programa com outros números não volta logo). Nada aqui é
gravado: o que o aluno já viu fica na memória da página e volta em `excluir`.

A chave de um item é "familia@versao:nivel:semente".
"""

import hashlib

from . import gerador, verificador
from .banco import BANCO
from .familias import FAMILIAS, NIVEIS, TEMAS

MAX_QUANTIDADE = 20
MAX_EXCLUIDOS = 500
MENSAGEM_RECUSADO = "este exercício não passou na conferência"


def _sorteio(*partes):
    return hashlib.sha256(":".join(str(parte) for parte in partes).encode("utf-8")).hexdigest()


def chave_do_banco(familia, nivel):
    return f"{familia}@{FAMILIAS[familia]['versao']}:{nivel}"


def catalogo():
    """{temas: [{id, nome, descricao, niveis: [{nivel, nome}]}], familias: {id: {versao, tema}}}."""
    return {
        "temas": [
            {
                "id": tema["id"],
                "nome": tema["nome"],
                "descricao": tema["descricao"],
                "niveis": [{"nivel": nivel, "nome": nome} for nivel, nome in sorted(tema["niveis"].items())],
            }
            for tema in TEMAS
        ],
        "familias": {familia: {"versao": dados["versao"], "tema": dados["tema"]} for familia, dados in sorted(FAMILIAS.items())},
    }


def _validar_serie(tema, nivel, semente, quantidade, familia, excluir):
    if tema not in [t["id"] for t in TEMAS]:
        raise ValueError(f"tema desconhecido: {tema!r}")
    if type(nivel) is not int or nivel not in NIVEIS:
        raise ValueError(f"nível precisa ser um de {NIVEIS}")
    if type(semente) is not int or not 0 <= semente <= gerador.SEMENTE_MAXIMA:
        raise ValueError(f"semente precisa ser um inteiro de 0 a {gerador.SEMENTE_MAXIMA}")
    if type(quantidade) is not int or not 1 <= quantidade <= MAX_QUANTIDADE:
        raise ValueError(f"quantidade precisa ser um inteiro de 1 a {MAX_QUANTIDADE}")
    if familia is not None and (familia not in FAMILIAS or FAMILIAS[familia]["tema"] != tema):
        raise ValueError(f"família desconhecida neste tema: {familia!r}")
    if not isinstance(excluir, (list, tuple)) or len(excluir) > MAX_EXCLUIDOS:
        raise ValueError(f"excluir precisa ser uma lista de até {MAX_EXCLUIDOS} chaves")
    if not all(isinstance(item, str) for item in excluir):
        raise ValueError("cada chave de excluir precisa ser texto")


def _alternar(filas):
    """Um item de cada fila por rodada: [[a1, a2], [b1]] dá [a1, b1, a2]."""
    return [fila[k] for k in range(max(map(len, filas), default=0)) for fila in filas if k < len(fila)]


def montar_serie(tema, nivel, semente, quantidade=5, familia=None, excluir=()):
    """Lista de {familia, versao, nivel, semente, chave}: os próximos itens da série, sem os excluídos.

    A série inteira tem uma ordem fixa para a semente; excluir só pula itens,
    sem mudar a ordem dos outros. Pode voltar com menos itens que
    `quantidade` (até vazia) quando o banco do tema e nível acabar.
    """
    _validar_serie(tema, nivel, semente, quantidade, familia, excluir)
    familias = [
        f for f, dados in FAMILIAS.items()
        if dados["tema"] == tema and nivel in dados["niveis"] and (familia is None or f == familia)
    ]
    filas = []
    for f in sorted(familias, key=lambda f: _sorteio(semente, f)):
        base = chave_do_banco(f, nivel)
        grupos = {}
        for s in BANCO.get(base, ()):
            grupos.setdefault(gerador.esqueleto_de(f, nivel, s), []).append(f"{base}:{s}")
        # Dentro da família, os esqueletos se alternam: o mesmo programa com outros
        # números só volta depois de todos os esqueletos dela.
        ordenados = sorted(grupos.items(), key=lambda par: _sorteio(semente, f, par[0]))
        filas.append(_alternar([sorted(grupo, key=lambda chave: _sorteio(semente, chave)) for _, grupo in ordenados]))
    # As famílias também se alternam: o 1º de cada uma, depois o 2º de cada uma...
    ordem = _alternar(filas)
    vistos = set(excluir)
    serie = []
    for chave in ordem:
        if chave in vistos:
            continue
        nome, resto = chave.split("@")
        versao, _, semente_do_item = resto.split(":")
        serie.append({"familia": nome, "versao": int(versao), "nivel": nivel, "semente": int(semente_do_item), "chave": chave})
        if len(serie) == quantidade:
            break
    return serie


def gerar_exercicio(familia, nivel, semente):
    """O exercício gerado; ValueError quando ele não passa na conferência.

    Semente do banco: só a conferência barata (escada e textos), porque a
    completa já rodou quando o banco foi gerado. Fora do banco: a completa.
    """
    exercicio = gerador.gerar(familia, nivel, semente)
    if semente in BANCO.get(chave_do_banco(familia, nivel), ()):
        motivos = verificador.conferir_rapido(exercicio)
    else:
        motivos = verificador.verificar(exercicio)["motivos"]
    if motivos:
        raise ValueError(MENSAGEM_RECUSADO)
    return exercicio
