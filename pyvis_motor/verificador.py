"""Conferência dos exercícios gerados (área Praticar): o motor é o juiz.

verificar(exercicio) roda o programa no motor do PyVis e devolve
{ok, motivos, medidas, concepcoes, pontos, so_decisao, chave}. O exercício só passa sem
nenhum motivo. Os grupos de conferência:

1. Sintaxe e a escada de conceitos DO TEMA (ESCADA): Laços 1 pede Condições
   1, que pede Variáveis 1, e nada mais; um elif ou um and em Laços 1 é
   recusado. Algumas construções nunca entram (import, def, lambda, class,
   try, with, global, compreensões, f-strings, texto com % ("%d" % n),
   dicionários, conjuntos, input, eval/exec/open/getattr, nomes com __,
   while True): o que não está
   em nenhum degrau da escada é recusado em todo nível.
2. Roda sem erro dentro de LIMITE passos; é determinístico (duas execuções
   e duas sementes do motor dão a mesma saída); a saída cabe em MAX_LINHAS
   linhas e MAX_CARACTERES caracteres; nenhum decimal ambíguo
   (0.30000000000000004).
3. Cabe no ORCAMENTO do tema e do nível (linhas, passos, voltas, operações).
4. A atividade de prever acha pelo menos 1 ponto nos dois formatos
   ("alternativas" com palpite_inicial e "livre"); as concepções que deram
   distrator ficam em `concepcoes`, e `so_decisao` diz se as alternativas só
   perguntam "o if vai entrar?" (o banco limita quantos itens são assim).
5. Mutação: o conceito do tema importa. Em Variáveis, trocar um valor
   atribuído muda a saída; em Condições, negar uma condição muda; em Laços,
   mexer no limite do laço muda.
6. Textos: a frase do contexto, cada texto entre aspas, os nomes e a saída
   não têm palavras de jogo de azar, de violência ou de placar, nem dado
   pessoal (telefone, CPF, e-mail). Textos entre aspas e a saída só têm
   letras sem acento. O contexto tem até 12 palavras e nenhuma pergunta:
   quem pergunta é o motor.
7. A chave do programa é o sha256 do próprio código (ast.dump mudou entre o
   3.12 e o 3.14 e não serve para dizer que dois programas são iguais).

Nada aqui mexe em api.ultimo: o verificador chama o rastreador e
montar_atividade direto, como a api faz, sem guardar o último rastro.
"""

import ast
import hashlib
import re
import unicodedata

from .familias import NIVEIS, TEMAS
from .previsao import montar_atividade
from .privacidade import DIGITOS_DE_DOCUMENTO
from .rastreador import rastrear

LIMITE = 300  # o limite dos aparelhos fracos: o exercício precisa caber nele
MAX_LINHAS, MAX_CARACTERES = 10, 300
MAX_PALAVRAS_NO_CONTEXTO = 12
MAX_MUTACOES = 4  # lugares mexidos por exercício (cada um de até 2 jeitos)
ORCAMENTO_DOS_MODELOS_MS = 5000  # folgado: a conferência não pode depender da velocidade do computador

# Escada por tema: cada degrau tem os degraus que pede e os conceitos que acrescenta.
# Um nível permite os próprios conceitos e os de todos os degraus que ele pede.
ESCADA = {
    ("variaveis", 1): ((), ("atribuicao", "soma_e_subtracao", "print")),
    ("variaveis", 2): (
        (("variaveis", 1),),
        ("multiplicacao", "divisao_inteira", "resto", "len", "atribuicao_composta"),
    ),
    ("variaveis", 3): ((("variaveis", 2),), ("troca", "int", "str", "divisao", "decimal")),
    ("condicoes", 1): ((("variaveis", 1),), ("if", "else", "comparacao", "booleano")),
    ("condicoes", 2): ((("condicoes", 1), ("variaveis", 2)), ("elif",)),
    ("condicoes", 3): ((("condicoes", 2),), ("e_ou_nao", "if_aninhado")),
    ("lacos", 1): ((("condicoes", 1),), ("while",)),
    ("lacos", 2): ((("lacos", 1),), ("for_range", "for_texto")),
    ("lacos", 3): ((("lacos", 2),), ("lista", "indice", "range_com_passo", "break", "while_composto")),
}

