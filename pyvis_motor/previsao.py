"""Palpites gerados do rastro (modo Prever).

Em qualquer programa, o PyVis escolhe sozinho os momentos em que vale pedir
um palpite: uma variável que muda de um jeito que exige pensar (o acumulador
de um laço, as primeiras voltas), um if ou while que decide, um print, o
número de voltas de um laço. O professor escolhe o programa e não escreve
perguntas.

As alternativas erradas vêm primeiro dos modelos de concepção
(concepcoes.py): quem errou daquele jeito provavelmente pensou daquele jeito.
Para completar, entram distratores de regra (o valor antigo, um a mais, um a
menos, o nome no lugar do valor), que nunca contam como diagnóstico.

Cada ponto declara de que campos do rastro a resposta depende
(depende_de_por_passo), e a regra de revelação (revelacao.py) esconde esses
campos até o aluno responder ou pular. Um ponto nunca fica dentro de outro:
a resposta de um não pode entregar a do outro.
"""

import ast
import hashlib
import re
import time

from . import concepcoes
from .anotar import anotar, estado_depois, passo_depois, passos_de_retorno
from .estrutura import NOS_INTERNOS, Analise
from .narrador import narrar_resultado
from .registro import registravel
from .revelacao import aplicar_dependencias
from .valores import com_aspas, formatar

VERSAO = 1
MODOS = ("assistir", "prever")
FORMATOS = ("alternativas", "livre")
MAX_PONTOS = 6
DISTANCIA = 3  # no máximo 1 ponto a cada 3 passos
ORCAMENTO_MS = 500
FOLGA_MS = 50  # o que fica do orçamento para montar as alternativas depois dos modelos
OCORRENCIAS = 3  # de cada comando, só as primeiras vezes viram candidatas
MAX_ALTERNATIVAS = 4
LIMITE_TEXTO = 60
SAIDA_INICIAL = (5, 150)  # linhas e caracteres da saída inteira, para o palpite antes de rodar
LINHAS_NAS_ALTERNATIVAS = 2  # blocos de 3 ou 4 linhas quase iguais cansam a leitura
PESO = {"valor": 2, "decisao": 2, "saida": 2, "voltas": 4}
DECISOES = ("if", "elif", "while")
SIMPLES = (int, float, bool, str, type(None))

PERGUNTAS = {
    "voltas": "Quantas voltas o laço vai dar?",
    "saida": "O que aparece na tela?",
    "inicial": "Qual é o seu palpite? O que vai aparecer na tela?",
}
ELOGIOS = {
    "valor": "Você acompanhou o valor de {nome} passo a passo.",
    "decisao": "Você conferiu a condição com os valores de agora.",
    "saida": "Você acompanhou o que vai para a tela.",
    "inicial": "Você previu a tela inteira antes de rodar.",
    "voltas": "Você contou as voltas do laço com cuidado.",
}


# --- Valores: do rastro para o Python e do Python para o aluno ---------------


def _python(valor):
    """(True, valor Python) a partir de um Valor de valores.py, ou (False, None)."""
    tipo = valor["tipo"]
    if valor.get("cortado"):
        return False, None  # só o começo do valor está no rastro
    if "itens" in valor or "pares" in valor:
        if "pares" in valor:
            pares = [(_python(chave), _python(item)) for chave, item in valor["pares"]]
            if not all(chave[0] and item[0] for chave, item in pares):
                return False, None
            try:
                return True, {chave[1]: item[1] for chave, item in pares}
            except TypeError:
                return False, None
        itens = [_python(item) for item in valor["itens"]]
        if not all(lido for lido, _ in itens) or tipo not in ("list", "tuple", "set"):
            return False, None
        try:
            return True, {"list": list, "tuple": tuple, "set": set}[tipo](item for _, item in itens)
        except TypeError:
            return False, None
    if tipo not in ("int", "float", "bool", "str", "NoneType"):
        return False, None
    try:
        lido = ast.literal_eval(valor["valor"])
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False, None
    return (True, lido) if type(lido).__name__ == tipo else (False, None)


def _exibir(tipo, resposta):
    """O texto que o aluno vê para uma resposta {texto, tipo_valor} (de concepcoes ou daqui)."""
    texto = resposta["texto"]
    if tipo != "valor" or resposta.get("tipo_valor") not in ("texto", "lista"):
        return texto
    try:
        return formatar(ast.literal_eval(texto))
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return texto


def _chave(tipo, resposta):
    return concepcoes._chave_da_resposta(tipo, resposta)


def _parece_numero(texto):
    try:
        return type(ast.literal_eval(texto.strip())) in (int, float)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError, AttributeError):
        return False


def _plural(n, palavra):
    return f"{n} {palavra}" if n == 1 else f"{n} {palavra}s"


def _na_tela(texto):
    """Saída numa linha só, entre aspas tipográficas, como no narrador."""
    return "“" + texto.replace("\n", " / ") + "”"


def _na_tela_e_ponto(texto):
    """“Fim de jogo!” sem um ponto depois do '!'."""
    return _na_tela(texto) + ("" if texto.rstrip().endswith((".", "!", "?", "…")) else ".")


# --- O código do aluno --------------------------------------------------------


def _e_chamada(no, *nomes):
    return isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in nomes


def _nomes_lidos(no):
    """Nomes lidos pela expressão, na ordem do código, fora de compreensões e lambdas."""
    nomes = []
    pendentes = [no]
    while pendentes:
        atual = pendentes.pop()
        if isinstance(atual, NOS_INTERNOS):
            continue  # dentro delas, um nome pode ser a variável da própria compreensão
        if isinstance(atual, ast.Name):
            if isinstance(atual.ctx, ast.Load):
                nomes.append(atual)
            continue
        if isinstance(atual, ast.Call) and isinstance(atual.func, ast.Name):
            pendentes.extend(atual.args)
            pendentes.extend(palavra.value for palavra in atual.keywords)
            continue  # o nome da função não é um valor
        pendentes.extend(ast.iter_child_nodes(atual))
    ordem = []
    for nome in sorted(nomes, key=lambda n: (n.lineno, n.col_offset)):
        if nome.id not in ordem:
            ordem.append(nome.id)
    return ordem


def _literal(no):
    """Um valor escrito direto no código (5, "Ana", [1, 2]): a resposta já está na tela."""
    if isinstance(no, ast.Constant):
        return True
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
        return isinstance(no.operand, ast.Constant)
    if isinstance(no, (ast.List, ast.Tuple, ast.Set)):
        return all(_literal(item) for item in no.elts)
    if isinstance(no, ast.Dict):
        return all(chave is not None and _literal(chave) for chave in no.keys) and all(_literal(v) for v in no.values)
    return False


