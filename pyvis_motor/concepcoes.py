"""Concepções equivocadas como modelos executáveis.

Uma concepção equivocada é um jeito coerente, mas errado, de pensar a
execução (Qian & Lehman, 2017). Aqui cada uma vira um programa: o código do
aluno é transformado para seguir aquela ideia (o range que chega até o fim,
o input que devolve número...) e roda de novo, com a mesma semente e as
mesmas entradas. Quando a versão transformada dá outra resposta num ponto
de previsão, essa resposta é um distrator diagnóstico: quem errou daquele
jeito provavelmente pensou daquele jeito. É a ideia dos bugs executáveis de
Brown & Burton (1978), trazida para a semântica do Python.

O modelo roda com rastrear_leve, que não tira fotos do estado: só conta as
ocorrências de cada comando e captura as respostas dos pontos pedidos. Um
ponto é achado no modelo pelo par (comando, ocorrência), então o modelo e o
programa de verdade precisam contar passos do mesmo jeito: rastrear_leve
reaproveita o gravador do rastreador e só troca o que ele guarda.

As referências de cada concepção indicam de onde ela veio para o catálogo.
"""

import ast
import builtins
import copy
import io
import random
import re
import time

from .avaliador import avaliar
from .estrutura import Analise
from .rastreador import (
    ARQUIVO_DO_ALUNO,
    GERADORES,
    LIMITE_PADRAO,
    OPERACOES_DE_RETORNO,
    LimiteDePassos,
    _deterministico,
    _dentro_do_laco,
    _Gravador,
    _input_com_entradas,
    _ligar_quadros,
    calcular_voltas,
    executar_isolado,
)
from .valores import formatar

LIMITE_LEVE = 200
TIPOS_DE_PONTO = ("valor", "decisao", "voltas", "saida")
LACOS = ("for", "while")
# O que o modelo insere fica numa linha que não é de nenhum comando do aluno,
# para não criar passos nem mudar a contagem de ocorrências.
LINHA_INSERIDA = 1_000_000
LIMITE_TEXTO = 60
# Dentro destas chamadas o aluno já sabe que o input é texto (ou não usa o valor como número).
CONVERSOES = frozenset({"int", "float", "str", "eval", "bool", "len", "list", "tuple", "set"})
FUNCOES_PURAS = frozenset({"len", "abs", "min", "max"})

_INTEIRO = re.compile(r"\s*[-+]?\d+\s*")
_DECIMAL = re.compile(r"\s*[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?\s*")


# --- Ajudantes que o programa transformado chama -----------------------------
# Não são código do aluno (o arquivo é outro), então não viram passos.


def _num(texto):
    """O input que 'devolve número': '12' vira 12, '2.5' vira 2.5 e 'Rex' continua texto."""
    if type(texto) is not str:
        return texto
    if _INTEIRO.fullmatch(texto):
        return int(texto)
    if _DECIMAL.fullmatch(texto):
        return float(texto)
    return texto


def _range_inclusivo(*limites):
    """range que chega até o último número: range(1, 5) dá 1, 2, 3, 4, 5."""
    if len(limites) == 1:
        return range(limites[0] + 1)
    inicio, fim, *passo = limites
    passo = passo[0] if passo else 1
    if type(passo) is int and passo < 0:
        return range(inicio, fim - 1, passo)
    return range(inicio, fim + 1, passo)


def _indice_de_1(colecao, indice):
    """lista[1] como se fosse o primeiro item. O 0 e os negativos ficam como estão."""
    if type(colecao) in (list, tuple, str) and type(indice) is int and indice >= 1:
        return colecao[indice - 1]
    return colecao[indice]


def _divisao_inteira(a, b):
    """a / b que corta a parte decimal quando os dois são inteiros."""
    if type(a) is int and type(b) is int:
        return a // b
    return a / b


AJUDANTES = {
    "_pyvis_num": _num,
    "_pyvis_range_inclusivo": _range_inclusivo,
    "_pyvis_indice": _indice_de_1,
    "_pyvis_div": _divisao_inteira,
}


# --- Onde cada concepção aparece no programa (padrao_ast) --------------------


def _e_chamada(no, nome):
    return isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == nome


def _e_range(no):
    return (
        _e_chamada(no, "range")
        and not no.keywords
        and 1 <= len(no.args) <= 3
        and not any(isinstance(a, ast.Starred) for a in no.args)
    )


def _redefinido(arvore, nome):
    """O aluno criou algo com esse nome: o modelo não pode supor que é o embutido."""
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name) and no.id == nome and not isinstance(no.ctx, ast.Load):
            return True
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and no.name == nome:
            return True
        if isinstance(no, ast.arg) and no.arg == nome:
            return True
        if isinstance(no, ast.alias) and (no.asname or no.name) == nome:
            return True
    return False


def _ranges(analise):
    if _redefinido(analise.arvore, "range"):
        return []
    return [no for no in ast.walk(analise.arvore) if _e_range(no)]


def _ranges_de_um_numero(analise):
    return [no for no in _ranges(analise) if len(no.args) == 1]


def _inputs_livres(arvore):
    """input() que o programa usa direto, sem int(), float() nem .split() em volta."""
    protegidos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in CONVERSOES:
            protegidos.update(id(a) for a in no.args if _e_chamada(a, "input"))
        elif isinstance(no, ast.Attribute) and _e_chamada(no.value, "input"):
            protegidos.add(id(no.value))
    return [no for no in ast.walk(arvore) if _e_chamada(no, "input") and id(no) not in protegidos]


def _inputs(analise):
    if _redefinido(analise.arvore, "input"):
        return []
    return _inputs_livres(analise.arvore)


def _atribuicoes(analise):
    return [analise.nos[c["id"]] for c in analise.comandos if c["tipo"] in ("atrib", "aug")]


def _cadeia(no, elifs):
    """O if e os elif que vêm atrás dele, até o else (ou o fim)."""
    cadeia = [no]
    while len(cadeia[-1].orelse) == 1 and (cadeia[-1].orelse[0].lineno, cadeia[-1].orelse[0].col_offset) in elifs:
        cadeia.append(cadeia[-1].orelse[0])
    return cadeia


def _posicoes_de_elif(analise):
    return _posicoes(analise.nos[c["id"]] for c in analise.comandos if c["tipo"] == "elif")