# Teto de tamanho por tema e nível, medido no rastro e na AST (medir()).
# Variáveis: tirado das famílias de familias_variaveis.py, com folga de 1 ou 2.
# Os maiores itens do banco: nível 1 com 6 linhas, 6 passos e 2 operações;
# nível 2 com 6, 6 e 3; nível 3 com 7, 7 e 3. A conta de 11 operações num
# nível 1 fica de fora.
# Condições: tirado de familias_condicoes.py, com o mesmo critério. Os maiores
# itens do banco: nível 1 com 9 linhas, 6 passos e 2 operações; nível 2 com 10,
# 7 e 6 (em dia % 3 == 0, o % e o == contam uma cada); nível 3 com 11, 8 e 4.
# Laços: tirado de familias_lacos.py, com o mesmo critério. Os maiores itens do
# banco: nível 1 com 7 linhas, 19 passos, 5 voltas e 4 operações; nível 2 com
# 8, 28, 8 e 3 (o for pelas letras de "vermelho"); nível 3 com 7, 17, 5 e 5.
# Os passos e as voltas não descem do nível 2 para o 3: o nível 3 ainda pode
# andar por um texto inteiro, como o 2.
ORCAMENTO = {
    ("variaveis", 1): {"linhas": 7, "passos": 7, "voltas": 0, "operacoes": 4},
    ("variaveis", 2): {"linhas": 7, "passos": 7, "voltas": 0, "operacoes": 5},
    ("variaveis", 3): {"linhas": 8, "passos": 8, "voltas": 0, "operacoes": 5},
    ("condicoes", 1): {"linhas": 10, "passos": 8, "voltas": 0, "operacoes": 4},
    ("condicoes", 2): {"linhas": 11, "passos": 9, "voltas": 0, "operacoes": 7},
    ("condicoes", 3): {"linhas": 12, "passos": 9, "voltas": 0, "operacoes": 5},
    ("lacos", 1): {"linhas": 8, "passos": 22, "voltas": 6, "operacoes": 5},
    ("lacos", 2): {"linhas": 9, "passos": 32, "voltas": 9, "operacoes": 5},
    ("lacos", 3): {"linhas": 9, "passos": 32, "voltas": 9, "operacoes": 7},
}

# Construções que nunca entram, com o nome do motivo.
PROIBIDAS = {
    "Import": "import",
    "ImportFrom": "import",
    "FunctionDef": "funcao",
    "AsyncFunctionDef": "funcao",
    "Lambda": "funcao",
    "Return": "funcao",
    "ClassDef": "classe",
    "Try": "try",
    "TryStar": "try",
    "With": "with",
    "AsyncWith": "with",
    "Global": "global",
    "Nonlocal": "global",
    "ListComp": "compreensao",
    "SetComp": "compreensao",
    "DictComp": "compreensao",
    "GeneratorExp": "compreensao",
    "JoinedStr": "fstring",
    "FormattedValue": "fstring",
    "TemplateStr": "fstring",
    "Interpolation": "fstring",
    "Dict": "dicionario",
    "Set": "conjunto",
    "Yield": "gerador",
    "YieldFrom": "gerador",
    "Await": "gerador",
    "Attribute": "atributo",
}
# Nós que só dão forma a outros (contexto, operadores, partes de um comando que já foi recusado).
NEUTROS = (
    ast.Module, ast.Load, ast.Store, ast.Del, ast.operator, ast.boolop, ast.cmpop, ast.unaryop, ast.alias,
    ast.arguments, ast.arg, ast.comprehension, ast.keyword, ast.ExceptHandler, ast.withitem,
)
NOMES_PROIBIDOS = frozenset({
    "eval", "exec", "open", "getattr", "setattr", "delattr", "hasattr", "globals", "locals", "vars", "compile",
    "breakpoint", "help", "exit", "quit", "dir", "id", "hash", "type", "object", "super", "memoryview",
})
FUNCOES = frozenset({"print", "len", "int", "str", "range", "input"})
OPERACOES = {
    ast.Add: "soma_e_subtracao",
    ast.Sub: "soma_e_subtracao",
    ast.Mult: "multiplicacao",
    ast.FloorDiv: "divisao_inteira",
    ast.Mod: "resto",
    ast.Div: "divisao",
    ast.Pow: "potencia",
}
COMPARACOES = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)