def _alvo_e_valor(no):
    """(nome, expressão) de `nome = expr`, `nome: tipo = expr` ou `nome += expr`; nome None se não for um nome só."""
    if isinstance(no, ast.Assign):
        alvos = no.targets
        nome = alvos[0].id if len(alvos) == 1 and isinstance(alvos[0], ast.Name) else None
        return nome, no.value
    if isinstance(no, (ast.AugAssign, ast.AnnAssign)):
        return (no.target.id if isinstance(no.target, ast.Name) else None), no.value
    return None, None


def _estado(passo, nome):
    """O Valor de `nome` no passo (antes do comando), procurando como o Python procura."""
    if passo["funcao"] is not None and nome in passo["locais"]:
        return passo["locais"][nome]
    return passo["globais"].get(nome)


def _depois(passo, seguinte, efeito, nome):
    """O Valor de `nome` depois do comando, ou None se ele não mudou (ou sumiu com a função)."""
    mudada = next((m for m in efeito["mudadas"] if m["nome"] == nome), None)
    if mudada is not None:
        return mudada["depois"]
    if nome not in efeito["criadas"]:
        return None
    if not efeito["parcial"] and passo["funcao"] is not None and nome in seguinte["locais"]:
        return seguinte["locais"][nome]
    return seguinte["globais"].get(nome)


def _valores_lidos(passo, nomes, limite=3):
    """'total valia 3 e numero valia 3', com os valores de antes do comando."""
    partes = []
    for nome in nomes:
        valor = _estado(passo, nome)
        if valor is None:
            continue
        lido, python = _python(valor)
        if not lido or (type(python) not in SIMPLES and len(formatar(python)) > 20):
            continue
        partes.append(f"{nome} valia {formatar(python)}")
        if len(partes) == limite:
            break
    if not partes:
        return ""
    return ", ".join(partes[:-1]) + " e " + partes[-1] if len(partes) > 1 else partes[0]


# --- Candidatos ----------------------------------------------------------------


class _Leitor:
    """O que todas as candidatas precisam: o rastro anotado, a AST e o que já foi visto."""

    def __init__(self, resultado, analise):
        self.passos = resultado["passos"]
        self.comandos = resultado["estrutura"]["comandos"]
        self.nos = analise.nos
        self.retornos = passos_de_retorno(self.passos)
        self.inicios = concepcoes.inicios_de_laco(self.passos, self.comandos)
        self.entrada_de = {i: (laco, k) for (laco, k), i in self.inicios.items()}
        self.tem_input = any(_e_chamada(no, "input") for no in ast.walk(analise.arvore))
        self.saidas = {}  # comando -> o que ele escreveu da última vez

    def depois(self, passo):
        indice, _ = passo_depois(passo, self.retornos)
        return indice

    def chama_funcao(self, passo):
        seguinte = passo["i"] + 1
        return seguinte < len(self.passos) and self.passos[seguinte]["profundidade"] > passo["profundidade"]


def _candidata(leitor, passo, tipo, certa, exibir, **extra):
    candidata = {
        "tipo": tipo,
        "passo": passo["i"],
        "comando": passo["comando"],
        "nome": None,
        "ocorrencia": 1,
        "certa": certa,
        "exibir": exibir,
        "regras": [],
        "peso": PESO[tipo],
        "fim": leitor.depois(passo) if passo["evento"] == "linha" else None,
    }
    candidata.update(extra)
    if len(exibir) > LIMITE_TEXTO * (3 if tipo == "saida" else 1):
        return None  # resposta comprida demais para palpite
    candidata["peso"] += _bonus_da_volta(passo)
    return candidata


def _ultima_volta(passo):
    volta = passo["volta"]
    return bool(volta) and volta["total"] is not None and volta["n"] == volta["total"] and volta["n"] > 0


def _bonus_da_volta(passo):
    """As duas primeiras voltas e a última (onde o laço erra por um) valem mais que as do meio."""
    volta = passo["volta"]
    if volta is None or passo["evento"] != "linha":
        return 0
    return 1 if volta["n"] <= 2 or _ultima_volta(passo) else -1


def _candidata_de_valor(leitor, passo, ocorrencia):
    comando = leitor.comandos[passo["comando"]]
    no = leitor.nos[passo["comando"]]
    efeito = passo["efeito"]
    seguinte, _ = estado_depois(passo, leitor.passos, leitor.retornos)
    if efeito is None or seguinte is None:
        return None
    volta = passo["volta"]
    if comando["tipo"] == "for":
        if not isinstance(no.target, ast.Name) or not volta or volta["laco"] != comando["id"] or volta["saindo"]:
            return None
        nome, expressao = no.target.id, None
    else:
        nome, expressao = _alvo_e_valor(no)
        if nome is None or expressao is None or (comando["tipo"] == "atrib" and _literal(expressao)):
            return None
    depois = _depois(passo, seguinte, efeito, nome)
    if depois is None:
        return None
    lido, valor = _python(depois)
    if not lido:
        return None
    certa = concepcoes.resposta_de_valor(valor)
    if certa["tipo_valor"] == "outro":
        return None
    candidata = _candidata(leitor, passo, "valor", certa, formatar(valor), nome=nome, ocorrencia=ocorrencia)
    if candidata is None:
        return None
    antes = _estado(passo, nome)
    acumulador = comando["acumulador"]
    if acumulador and acumulador["nome"] == nome:
        candidata["peso"] += 2
    if isinstance(expressao, ast.Name):
        candidata["peso"] -= 1  # só uma cópia: o valor já está na outra caixinha
    lidos = [] if expressao is None else _nomes_lidos(expressao)
    if isinstance(no, ast.AugAssign):
        lidos = [nome] + [n for n in lidos if n != nome]
    candidata["sensivel_texto"] = type(valor) is str and _parece_numero(valor)
    if candidata["sensivel_texto"]:
        candidata["peso"] += 1
    candidata["regras"] = _regras_de_valor(passo, valor, antes, lidos)
    if comando["tipo"] == "for" and isinstance(no.iter, ast.Name):
        # Os outros itens da lista percorrida (ou letras do texto): pular um item ou repetir o anterior.
        lista = _estado(passo, no.iter.id)
        lido, itens = _python(lista) if lista is not None else (False, None)
        if lido and type(itens) in (list, tuple, str):
            candidata["regras"] += [concepcoes.resposta_de_valor(item) for item in itens[:10]]
    candidata["pergunta"] = f"Depois desta linha, quanto vale {nome}?"
    candidata["explicacao"] = _explicar_valor(passo, comando, expressao, nome, valor, lidos)
    return candidata


def _regras_de_valor(passo, certa, antes, lidos):
    """Distratores de regra para um valor: o antigo, o de outra variável, o tipo trocado, ±1."""
    opcoes = []
    if antes is not None:
        lido, valor = _python(antes)
        if lido:
            opcoes.append(valor)
    categoria = concepcoes._tipo_valor(certa)
    for nome in lidos:
        valor = _estado(passo, nome)
        if valor is None:
            continue
        lido, python = _python(valor)
        if lido and concepcoes._tipo_valor(python) == categoria:
            opcoes.append(python)  # o valor de outra variável da conta
    if type(certa) is str and _parece_numero(certa):
        opcoes.append(ast.literal_eval(certa.strip()))  # o texto "11" lido como número
    if type(certa) is bool:
        opcoes.append(not certa)
    elif type(certa) in (int, float):
        opcoes += [certa + 1, certa - 1]
    return [concepcoes.resposta_de_valor(valor) for valor in opcoes]