def _ifs_com_else(analise):
    """if (com seus elif) que termina num else de verdade."""
    elifs = _posicoes_de_elif(analise)
    return [
        analise.nos[c["id"]]
        for c in analise.comandos
        if c["tipo"] == "if" and _cadeia(analise.nos[c["id"]], elifs)[-1].orelse
    ]


def _condicao_pura(teste):
    """Conferir a condição de novo não pode ter efeito: nada de input(), métodos ou :=."""
    for no in ast.walk(teste):
        if isinstance(no, ast.Call) and not (isinstance(no.func, ast.Name) and no.func.id in FUNCOES_PURAS):
            return False
        if isinstance(no, (ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom, ast.Lambda)):
            return False
    return True


def _whiles_observaveis(analise):
    """while em que a condição pode ficar falsa no meio do corpo (2 ou mais comandos)."""
    return [
        analise.nos[c["id"]]
        for c in analise.comandos
        if c["tipo"] == "while"
        and not c["corpo_mesma_linha"]
        and len(analise.nos[c["id"]].body) >= 2
        and _condicao_pura(analise.nos[c["id"]].test)
    ]


def _e_leitura_por_posicao(no):
    return (
        isinstance(no, ast.Subscript)
        and isinstance(no.ctx, ast.Load)
        and not isinstance(no.slice, ast.Slice)
        and not (isinstance(no.slice, ast.Constant) and isinstance(no.slice.value, str))
    )


def _leituras_por_posicao(analise):
    return [no for no in ast.walk(analise.arvore) if _e_leitura_por_posicao(no)]


def _divisoes(analise):
    return [
        no
        for no in ast.walk(analise.arvore)
        if (isinstance(no, ast.BinOp) and isinstance(no.op, ast.Div))
        or (isinstance(no, ast.AugAssign) and isinstance(no.op, ast.Div) and isinstance(no.target, ast.Name))
    ]


def _posicoes(nos):
    return {(no.lineno, no.col_offset) for no in nos}


# --- Transformações ----------------------------------------------------------


def _chamar(nome, argumentos, modelo):
    """Chamada a um ajudante, na mesma posição do nó que ela substitui."""
    return ast.copy_location(ast.Call(func=ast.Name(nome, ast.Load()), args=argumentos, keywords=[]), modelo)


class _Transformacao(ast.NodeTransformer):
    """Base: transforma uma cópia da árvore, sem mexer na do programa de verdade."""

    def __init__(self, analise):
        self.analise = analise

    def aplicar(self, arvore):
        return ast.fix_missing_locations(self.visit(copy.deepcopy(arvore)))


class RangeIncluiFim(_Transformacao):
    """C01: range(a, b) vira range(a, b + 1); range(n) vira range(n + 1)."""

    def visit_Call(self, no):
        self.generic_visit(no)
        if _e_range(no):
            return _chamar("_pyvis_range_inclusivo", no.args, no)
        return no


class RangeComecaEm1(_Transformacao):
    """C02: range(n) vira range(1, n + 1)."""

    def visit_Call(self, no):
        self.generic_visit(no)
        if _e_range(no) and len(no.args) == 1:
            fim = no.args[0]
            um = ast.copy_location(ast.Constant(1), fim)
            no.args = [um, ast.copy_location(ast.BinOp(fim, ast.Add(), ast.Constant(1)), fim)]
        return no


class InputENumero(_Transformacao):
    """C03: um input(...) fora de int() ou float() vira _num(input(...))."""

    def aplicar(self, arvore):
        copia = copy.deepcopy(arvore)
        self.livres = {id(no) for no in _inputs_livres(copia)}
        return ast.fix_missing_locations(self.visit(copia))

    def visit_Call(self, no):
        self.generic_visit(no)
        if id(no) in self.livres:
            return _chamar("_pyvis_num", [no], no)
        return no


class ElseTambemRoda(_Transformacao):
    """C05: o else roda depois de qualquer caminho do if/elif, como se não dependesse da condição."""

    def __init__(self, analise):
        super().__init__(analise)
        self.cabecas = _posicoes(_ifs_com_else(analise))
        self.elifs = _posicoes_de_elif(analise)

    def visit_If(self, no):
        self.generic_visit(no)
        if (no.lineno, no.col_offset) in self.cabecas:
            cadeia = _cadeia(no, self.elifs)
            senao = cadeia[-1].orelse
            for ramo in cadeia:
                # A cópia guarda as linhas do else: cada comando continua sendo o mesmo comando.
                ramo.body = ramo.body + copy.deepcopy(senao)
        return no


class WhileVigiaCondicao(_Transformacao):
    """C06: depois de cada comando do corpo, `if not (condição): break`."""

    def __init__(self, analise):
        super().__init__(analise)
        self.alvos = _posicoes(_whiles_observaveis(analise))

    def visit_While(self, no):
        self.generic_visit(no)
        if (no.lineno, no.col_offset) in self.alvos:
            corpo = []
            for comando in no.body:
                corpo += [comando, _vigia(no.test)]
            no.body = corpo
        return no


def _vigia(teste):
    vigia = ast.If(test=ast.UnaryOp(ast.Not(), copy.deepcopy(teste)), body=[ast.Break()], orelse=[])
    for no in ast.walk(vigia):
        if "lineno" in no._attributes:
            no.lineno = no.end_lineno = LINHA_INSERIDA
            no.col_offset = no.end_col_offset = 0
    return vigia


class IndiceComecaEm1(_Transformacao):
    """C07: lista[i] numa leitura vira lista[i - 1] (só em list, tuple e str, com i >= 1)."""

    def visit_Subscript(self, no):
        self.generic_visit(no)
        if _e_leitura_por_posicao(no):
            return _chamar("_pyvis_indice", [no.value, no.slice], no)
        return no


class DivisaoInteira(_Transformacao):
    """C08: a / b entre inteiros vira a // b."""

    def visit_BinOp(self, no):
        self.generic_visit(no)
        if isinstance(no.op, ast.Div):
            return _chamar("_pyvis_div", [no.left, no.right], no)
        return no

    def visit_AugAssign(self, no):
        self.generic_visit(no)
        if isinstance(no.op, ast.Div) and isinstance(no.target, ast.Name):
            leitura = ast.copy_location(ast.Name(no.target.id, ast.Load()), no.target)
            return ast.copy_location(ast.Assign(targets=[no.target], value=_chamar("_pyvis_div", [leitura, no.value], no)), no)
        return no


