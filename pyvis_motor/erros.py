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
    """Recebe a exceção e devolve (mensagem, detalhe) em português.

    A mensagem é curta (até 12 palavras): é o que aparece na caixa de erro. O
    detalhe (às vezes vazio) explica mais e fica atrás de 'Mais detalhes'.
    """
    texto = str(erro)

    if isinstance(erro, IndentationError):
        if "unexpected indent" in texto:
            return "Esta linha começa com espaços sobrando.", "Tire os espaços do começo, ou alinhe com a linha de cima."
        if "expected an indented block" in texto:
            return (
                "Depois do dois-pontos (:), a próxima linha começa mais à direita.",
                "As linhas de dentro de um if, for, while ou def ficam todas alinhadas igual.",
            )
        if "unindent does not match" in texto:
            return (
                "O espaçamento desta linha não bate com o das outras.",
                "As linhas do mesmo bloco precisam começar na mesma coluna.",
            )
        if "tabs and spaces" in texto:
            return "Esta linha mistura tab e espaços no começo.", "Use só espaços para empurrar as linhas."
        return (
            "O espaçamento no começo desta linha está estranho.",
            "Depois de uma linha que termina com dois-pontos (:), as linhas de dentro precisam começar "
            "mais para a direita, todas alinhadas igual.",
        )

    if isinstance(erro, SyntaxError):
        if "expected ':'" in texto:
            return "Faltou o dois-pontos (:) no fim da linha.", "Ele vem depois de if, for, while, def e else."
        if "unterminated string" in texto or "EOL while scanning" in texto:
            return "Um texto abriu aspas e não fechou.", "Confira se as aspas estão em par."
        if "was never closed" in texto:
            return "Um parêntese, colchete ou chave abriu e não fechou.", "Confira se cada ( [ { tem o seu par."
        if "invalid syntax. Maybe you meant '==' or ':='" in texto or "cannot assign" in texto:
            return "Parece que você usou = onde queria ==.", "Um = guarda um valor. Dois == comparam dois valores."
        return "O Python não entendeu como esta linha foi escrita.", "Confira parênteses, aspas e dois-pontos."

    # UnboundLocalError é um NameError: precisa vir antes, com a explicação certa.
    if isinstance(erro, UnboundLocalError):
        achado = re.search(r"local variable '(\w+)'", texto)
        nome = achado.group(1) if achado else "essa variável"
        return (
            f"Dentro da função, `{nome} = ...` cria outra `{nome}`, só da função.",
            "Para usar a de fora, passe-a como parâmetro e devolva com return.",
        )

    if isinstance(erro, NameError):
        nome = getattr(erro, "name", None)
        if nome is None:
            achado = re.search(r"name '(\w+)'", texto)
            nome = achado.group(1) if achado else "esse nome"
        return (
            f"`{nome}` ainda não existe.",
            "Confira se o nome está escrito igualzinho (maiúsculas contam!) e se ele recebe um valor antes desta linha.",
        )

    if isinstance(erro, ModuleNotFoundError):
        return "Esse módulo não está disponível no PyVis.", ""

    if isinstance(erro, ImportError):
        achado = re.search(r"cannot import name '(\w+)'", texto)
        if achado:
            return f"Esse módulo não tem `{achado.group(1)}`.", "Confira se o nome está escrito certo."
        return "Esse módulo não está disponível no PyVis.", ""

    if isinstance(erro, ZeroDivisionError):
        return "Não dá para dividir por zero!", "Confira o valor que está embaixo da divisão."

    if isinstance(erro, IndexError):
        onde = "no texto" if texto.startswith("string") else "na tupla" if texto.startswith("tuple") else "na lista"
        return f"Essa posição não existe {onde}.", "A primeira posição é 0 e a última é o tamanho menos 1."

    if isinstance(erro, KeyError):
        return f"A chave {texto} não existe nesse dicionário.", ""

    if isinstance(erro, TypeError):
        achado = re.search(r'can only concatenate (\w+) \(not "(\w+)"\) to \w+', texto)
        if achado:
            return (
                f"Não dá para juntar {_tipo(achado.group(1))} com {_tipo(achado.group(2))} usando +.",
                "Para juntar com texto, transforme o número com str(numero).",
            )
        achado = re.search(r"unsupported operand type\(s\) for (.+): '(\w+)' and '(\w+)'", texto)
        if achado:
            return (
                f"A conta {achado.group(1)} não funciona entre {_tipo(achado.group(2))} e {_tipo(achado.group(3))}.",
                "Se um deles veio do input(), lembre de usar int() ou float().",
            )
        return "Você misturou tipos de valor que não combinam nessa operação.", ""

    if isinstance(erro, ValueError):
        if "invalid literal for int()" in texto:
            return "Esse texto não é um número inteiro.", 'O int() só transforma textos que são números inteiros, como "42".'
        if "could not convert string to float" in texto:
            return "Esse texto não é um número.", 'O float() só transforma textos que são números, como "3.5".'
        return "Um valor chegou num formato que essa operação não aceita.", ""

    if isinstance(erro, AttributeError):
        return "Esse valor não tem essa função ou propriedade.", "Confira se o nome depois do ponto está certo."

    if isinstance(erro, EOFError):
        return "O programa pediu mais respostas do que você digitou.", "Escreva uma resposta por linha."

    if isinstance(erro, RecursionError):
        return "Uma função chamou a si mesma vezes demais, sem nunca parar.", ""

    return "Aconteceu um erro que o PyVis ainda não sabe explicar.", ""