def _explicar_valor(passo, comando, expressao, nome, valor, lidos):
    texto = formatar(valor)
    if comando["tipo"] == "for":
        return f"O for pegou o próximo valor: {nome} recebe {texto}."
    if _e_chamada(expressao, "input"):
        return f"O input devolve texto: {nome} recebeu {texto}."
    if _e_chamada(expressao, "int", "float") and expressao.args and _e_chamada(expressao.args[0], "input"):
        return f"O {expressao.func.id} transformou o texto do input em número: {nome} recebeu {texto}."
    porque = _valores_lidos(passo, lidos)
    if porque:
        return f"O Python guardou {texto} em {nome} porque {porque}."
    return f"O Python guardou {texto} em {nome}."


def _candidata_de_decisao(leitor, passo, ocorrencia):
    comando = leitor.comandos[passo["comando"]]
    no = leitor.nos[passo["comando"]]
    decisao = passo["decisao"]
    if not decisao or decisao["ramo"] == "desconhecido" or isinstance(no.test, ast.Constant):
        return None
    if decisao["texto"] in ("True", "False"):
        return None  # `if achou:`: o valor já está na caixinha
    entrou = decisao["ramo"] == "corpo"
    certa = concepcoes.resposta_de_decisao(entrou)
    tipo = comando["tipo"]
    entrada = passo["i"] in leitor.entrada_de
    if tipo == "while":
        pergunta = "O while vai entrar no laço?" if entrada else "O while vai dar mais uma volta?"
        sim = "Verdadeiro: entra no laço" if entrada else "Verdadeiro: dá mais uma volta"
        nao = "Falso: nem entra no laço" if entrada else "Falso: sai do laço"
    else:
        bloco = "elif" if tipo == "elif" else "if"
        pergunta = f"O {bloco} vai entrar?"
        sim = f"Verdadeiro: entra no {bloco}"
        senao = comando["orelse"]
        if senao and any(c["pai"] == comando["id"] and c["tipo"] == "elif" and c["linhas"][0] == senao[0]
                         for c in leitor.comandos):
            nao = "Falso: testa o elif"
        elif senao:
            nao = "Falso: vai para o else"
        else:
            nao = f"Falso: não entra no {bloco}"
    resposta = "Verdadeiro" if entrou else "Falso"
    volta = passo["volta"]
    saindo = bool(volta) and volta["laco"] == comando["id"] and volta["saindo"]
    if decisao["texto"]:
        explicacao = f"Com os valores de agora, {decisao['texto']} dá {resposta}."
    else:
        explicacao = f"A condição deu {resposta}."
    candidata = _candidata(leitor, passo, "decisao", certa, resposta, ocorrencia=ocorrencia, pergunta=pergunta,
                           textos=(sim, nao), explicacao=explicacao,
                           regras=[concepcoes.resposta_de_decisao(not entrou)])
    if candidata is not None and saindo and not entrada:
        candidata["peso"] += 1  # a conferência que encerra o laço
    return candidata


def _candidata_de_saida(leitor, passo, ocorrencia):
    comando = leitor.comandos[passo["comando"]]
    no = leitor.nos[passo["comando"]]
    efeito = passo["efeito"]
    if efeito is None or not efeito["saida_nova"] or not isinstance(no, ast.Expr):
        return None
    chamada = no.value
    if not isinstance(chamada, ast.Call) or any(_e_chamada(filho, "input") for filho in ast.walk(chamada)):
        return None  # o input também escreve na tela: a pergunta e o que foi digitado
    if leitor.tem_input and leitor.chama_funcao(passo):
        return None  # uma função do aluno pode pedir input no meio
    if comando["tipo"] == "expr" and not leitor.chama_funcao(passo):
        return None  # só um print ou uma função do aluno escrevem na tela
    if comando["tipo"] == "print" and all(
        isinstance(filho, ast.Constant) for filho in chamada.args + [chave.value for chave in chamada.keywords]
    ):
        return None  # print("Pronto!"): a resposta já está escrita no código
    certa = concepcoes.resposta_de_saida(efeito["saida_nova"])
    if not certa["texto"].strip():
        return None
    anterior = leitor.saidas.get(passo["comando"])
    candidata = _candidata(leitor, passo, "saida", certa, certa["texto"], ocorrencia=ocorrencia,
                           pergunta=PERGUNTAS["saida"])
    if candidata is None:
        return None
    if comando["tipo"] == "expr":
        candidata["peso"] -= 1
    regras = []
    if anterior is not None:
        regras.append(anterior)  # "a tela mostra o mesmo da volta de antes"
    regras += _regras_de_saida(passo, chamada, certa["texto"])
    candidata["regras"] = [concepcoes.resposta_de_saida(texto) for texto in regras]
    lidos = _nomes_lidos(chamada) if comando["tipo"] == "print" else []
    porque = _valores_lidos(passo, lidos)
    candidata["explicacao"] = (
        f"Na tela apareceu {_na_tela(certa['texto'])} porque {porque}." if porque
        else f"Na tela apareceu {_na_tela_e_ponto(certa['texto'])}"
    )
    if lidos:
        candidata["elogio"] = f"Você leu o valor de {' e '.join(lidos[:2])} na hora do print."
    return candidata


def _regras_de_saida(passo, chamada, texto):
    """O nome no lugar do valor (print(total) mostrando 'total'), o último número ±1 e as aspas na tela."""
    opcoes = []
    argumentos = chamada.args
    if _e_chamada(chamada, "print") and not chamada.keywords and argumentos:
        partes = []
        for argumento in argumentos:
            if isinstance(argumento, ast.Constant) and isinstance(argumento.value, (str, int, float)):
                partes.append(str(argumento.value))
            elif isinstance(argumento, ast.Name):
                partes.append(argumento.id)
            else:
                partes = None
                break
        if partes and any(isinstance(a, ast.Name) for a in argumentos):
            opcoes.append(" ".join(partes))
    opcoes += _numero_vizinho(texto)
    if _e_chamada(chamada, "print") and len(argumentos) == 1 and isinstance(argumentos[0], ast.Constant):
        if isinstance(argumentos[0].value, str) and "\n" not in texto:
            opcoes.append(f'"{texto}"')
    return opcoes


def _numero_vizinho(texto):
    numeros = list(re.finditer(r"(?<![\w.])-?\d+(?![\w.])", texto))
    if not numeros:
        return []
    ultimo = numeros[-1]
    valor = int(ultimo.group())
    return [texto[: ultimo.start()] + str(valor + delta) + texto[ultimo.end() :] for delta in (1, -1)]