# --- Concepção sem transformação: lida direto do rastro ----------------------


def _nomes_atribuidos(no):
    alvos = no.targets if isinstance(no, ast.Assign) else [getattr(no, "target", None)]
    return {n.id for alvo in alvos if alvo is not None for n in ast.walk(alvo) if isinstance(n, ast.Name)}


def _valor_antigo(alvo, real, analise):
    """C04: a variável continua com o valor de antes da atribuição."""
    if alvo["tipo"] != "valor" or alvo.get("comando") is None:
        return None
    comando = analise.comandos[alvo["comando"]]
    if comando["tipo"] not in ("atrib", "aug") or alvo.get("nome") not in _nomes_atribuidos(analise.nos[comando["id"]]):
        return None
    return real["antes"].get(alvo["id"])


# --- Catálogo ----------------------------------------------------------------
# `camadas.onde` diz qual caixinha ganha contorno: a do ponto ('alvo'), a da
# variável do laço ('laco'), a da lista ('lista') ou a que recebeu o input ('entrada').
# Os modelos de frase usam {valores} da execução e do código; `crenca` completa
# "Será que você pensou que ...?". Nenhum texto para o aluno mostra id ou nome técnico.

SWIDAN_2018 = "Swidan, Hermans & Smit (2018). Programming Misconceptions for School Students. ICER."
QIAN_LEHMAN_2017 = "Qian & Lehman (2017). Students' Misconceptions and Other Difficulties in Introductory Programming. ACM TOCE 18(1)."
PEA_1986 = "Pea (1986). Language-Independent Conceptual 'Bugs' in Novice Programming. JECR 2(1)."
PROGMISCON = "progmiscon.org: catálogo de concepções equivocadas em Python."
CORTINOVIS_2023 = "Cortinovis, Frank Bolton & Caceffo (2023). EDUCOMP."

CATALOGO = [
    {
        "id": "C01",
        "nome": "range-inclui-fim",
        "regra_para_aluno": "O range para antes do último número.",
        "crenca": "o `{range}` chegava até o `{fim}`",
        "camadas": {
            "onde": "laco",
            "regra": "O `{range}` para antes do `{fim}`. O `{fim}` nunca entra.",
            "resolvido": "{certa_frase} O último número vem antes do `{fim}`.",
        },
        "transformar": RangeIncluiFim,
        "regra_rastro": None,
        "observavel_em": ["voltas", "valor", "saida", "decisao"],
        "padrao_ast": _ranges,
        "referencias": [PROGMISCON, CORTINOVIS_2023],
    },
    {
        "id": "C02",
        "nome": "range-comeca-em-1",
        "regra_para_aluno": "Com um número só, o range começa no 0.",
        "crenca": "o `{range}` começava no 1",
        "camadas": {
            "onde": "laco",
            "regra": "O `{range}` começa no 0 e para antes do `{fim}`.",
            "resolvido": "{certa_frase} A contagem começa no 0.",
        },
        "transformar": RangeComecaEm1,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao", "voltas"],
        "padrao_ast": _ranges_de_um_numero,
        "referencias": [PROGMISCON, CORTINOVIS_2023],
    },
    {
        "id": "C03",
        "nome": "input-e-numero",
        "regra_para_aluno": "O input sempre devolve texto, mesmo quando você digita número.",
        "crenca": "o `input` devolvia um número",
        "camadas": {
            "onde": "entrada",
            "regra": "O `input` devolve texto, mesmo que você digite um número. Para virar número, use `int(...)`.",
            "resolvido": "{certa_frase} O que vem do `input` é texto.",
        },
        "transformar": InputENumero,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao"],
        "padrao_ast": _inputs,
        "referencias": [PROGMISCON, CORTINOVIS_2023],
    },
    {
        "id": "C04",
        "nome": "atribuicao-nao-muda",
        "regra_para_aluno": "Depois do =, a variável guarda só o valor novo.",
        "crenca": "`{nome}` continuava com o valor antigo",
        "camadas": {
            "onde": "alvo",
            "regra": "O `=` troca o valor: `{nome}` valia {antes} e passa a valer {certa}.",
            "resolvido": "{certa_frase} O valor antigo, {antes}, foi trocado.",
        },
        "transformar": None,
        "regra_rastro": _valor_antigo,
        "observavel_em": ["valor"],
        "padrao_ast": _atribuicoes,
        "referencias": [SWIDAN_2018, QIAN_LEHMAN_2017],
    },
    {
        "id": "C05",
        "nome": "else-tambem-roda",
        "regra_para_aluno": "O else só roda quando a condição do if é falsa.",
        "crenca": "o else também rodava depois do if",
        "camadas": {
            "onde": "alvo",
            "regra": "O Python escolhe um caminho só. Se o if ou um elif entra, o else é pulado.",
            "resolvido": "{certa_frase} Só um dos caminhos rodou.",
        },
        "transformar": ElseTambemRoda,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao"],
        "padrao_ast": _ifs_com_else,
        "referencias": [QIAN_LEHMAN_2017, PROGMISCON],
    },
    {
        "id": "C06",
        "nome": "while-vigia-condicao",
        "regra_para_aluno": "O while só confere a condição no começo de cada volta.",
        "crenca": "o while parava no meio da volta",
        "camadas": {
            "onde": "alvo",
            "regra": "O `{condicao}` só é conferido no começo da volta. A volta termina inteira.",
            "resolvido": "{certa_frase} A volta terminou antes de conferir de novo.",
        },
        "transformar": WhileVigiaCondicao,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao", "voltas"],
        "padrao_ast": _whiles_observaveis,
        "referencias": [PEA_1986, QIAN_LEHMAN_2017],
    },
    {
        "id": "C07",
        "nome": "indice-comeca-em-1",
        "regra_para_aluno": "Numa lista, a primeira posição é a 0.",
        "crenca": "a posição 1 era a do primeiro item",
        "camadas": {
            "onde": "lista",
            "regra": "Em `{acesso}`, as posições começam no 0. A posição 1 é a do segundo item.",
            "resolvido": "{certa_frase} A posição 0 é a do primeiro item.",
        },
        "transformar": IndiceComecaEm1,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao", "voltas"],
        "padrao_ast": _leituras_por_posicao,
        "referencias": [QIAN_LEHMAN_2017, PROGMISCON],
    },
    {
        "id": "C08",
        "nome": "divisao-inteira",
        "regra_para_aluno": "A divisão com / sempre dá número decimal.",
        "crenca": "o `/` cortava a parte decimal",
        "camadas": {
            "onde": "alvo",
            "regra": "Em `{conta}`, o `/` guarda a parte decimal. Quem corta é o `//`.",
            "resolvido": "{certa_frase} O `/` manteve a parte decimal.",
        },
        "transformar": DivisaoInteira,
        "regra_rastro": None,
        "observavel_em": ["valor", "saida", "decisao", "voltas"],
        "padrao_ast": _divisoes,
        "referencias": [PROGMISCON, CORTINOVIS_2023],
    },
]