# Palavras que o PyVis não usa (jogo de azar, violência, placar), sem acento e em minúsculas.
# Cada uma vem com as flexões (ganha, ganhou, ganhando...): a família pode vir de
# qualquer pessoa, até de uma IA, e este filtro é a rede de proteção das crianças.
# Os radicais ambíguos ficam com a lista fechada de flexões ("morr" pegaria
# "morro", "mata" é também a floresta: nenhuma família usa). A primeira é
# montada em pedaços para este arquivo não acusar a si mesmo.
PALAVRAS_PROIBIDAS = (
    "a" + "post\\w*", "sort(e|es|ear|eio|eou|eado|udos?|udas?)", "vidas?", "pontos?", "pontu\\w*",
    "premi\\w*", "medalhas?", "trofeus?", "ouro", "prata", "bronze", "placar", "recordes?",
    "campe(ao|oes|a|as)", "ganh\\w*", "perd(e|es|er|eu|endo|eram|i|emos)", "venc(e|es|er|eu|endo|eram|i|edor\\w*)",
    "derrot\\w*", "chef(ao|oes|ona|onas)", "danos?", "golpe\\w*", "inimig\\w*",
    "mat(a|am|ar|ou|ando|ei|aram|ador\\w*)", "mort(e|es|o|os|a|as)", "morr(e|er|eu|endo|eram|i)",
    "armas?", "armad(o|os|a|as)", "tiros?", "atir\\w*", "bombas?", "explod\\w*", "batalhas?", "lut(a|as|ar|ou|ando)",
    "sangue",
)
_PROIBIDA = re.compile(r"\b(?:" + "|".join(PALAVRAS_PROIBIDAS) + r")\b")
DADOS_PESSOAIS = {
    # Com DDD, ou sem DDD com o meio separado por espaço, ponto ou traço (3333 4444, 9 8765-4321).
    "telefone": re.compile(r"\(?\b\d{2}\)?[ .-]?\d{4,5}[ .-]?\d{4}\b|\b9?\s?\d{4,5}[ .-]\d{4}\b"),
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "documento": re.compile(r"\d{%d,}" % DIGITOS_DE_DOCUMENTO),  # RG, cartão: 8 dígitos ou mais seguidos
}
_ENTRE_PALAVRAS = re.compile(r"(?<=[a-z])(?=[A-Z0-9])")
_DECIMAL_LONGO = re.compile(r"\d\.\d{5,}|\de[-+]\d")


def _cheia(tema, nivel):
    """O conjunto de conceitos que (tema, nível) permite, com os degraus que ele pede."""
    pedidos, novos = ESCADA[(tema, nivel)]
    permitidos = set(novos)
    for pedido in pedidos:
        permitidos |= _cheia(*pedido)
    return permitidos


PERMITIDOS = {degrau: frozenset(_cheia(*degrau)) for degrau in ESCADA}
NA_ESCADA = frozenset().union(*PERMITIDOS.values())


# --- 1. Conceitos ----------------------------------------------------------------


def _caminhos(no):
    """Quantos caminhos tem a cadeia if/elif/else que começa em `no`."""
    total = 1
    while len(no.orelse) == 1 and isinstance(no.orelse[0], ast.If):
        no = no.orelse[0]
        total += 1
    return total + (1 if no.orelse else 0)