def _candidata_de_voltas(leitor, passo, totais):
    laco, k = leitor.entrada_de[passo["i"]]
    volta = passo["volta"]
    if not volta or volta["laco"] != laco or volta["total"] is None:
        return None
    total = volta["total"]
    totais.setdefault(laco, []).append(total)
    if k > 2 or (k == 2 and totais[laco][0] == total):
        return None  # a segunda entrada só vale se o número de voltas mudou
    certa = concepcoes.resposta_de_voltas(total)
    comando = leitor.comandos[laco]
    explicacao = f"O laço deu {_plural(total, 'volta')}."
    leitura = comando.get("leitura")
    if comando["tipo"] == "for" and leitura and leitura["traduzida"] != leitura["literal"]:
        # A leitura traduzida é 'para cada numero de 1 até 4': fica a faixa.
        prefixo = f"para cada {ast.unparse(leitor.nos[laco].target)} "
        if leitura["traduzida"].startswith(prefixo):
            explicacao += f" Ele foi {leitura['traduzida'][len(prefixo) :]}."
    elif comando["tipo"] == "for":
        explicacao += _itens_do_for(leitor, passo, laco, total)
    elif comando["tipo"] == "while" and volta["total_visivel_desde"] is not None:
        saida = leitor.passos[volta["total_visivel_desde"] - 1] if volta["total_visivel_desde"] > 0 else None
        decisao = saida.get("decisao") if saida and saida["comando"] == laco else None
        if decisao and decisao["texto"] and decisao["ramo"] in ("sai", "orelse"):
            explicacao += f" Depois, {decisao['texto']} deu Falso."
    vizinhos = [total + 1, total - 1, total + 2]
    # Onde olhar: a última volta mostra onde o laço para; a primeira não diz nada sobre isso.
    fim = volta["total_visivel_desde"] if volta["total_visivel_desde"] is not None else len(leitor.passos)
    ultima = next((p["i"] for p in reversed(leitor.passos[passo["i"] : fim])
                   if p["comando"] == laco and p["volta"] and p["volta"]["laco"] == laco
                   and p["volta"]["n"] == total and not p["volta"]["saindo"]), passo["i"])
    return _candidata(
        leitor, passo, "voltas", certa, certa["texto"], comando=laco, ocorrencia=k, pergunta=PERGUNTAS["voltas"],
        explicacao=explicacao, regras=[concepcoes.resposta_de_voltas(n) for n in vizinhos if n >= 0],
        fim=passo["i"] + 1, onde=ultima,
    )


ITENS = {"list": ("item", "itens"), "tuple": ("item", "itens"), "set": ("item", "itens"),
         "str": ("letra", "letras"), "dict": ("chave", "chaves")}


def _itens_do_for(leitor, passo, laco, total):
    """' Uma volta para cada item de frutas: são 3 itens.' quando o for anda por uma coleção.

    Só quando o número de itens é o de voltas: com um break no meio, a frase mentiria.
    """
    iteravel = leitor.nos[laco].iter
    if isinstance(iteravel, ast.Name):
        valor = _estado(passo, iteravel.id)
        lido, colecao = _python(valor) if valor is not None else (False, None)
    elif _literal(iteravel):
        lido, colecao = True, ast.literal_eval(iteravel)
    else:
        return ""
    if not lido or type(colecao).__name__ not in ITENS or len(colecao) != total:
        return ""
    um, varios = ITENS[type(colecao).__name__]
    fonte = iteravel.id if isinstance(iteravel, ast.Name) else formatar(colecao)
    if len(fonte) > 20:
        return ""
    return f" Uma volta para cada {um} de {fonte}: são {total} {um if total == 1 else varios}."


def _candidata_inicial(leitor, resultado, formato):
    """A saída inteira, perguntada antes de rodar e corrigida no fim.

    Com input não há palpite: a saída traz as perguntas e o que foi digitado.
    """
    saida = resultado["saida"]
    if resultado["erro"] is not None or not leitor.passos or not saida.strip() or leitor.tem_input:
        return None
    linhas, caracteres = SAIDA_INICIAL
    if formato == "alternativas":
        linhas = LINHAS_NAS_ALTERNATIVAS
    certa = concepcoes.resposta_de_saida(saida)
    if certa["texto"].count("\n") >= linhas or len(certa["texto"]) > caracteres:
        return None
    regras = _numero_vizinho(certa["texto"])
    if "\n" in certa["texto"]:
        regras.append(certa["texto"].rsplit("\n", 1)[0])  # parou um print antes
    return {
        "tipo": "saida", "passo": 0, "comando": None, "nome": None, "ocorrencia": 1, "certa": certa,
        "exibir": certa["texto"], "regras": [concepcoes.resposta_de_saida(texto) for texto in regras],
        "peso": 0, "fim": None, "pergunta": PERGUNTAS["inicial"], "elogio": ELOGIOS["inicial"],
        "explicacao": f"No fim, a tela mostrou {_na_tela_e_ponto(certa['texto'])}",
    }


def candidatas(resultado, analise):
    """Os candidatos a ponto, como em 2.2 (a)-(d), cada um com a resposta certa do rastro.

    (a) mudança não trivial de uma variável (atribuição, += ou a variável do
    for), (b) decisão de if, elif ou while, (c) saída nova de um print, (d) o
    número de voltas, perguntado na entrada do laço. De cada comando, só as
    primeiras ocorrências, a da última volta e a da saída do laço.
    """
    leitor = _Leitor(resultado, analise)
    contagem = {}
    extras = {}
    totais = {}
    lista = []
    for passo in leitor.passos:
        if passo["evento"] != "linha" or passo["comando"] is None:
            continue
        indice = passo["comando"]
        n = contagem[indice] = contagem.get(indice, 0) + 1
        tipo = leitor.comandos[indice]["tipo"]
        achadas = []
        if passo["i"] in leitor.entrada_de:
            achadas.append(_candidata_de_voltas(leitor, passo, totais))
        volta = passo["volta"]
        saindo = bool(volta) and volta["laco"] == indice and volta["saindo"]
        # As primeiras vezes de cada comando, mais a última volta e a saída do laço.
        extra = (_ultima_volta(passo) or saindo) and extras.get(indice, 0) < 2
        if n <= OCORRENCIAS or extra:
            if n > OCORRENCIAS:
                extras[indice] = extras.get(indice, 0) + 1
            if tipo in ("atrib", "aug", "for"):
                achadas.append(_candidata_de_valor(leitor, passo, n))
            elif tipo in DECISOES:
                achadas.append(_candidata_de_decisao(leitor, passo, n))
            elif tipo in ("print", "expr"):
                achadas.append(_candidata_de_saida(leitor, passo, n))
        if tipo in ("print", "expr") and passo["efeito"] and passo["efeito"]["saida_nova"]:
            leitor.saidas[indice] = concepcoes.resposta_de_saida(passo["efeito"]["saida_nova"])["texto"]
        lista += [candidata for candidata in achadas if candidata is not None]
    return lista, leitor


