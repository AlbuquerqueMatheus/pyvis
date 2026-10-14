"""Gerador de exercícios da área Praticar: (família, nível, semente) -> exercício.

O mesmo trio dá sempre o mesmo exercício, em qualquer Python (3.11 a 3.14 e
o Pyodide): cada escolha sai do sha256 de um texto como
"robo_energia@1:2:17:0:robo" (família@versão, nível, semente, tentativa e o
nome da lacuna). O random.Random não serve: a sequência do randint e do
choice não é garantida entre versões do Python.

O esqueleto é sorteado uma vez; as lacunas são sorteadas de novo (com a
tentativa seguinte) até cumprirem as regras, no máximo TENTATIVAS vezes. Se
nenhuma tentativa cumprir, é ValueError: a família pede o impossível.

problemas() confere o formato de uma família (o teste e o script do banco
usam). O gerador não confere se o exercício presta: quem faz isso é o
verificador (verificador.py), rodando o programa no motor.
"""

import hashlib
import re

from .familias import FAMILIAS, LISTAS, NIVEIS, TEMAS

TENTATIVAS = 20
SEMENTE_MAXIMA = 2**32 - 1  # cabe num Uint32 do crypto.getRandomValues da página

CHAVES_DA_FAMILIA = ("versao", "tema", "niveis")
CHAVES_DO_ESQUELETO = ("id", "contexto", "codigo", "lacunas", "regras")
# Cada tipo de lacuna e os tipos dos campos depois do nome do tipo.
LACUNAS = {"lista": (str,), "inteiro": (int, int, int), "opcao": (tuple,)}
# Cada regra compara duas lacunas: diferentes (valores diferentes) e menor (a < b, inteiros).
REGRAS = ("diferentes", "menor")

_MARCADOR = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_ID = re.compile(r"[a-z][a-z0-9_]*")


def _sorteio(*partes):
    return hashlib.sha256(":".join(str(parte) for parte in partes).encode("utf-8")).hexdigest()


def _indice(tamanho, *partes):
    """Um índice de 0 a tamanho - 1 tirado do hash (o viés do resto é desprezível com 48 bits)."""
    return int(_sorteio(*partes)[:12], 16) % tamanho


def _opcoes(lacuna):
    tipo = lacuna[0]
    if tipo == "lista":
        return LISTAS[lacuna[1]]
    if tipo == "inteiro":
        return tuple(range(lacuna[1], lacuna[2] + 1, lacuna[3]))
    return lacuna[1]


def _cumpre(regra, valores):
    nome, a, b = regra
    if nome == "diferentes":
        return valores[a] != valores[b]
    return valores[a] < valores[b]


def _preencher(texto, valores):
    return _MARCADOR.sub(lambda achado: str(valores[achado.group(1)]), texto)


def _esqueleto(base, dados, nivel, semente):
    esqueletos = dados["niveis"][nivel]
    return esqueletos[_indice(len(esqueletos), base, nivel, semente, "esqueleto")]


def montar(familia, dados, nivel, semente):
    """O exercício de uma família já lida (dados = FAMILIAS[familia]). gerar() valida e chama esta."""
    base = f"{familia}@{dados['versao']}"
    esqueleto = _esqueleto(base, dados, nivel, semente)
    lacunas = esqueleto["lacunas"]
    for tentativa in range(TENTATIVAS):
        valores = {}
        for nome in sorted(lacunas):
            opcoes = _opcoes(lacunas[nome])
            valores[nome] = opcoes[_indice(len(opcoes), base, nivel, semente, tentativa, nome)]
        if all(_cumpre(regra, valores) for regra in esqueleto["regras"]):
            break
    else:
        raise ValueError(f"{familia} nível {nivel}: as lacunas de {esqueleto['id']} não cumprem as regras")
    return {
        "familia": familia,
        "versao": dados["versao"],
        "tema": dados["tema"],
        "nivel": nivel,
        "semente": semente,
        "esqueleto": esqueleto["id"],
        "contexto": _preencher(esqueleto["contexto"], valores),
        "codigo": _preencher(esqueleto["codigo"], valores),
        "entradas": [],
    }