def _e_troca(no):
    alvo, valor = no.targets[0], no.value
    if not (isinstance(alvo, ast.Tuple) and isinstance(valor, ast.Tuple) and len(alvo.elts) == len(valor.elts) == 2):
        return False
    nomes = [e.id if isinstance(e, ast.Name) else None for e in alvo.elts]
    lidos = [e.id if isinstance(e, ast.Name) else None for e in valor.elts]
    return None not in nomes and nomes[0] != nomes[1] and lidos == nomes[::-1]


def _e_texto(no, textos):
    """O nó dá um texto? Um texto entre aspas, uma f-string, str(...), uma conta com texto ou um nome que guarda texto."""
    if isinstance(no, ast.Constant):
        return isinstance(no.value, str)
    if isinstance(no, ast.JoinedStr):
        return True
    if isinstance(no, ast.Name):
        return no.id in textos
    if isinstance(no, ast.Call):
        return isinstance(no.func, ast.Name) and no.func.id == "str"
    if isinstance(no, ast.BinOp) and isinstance(no.op, (ast.Add, ast.Mult)):
        return _e_texto(no.left, textos) or _e_texto(no.right, textos)
    return False


def _nomes_de_texto(arvore):
    """Os nomes que recebem texto em algum lugar do programa (nome = "...", nome = outro + "...")."""
    textos = set()
    while True:
        novos = {
            alvo.id
            for no in ast.walk(arvore) if isinstance(no, ast.Assign) and _e_texto(no.value, textos)
            for alvo in no.targets if isinstance(alvo, ast.Name)
        } - textos
        if not novos:
            return textos
        textos |= novos


