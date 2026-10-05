"""Traduz erros do Python para mensagens que um aluno de 10 a 17 anos entende."""

import re

NOMES_DE_TIPO = {
    "int": "número inteiro",
    "float": "número decimal",
    "str": "texto",
    "list": "lista",
    "dict": "dicionário",
    "tuple": "tupla",
    "bool": "verdadeiro/falso",
    "NoneType": "None (nada)",
}


def _tipo(nome):
    return NOMES_DE_TIPO.get(nome, nome)


def traduzir(erro):
    """Recebe a exceção e devolve uma mensagem amigável em português."""
    texto = str(erro)

    if isinstance(erro, IndentationError):
        return (
            "O espaçamento no começo da linha está estranho. Depois de uma linha que "
            "termina com dois-pontos (:), as linhas de dentro precisam começar mais para a direita, "
            "todas alinhadas igual."
        )

    if isinstance(erro, SyntaxError):
        if "expected ':'" in texto:
            return "Faltou os dois-pontos (:) no final da linha. Eles vêm depois de if, for, while, def e else."
        if "unterminated string" in texto or "EOL while scanning" in texto:
            return "Um texto foi aberto com aspas mas não foi fechado. Confira se as aspas estão em par."
        if "was never closed" in texto:
            return "Um parêntese, colchete ou chave foi aberto e não foi fechado."
        if "invalid syntax. Maybe you meant '==' or ':='" in texto or "cannot assign" in texto:
            return "Parece que você usou = (guardar valor) onde queria == (comparar)."
        return "O Python não conseguiu entender como esta linha foi escrita. Confira parênteses, aspas e dois-pontos."

    if isinstance(erro, NameError):
        nome = getattr(erro, "name", None)
        if nome is None:
            achado = re.search(r"name '(\w+)'", texto)
            nome = achado.group(1) if achado else "esse nome"
        return (
            f"Você usou `{nome}`, mas ele ainda não foi criado. Confira se o nome está escrito "
            f"igualzinho (maiúsculas contam!) e se ele recebe um valor antes desta linha."
        )

    if isinstance(erro, ZeroDivisionError):
        return "Não dá para dividir por zero! Confira o valor que está embaixo da divisão."

    if isinstance(erro, IndexError):
        return (
            "Você tentou pegar uma posição que não existe na lista. Lembre que a primeira "
            "posição é 0 e a última é o tamanho da lista menos 1."
        )

    if isinstance(erro, KeyError):
        return f"A chave {texto} não existe nesse dicionário."

    if isinstance(erro, TypeError):
        achado = re.search(r'can only concatenate (\w+) \(not "(\w+)"\) to \w+', texto)
        if achado:
            return (
                f"Não dá para juntar {_tipo(achado.group(1))} com {_tipo(achado.group(2))} usando +. "
                "Para juntar com texto, transforme o número com str(numero)."
            )
        achado = re.search(r"unsupported operand type\(s\) for (.+): '(\w+)' and '(\w+)'", texto)
        if achado:
            return (
                f"A conta {achado.group(1)} não funciona entre {_tipo(achado.group(2))} e "
                f"{_tipo(achado.group(3))}. Se um deles veio do input(), lembre de usar int() ou float()."
            )
        return "Você misturou tipos de valor que não combinam nessa operação."

    if isinstance(erro, ValueError):
        if "invalid literal for int()" in texto:
            return "O int() só transforma textos que são números inteiros, como \"42\". Esse texto não é um número."
        if "could not convert string to float" in texto:
            return "O float() só transforma textos que são números, como \"3.5\". Esse texto não é um número."
        return "Um valor chegou num formato que essa operação não aceita."

    if isinstance(erro, AttributeError):
        return "Esse tipo de valor não tem essa função ou propriedade. Confira se o nome depois do ponto está certo."

    if isinstance(erro, RecursionError):
        return "Uma função chamou a si mesma vezes demais, sem nunca parar."

    return "Aconteceu um erro que o PyVis ainda não sabe explicar."