def validar_pedido(familia, nivel, semente):
    """ValueError se a família não existe, o nível não é dela ou a semente sai da faixa."""
    if not isinstance(familia, str) or familia not in FAMILIAS:
        raise ValueError(f"família desconhecida: {familia!r}")
    if type(nivel) is not int or nivel not in FAMILIAS[familia]["niveis"]:
        raise ValueError(f"nível precisa ser um dos níveis da família: {sorted(FAMILIAS[familia]['niveis'])}")
    if type(semente) is not int or not 0 <= semente <= SEMENTE_MAXIMA:
        raise ValueError(f"semente precisa ser um inteiro de 0 a {SEMENTE_MAXIMA}")


def gerar(familia, nivel, semente):
    """{familia, versao, tema, nivel, semente, esqueleto, contexto, codigo, entradas: []}."""
    validar_pedido(familia, nivel, semente)
    return montar(familia, FAMILIAS[familia], nivel, semente)


def esqueleto_de(familia, nivel, semente):
    """O id do esqueleto que a semente sorteia, sem preencher as lacunas (a série usa para variar)."""
    validar_pedido(familia, nivel, semente)
    dados = FAMILIAS[familia]
    return _esqueleto(f"{familia}@{dados['versao']}", dados, nivel, semente)["id"]


def impressao(familia, nivel, sementes):
    """A impressão digital do que as sementes geram: o sha256 dos contextos e códigos, em ordem.

    O banco guarda a impressão de cada família@versão e nível. Se ela mudar sem
    a versão subir (outro texto, outra faixa, outra LISTA), um link de
    professor já mandado abriria outro exercício: o teste do banco e o
    --conferir de analise/verificar_familias.py acusam.
    """
    resumo = hashlib.sha256()
    for semente in sementes:
        exercicio = gerar(familia, nivel, semente)
        resumo.update(f"{semente}\0{exercicio['contexto']}\0{exercicio['codigo']}\0".encode("utf-8"))
    return resumo.hexdigest()[:16]


# --- Formato das famílias -------------------------------------------------------


def _problemas_da_lacuna(nome, lacuna):
    if not isinstance(lacuna, tuple) or not lacuna or lacuna[0] not in LACUNAS:
        return [f"lacuna {nome}: tipo desconhecido {lacuna!r}"]
    campos = LACUNAS[lacuna[0]]
    if len(lacuna) != len(campos) + 1 or not all(type(v) is t for v, t in zip(lacuna[1:], campos)):
        return [f"lacuna {nome}: formato errado para {lacuna[0]}: {lacuna!r}"]
    if lacuna[0] == "lista" and lacuna[1] not in LISTAS:
        return [f"lacuna {nome}: lista desconhecida {lacuna[1]!r}"]
    if lacuna[0] == "inteiro":
        minimo, maximo, passo = lacuna[1:]
        if passo < 1 or minimo > maximo:
            return [f"lacuna {nome}: faixa vazia {lacuna!r}"]
    if lacuna[0] == "opcao":
        opcoes = lacuna[1]
        if not opcoes or not all(isinstance(o, str) and o and o.isascii() for o in opcoes):
            return [f"lacuna {nome}: as opções precisam ser textos sem acento"]
    return []