def conceitos(arvore):
    """Os conceitos que o programa usa: nomes da ESCADA e, fora dela, o que nunca entra."""
    achados = set()
    trocas, iteraveis, nos_testes_do_while = set(), set(), set()
    textos = _nomes_de_texto(arvore)
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and _e_troca(no):
            trocas |= {id(no.targets[0]), id(no.value)}
        elif isinstance(no, ast.For):
            iteraveis.add(id(no.iter))
        elif isinstance(no, ast.While):
            nos_testes_do_while |= {id(n) for n in ast.walk(no.test)}

    def descer(no, ifs, lacos, elif_de=None):
        if isinstance(no, ast.If):
            if elif_de is None:
                ifs += 1
                if _caminhos(no) > 3:
                    achados.add("mais_de_3_caminhos")
            if ifs == 2:
                achados.add("if_aninhado")
            elif ifs > 2:
                achados.add("if_em_3_niveis")
        if isinstance(no, (ast.For, ast.While)):
            lacos += 1
            if lacos > 1:
                achados.add("laco_dentro_de_laco")
        anotar(no)
        for campo, valor in ast.iter_fields(no):
            filhos = valor if isinstance(valor, list) else [valor]
            for filho in filhos:
                if isinstance(filho, ast.AST):
                    e_elif = isinstance(no, ast.If) and campo == "orelse" and no.orelse == [filho] and isinstance(filho, ast.If)
                    descer(filho, ifs, lacos, no if e_elif else None)

    def anotar(no):
        nome = type(no).__name__
        if nome in PROIBIDAS:
            achados.add(PROIBIDAS[nome])
        elif isinstance(no, ast.Expr):
            if not isinstance(no.value, ast.Call):
                achados.add("expressao_solta")
        elif isinstance(no, ast.Assign):
            achados.add("atribuicao")
            if len(no.targets) > 1:
                achados.add("atribuicao_encadeada")
            elif id(no.targets[0]) in trocas:
                achados.add("troca")
            elif isinstance(no.targets[0], ast.Tuple):
                achados.add("desempacotar")
        elif isinstance(no, ast.AugAssign):
            achados.add("atribuicao_composta")
            achados.add(OPERACOES.get(type(no.op), "operador_fora_da_lista"))
        elif isinstance(no, ast.BinOp):
            if isinstance(no.op, ast.Mod) and _e_texto(no.left, textos):
                # "Restam %d copos" % copos: interpolação de texto, como a f-string (nunca entra), não o resto.
                achados.add("formatacao_de_texto")
            else:
                achados.add(OPERACOES.get(type(no.op), "operador_fora_da_lista"))
        elif isinstance(no, ast.UnaryOp):
            if isinstance(no.op, ast.USub):
                achados.add("soma_e_subtracao")
            elif isinstance(no.op, ast.Not):
                achados.add("while_composto" if id(no) in nos_testes_do_while else "e_ou_nao")
            else:
                achados.add("operador_fora_da_lista")
        elif isinstance(no, ast.BoolOp):
            achados.add("while_composto" if id(no) in nos_testes_do_while else "e_ou_nao")
        elif isinstance(no, ast.Compare):
            achados.add("comparacao")
            if len(no.ops) > 1:
                achados.add("comparacao_encadeada")
            if not all(isinstance(op, COMPARACOES) for op in no.ops):
                achados.add("comparacao_fora_da_lista")
        elif isinstance(no, ast.Constant):
            valor = no.value
            if isinstance(valor, bool):
                achados.add("booleano")
            elif isinstance(valor, float):
                achados.add("decimal")
            elif not isinstance(valor, (int, str)):
                achados.add("valor_fora_da_lista")
        elif isinstance(no, ast.If):
            achados.add("if")
            if len(no.orelse) == 1 and isinstance(no.orelse[0], ast.If):
                achados.add("elif")
            elif no.orelse:
                achados.add("else")
        elif isinstance(no, ast.While):
            achados.add("while")
            if isinstance(no.test, ast.Constant):
                achados.add("while_true")
            if no.orelse:
                achados.add("laco_com_else")
        elif isinstance(no, ast.For):
            if not isinstance(no.target, ast.Name):
                achados.add("for_desempacotando")
            if no.orelse:
                achados.add("laco_com_else")
            iteravel = no.iter
            if isinstance(iteravel, ast.Call) and getattr(iteravel.func, "id", None) == "range":
                achados.add("range_com_passo" if len(iteravel.args) == 3 else "for_range")
            elif isinstance(iteravel, (ast.Name, ast.Constant)):
                achados.add("for_texto")  # um nome que guarda lista já pediu a lista (Laços 3)
            elif isinstance(iteravel, ast.List):
                achados.add("lista")
            else:
                achados.add("for_fora_da_lista")
        elif isinstance(no, ast.Break):
            achados.add("break")
        elif isinstance(no, ast.List):
            achados.add("lista")
        elif isinstance(no, ast.Subscript):
            achados.add("fatia" if isinstance(no.slice, ast.Slice) else "indice")
        elif isinstance(no, ast.Tuple):
            if id(no) not in trocas:
                achados.add("tupla")
        elif isinstance(no, ast.Call):
            funcao = no.func.id if isinstance(no.func, ast.Name) else None
            if funcao is None:
                achados.add("metodo")
            elif funcao == "range":
                if id(no) not in iteraveis:
                    achados.add("range_fora_do_for")
            elif funcao in FUNCOES:
                achados.add(funcao)
            elif funcao not in NOMES_PROIBIDOS:
                achados.add("funcao_fora_da_lista")
            if no.keywords:
                achados.add("argumento_nomeado")
        elif isinstance(no, ast.Name):
            if no.id.startswith("__") or no.id in NOMES_PROIBIDOS:
                achados.add("nome_proibido")
        elif isinstance(no, ast.Slice):
            achados.add("fatia")
        elif not isinstance(no, NEUTROS):
            achados.add(f"construcao:{nome}")

    descer(arvore, 0, 0)
    return achados


def fora_da_escada(arvore, tema, nivel):
    """Os motivos de conceito: 'proibido:x' (nunca entra) e 'acima_do_nivel:x' (entra num degrau mais alto)."""
    permitidos = PERMITIDOS[(tema, nivel)]
    motivos = []
    for conceito in sorted(conceitos(arvore) - permitidos):
        motivos.append(f"acima_do_nivel:{conceito}" if conceito in NA_ESCADA else f"proibido:{conceito}")
    return motivos


