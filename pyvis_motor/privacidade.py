"""Higiene do código antes de ele sair do aparelho.

Nomes, recados e telefones aparecem no código dos alunos dentro de textos e
comentários: print("Oi, Ana"), # feito pela Bia. Tudo o que sai do aparelho
(o código projetado, a exportação para pesquisa e o hash do código no diário)
passa antes por higienizar(): os comentários somem, cada texto (inclusive
f-string) vira <texto> e cada inteiro com 8 dígitos ou mais vira <numero>.

O caminho normal usa tokenize, o mesmo leitor do Python. Código com erro de
digitação pode quebrar o tokenize (um texto sem fechar) ou, no 3.11, ser lido
pela metade (uma f-string com aspas iguais dentro). Nesses casos entra uma
leitura própria, mais simples, que na dúvida apaga mais. Sem uma aspa, o
resto de um texto parece código, e não dá para saber onde o texto começava:
por isso cada linha onde começa um texto vira <texto> inteira, e um texto de
aspas triplas sem fechar apaga o programa todo.

Os nomes de variáveis e funções ficam como estão: são o próprio programa.
"""

import io
import itertools
import re
import tokenize

TEXTO = "<texto>"
NUMERO = "<numero>"
DIGITOS_DE_DOCUMENTO = 8  # telefone, CPF e RG têm 8 dígitos ou mais

# f-string (3.12+) e t-string (3.14+) chegam em pedaços, com as expressões no meio.
_ABRE = {getattr(tokenize, nome) for nome in ("FSTRING_START", "TSTRING_START") if hasattr(tokenize, nome)}
_FECHA = {getattr(tokenize, nome) for nome in ("FSTRING_END", "TSTRING_END") if hasattr(tokenize, nome)}

_PREFIXOS = frozenset({"r", "u", "b", "br", "rb", "f", "fr", "rf", "t", "tr", "rt"})
_ASPAS = "'\""
_NUMERO = re.compile(
    r"0[xXoObB][0-9a-fA-F_]+"
    r"|(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9][0-9_]*)(?:[eE][+-]?[0-9][0-9_]*)?[jJ]?"
)
_INTEIRO = re.compile(r"[0-9][0-9_]*")
_RECUO = re.compile(r"[ \t\f]*")


def higienizar(codigo):
    """Devolve o código sem comentários e com <texto> no lugar de cada texto."""
    texto = _linhas_unix(codigo)
    lido = _por_tokenize(texto)
    limpo = lido[0] if lido else _por_leitura_propria(texto)
    return "\n".join(linha.rstrip() for linha in limpo.split("\n")).rstrip("\n")


def forma_canonica(codigo):
    """O código higienizado numa forma só, para o mesmo programa dar o mesmo hash.

    Os tokens vão separados por um espaço, cada comando numa linha e o recuo de
    4 em 4: mudar espaços, linhas em branco, comentários ou o conteúdo de um
    texto não muda a forma.
    """
    texto = _linhas_unix(codigo)
    lido = _por_tokenize(texto)
    if lido:
        return lido[1]
    linhas = []
    for linha in _por_leitura_propria(texto).split("\n"):
        if linha.strip():
            linhas.append(_RECUO.match(linha).group() + " ".join(linha.split()))
    return "\n".join(linhas)


def _linhas_unix(codigo):
    return codigo.replace("\r\n", "\n").replace("\r", "\n")


def _documento(numero):
    return _INTEIRO.fullmatch(numero) is not None and len(numero.replace("_", "")) >= DIGITOS_DE_DOCUMENTO


def _fstring_cortada(token):
    # No 3.11, f"{d["Ana"]}" vira três tokens e "Ana" sairia como nome:
    # a primeira parte termina com uma chave aberta.
    prefixo = token[: len(token) - len(token.lstrip("rRbBuUfFtT"))].lower()
    if "f" not in prefixo:
        return False
    corpo = token[len(prefixo):]
    profundidade = 0
    i = 0
    while i < len(corpo):
        if profundidade == 0 and corpo.startswith(("{{", "}}"), i):
            i += 2
            continue
        if corpo[i] == "{":
            profundidade += 1
        elif corpo[i] == "}":
            profundidade -= 1
        i += 1
    return profundidade != 0


def _prefixo_solto(anterior, token):
    # Antes do 3.14, t"..." chega como o nome t seguido de um texto: o t vai junto.
    return (
        anterior is not None
        and anterior.type == tokenize.NAME
        and anterior.end == token.start
        and anterior.string.lower() in ("t", "tr", "rt")
    )