def _problemas_do_esqueleto(esqueleto):
    if not isinstance(esqueleto, dict):
        return ["esqueleto não é um dicionário"]
    rotulo = f"esqueleto {esqueleto.get('id')!r}"
    problemas = []
    if tuple(sorted(esqueleto)) != tuple(sorted(CHAVES_DO_ESQUELETO)):
        return [f"{rotulo}: chaves precisam ser {CHAVES_DO_ESQUELETO}, vieram {tuple(esqueleto)}"]
    if not isinstance(esqueleto["id"], str) or not _ID.fullmatch(esqueleto["id"]):
        problemas.append(f"{rotulo}: id precisa ser minúsculo, sem acento e sem espaço")
    for campo in ("contexto", "codigo"):
        if not isinstance(esqueleto[campo], str) or not esqueleto[campo].strip():
            problemas.append(f"{rotulo}: {campo} precisa ser um texto")
    if problemas:
        return problemas
    if not esqueleto["codigo"].endswith("\n"):
        problemas.append(f"{rotulo}: o código termina com uma quebra de linha")
    lacunas = esqueleto["lacunas"]
    if not isinstance(lacunas, dict):
        return problemas + [f"{rotulo}: lacunas precisa ser um dicionário"]
    for nome, lacuna in lacunas.items():
        if not isinstance(nome, str) or not _ID.fullmatch(nome):
            problemas.append(f"{rotulo}: nome de lacuna inválido {nome!r}")
        problemas += [f"{rotulo}: {p}" for p in _problemas_da_lacuna(nome, lacuna)]
    usadas = set(_MARCADOR.findall(esqueleto["contexto"] + esqueleto["codigo"]))
    for nome in sorted(usadas - set(lacunas)):
        problemas.append(f"{rotulo}: {{{nome}}} não tem lacuna")
    for nome in sorted(set(lacunas) - usadas):
        problemas.append(f"{rotulo}: a lacuna {nome} nunca é usada")
    regras = esqueleto["regras"]
    if not isinstance(regras, tuple):
        return problemas + [f"{rotulo}: regras precisa ser uma tupla"]
    for regra in regras:
        if not (isinstance(regra, tuple) and len(regra) == 3 and regra[0] in REGRAS):
            problemas.append(f"{rotulo}: regra desconhecida {regra!r}")
        elif not {regra[1], regra[2]} <= set(lacunas):
            problemas.append(f"{rotulo}: a regra {regra!r} usa lacuna que não existe")
        elif regra[0] == "menor" and not all(lacunas[n][0] == "inteiro" for n in regra[1:]):
            problemas.append(f"{rotulo}: a regra menor só compara lacunas inteiras")
    return problemas


def problemas(familia, dados, tema=None):
    """Lista de problemas de formato da família (vazia quando está tudo certo)."""
    if not isinstance(familia, str) or not _ID.fullmatch(familia):
        return [f"id de família inválido: {familia!r}"]
    if not isinstance(dados, dict) or tuple(sorted(dados)) != tuple(sorted(CHAVES_DA_FAMILIA)):
        return [f"{familia}: chaves precisam ser {CHAVES_DA_FAMILIA}"]
    achados = []
    if type(dados["versao"]) is not int or dados["versao"] < 1:
        achados.append(f"{familia}: versao precisa ser um inteiro a partir de 1")
    temas = [t["id"] for t in TEMAS]
    if dados["tema"] not in temas or (tema is not None and dados["tema"] != tema):
        achados.append(f"{familia}: tema {dados['tema']!r} não é {tema or temas}")
    niveis = dados["niveis"]
    if not isinstance(niveis, dict) or not niveis or not set(niveis) <= set(NIVEIS):
        return achados + [f"{familia}: niveis precisa ter chaves entre {NIVEIS}"]
    ids = []
    for nivel, esqueletos in sorted(niveis.items()):
        if not isinstance(esqueletos, tuple) or len(esqueletos) < 3:
            achados.append(f"{familia} nível {nivel}: precisa de uma tupla com pelo menos 3 esqueletos")
            continue
        for esqueleto in esqueletos:
            achados += [f"{familia} nível {nivel}: {p}" for p in _problemas_do_esqueleto(esqueleto)]
            if isinstance(esqueleto, dict):
                ids.append(esqueleto.get("id"))
    repetidos = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    if repetidos:
        achados.append(f"{familia}: ids de esqueleto repetidos {repetidos}")
    return achados