# --- 6. Textos -------------------------------------------------------------------


def _sem_acento(texto):
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def _textos_do_codigo(arvore):
    textos = [no.value for no in ast.walk(arvore) if isinstance(no, ast.Constant) and isinstance(no.value, str)]
    nomes = sorted({no.id for no in ast.walk(arvore) if isinstance(no, ast.Name)})
    return textos, nomes


def motivos_de_texto(contexto, arvore, saida=""):
    """Vocabulário, dados pessoais, letras sem acento e a frase do contexto."""
    motivos = []
    textos, nomes = _textos_do_codigo(arvore)
    # Nos nomes, o _, a letra maiúscula e o número separam palavras (vidas_extras, vidasExtras, vidas2).
    nomes = [_ENTRE_PALAVRAS.sub(" ", nome).replace("_", " ") for nome in nomes]
    for onde, partes in (("contexto", [contexto]), ("texto", textos), ("nome", nomes),
                         ("saida", [saida])):
        for parte in partes:
            achado = _PROIBIDA.search(_sem_acento(parte))
            if achado:
                motivos.append(f"palavra_proibida:{onde}:{achado.group(0)}")
            for tipo, padrao in DADOS_PESSOAIS.items():
                if padrao.search(parte):
                    motivos.append(f"dado_pessoal:{onde}:{tipo}")
    if not all(texto.isascii() for texto in textos) or not saida.isascii():
        motivos.append("texto_com_acento")
    palavras = contexto.split()
    if not palavras:
        motivos.append("contexto_vazio")
    if len(palavras) > MAX_PALAVRAS_NO_CONTEXTO:
        motivos.append("contexto_longo")
    if "?" in contexto:
        motivos.append("contexto_com_pergunta")
    if "{" in contexto or "}" in contexto:
        motivos.append("contexto_com_lacuna")
    return list(dict.fromkeys(motivos))


# --- 5. Mutações -----------------------------------------------------------------

INVERSO = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
SITIOS = {"variaveis": (ast.Assign,), "condicoes": (ast.If,), "lacos": (ast.While, ast.For)}


def _mudar(no, tema, jeito):
    """Muda o nó no lugar (jeito 0: a borda; jeito 1: um passo maior). False se não se aplica."""
    if tema == "variaveis":
        if not isinstance(no.value, ast.Constant) or isinstance(no.value.value, bool):
            return False
        valor = no.value.value
        if isinstance(valor, str):
            if jeito:
                return False
            no.value = ast.Constant(valor + "x")
        elif isinstance(valor, (int, float)):
            no.value = ast.Constant(valor + (1 if jeito == 0 else 10))
        else:
            return False
    elif tema == "condicoes":
        if jeito:
            return False
        no.test = ast.UnaryOp(ast.Not(), no.test)
    elif isinstance(no, ast.While):
        comparacao = next((c for c in ast.walk(no.test) if isinstance(c, ast.Compare)), None)
        if comparacao is None:
            return False
        if jeito == 0:
            if type(comparacao.ops[0]) not in INVERSO:
                return False
            comparacao.ops[0] = INVERSO[type(comparacao.ops[0])]()
        else:
            comparacao.comparators[-1] = ast.BinOp(comparacao.comparators[-1], ast.Add(), ast.Constant(1))
    else:
        chamada = no.iter
        if isinstance(chamada, ast.Call) and getattr(chamada.func, "id", None) == "range":
            k = 0 if len(chamada.args) == 1 else 1
            chamada.args[k] = ast.BinOp(chamada.args[k], ast.Add() if jeito == 0 else ast.Sub(), ast.Constant(1))
        elif jeito == 0:
            no.iter = ast.Subscript(no.iter, ast.Slice(None, ast.Constant(-1)), ast.Load())
        else:
            return False
    return True