# --- Escolha dos pontos -----------------------------------------------------------


def _alvo(candidata, cid):
    # `passo` vira o onde.passo do retorno; o palpite antes de rodar não tem um passo só.
    passo = None if candidata["comando"] is None else candidata.get("onde", candidata["passo"])
    return {"id": cid, "tipo": candidata["tipo"], "passo": passo,
            "alvo": {"comando": candidata["comando"], "nome": candidata["nome"]}, "ocorrencia": candidata["ocorrencia"]}


def _distratores(candidata, bloco):
    """Distratores de modelo (os de uma concepção só primeiro) e de regra, sem repetir e sem a certa."""
    tipo = candidata["tipo"]
    vistas = {_chave(tipo, candidata["certa"])}
    textos = {candidata["exibir"]}
    lista = []
    modelos = sorted(bloco["alternativas"], key=lambda a: len(a["concepcoes"]) > 1)
    for modelo in modelos:
        if modelo["tipo_valor"] == "outro" or modelo["texto"].endswith("…"):
            continue  # cortado, o distrator se denunciaria ao lado da certa inteira
        texto = _exibir(tipo, modelo)
        chave = _chave(tipo, modelo)
        if chave in vistas or texto in textos:
            continue
        vistas.add(chave)
        textos.add(texto)
        lista.append({"texto": texto, "tipo_valor": modelo["tipo_valor"], "certa": False,
                      "concepcao": modelo["concepcao"], "concepcoes": list(modelo["concepcoes"]), "origem": "modelo",
                      "feedback": modelo["feedback"]})
    for regra in candidata["regras"]:
        texto = _exibir(tipo, regra)
        if regra["chave"] in vistas or texto in textos or len(texto) > LIMITE_TEXTO * 3:
            continue
        vistas.add(regra["chave"])
        textos.add(texto)
        lista.append({"texto": texto, "tipo_valor": regra["tipo_valor"], "certa": False, "concepcao": None,
                      "concepcoes": [], "origem": "regra", "feedback": None})
    return lista


def _pontuar(candidata, observaveis):
    pontos = candidata["peso"]
    if observaveis[candidata["tipo"]]:
        pontos += 2  # alguma concepção pode aparecer neste tipo de pergunta
    if candidata["com_modelo"]:
        # E uma delas de fato dá outra resposta aqui. A C04 (o valor antigo) vale
        # menos: ela é o mesmo distrator de regra, só que com diagnóstico.
        so_valor_antigo = all(d["concepcoes"] == ["C04"] for d in candidata["distratores"] if d["origem"] == "modelo")
        pontos += 1 if so_valor_antigo else 2
    if candidata["ocorrencia"] > 2:
        pontos -= 1
    if candidata["tipo"] != "decisao" and len(candidata["distratores"]) < 2:
        pontos -= 1  # sem pelo menos 3 alternativas
    return pontos


def _conflita(a, b, comandos):
    if abs(a["passo"] - b["passo"]) < DISTANCIA:
        return True
    if (a["tipo"], a["comando"]) == (b["tipo"], b["comando"]):
        return True
    for de_fora, de_dentro in ((a, b), (b, a)):
        # A resposta de um ponto que contém o outro (uma chamada de função) entregaria a dele.
        if de_fora["fim"] is not None and de_fora["passo"] < de_dentro["passo"] < de_fora["fim"]:
            return True
    # No while, saber quantas voltas ele dá responde se a condição entra (e vice-versa).
    if {a["tipo"], b["tipo"]} == {"voltas", "decisao"} and a["comando"] == b["comando"]:
        return comandos[a["comando"]]["tipo"] == "while"
    return False


def _escolher(candidatas, maximo, comandos):
    escolhidas = []
    restantes = [c for c in candidatas if c.get("elegivel", True)]
    while len(escolhidas) < maximo:
        melhor = None
        for candidata in restantes:
            if any(_conflita(candidata, outra, comandos) for outra in escolhidas):
                continue
            # Tipos variados: cada ponto do mesmo tipo já escolhido tira 1.
            nota = candidata["nota"] - sum(1 for outra in escolhidas if outra["tipo"] == candidata["tipo"])
            if melhor is None or (nota, -candidata["passo"]) > melhor[0]:
                melhor = ((nota, -candidata["passo"]), candidata)
        if melhor is None:
            break
        escolhidas.append(melhor[1])
        restantes.remove(melhor[1])
    return sorted(escolhidas, key=lambda c: c["passo"])


# --- Montagem da atividade ---------------------------------------------------------


def _embaralhar(alternativas, semente, pid):
    def chave(alternativa):
        return hashlib.sha256(f"{semente}|{pid}|{alternativa['texto']}".encode("utf-8", "surrogatepass")).hexdigest()

    return sorted(alternativas, key=chave)


def _alternativas(candidata, semente, pid):
    """De 3 a 4 alternativas embaralhadas com a semente (2 na decisão: Verdadeiro e Falso)."""
    if candidata["tipo"] == "decisao":
        sim, nao = candidata["textos"]
        entrou = candidata["certa"]["chave"][1]
        errada = candidata["distratores"][0] if candidata["distratores"] else None
        lista = [
            {"texto": sim, "tipo_valor": "bool", "certa": entrou},
            {"texto": nao, "tipo_valor": "bool", "certa": not entrou},
        ]
        for alternativa in lista:
            if alternativa["certa"]:
                alternativa.update(concepcao=None, concepcoes=[], origem="correta", feedback=None)
            elif errada is not None:
                alternativa.update(concepcao=errada["concepcao"], concepcoes=errada["concepcoes"],
                                   origem=errada["origem"], feedback=errada["feedback"])
            else:
                alternativa.update(concepcao=None, concepcoes=[], origem="regra", feedback=None)
        # Verdadeiro sempre primeiro: trocar a ordem de duas opções só confunde.
    else:
        correta = {"texto": candidata["exibir"], "tipo_valor": candidata["certa"]["tipo_valor"], "certa": True,
                   "concepcao": None, "concepcoes": [], "origem": "correta", "feedback": None}
        lista = _embaralhar([correta] + candidata["distratores"][: MAX_ALTERNATIVAS - 1], semente, pid)
    for numero, alternativa in enumerate(lista, 1):
        alternativa["id"] = f"{pid}a{numero}"
    return lista


def _publica(alternativa):
    return {chave: alternativa[chave] for chave in ("id", "texto", "tipo_valor", "certa", "concepcao", "origem",
                                                    "feedback")}


def _elogio(candidata, testadas):
    if "elogio" in candidata:
        return candidata["elogio"]  # o que a pergunta testou de fato (ler o valor no print, a tela inteira)
    if testadas:
        return f"Isso! {concepcoes.POR_ID[testadas[0]]['regra_para_aluno']}"
    return ELOGIOS[candidata["tipo"]].format(nome=candidata["nome"])