def _por_tokenize(texto):
    """(código higienizado, forma canônica), ou None quando o tokenize não deu conta."""
    inicio_da_linha = [0] + [achado.end() for achado in re.finditer("\n", texto)]

    def posicao(linha_coluna):
        linha, coluna = linha_coluna
        return inicio_da_linha[linha - 1] + coluna

    trocas = []  # (início, fim, novo) no texto original
    canonica, comando, nivel = [], [], 0
    profundidade = 0
    inicio_formatada = None
    try:
        tokens = tokenize.generate_tokens(io.StringIO(texto).readline)
        for anterior, token in itertools.pairwise(itertools.chain([None], tokens)):
            if token.type in _ABRE:
                if profundidade == 0:
                    inicio_formatada = token.start
                profundidade += 1
            elif token.type in _FECHA:
                profundidade -= 1
                if profundidade == 0:
                    trocas.append((posicao(inicio_formatada), posicao(token.end), TEXTO))
                    comando.append(TEXTO)
            elif profundidade:
                continue  # tudo dentro da f-string some junto com ela
            elif token.type == tokenize.STRING:
                if _fstring_cortada(token.string):
                    return None
                inicio = token.start
                if _prefixo_solto(anterior, token):
                    inicio = anterior.start
                    comando.pop()
                trocas.append((posicao(inicio), posicao(token.end), TEXTO))
                comando.append(TEXTO)
            elif token.type == tokenize.COMMENT:
                trocas.append((posicao(token.start), posicao(token.end), ""))
            elif token.type == tokenize.NUMBER and _documento(token.string):
                trocas.append((posicao(token.start), posicao(token.end), NUMERO))
                comando.append(NUMERO)
            elif token.type == tokenize.ERRORTOKEN:
                # No 3.11, uma aspa sem par vira ERRORTOKEN e o resto do texto sai como nomes.
                return None
            elif token.type == tokenize.INDENT:
                nivel += 1
            elif token.type == tokenize.DEDENT:
                nivel -= 1
            elif token.type == tokenize.NEWLINE:
                canonica.append("    " * nivel + " ".join(comando))
                comando = []
            elif token.type not in (tokenize.NL, tokenize.ENDMARKER):
                comando.append(token.string)
    except Exception:  # TokenError, IndentationError, bytes nulos...: a leitura própria resolve
        return None
    if profundidade:
        return None
    if comando:
        canonica.append("    " * nivel + " ".join(comando))

    partes = []
    atual = 0
    for inicio, fim, novo in trocas:
        partes.append(texto[atual:inicio])
        partes.append(novo)
        atual = fim
    partes.append(texto[atual:])
    return "".join(partes), "\n".join(canonica)


def _por_leitura_propria(texto):
    """Leitura caractere a caractere para código que o tokenize não lê.

    O código está quebrado, então um texto pode ter perdido uma aspa e o resto
    dele parecer código: toda linha onde começa um texto vira <texto> inteira,
    e um texto de aspas triplas sem fechar apaga o programa todo.
    """
    linhas = []
    atual = []
    com_texto = False
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        prefixo = None
        if c == "\n":
            linhas.append(_linha(atual, com_texto))
            atual, com_texto = [], False
            i += 1
        elif c == "#":
            fim = texto.find("\n", i)
            i = n if fim < 0 else fim
        elif c in _ASPAS:
            prefixo = ""
        elif c in "0123456789." and _NUMERO.match(texto, i):
            numero = _NUMERO.match(texto, i).group()
            atual.append(NUMERO if _documento(numero) else numero)
            i += len(numero)
        elif c.isalpha() or c == "_":
            fim = i + 1
            while fim < n and (texto[fim].isalnum() or texto[fim] == "_"):
                fim += 1
            palavra = texto[i:fim]
            if fim < n and texto[fim] in _ASPAS and palavra.lower() in _PREFIXOS:
                prefixo = palavra.lower()
            else:
                atual.append(palavra)
            i = fim
        else:
            atual.append(c)
            i += 1
        if prefixo is not None:
            fim, fechou = _fim_do_texto(texto, i, prefixo)
            if not fechou and texto.startswith(texto[i] * 3, i):
                return TEXTO
            com_texto = True
            i = fim
    linhas.append(_linha(atual, com_texto))
    return "\n".join(linhas)


def _linha(pedacos, com_texto):
    linha = "".join(pedacos)
    return _RECUO.match(linha).group() + TEXTO if com_texto else linha


def _fim_do_texto(texto, i, prefixo):
    """(posição depois do texto, se ele fechou). Sem fechar, vai até o fim da linha (ou do código, se tripla)."""
    aspa = texto[i]
    fecho = aspa * 3 if texto.startswith(aspa * 3, i) else aspa
    tripla = len(fecho) == 3
    formatado = "f" in prefixo or "t" in prefixo
    j, n = i + len(fecho), len(texto)
    while j < n:
        c = texto[j]
        if c == "\\":
            j += 2
        elif texto.startswith(fecho, j):
            return j + len(fecho), True
        elif c == "\n" and not tripla:
            return j, False
        elif formatado and c == "{":
            if texto.startswith("{{", j):
                j += 2
            else:
                j = _fim_da_expressao(texto, j + 1, tripla)
        else:
            j += 1
    return n, False


def _fim_da_expressao(texto, j, tripla):
    """Pula a expressão entre chaves de uma f-string (que pode ter textos com as mesmas aspas)."""
    profundidade = 0
    n = len(texto)
    while j < n:
        c = texto[j]
        if c in _ASPAS:
            j, fechou = _fim_do_texto(texto, j, "")
            if not fechou:
                return j
        elif c in "([{":
            profundidade += 1
            j += 1
        elif c in ")]}":
            if profundidade == 0:
                return j + 1
            profundidade -= 1
            j += 1
        elif c == "\n" and not tripla:
            return j
        else:
            j += 1
    return n