POR_ID = {concepcao["id"]: concepcao for concepcao in CATALOGO}


def catalogo_publico():
    """O catálogo sem as funções, pronto para virar JSON (a interface nunca mostra id nem nome)."""
    return [
        {
            "id": c["id"],
            "nome": c["nome"],
            "regra_para_aluno": c["regra_para_aluno"],
            "observavel_em": list(c["observavel_em"]),
            "referencias": list(c["referencias"]),
        }
        for c in CATALOGO
    ]


def observaveis(tipo, codigo=None):
    """Concepções observáveis num tipo de pergunta; com o código, só as que o programa tem."""
    candidatas = [c for c in CATALOGO if tipo in c["observavel_em"]]
    if codigo is None:
        return [c["id"] for c in candidatas]
    try:
        analise = codigo if isinstance(codigo, Analise) else Analise(codigo)
    except (SyntaxError, ValueError):
        return []
    return [c["id"] for c in candidatas if c["padrao_ast"](analise)]


# --- Respostas: o texto que o aluno vê e a chave que compara -----------------


def _texto_curto(valor):
    try:
        texto = formatar(valor)  # "Ana", com as aspas que o aluno vê no resto da tela
    except Exception:  # um __repr__ quebrado do aluno não pode derrubar o modelo
        texto = f"<{type(valor).__name__}>"
    return texto if len(texto) <= LIMITE_TEXTO else texto[: LIMITE_TEXTO - 1] + "…"


def _chave(valor, profundidade=0):
    """Igualdade de resposta: 7 e 7.0 empatam (diferença de tipo é mensagem, não diagnóstico)."""
    tipo = type(valor)
    if tipo is bool:
        return ("bool", valor)
    if tipo in (int, float):
        return ("numero", "nan" if valor != valor else valor)
    if tipo is str:
        return ("texto", valor)
    if tipo in (list, tuple) and profundidade < 4 and len(valor) <= 200:
        return ("lista", tipo.__name__, tuple(_chave(item, profundidade + 1) for item in valor))
    return ("outro", tipo.__name__, _texto_curto(valor))


def _tipo_valor(valor):
    tipo = type(valor)
    if tipo is bool:
        return "bool"
    if tipo in (int, float):
        return "numero"
    if tipo is str:
        return "texto"
    if tipo in (list, tuple):
        return "lista"
    return "outro"


def resposta_de_valor(valor):
    return {"texto": _texto_curto(valor), "tipo_valor": _tipo_valor(valor), "chave": _chave(valor)}


def _normalizar_saida(texto):
    # Espaço não se vê: um espaço a mais no começo ou no meio não pode virar erro.
    return "\n".join(" ".join(linha.split()) for linha in texto.split("\n")).strip("\n")


def resposta_de_saida(texto):
    if texto.endswith("\n"):
        texto = texto[:-1]
    return {"texto": texto, "tipo_valor": "texto", "chave": ("saida", _normalizar_saida(texto))}


def resposta_de_decisao(entrou):
    return {"texto": "Verdadeiro" if entrou else "Falso", "tipo_valor": "bool", "chave": ("bool", bool(entrou))}


def resposta_de_voltas(total):
    return {"texto": str(total), "tipo_valor": "numero", "chave": ("numero", total)}


def _publica(resposta):
    return None if resposta is None else {"texto": resposta["texto"], "tipo_valor": resposta["tipo_valor"]}


_VERDADES = {"verdadeiro": True, "true": True, "sim": True, "v": True, "entra": True,
             "falso": False, "false": False, "não": False, "nao": False, "f": False, "não entra": False}


def _literal(texto):
    try:
        return True, ast.literal_eval(texto.strip())
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False, None


def _sem_aspas(texto):
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in "'\"":
        return texto[1:-1]
    return texto


def normalizar(tipo, texto, tipo_escolhido=None):
    """Chave de comparação de uma resposta livre, ou None quando não dá para ler.

    `tipo_escolhido` é o botão que o aluno marcou ('numero' ou 'texto'): '12'
    marcado como número é o número 12, e só assim casa com um modelo que acha
    que o input devolve número.
    """
    if not isinstance(texto, str):
        return None
    if tipo == "saida":
        return ("saida", _normalizar_saida(texto))
    if tipo == "decisao":
        valor = _VERDADES.get(texto.strip().lower())
        return None if valor is None else ("bool", valor)
    if tipo == "voltas":
        lido, valor = _literal(texto)
        return ("numero", valor) if lido and type(valor) is int else None
    if tipo_escolhido == "texto":
        return ("texto", _sem_aspas(texto))
    lido, valor = _literal(texto)
    if tipo_escolhido == "numero":
        return _chave(valor) if lido and type(valor) in (int, float) else None
    return _chave(valor) if lido else ("texto", texto)


def _chave_da_resposta(tipo, resposta):
    """Chave de uma resposta {texto, tipo_valor}, venha ela daqui ou do rastro completo."""
    if resposta is None:
        return None
    if "chave" in resposta:
        return resposta["chave"]
    texto, tipo_valor = resposta.get("texto"), resposta.get("tipo_valor")
    if tipo in ("saida", "decisao", "voltas"):
        return normalizar(tipo, texto)
    if tipo_valor == "texto":
        lido, valor = _literal(texto)
        return ("texto", valor if lido and type(valor) is str else texto)
    if tipo_valor == "numero":
        return normalizar(tipo, texto, "numero")
    if tipo_valor == "bool":
        valor = _VERDADES.get(str(texto).strip().lower())
        return None if valor is None else ("bool", valor)
    return normalizar(tipo, texto)


# --- rastrear_leve -----------------------------------------------------------