def _ponto(candidata, pid, formato, semente, observaveis):
    """Ponto da atividade. As chaves que começam com '_' ficam só no Python (para corrigir)."""
    bloco = candidata["bloco"]
    certa = candidata["certa"]
    testadas = []
    for modelo in bloco["modelos"]:
        if modelo["concepcao"] not in testadas:
            testadas.append(modelo["concepcao"])
    tipo_valor = certa["tipo_valor"]
    so_alternativas = candidata["tipo"] == "decisao" or (
        candidata["tipo"] == "valor" and tipo_valor not in ("numero", "texto")
    )
    formato_do_ponto = "alternativas" if formato == "alternativas" or so_alternativas else "livre"
    alternativas = _alternativas(candidata, semente, pid)
    modelos_com_tipo = {m["tipo_valor"] for m in bloco["modelos"]}
    ponto = {
        "id": pid,
        "passo": candidata["passo"],
        "tipo": candidata["tipo"],
        "alvo": {"comando": candidata["comando"]},
        "ocorrencia": candidata["ocorrencia"],
        "pergunta": candidata["pergunta"],
        "resposta": {"texto": candidata["exibir"], "tipo_valor": tipo_valor},
        "formato": formato_do_ponto,
        "sensivel_a_tipo": candidata["tipo"] == "valor"
        and tipo_valor in ("numero", "texto")
        and (candidata.get("sensivel_texto", False) or bool(modelos_com_tipo & ({"numero", "texto"} - {tipo_valor}))),
        "concepcoes_observaveis": list(observaveis[candidata["tipo"]]),
        "testadas": testadas,
        "explicacao": candidata["explicacao"],
        "elogio": _elogio(candidata, testadas),
        "_modelos": bloco["modelos"],
        "_alternativas": alternativas,
    }
    if candidata["nome"] is not None:
        ponto["alvo"]["nome"] = candidata["nome"]
    if formato_do_ponto == "alternativas":
        ponto["alternativas"] = [_publica(alternativa) for alternativa in alternativas]
    return ponto


def publico(ponto):
    """O Ponto sem o que fica só no Python (os modelos usados na correção da resposta livre)."""
    return {chave: valor for chave, valor in ponto.items() if not chave.startswith("_")}


def _config(config, resultado):
    config = dict(config or {})
    modo = config.get("modo", "prever")
    formato = config.get("formato", "alternativas")
    maximo = config.get("max_pontos", MAX_PONTOS)
    if modo not in MODOS:
        raise ValueError("modo precisa ser 'assistir' ou 'prever'")
    if formato not in FORMATOS:
        raise ValueError("formato precisa ser 'alternativas' ou 'livre'")
    if type(maximo) is not int or not 0 <= maximo <= 20:
        raise ValueError("max_pontos precisa ser um inteiro de 0 a 20")
    semente = config.get("semente")
    return {
        "modo": modo,
        "formato": formato,
        "max_pontos": maximo,
        "semente": resultado.get("semente", 0) if semente is None else semente,
        "palpite_inicial": bool(config.get("palpite_inicial", True)),
        "orcamento_ms": float(config.get("orcamento_ms", ORCAMENTO_MS)),
    }


def _vazia(config):
    return {
        "versao": VERSAO,
        "modo": config["modo"],
        "formato": config["formato"],
        "semente": config["semente"],
        "pontos": [],
        "palpite_inicial": None,
        "depende_de_por_passo": {},
        "traduzida_depende_de": {},
        "cobertura": {"pontos_com_modelo": 0, "total": 0, "candidatos": 0, "candidatos_com_modelo": 0},
        "completa": True,
        "tempo_ms": 0.0,
    }


def montar_atividade(resultado, codigo, entradas=(), config=None):
    """A atividade e os pontos completos: {atividade: Atividade, pontos: {id: Ponto com _modelos}}.

    O resultado precisa ser o de rastrear(codigo, entradas). Ele é anotado e
    narrado se ainda não foi, e ganha passo.depende_de e a leitura traduzida
    dependente dos pontos (revelacao.aplicar_dependencias). Pode ser chamado de
    novo com outra configuração: as dependências são refeitas do zero.
    """
    inicio = time.perf_counter()
    config = _config(config, resultado)
    atividade = _vazia(config)
    comandos = resultado["estrutura"]["comandos"]
    passos = resultado["passos"]
    if passos and "efeito" not in passos[0]:
        anotar(resultado)
    if comandos and "leitura" not in comandos[0]:
        narrar_resultado(resultado, codigo)
    for comando in comandos:
        comando["leitura"]["traduzida_depende_de"] = []
    if config["modo"] != "prever" or not comandos or not passos:
        aplicar_dependencias(resultado, {})
        atividade["tempo_ms"] = (time.perf_counter() - inicio) * 1000
        return {"atividade": atividade, "pontos": {}}

    analise = Analise(codigo)
    if len(analise.nos) != len(comandos):
        raise ValueError("o código não é o mesmo que gerou o resultado")
    lista, leitor = candidatas(resultado, analise)
    inicial = _candidata_inicial(leitor, resultado, config["formato"]) if config["palpite_inicial"] else None
    todas = lista + ([inicial] if inicial else [])
    alvos = [_alvo(candidata, f"c{numero}") for numero, candidata in enumerate(todas)]

    gasto = (time.perf_counter() - inicio) * 1000
    modelos = concepcoes.gerar_modelos(
        codigo, list(entradas), alvos, resultado=resultado, orcamento_ms=max(0.0, config["orcamento_ms"] - gasto - FOLGA_MS)
    )
    observaveis = {tipo: concepcoes.observaveis(tipo, analise) for tipo in PESO}
    completa = modelos["completa"]
    for candidata, alvo in zip(todas, alvos):
        bloco = modelos["por_ponto"][alvo["id"]]
        completa = completa and "orcamento" not in bloco["sem_modelo"].values()
        certa_do_modelo = bloco["certa"]
        if certa_do_modelo is not None and _chave(candidata["tipo"], certa_do_modelo) != candidata["certa"]["chave"]:
            # O rastro completo é o que o aluno vê: se o rastreio leve discordar, o modelo não vale aqui.
            bloco = dict(bloco, alternativas=[], modelos=[])
        candidata["bloco"] = bloco
        candidata["distratores"] = _distratores(candidata, bloco)
        candidata["com_modelo"] = any(d["origem"] == "modelo" for d in candidata["distratores"])
        candidata["nota"] = _pontuar(candidata, observaveis)
        candidata["elegivel"] = config["formato"] == "livre" or bool(candidata["distratores"])
    if inicial is not None and inicial["elegivel"]:
        for candidata in lista:
            if candidata["tipo"] == "saida" and candidata["certa"]["chave"] == inicial["certa"]["chave"]:
                candidata["elegivel"] = False  # a mesma pergunta do palpite antes de rodar

    escolhidas = _escolher(lista, config["max_pontos"], comandos)
    numero = 1
    pontos = []
    if inicial is not None and inicial["elegivel"]:
        atividade["palpite_inicial"] = _ponto(inicial, "p1", config["formato"], config["semente"], observaveis)
        numero = 2
    for candidata in escolhidas:
        pontos.append(_ponto(candidata, f"p{numero}", config["formato"], config["semente"], observaveis))
        numero += 1

    depende_de, traduzidas = dependencias(resultado, pontos)
    for indice, ids in traduzidas.items():
        comandos[int(indice)]["leitura"]["traduzida_depende_de"] = list(ids)
    aplicar_dependencias(resultado, depende_de)

    todos = pontos + ([atividade["palpite_inicial"]] if atividade["palpite_inicial"] else [])
    atividade["pontos"] = [publico(ponto) for ponto in pontos]
    if atividade["palpite_inicial"] is not None:
        atividade["palpite_inicial"] = publico(atividade["palpite_inicial"])
    atividade["depende_de_por_passo"] = {
        str(passo["i"]): passo["depende_de"] for passo in passos if "depende_de" in passo
    }
    atividade["traduzida_depende_de"] = traduzidas
    atividade["cobertura"] = {
        "pontos_com_modelo": sum(1 for ponto in todos if any(a["origem"] == "modelo" for a in ponto["_alternativas"])),
        "total": len(todos),
        "candidatos": len(todas),
        "candidatos_com_modelo": sum(1 for candidata in todas if candidata["com_modelo"]),
    }
    atividade["completa"] = completa
    atividade["tempo_ms"] = (time.perf_counter() - inicio) * 1000
    return {"atividade": atividade, "pontos": {ponto["id"]: ponto for ponto in todos}}


