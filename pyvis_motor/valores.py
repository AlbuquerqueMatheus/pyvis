"""Converte valores Python em dicionários simples, prontos para virar JSON.

Cada passo guarda uma cópia dos valores naquele momento. Sem essa cópia,
uma lista alterada depois apareceria alterada em todos os passos.
"""

import types

PROFUNDIDADE_MAXIMA = 4
ITENS_MAXIMOS = 50


def converter(valor, profundidade=0):
    if valor is None or isinstance(valor, (bool, int, float, str)):
        return {"tipo": type(valor).__name__, "valor": repr(valor)}

    if profundidade >= PROFUNDIDADE_MAXIMA:
        return {"tipo": type(valor).__name__, "valor": "..."}

    if isinstance(valor, (list, tuple, set)):
        itens = list(valor)
        if isinstance(valor, set):
            itens = sorted(itens, key=repr)
        return {
            "tipo": type(valor).__name__,
            "itens": [converter(item, profundidade + 1) for item in itens[:ITENS_MAXIMOS]],
            "cortado": len(itens) > ITENS_MAXIMOS,
        }

    if isinstance(valor, dict):
        pares = list(valor.items())
        return {
            "tipo": "dict",
            "pares": [
                [converter(chave, profundidade + 1), converter(item, profundidade + 1)]
                for chave, item in pares[:ITENS_MAXIMOS]
            ],
            "cortado": len(pares) > ITENS_MAXIMOS,
        }

    if isinstance(valor, types.FunctionType):
        return {"tipo": "function", "valor": f"função {valor.__name__}"}

    return {"tipo": type(valor).__name__, "valor": repr(valor)}


def variaveis_visiveis(nomes_e_valores):
    """Filtra o que o aluno criou, escondendo módulos e nomes internos."""
    resultado = {}
    for nome, valor in nomes_e_valores.items():
        if nome.startswith("__") or isinstance(valor, types.ModuleType):
            continue
        resultado[nome] = converter(valor)
    return resultado