def _mutantes(arvore, tema):
    """Versões do programa com o conceito do tema mexido (até MAX_MUTACOES lugares, 2 jeitos cada)."""
    tipos = SITIOS[tema]
    total = sum(1 for no in ast.walk(arvore) if isinstance(no, tipos))
    codigo = ast.unparse(arvore)
    for k in range(min(total, MAX_MUTACOES)):
        for jeito in (0, 1):
            copia = ast.parse(codigo)
            no = [n for n in ast.walk(copia) if isinstance(n, tipos)][k]
            if _mudar(no, tema, jeito):
                yield ast.unparse(ast.fix_missing_locations(copia))


def _resposta(resultado):
    return resultado["saida"], resultado["erro"]["tipo"] if resultado["erro"] else None


def _mutacao(arvore, tema, original):
    """(motivo ou None, mutantes testados)."""
    testados = 0
    for mutante in _mutantes(arvore, tema):
        testados += 1
        if _resposta(rastrear(mutante, [], LIMITE, 1)) != original:
            return None, testados
    return ("conceito_do_tema_ausente" if not testados else "resposta_nao_depende_do_conceito"), testados


# --- 2 e 3. Execução e medidas -----------------------------------------------------


def _assinatura(resultado):
    return [
        (p["linha"], p["evento"], sorted((k, v["h"]) for k, v in p["globais"].items()))
        for p in resultado["passos"]
    ], resultado["saida"]


def _decimal_ambiguo(resultado):
    for passo in resultado["passos"]:
        for escopo in (passo["globais"], passo["locais"]):
            for valor in escopo.values():
                if valor["tipo"] == "float" and _DECIMAL_LONGO.search(valor["valor"]):
                    return True
    return bool(_DECIMAL_LONGO.search(resultado["saida"]))


def _operacoes(arvore):
    total = 0
    for no in ast.walk(arvore):
        if isinstance(no, (ast.BinOp, ast.AugAssign)):
            total += 1
        elif isinstance(no, ast.Compare):
            total += len(no.ops)
        elif isinstance(no, ast.BoolOp):
            total += len(no.values) - 1
        elif isinstance(no, ast.UnaryOp) and not isinstance(no.operand, ast.Constant):
            total += 1
    return total


def _aninhamento(arvore):
    def fundo(no, d):
        maior = d
        for filho in ast.iter_child_nodes(no):
            maior = max(maior, fundo(filho, d + 1 if isinstance(filho, (ast.If, ast.For, ast.While)) else d))
        return maior

    return fundo(arvore, 0)


def medir(resultado, arvore, codigo):
    """Linhas, passos, voltas, operações, variáveis e aninhamento (o resultado já anotado)."""
    linhas_do_rastro = [p for p in resultado["passos"] if p["evento"] == "linha"]
    nomes = set()
    for passo in resultado["passos"]:
        nomes |= set(passo["globais"])
    return {
        "linhas": sum(1 for linha in codigo.splitlines() if linha.strip()),
        "passos": len(linhas_do_rastro),
        "voltas": sum(
            1 for p in linhas_do_rastro
            if p.get("volta") and p["volta"]["laco"] == p["comando"] and not p["volta"]["saindo"]
        ),
        "operacoes": _operacoes(arvore),
        "variaveis": len(nomes),
        "aninhamento": _aninhamento(arvore),
    }


# --- O verificador -----------------------------------------------------------------


def _ler(exercicio):
    if not isinstance(exercicio, dict):
        raise ValueError("o exercício precisa ser um objeto")
    tema, nivel = exercicio.get("tema"), exercicio.get("nivel")
    if (tema, nivel) not in ESCADA or type(nivel) is not int:
        raise ValueError(f"tema e nível desconhecidos: {tema!r} {nivel!r}")
    codigo, contexto = exercicio.get("codigo"), exercicio.get("contexto", "")
    if not isinstance(codigo, str) or not isinstance(contexto, str):
        raise ValueError("codigo e contexto precisam ser texto")
    if exercicio.get("entradas"):
        raise ValueError("os exercícios de Praticar não têm entradas")
    return tema, nivel, codigo, contexto