class _GravadorLeve(_Gravador):
    """O gravador do rastreador sem fotos: conta ocorrências e captura os alvos.

    A fusão de avisos, os quadros e as voltas são os do gravador original, por
    isso a k-ésima ocorrência de um comando aqui é a mesma do rastro completo.
    """

    def __init__(self, analise, limite, saida, alvos, prazo=None):
        super().__init__(analise, limite, saida)
        self.prazo = prazo  # perf_counter em que o orçamento acaba
        self.sem_tempo = False
        self.ocorrencias = {}
        self.por_ocorrencia = {}  # (comando, ocorrência) -> alvos que começam ali
        self.pendentes = {}  # número do quadro -> [(alvo, dado)] esperando o próximo passo do quadro
        self.respostas = {}
        self.antes = {}
        for alvo in alvos:
            if alvo["tipo"] != "voltas" and alvo.get("comando") is not None:
                chave = (alvo["comando"], alvo.get("ocorrencia") or 1)
                self.por_ocorrencia.setdefault(chave, []).append(alvo)

    def gravar(self, frame, quadro, comando, evento):
        # O próximo passo do mesmo quadro é o "depois" do comando anterior dele.
        self._fechar(quadro.numero, frame, quadro.funcao, comando)
        passo = {"i": len(self.passos), "comando": comando, "evento": evento, "quadro": quadro.numero,
                 "proximo_no_quadro": None}
        if self.retornos:
            passo["retornos"] = self.retornos
            self.retornos = []
        self.passos.append(passo)
        if evento == "linha" and len(self.passos) > self.limite:
            self.estourou = True
            raise LimiteDePassos()
        if self.prazo is not None and time.perf_counter() > self.prazo:
            # Um modelo pode rodar o que o programa de verdade nunca rodou (o else da C05).
            self.estourou = self.sem_tempo = True
            raise LimiteDePassos()
        if comando is None:
            return
        n = self.ocorrencias[comando] = self.ocorrencias.get(comando, 0) + 1
        for alvo in self.por_ocorrencia.get((comando, n), ()):
            self._abrir(alvo, frame, quadro)

    def _fim_do_quadro(self, quadro, frame, valor):
        if quadro.funcao is not None and not frame.f_code.co_flags & GERADORES:
            if self._terminou_bem(frame):
                self._fechar(quadro.numero, frame, quadro.funcao, None)
            else:
                self.pendentes.pop(quadro.numero, None)  # o comando não terminou: saiu por um erro
        super()._fim_do_quadro(quadro, frame, valor)

    def _retorno(self, quadro, frame, valor):
        return {"quadro": quadro.numero}  # sem fotos: só quem terminou importa (as voltas)

    def _terminou_bem(self, frame):
        bytecode = self._ler_codigo(frame.f_code)[0]
        return 0 <= frame.f_lasti < len(bytecode) and bytecode[frame.f_lasti] in OPERACOES_DE_RETORNO

    def _abrir(self, alvo, frame, quadro):
        tipo = alvo["tipo"]
        dado = None
        if tipo == "valor":
            self.antes[alvo["id"]] = _ler_variavel(frame, quadro.funcao, alvo.get("nome"))
        elif tipo == "saida":
            dado = self.saida.tell()
        elif tipo == "decisao":
            info = self.analise.comandos[alvo["comando"]]
            if info["tipo"] not in ("if", "elif", "while"):
                return
            if info["corpo_mesma_linha"]:
                # Sem passo próprio para o corpo: quem decide é o avaliador seguro.
                decisao = avaliar(self.analise.nos[info["id"]].test, frame.f_globals, frame.f_locals)
                if decisao["valor"] is not None:
                    self.respostas[alvo["id"]] = resposta_de_decisao(decisao["valor"])
                return
            dado = info["corpo"]
        self.pendentes.setdefault(quadro.numero, []).append((alvo, dado))

    def _fechar(self, numero, frame, funcao, comando_seguinte):
        pendentes = self.pendentes.pop(numero, None)
        if not pendentes:
            return
        for alvo, dado in pendentes:
            tipo = alvo["tipo"]
            if tipo == "valor":
                resposta = _ler_variavel(frame, funcao, alvo.get("nome"))
            elif tipo == "saida":
                resposta = resposta_de_saida(self.saida.getvalue()[dado:])
            else:
                linha = self.analise.comandos[comando_seguinte]["linhas"][0] if comando_seguinte is not None else None
                resposta = resposta_de_decisao(linha is not None and bool(dado) and dado[0] <= linha <= dado[1])
            self.respostas[alvo["id"]] = resposta


def _ler_variavel(frame, funcao, nome):
    if not nome:
        return None
    if funcao is not None:
        locais = frame.f_locals
        if nome in locais:
            return resposta_de_valor(locais[nome])
    globais = frame.f_globals
    if nome in globais:
        return resposta_de_valor(globais[nome])
    return None


def inicios_de_laco(passos, comandos):
    """{(laço, k): i} — o passo em que começa a k-ésima entrada em cada laço.

    Uma entrada começa quando o cabeçalho é alcançado vindo de fora do laço
    (o passo anterior do mesmo quadro não é do laço), como em calcular_voltas.
    """
    inicios = {}
    contagem = {}
    anterior = {}
    for passo in passos:
        comando, quadro = passo["comando"], passo["quadro"]
        antes = anterior.get(quadro)
        anterior[quadro] = comando
        if comando is None or comandos[comando]["tipo"] not in LACOS:
            continue
        if antes is not None and _dentro_do_laco(comandos, comando, antes):
            continue
        k = contagem[comando] = contagem.get(comando, 0) + 1
        inicios[(comando, k)] = passo["i"]
    return inicios