def preparar_atividade(resultado, codigo, entradas=(), config=None):
    """Atividade = {versao, modo, formato, semente, pontos, palpite_inicial, depende_de_por_passo,
    traduzida_depende_de, cobertura, completa, tempo_ms}.

    config = {modo: 'assistir'|'prever', formato: 'alternativas'|'livre',
    max_pontos: 6, semente, palpite_inicial: True, orcamento_ms: 500}. O
    orçamento vale para os modelos: estourado, os pontos ficam só com os
    distratores de regra e `completa` é False.
    """
    return montar_atividade(resultado, codigo, entradas, config)["atividade"]


# --- Dependências: o que cada ponto esconde --------------------------------------


def _desfechos_adiantados(passos, retornos):
    """[(j, desde, depois)]: passos cujo desfecho pode aparecer antes do passo de onde ele vem.

    Num gerador, o próximo passo do quadro só chega quando alguém pede outro
    valor, e no meio o programa de fora roda: o efeito do yield traria mudanças
    que ainda não aconteceram.
    """
    adiantados = []
    for passo in passos:
        depois, _ = passo_depois(passo, retornos)
        desde = passo.get("desfecho_visivel_desde", passo["i"])
        if depois is not None and desde is not None and depois > passo["i"] + 1 and desde < depois:
            adiantados.append((passo["i"], desde, depois))
    return adiantados


def _juntar(dependencias, i, campo, pid):
    lista = dependencias.setdefault(str(i), {}).setdefault(campo, [])
    if pid not in lista:
        lista.append(pid)


def dependencias(resultado, pontos):
    """({str(i): {campo: [ponto_id]}}, {str(comando): [ponto_id]}) dos pontos de previsão.

    - valor e saída escondem o efeito do passo; decisão, a condição com os
      valores e o resultado dela (e as partes que nem foram calculadas, que
      já dizem o resultado); voltas,
      o total. Os campos do desfecho se escondem juntos (revelacao.desfecho).
    - voltas de um for com range traduzido, ou o valor da variável desse for,
      também esconde a leitura traduzida ('de 1 até 4'): ela conta as voltas
      e diz qual é o próximo valor.
    - um passo anterior cujo desfecho viria de depois do ponto (o yield de um
      gerador) também esconde o efeito.
    O palpite inicial (comando None) não esconde nada: é corrigido no fim.
    """
    passos = resultado["passos"]
    comandos = resultado["estrutura"]["comandos"]
    adiantados = _desfechos_adiantados(passos, passos_de_retorno(passos))
    deps = {}
    traduzidas = {}
    for ponto in pontos:
        comando = ponto["alvo"]["comando"]
        if comando is None:
            continue
        i, pid, tipo = ponto["passo"], ponto["id"], ponto["tipo"]
        if tipo in ("valor", "saida"):
            _juntar(deps, i, "efeito", pid)
        elif tipo == "decisao":
            # 'nota >= 6? 7 >= 6' já é a conta que a pergunta pede: a condição com valores também espera.
            _juntar(deps, i, "decisao.texto", pid)
            _juntar(deps, i, "decisao.valor", pid)
            if (passos[i].get("decisao") or {}).get("nao_calculado"):
                _juntar(deps, i, "decisao.nao_calculado", pid)
        elif tipo == "voltas":
            _juntar(deps, i, "volta.total", pid)
        leitura = comandos[comando].get("leitura")
        if tipo in ("voltas", "valor") and comandos[comando]["tipo"] == "for" and leitura:
            # 'de 1 até 4' conta as voltas e diz qual é o próximo valor da variável do laço.
            if leitura["traduzida"] != leitura["literal"]:
                lista = traduzidas.setdefault(str(comando), [])
                if pid not in lista:
                    lista.append(pid)
        for j, desde, depois in adiantados:
            if j < i and desde <= i < depois:
                _juntar(deps, j, "efeito", pid)
    return deps, traduzidas


# --- Correção da resposta livre ------------------------------------------------------


def _frase_da_resposta(ponto):
    texto = ponto["resposta"]["texto"]
    tipo = ponto["tipo"]
    if tipo == "valor":
        return f"O Python guardou {texto}."
    if tipo == "saida":
        if ponto["alvo"]["comando"] is None:
            return f"No fim, a tela mostrou {_na_tela_e_ponto(texto)}"
        return f"Na tela apareceu {_na_tela_e_ponto(texto)}"
    if tipo == "voltas":
        return f"O laço deu {_plural(int(texto), 'volta')}."
    return f"A condição deu {texto}."


def _mensagem_de_erro(ponto, palpite, saida_do_aluno=None):
    """'Seu palpite: X. O que aconteceu.' No palpite antes de rodar, diz também a primeira linha diferente."""
    ponto_final = "" if palpite.rstrip("”").endswith((".", "!", "?", "…")) else "."
    mensagem = f"Seu palpite: {palpite}{ponto_final} {_frase_da_resposta(ponto)}"
    if saida_do_aluno is not None and ponto["alvo"]["comando"] is None:
        mensagem += _linha_diferente(saida_do_aluno, ponto["resposta"]["texto"])
    return mensagem


