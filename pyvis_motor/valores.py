"""Converte valores Python em dicionários simples, prontos para virar JSON.

Cada passo guarda uma cópia dos valores naquele momento. Sem essa cópia,
uma lista alterada depois apareceria alterada em todos os passos.

Cada valor convertido ganha `h`, um resumo curto do conteúdo: a interface
compara `h` para saber se uma caixinha mudou, sem comparar o valor inteiro.
"""

import math
import types
import zlib

PROFUNDIDADE_MAXIMA = 4
ITENS_MAXIMOS = 50
# Um texto enorme copiado em cada passo faria o rastro crescer sem limite: a
# caixinha mostra o começo, e o `h` continua sendo do texto inteiro.
LETRAS_MAXIMAS = 200
# Acima disso, o Python nem converte o inteiro em texto (limite de 4300 dígitos).
DIGITOS_MAXIMOS = 100
_PRIMO = 2**61 - 1
_RESUMOS_DE_TEXTO = {}  # id -> (texto, h): o mesmo texto longo não é resumido de novo a cada passo


_INICIO_DO_TIPO = {}  # crc32 de "tipo:", para continuar a conta sem juntar textos


def _resumo(texto, inicio=0):
    # crc32 é estável entre execuções (o hash() do Python muda a cada processo).
    return "%08x" % zlib.crc32(texto.encode("utf-8", "surrogatepass"), inicio)


def _simples(tipo, texto):
    inicio = _INICIO_DO_TIPO.get(tipo)
    if inicio is None:
        inicio = _INICIO_DO_TIPO[tipo] = zlib.crc32(f"{tipo}:".encode())
    return {"tipo": tipo, "valor": texto, "h": _resumo(texto, inicio)}


def com_aspas(texto):
    """'Ana' como os alunos escrevem: "Ana" (o repr do Python usa aspas simples).

    Caixinhas, narrador, perguntas e retornos usam o mesmo estilo: aspas
    diferentes pareceriam valores diferentes, justo nas perguntas de texto ou número.
    """
    representacao = repr(texto)
    if '"' in texto or "\\" in representacao:
        return representacao
    return f'"{texto}"'


def formatar(valor):
    """O valor como texto de código, com aspas duplas nos textos: ["a", 1]."""
    tipo = type(valor)
    if tipo is str:
        return com_aspas(valor)
    if tipo in (list, tuple):
        itens = [formatar(item) for item in valor]
        if tipo is tuple:
            return "(" + ", ".join(itens) + ("," if len(itens) == 1 else "") + ")"
        return "[" + ", ".join(itens) + "]"
    if tipo is dict:
        return "{" + ", ".join(f"{formatar(chave)}: {formatar(item)}" for chave, item in valor.items()) + "}"
    if tipo is set:
        return "{" + ", ".join(sorted(formatar(item) for item in valor)) + "}" if valor else "set()"
    return repr(valor)


def _digitos(numero):
    """Quantos dígitos tem o inteiro, sem convertê-lo em texto."""
    numero = abs(numero)
    if numero == 0:
        return 1
    digitos = int(numero.bit_length() * math.log10(2)) + 1
    return digitos - 1 if numero < 10 ** (digitos - 1) else digitos


def _inteiro(valor):
    tipo = type(valor).__name__
    if valor.bit_length() <= DIGITOS_MAXIMOS * 3:  # até uns 90 dígitos, o repr é barato e cabe na caixinha
        return _simples(tipo, repr(valor))
    digitos = _digitos(valor)
    if digitos <= DIGITOS_MAXIMOS:
        return _simples(tipo, repr(valor))
    convertido = _simples(tipo, f"um número com {digitos} dígitos")
    convertido["h"] = _resumo(f"{tipo}:{digitos}:{valor % _PRIMO}")
    convertido["cortado"] = True
    return convertido


def _texto_longo(valor):
    """O começo do texto (um literal válido, com '…' no fim) e o `h` do texto inteiro."""
    guardado = _RESUMOS_DE_TEXTO.get(id(valor))
    if guardado is None or guardado[0] is not valor:
        if len(_RESUMOS_DE_TEXTO) >= 16:
            _RESUMOS_DE_TEXTO.clear()
        guardado = _RESUMOS_DE_TEXTO[id(valor)] = (valor, _simples(type(valor).__name__, repr(valor))["h"])
    convertido = _simples(type(valor).__name__, repr(valor[:LETRAS_MAXIMAS] + "…"))
    convertido["h"] = guardado[1]
    convertido["cortado"] = True
    return convertido


def esquecer_textos():
    """Solta os textos longos guardados (fim de uma execução)."""
    _RESUMOS_DE_TEXTO.clear()


def converter(valor, profundidade=0):
    if isinstance(valor, int) and not isinstance(valor, bool):
        return _inteiro(valor)
    if isinstance(valor, str) and len(valor) > LETRAS_MAXIMAS:
        return _texto_longo(valor)
    if valor is None or isinstance(valor, (bool, float, str)):
        return _simples(type(valor).__name__, repr(valor))

    if profundidade >= PROFUNDIDADE_MAXIMA:
        return _simples(type(valor).__name__, "...")

    if isinstance(valor, (list, tuple, set)):
        itens = list(valor)
        if isinstance(valor, set):
            itens = sorted(itens, key=repr)
        convertidos = [converter(item, profundidade + 1) for item in itens[:ITENS_MAXIMOS]]
        cortado = len(itens) > ITENS_MAXIMOS
        tipo = type(valor).__name__
        resumo = _resumo(f"{tipo}[{','.join(item['h'] for item in convertidos)}{'+' if cortado else ''}]")
        return {"tipo": tipo, "itens": convertidos, "cortado": cortado, "h": resumo}

    if isinstance(valor, dict):
        pares = list(valor.items())
        convertidos = [
            [converter(chave, profundidade + 1), converter(item, profundidade + 1)]
            for chave, item in pares[:ITENS_MAXIMOS]
        ]
        cortado = len(pares) > ITENS_MAXIMOS
        pares_resumidos = ",".join(f"{chave['h']}:{item['h']}" for chave, item in convertidos)
        resumo = _resumo(f"dict{{{pares_resumidos}{'+' if cortado else ''}}}")
        return {"tipo": "dict", "pares": convertidos, "cortado": cortado, "h": resumo}

    if isinstance(valor, types.FunctionType):
        return _simples("function", f"função {valor.__name__}")

    try:
        texto = repr(valor)
    except Exception:  # um __repr__ quebrado do aluno não pode derrubar o rastreador
        texto = f"<{type(valor).__name__}>"
    convertido = _simples(type(valor).__name__, texto)
    if len(texto) > LETRAS_MAXIMAS:
        convertido["valor"] = texto[:LETRAS_MAXIMAS] + "…"
        convertido["cortado"] = True
    return convertido


def variaveis_visiveis(nomes_e_valores):
    """Filtra o que o aluno criou, escondendo módulos e nomes internos."""
    resultado = {}
    for nome, valor in nomes_e_valores.items():
        # Nomes como `.0` são variáveis internas das compreensões.
        if not isinstance(nome, str) or nome.startswith("__") or not nome.isidentifier():
            continue
        if isinstance(valor, types.ModuleType):
            continue
        resultado[nome] = converter(valor)
    return resultado