def rastrear_leve(codigo, entradas=(), alvos=(), semente=0, limite=LIMITE_LEVE, arvore=None, extras=None,
                  analise=None, prazo=None):
    """Roda o programa sem fotos do estado e devolve só o que os alvos pedem.

    `codigo` é sempre o programa original: é dele que saem os comandos. Para
    rodar um modelo, `arvore` é a árvore transformada (com as linhas do
    original) e `extras` os ajudantes que ela chama. Mesma semente, mesmas
    entradas e o mesmo bloqueio de módulos de rastrear().

    alvos = [{id, tipo, comando, ocorrencia, nome?}]:
    - valor: o valor de `nome` depois da `ocorrencia`-ésima vez que o comando rodou;
    - decisao: se o if/elif/while entrou naquela vez;
    - saida: o que aquela vez do comando escreveu (comando None: a saída inteira);
    - voltas: quantas voltas o laço deu na `ocorrencia`-ésima vez que começou.

    `prazo` (um time.perf_counter()) para a execução no primeiro passo depois
    dele, como se estourasse o limite (`sem_tempo`). Uma chamada embutida longa,
    sem passos, não para no meio: a página tem o próprio tempo limite.

    Devolve {respostas, antes, ocorrencias, passos, estourou, sem_tempo, erro, saida, sequencia}.
    Cada resposta é {texto, tipo_valor, chave} ou None (o ponto não aconteceu).
    """
    alvos = list(alvos)
    saida = io.StringIO()
    meus_builtins = dict(vars(builtins))
    meus_builtins["input"] = _input_com_entradas(entradas, saida)
    meus_builtins["print"] = lambda *args, **kwargs: print(*args, **{"file": saida, **kwargs})
    meus_builtins.update(extras or {})
    escopo = {"__name__": "__main__", "__builtins__": meus_builtins}
    resultado = {"respostas": {alvo["id"]: None for alvo in alvos}, "antes": {}, "ocorrencias": {}, "passos": 0,
                 "estourou": False, "sem_tempo": False, "erro": None, "saida": "", "sequencia": []}
    gravador = None

    def ao_errar(e):
        # O erro do programa (ou do modelo) é parte do resultado; exit() e o limite, não.
        return None if isinstance(e, (SystemExit, LimiteDePassos)) else type(e).__name__

    estado_do_random = random.getstate()
    try:
        if analise is None:
            analise = Analise(codigo, ast.parse(codigo, ARQUIVO_DO_ALUNO))
        compilado = compile(arvore if arvore is not None else analise.arvore, ARQUIVO_DO_ALUNO, "exec")
        gravador = _GravadorLeve(analise, limite, saida, alvos, prazo)
        random.seed(semente)
        # Sem coletar o lixo a cada modelo: custaria caro nos 8 modelos de um programa.
        resultado["erro"] = executar_isolado(compilado, escopo, gravador.chamada, ao_errar, coletar=False)
    except Exception as e:
        resultado["erro"] = type(e).__name__
    finally:
        random.setstate(estado_do_random)

    resultado["saida"] = saida.getvalue()
    if gravador is None:
        return resultado
    passos = gravador.passos
    resultado["estourou"] = gravador.estourou
    resultado["sem_tempo"] = gravador.sem_tempo
    resultado["passos"] = sum(1 for p in passos if p["evento"] == "linha")
    resultado["ocorrencias"] = dict(gravador.ocorrencias)
    resultado["sequencia"] = [[p["comando"], p["quadro"]] for p in passos]
    resultado["respostas"].update(gravador.respostas)
    resultado["antes"] = gravador.antes
    terminou = resultado["erro"] is None and not gravador.estourou

    for alvo in alvos:
        if alvo["tipo"] == "saida" and alvo.get("comando") is None:
            # A saída inteira só vale se o programa terminou: uma saída cortada não é palpite de ninguém.
            resultado["respostas"][alvo["id"]] = resposta_de_saida(resultado["saida"]) if terminou else None

    voltas = [alvo for alvo in alvos if alvo["tipo"] == "voltas"]
    if voltas and passos:
        _ligar_quadros(passos)
        comandos = analise.comandos
        marcas = calcular_voltas({"passos": passos, "estrutura": {"comandos": comandos},
                                  "erro": None if terminou else "parou"})
        inicios = inicios_de_laco(passos, comandos)
        for alvo in voltas:
            i = inicios.get((alvo["comando"], alvo.get("ocorrencia") or 1))
            marca = marcas[i] if i is not None else None
            if marca is not None and marca["laco"] == alvo["comando"] and marca["total"] is not None:
                resultado["respostas"][alvo["id"]] = resposta_de_voltas(marca["total"])
    return resultado


# --- Pontos e alvos ----------------------------------------------------------


def ocorrencia_do_passo(resultado, i, tipo, comando):
    """Ocorrência do passo i no rastro completo: a k-ésima vez do comando (ou do laço, em voltas)."""
    passos = resultado["passos"][: i + 1]
    if tipo == "voltas":
        inicios = inicios_de_laco(passos, resultado["estrutura"]["comandos"])
        return max([k for (laco, k) in inicios if laco == comando], default=1)
    return sum(1 for passo in passos if passo["comando"] == comando) or 1


def alvo_do_ponto(ponto, resultado=None):
    """Ponto (contrato da Atividade) -> alvo de rastrear_leve."""
    alvo = ponto.get("alvo") or {}
    comando = alvo.get("comando", ponto.get("comando"))
    ocorrencia = ponto.get("ocorrencia")
    if ocorrencia is None and resultado is not None and ponto.get("passo") is not None and comando is not None:
        ocorrencia = ocorrencia_do_passo(resultado, ponto["passo"], ponto["tipo"], comando)
    return {"id": ponto["id"], "tipo": ponto["tipo"], "comando": comando, "ocorrencia": ocorrencia or 1,
            "nome": alvo.get("nome", ponto.get("nome"))}


# --- Gerar os modelos de um programa -----------------------------------------


class _Valores(dict):
    def __missing__(self, chave):
        return "?"


def _trecho(codigo, no, limite=40):
    texto = ast.get_source_segment(codigo, no) or ast.unparse(no)
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _no_relevante(nos, analise, comando):
    """Entre os lugares em que a concepção aparece, o mais ligado ao ponto.

    Primeiro o que está no próprio comando, depois o de um bloco que o
    contém (o range do for em volta), depois o último antes da linha do
    ponto, e por fim o primeiro do programa. ast.walk anda por largura:
    sem ordenar, um nó raso lá embaixo passaria na frente de um aninhado lá em cima.
    """
    if not nos:
        return None
    nos = sorted(nos, key=lambda no: (no.lineno, no.col_offset))
    if comando is None:
        return nos[0]
    linhas = analise.linha_para_comando
    ancestrais = []
    atual = comando
    while atual is not None:
        ancestrais.append(atual)
        atual = analise.comandos[atual]["pai"]
    for candidato in ancestrais:
        for no in nos:
            if linhas.get(no.lineno) == candidato:
                return no
    linha = analise.nos[comando].lineno
    antes = [no for no in nos if no.lineno <= linha]
    return antes[-1] if antes else nos[0]