def conferir_rapido(exercicio):
    """Só as conferências baratas (escada e textos, sem rodar): para os itens do banco."""
    tema, nivel, codigo, contexto = _ler(exercicio)
    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        return ["erro_de_sintaxe"]
    return fora_da_escada(arvore, tema, nivel) + motivos_de_texto(contexto, arvore)


def chave(codigo):
    """A chave do programa: o sha256 do próprio texto, igual em todo Python."""
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()[:16]


def verificar(exercicio):
    """{ok, motivos, medidas, concepcoes, pontos, so_decisao, chave} do exercício (ok só sem nenhum motivo)."""
    tema, nivel, codigo, contexto = _ler(exercicio)
    motivos = []
    saida = {"ok": False, "motivos": motivos, "medidas": {}, "concepcoes": [], "pontos": 0, "so_decisao": False,
             "chave": chave(codigo)}
    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        motivos.append("erro_de_sintaxe")
        return saida

    # 1. A escada vem antes de rodar: um import nem chega ao motor.
    motivos += fora_da_escada(arvore, tema, nivel)
    motivos += motivos_de_texto(contexto, arvore)
    if any(m.startswith("proibido:") for m in motivos):
        return saida

    # 2. Roda, de novo, e com outra semente.
    resultado = rastrear(codigo, [], LIMITE, 1)
    erro = resultado["erro"]
    if erro is not None:
        motivos.append("nao_termina" if erro["tipo"] == "LimiteDePassos" else f"erro_ao_rodar:{erro['tipo']}")
    if not resultado["deterministico"]:
        motivos.append("nao_deterministico")
    texto = resultado["saida"]
    if len(texto.splitlines()) > MAX_LINHAS or len(texto) > MAX_CARACTERES:
        motivos.append("saida_longa")
    if _decimal_ambiguo(resultado):
        motivos.append("decimal_ambiguo")
    motivos += [m for m in motivos_de_texto(contexto, arvore, texto) if m not in motivos]
    if erro is None:
        if _assinatura(rastrear(codigo, [], LIMITE, 1)) != _assinatura(resultado):
            motivos.append("nao_deterministico")
        if rastrear(codigo, [], LIMITE, 2)["saida"] != texto:
            motivos.append("depende_do_sorteio")

    # 4. Pontos de previsão nos dois formatos; as concepções que deram distrator.
    pontos = {}
    for formato in ("livre", "alternativas"):
        configuracao = {"modo": "prever", "formato": formato, "semente": 1, "orcamento_ms": ORCAMENTO_DOS_MODELOS_MS}
        atividade = montar_atividade(resultado, codigo, [], configuracao)["atividade"]
        pontos[formato] = atividade["pontos"] + ([atividade["palpite_inicial"]] if atividade["palpite_inicial"] else [])
    saida["pontos"] = len(pontos["alternativas"])
    # Só perguntas de sim ou não ("O if vai entrar?") nas alternativas: um cara ou coroa.
    saida["so_decisao"] = all(p["tipo"] == "decisao" for p in pontos["alternativas"])
    if not pontos["alternativas"] or not pontos["livre"]:
        motivos.append("sem_ponto_de_previsao")
    saida["concepcoes"] = sorted({
        a["concepcao"] for p in pontos["alternativas"] for a in p.get("alternativas") or []
        if a["origem"] == "modelo" and a["concepcao"]
    })

    # 3. Tamanho (o resultado já foi anotado pela atividade, com as voltas).
    medidas = saida["medidas"] = medir(resultado, arvore, codigo)
    for nome, teto in ORCAMENTO[(tema, nivel)].items():
        if medidas[nome] > teto:
            motivos.append(f"acima_do_orcamento:{nome}")

    # 5. O conceito do tema importa?
    if erro is None:
        motivo, _ = _mutacao(arvore, tema, _resposta(resultado))
        if motivo:
            motivos.append(motivo)

    saida["ok"] = not motivos
    return saida


def temas_e_niveis():
    """Os pares (tema, nível) do catálogo, na ordem da página."""
    return [(tema["id"], nivel) for tema in TEMAS for nivel in NIVEIS]