def _linha_diferente(palpite, certa):
    """' A 3ª linha foi “Você tem 1 vidas”.': com várias linhas, achar a diferença sozinho cansa."""
    certas = concepcoes.normalizar("saida", certa)[1].split("\n")
    if len(certas) < 2:
        return ""
    palpites = concepcoes.normalizar("saida", palpite)[1].split("\n")
    for numero, linha in enumerate(certas):
        if numero >= len(palpites) or palpites[numero] != linha:
            return f" A {numero + 1}ª linha foi {_na_tela_e_ponto(linha)}"
    return f" A tela teve só {len(certas)} linhas."


def _palpite(tipo, chave, texto):
    """O palpite do aluno como ele aparece na mensagem ('o texto ganha aspas sozinho')."""
    if chave is None:
        return texto.strip()
    if tipo == "saida":
        return _na_tela(chave[1])
    if chave[0] == "texto":
        return com_aspas(chave[1])
    if chave[0] == "bool":
        return "Verdadeiro" if chave[1] else "Falso"
    return texto.strip()


def _sem_tipo(chave):
    """A chave sem o tipo: o texto "11" e o número 11 empatam."""
    if chave and chave[0] == "texto":
        texto = chave[1].strip()
        if _parece_numero(texto):
            return ("numero", ast.literal_eval(texto))
        return ("texto", texto)
    return chave


def _valor_registravel(chave):
    if chave is None or chave[0] not in ("numero", "texto", "bool", "saida"):
        return None
    valor = chave[1]
    return valor if registravel(valor) else None


def _tipo_python(texto):
    try:
        return type(ast.literal_eval(texto.strip()))
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


ILEGIVEL = {
    "valor": "Isso não parece um número. Confira ou escolha texto.",
    "voltas": "Escreva o número de voltas, como 3.",
    "decisao": "Responda Verdadeiro ou Falso.",
    "saida": "Escreva o que vai aparecer na tela.",
}


def corrigir(ponto, resposta):
    """Correcao = {certa, legivel, valor_certo, tipo_certo, concepcao, feedback, mensagem,
    explicacao, resposta, palpite, valor_normalizado, testadas}.

    `resposta` é {texto, tipo_escolhido?: 'numero'|'texto'} (resposta livre) ou
    {alternativa: id}. Com 'numero', o texto é lido com ast.literal_eval; com
    'texto', vale como está (as aspas, se o aluno digitou, saem). Valor certo
    com tipo errado ('11' contra 11) não é acerto e ganha uma mensagem própria;
    só conta como 'o input devolve número' se o aluno marcou 'numero'. 7
    contra 7.0 é acerto com um recado, nunca diagnóstico.
    """
    tipo = ponto["tipo"]
    certa = ponto["resposta"]
    chave_certa = _chave(tipo, certa)
    correcao = {
        "certa": False,
        "legivel": True,
        "valor_certo": False,
        "tipo_certo": False,
        "concepcao": None,
        "feedback": None,
        "mensagem": "",
        "explicacao": ponto.get("explicacao", ""),
        "resposta": dict(certa),
        "palpite": "",
        "valor_normalizado": None,
        "testadas": list(ponto.get("testadas", [])),
    }
    if not isinstance(resposta, dict):
        raise ValueError("a resposta precisa ser {texto, tipo_escolhido} ou {alternativa}")
    if "alternativa" in resposta:
        return _corrigir_alternativa(ponto, resposta, correcao)

    texto = resposta.get("texto")
    if not isinstance(texto, str):
        raise ValueError("a resposta livre precisa de texto")
    escolhido = resposta.get("tipo_escolhido")
    if escolhido not in (None, "numero", "texto"):
        raise ValueError("tipo_escolhido precisa ser 'numero' ou 'texto'")
    chave = concepcoes.normalizar(tipo, texto, escolhido if tipo == "valor" else None)
    correcao["palpite"] = _palpite(tipo, chave, texto)
    if chave is None or not texto.strip():
        correcao.update(legivel=False, mensagem=ILEGIVEL[tipo])
        return correcao
    correcao["valor_normalizado"] = _valor_registravel(chave)

    if chave == chave_certa:
        correcao.update(certa=True, valor_certo=True, tipo_certo=True, mensagem=ponto.get("elogio", ""))
        aluno, python = _tipo_python(texto), _tipo_python(certa["texto"])
        if tipo == "valor" and {aluno, python} == {int, float}:
            nome = "um número decimal" if python is float else "um número inteiro"
            correcao["mensagem"] += f" Repare: o Python mostra {certa['texto']}, {nome}."
        return correcao

    correcao["valor_certo"] = tipo == "valor" and _sem_tipo(chave) == _sem_tipo(chave_certa)
    correcao["tipo_certo"] = tipo != "valor" or chave[0] == chave_certa[0]
    mensagem = _mensagem_de_erro(ponto, correcao["palpite"], chave[1] if tipo == "saida" else None)
    if correcao["valor_certo"] and not correcao["tipo_certo"]:
        if chave_certa[0] == "texto":
            mensagem += " O valor é esse, mas é texto, não número."
        else:
            mensagem += " O valor é esse, mas é número, não texto."
    concepcao = concepcoes.diagnosticar(_para_diagnostico(ponto), {"texto": texto, "tipo_escolhido": escolhido})
    if concepcao == "C03" and escolhido != "numero":
        concepcao = None  # 'o input devolve número' só vale se o aluno disse que era número
    correcao.update(concepcao=concepcao, mensagem=mensagem)
    if concepcao is not None:
        correcao["feedback"] = concepcoes.feedback_do_modelo(_para_diagnostico(ponto), concepcao)
    return correcao


def _para_diagnostico(ponto):
    """O ponto no formato que concepcoes.diagnosticar lê (modelos, alternativas e resposta certa)."""
    alternativas = ponto.get("_alternativas") or ponto.get("alternativas") or []
    diagnostico = {"tipo": ponto["tipo"], "resposta": ponto["resposta"], "alternativas": alternativas}
    if "_modelos" in ponto:
        diagnostico["modelos"] = ponto["_modelos"]
    return diagnostico


def _corrigir_alternativa(ponto, resposta, correcao):
    alternativas = ponto.get("_alternativas") or ponto.get("alternativas") or []
    escolhida = next((a for a in alternativas if a["id"] == resposta["alternativa"]), None)
    if escolhida is None:
        correcao.update(legivel=False, mensagem="Escolha uma das alternativas.")
        return correcao
    palpite = _na_tela(escolhida["texto"]) if ponto["tipo"] == "saida" else escolhida["texto"]
    correcao["palpite"] = palpite
    if escolhida["certa"]:
        correcao.update(certa=True, valor_certo=True, tipo_certo=True, mensagem=ponto.get("elogio", ""))
        return correcao
    concepcao = concepcoes.diagnosticar(_para_diagnostico(ponto), {"alternativa": escolhida["id"]})
    correcao.update(
        concepcao=concepcao,
        feedback=escolhida["feedback"] if concepcao else None,
        mensagem=_mensagem_de_erro(ponto, palpite, escolhida["texto"] if ponto["tipo"] == "saida" else None),
    )
    return correcao