def _laco_do_range(analise, no_range):
    for comando in analise.comandos:
        no = analise.nos[comando["id"]]
        if comando["tipo"] == "for" and no.iter is no_range and isinstance(no.target, ast.Name):
            return no.target.id
    return None


def _contexto(concepcao, analise, codigo, alvo, nos):
    """Valores para os modelos de frase e a caixinha que ganha contorno."""
    valores = _Valores()
    destacar = alvo.get("nome") if alvo["tipo"] == "valor" else None
    no = _no_relevante(nos, analise, alvo.get("comando"))
    onde = concepcao["camadas"]["onde"]
    if no is None:
        return valores, destacar
    if isinstance(no, ast.Call) and _e_range(no):
        valores["range"] = _trecho(codigo, no)
        valores["fim"] = _trecho(codigo, no.args[0] if len(no.args) == 1 else no.args[1])
        if onde == "laco":
            destacar = _laco_do_range(analise, no) or destacar
    elif isinstance(no, (ast.If, ast.While)):
        valores["condicao"] = _trecho(codigo, no.test)
    elif isinstance(no, ast.Subscript):
        valores["acesso"] = _trecho(codigo, no)
        if onde == "lista" and isinstance(no.value, ast.Name):
            destacar = no.value.id
    elif isinstance(no, (ast.BinOp, ast.AugAssign)):
        valores["conta"] = _trecho(codigo, no)
    elif _e_chamada(no, "input") and onde == "entrada":
        for comando in analise.comandos:
            atribuicao = analise.nos[comando["id"]]
            if isinstance(atribuicao, ast.Assign) and any(n is no for n in ast.walk(atribuicao.value)):
                nomes = [t.id for t in atribuicao.targets if isinstance(t, ast.Name)]
                destacar = nomes[0] if nomes else destacar
                break
    return valores, destacar


def _frase_da_certa(alvo, certa):
    tipo = alvo["tipo"]
    if tipo == "valor":
        return f"Depois desta linha, `{alvo.get('nome')}` vale {certa['texto']}."
    if tipo == "saida":
        return f"Na tela aparece “{certa['texto']}”."
    if tipo == "voltas":
        return f"O laço dá {certa['texto']} {'volta' if certa['texto'] == '1' else 'voltas'}."
    return f"A condição deu {certa['texto']}."


def _feedback(concepcao, alvo, ponto, certa, resposta, valores, destacar, real):
    valores = _Valores(valores)
    valores.update(nome=alvo.get("nome") or "", certa=certa["texto"], modelo=resposta["texto"],
                   certa_frase=_frase_da_certa(alvo, certa))
    antes = real["antes"].get(alvo["id"])
    if antes is not None:
        valores["antes"] = antes["texto"]
    camadas = concepcao["camadas"]
    return {
        "onde": {"passo": ponto.get("passo"), "destacar": destacar},
        "regra": camadas["regra"].format_map(valores),
        "resolvido": camadas["resolvido"].format_map(valores),
        "resumo": f"Será que você pensou que {concepcao['crenca'].format_map(valores)}? {concepcao['regra_para_aluno']}",
    }


def _estatistica_vazia():
    return {"aplicavel": 0, "geradas": 0, "iguais": 0, "repetidas": 0, "mantidas": 0, "estouro": 0, "erro": 0,
            "sem_resposta": 0, "execucoes": 0, "tempo_ms": 0.0}


def gerar_modelos(codigo, entradas=(), pontos=(), semente=0, resultado=None, limite=LIMITE_LEVE, orcamento_ms=None):
    """Alternativas de modelo para cada ponto de previsão de um programa.

    Cada transformação roda UMA vez, só se o programa tem a construção e
    algum ponto é de um tipo em que ela é observável. As respostas do modelo
    são alinhadas aos pontos por (comando, ocorrência). Uma resposta igual à
    certa é descartada, e respostas repetidas viram uma alternativa só; se
    duas concepções dão a mesma resposta, a alternativa fica sem concepção
    (não dá para dizer qual das duas o aluno seguiu). Programa não
    determinístico, modelo que estoura o limite ou orçamento esgotado: sem
    alternativa de modelo.

    `pontos` seguem o contrato da Atividade ({id, tipo, passo?, alvo: {comando,
    nome?}}) e podem trazer `ocorrencia`; sem ela, vem de `passo` e `resultado`.
    Devolve {por_ponto: {id: {certa, alternativas, modelos, descartadas,
    sem_modelo}}, concepcoes: {id: estatística}, deterministico, completa, tempo_ms}.
    `completa` é False quando o orçamento acabou antes de algum modelo terminar.
    """
    inicio = time.perf_counter()
    prazo = None if orcamento_ms is None else inicio + orcamento_ms / 1000
    pontos = list(pontos)
    saida = {"por_ponto": {}, "concepcoes": {c["id"]: _estatistica_vazia() for c in CATALOGO},
             "deterministico": True, "completa": True, "tempo_ms": 0.0}
    vazio = {"certa": None, "alternativas": [], "modelos": [], "descartadas": {"iguais": 0, "repetidas": 0},
             "sem_modelo": {}}
    try:
        analise = Analise(codigo, ast.parse(codigo, ARQUIVO_DO_ALUNO))
        compile(analise.arvore, ARQUIVO_DO_ALUNO, "exec")
    except (SyntaxError, ValueError):
        saida["por_ponto"] = {ponto["id"]: copy.deepcopy(vazio) for ponto in pontos}
        return saida
    deterministico = _deterministico(analise.arvore)
    if resultado is not None:
        deterministico = resultado.get("deterministico", deterministico)
    if resultado is not None:
        semente = resultado.get("semente", semente)
    saida["deterministico"] = deterministico

    alvos = [alvo_do_ponto(ponto, resultado) for ponto in pontos]
    # O programa do aluno já rodou inteiro em rastrear; o orçamento vale só para os modelos.
    real = rastrear_leve(codigo, entradas, alvos, semente, max(LIMITE_PADRAO, limite), analise=analise)
    certas = real["respostas"]
    respostas = {alvo["id"]: [] for alvo in alvos}
    sem_modelo = {alvo["id"]: {} for alvo in alvos}
    contextos = {}

    for concepcao in CATALOGO:
        cid = concepcao["id"]
        estatistica = saida["concepcoes"][cid]
        relevantes = [a for a in alvos if a["tipo"] in concepcao["observavel_em"] and certas[a["id"]] is not None]
        if not relevantes:
            continue
        nos = concepcao["padrao_ast"](analise)
        if not nos:
            continue
        estatistica["aplicavel"] += len(relevantes)
        contextos[cid] = nos
        if not deterministico or (prazo is not None and time.perf_counter() > prazo):
            motivo = "nao_deterministico" if not deterministico else "orcamento"
            saida["completa"] = saida["completa"] and motivo != "orcamento"
            for alvo in relevantes:
                sem_modelo[alvo["id"]][cid] = motivo
            continue
        comeco = time.perf_counter()
        estourou = sem_tempo = False
        if concepcao["transformar"] is not None:
            arvore = concepcao["transformar"](analise).aplicar(analise.arvore)
            modelo = rastrear_leve(codigo, entradas, relevantes, semente, limite, arvore=arvore, extras=AJUDANTES,
                                   analise=analise, prazo=prazo)
            estatistica["execucoes"] += 1
            if modelo["erro"] is not None:
                estatistica["erro"] += 1
            # Se o modelo estourou o limite, a concepção fica sem alternativa (mesmo nos pontos de antes).
            estourou = modelo["estourou"]
            sem_tempo = modelo["sem_tempo"]
            saida["completa"] = saida["completa"] and not sem_tempo
            obtidas = {} if estourou else modelo["respostas"]
        else:
            obtidas = {a["id"]: concepcao["regra_rastro"](a, real, analise) for a in relevantes}
        estatistica["tempo_ms"] += (time.perf_counter() - comeco) * 1000
        for alvo in relevantes:
            obtida = obtidas.get(alvo["id"])
            if obtida is None:
                if sem_tempo:
                    sem_modelo[alvo["id"]][cid] = "orcamento"
                    continue
                sem_modelo[alvo["id"]][cid] = "estouro" if estourou else "sem_resposta"
                estatistica["estouro" if estourou else "sem_resposta"] += 1
                continue
            estatistica["geradas"] += 1
            respostas[alvo["id"]].append((cid, obtida))

    for ponto, alvo in zip(pontos, alvos):
        pid = alvo["id"]
        certa = certas[pid]
        bloco = {"certa": _publica(certa), "alternativas": [], "modelos": [], "descartadas": {"iguais": 0, "repetidas": 0},
                 "sem_modelo": sem_modelo[pid]}
        saida["por_ponto"][pid] = bloco
        if certa is None:
            continue
        vistas = {}
        for cid, obtida in respostas[pid]:
            estatistica = saida["concepcoes"][cid]
            if obtida["chave"] == certa["chave"]:
                bloco["descartadas"]["iguais"] += 1
                estatistica["iguais"] += 1
                sem_modelo[pid][cid] = "igual_a_certa"
                continue
            concepcao = POR_ID[cid]
            valores, destacar = _contexto(concepcao, analise, codigo, alvo, contextos.get(cid, []))
            feedback = _feedback(concepcao, alvo, ponto, certa, obtida, valores, destacar, real)
            bloco["modelos"].append({"concepcao": cid, "texto": obtida["texto"], "tipo_valor": obtida["tipo_valor"],
                                     "feedback": feedback})
            if obtida["chave"] in vistas:
                bloco["descartadas"]["repetidas"] += 1
                estatistica["repetidas"] += 1
                vistas[obtida["chave"]]["concepcoes"].append(cid)
                continue
            vistas[obtida["chave"]] = {"texto": obtida["texto"], "tipo_valor": obtida["tipo_valor"], "certa": False,
                                       "concepcao": cid, "concepcoes": [cid], "origem": "modelo", "feedback": feedback}
        for alternativa in vistas.values():
            if len(alternativa["concepcoes"]) > 1:
                # Duas ideias explicam a mesma resposta: o distrator fica, o diagnóstico não.
                alternativa["concepcao"] = None
                alternativa["feedback"] = None
            for cid in alternativa["concepcoes"]:
                saida["concepcoes"][cid]["mantidas"] += 1
            bloco["alternativas"].append(alternativa)

    saida["tempo_ms"] = (time.perf_counter() - inicio) * 1000
    return saida


# --- Diagnóstico ---------------------------------------------------------------


def diagnosticar(ponto, resposta):
    """Id da concepção que explica a resposta errada, só quando exatamente uma explica.

    `ponto` traz `modelos` (de gerar_modelos) ou `alternativas`, e a resposta
    certa em `certa` ou `resposta`. `resposta` é {alternativa: id} (múltipla
    escolha) ou {texto, tipo_escolhido?} (resposta livre). Distrator de regra
    nunca conta como diagnóstico.
    """
    alternativas = ponto.get("alternativas") or []
    if "alternativa" in resposta:
        escolhida = next((a for a in alternativas if a.get("id") == resposta["alternativa"]), None)
        if escolhida is None or escolhida.get("origem") != "modelo" or escolhida.get("certa"):
            return None
        concepcoes = escolhida.get("concepcoes") or [escolhida.get("concepcao")]
        return concepcoes[0] if len(set(concepcoes)) == 1 and concepcoes[0] else None

    tipo = ponto.get("tipo")
    chave = normalizar(tipo, resposta.get("texto"), resposta.get("tipo_escolhido"))
    if chave is None:
        return None
    certa = ponto.get("certa") or ponto.get("resposta")
    if certa is not None and chave == _chave_da_resposta(tipo, certa):
        return None
    modelos = ponto.get("modelos")
    if modelos is None:
        modelos = [
            {"concepcao": cid, "texto": a["texto"], "tipo_valor": a.get("tipo_valor")}
            for a in alternativas
            if a.get("origem") == "modelo"
            for cid in (a.get("concepcoes") or [a.get("concepcao")])
            if cid
        ]
    coincidem = {m["concepcao"] for m in modelos if _chave_da_resposta(tipo, m) == chave}
    return coincidem.pop() if len(coincidem) == 1 else None


def feedback_do_modelo(ponto, concepcao):
    """O Feedback que o modelo daquela concepção preparou para o ponto, ou None."""
    for modelo in ponto.get("modelos") or ():
        if modelo["concepcao"] == concepcao:
            return modelo.get("feedback")
    return None
