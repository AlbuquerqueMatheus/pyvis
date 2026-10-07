"""Narrador em texto: uma frase curta (até 12 palavras) e uma longa para cada passo.

A narração descreve cada passo como uma ação mecânica da máquina (Sorva, 2013)
e lê '=' como 'recebe'. A frase do passo i fala do comando do passo i e do que
ele faz, como a linha destacada: 'total recebe total + numero: vai valer 6.'
No futuro, porque as caixinhas mostram o estado ANTES da linha destacada: o
total ainda está com o valor antigo enquanto a frase é lida.

Cada frase vem em partes. A parte que conta o desfecho do comando (efeito,
decisão, volta) declara de que campos depende, e a interface monta a frase com
revelacao.montar: com um palpite pendente, a frase fica sem o desfecho.

Regra para quem mexer aqui: texto sem campos e o `oculto` de uma parte só
podem usar o código e o estado ANTES do passo. Tudo o que depende de o comando
rodar (valores novos, saída, ramo, volta) vai numa parte com campos.
"""

import ast

from .anotar import anotar, estado_depois, passos_de_retorno, retorno_do_quadro
from .rastreador import retornos_do_passo
from .avaliador import BINARIOS
from .erros import NOMES_DE_TIPO
from .estrutura import NOS_INTERNOS, Analise

LIMITE_PALAVRAS = 12
SIMPLES = frozenset({"int", "float", "bool", "NoneType", "str"})
CONTEINERES = frozenset({"list", "tuple", "set", "dict"})
FECHA = {"(": ")", "[": "]", "{": "}", "“": "”"}

# Métodos de lista narrados pelo que fazem: (frase, número de argumentos).
METODOS_DE_LISTA = {
    ("append", 1): "Coloca {0} no fim de {lista}",
    ("insert", 2): "Coloca {1} na posição {0} de {lista}",
    ("extend", 1): "Junta os itens de {0} no fim de {lista}",
    ("remove", 1): "Tira o primeiro {0} de {lista}",
    ("pop", 0): "Tira o último item de {lista}",
    ("pop", 1): "Tira o item da posição {0} de {lista}",
    ("sort", 0): "Ordena {lista}",
    ("reverse", 0): "Inverte a ordem de {lista}",
    ("clear", 0): "Esvazia {lista}",
}


def contar_palavras(texto):
    return len(texto.split())


def narrar_resultado(resultado, codigo):
    """Acrescenta `leitura` a cada comando e `narracao` a cada passo (no lugar).

    `codigo` é o mesmo texto que foi para rastrear(). Roda anotar() antes, se
    ainda não rodou, porque a narração usa efeito, decisão e volta.
    """
    passos = resultado["passos"]
    if not resultado["estrutura"]["comandos"]:
        return resultado  # erro de sintaxe: não há o que narrar
    if passos and "efeito" not in passos[0]:
        anotar(resultado)
    narrador = _Narrador(resultado, codigo)
    for comando, leitura in zip(resultado["estrutura"]["comandos"], narrador.leituras):
        comando["leitura"] = leitura
    for passo in passos:
        passo["narracao"] = narrador.narrar(passo)
    return resultado


def ler_comando(comando, codigo):
    """Leitura de um comando: {literal, traduzida, traduzida_depende_de}.

    A traduzida só muda nos laços com range ('de 1 até 4'), porque ela entrega
    quantas voltas o laço dá; traduzida_depende_de começa vazia e é a
    atividade (previsao.py) que a preenche.
    """
    texto = _normalizar(codigo)
    analise = Analise(texto)
    return _ler(analise.nos[comando["id"]], comando, _Fonte(texto))


def narrar(passo, resultado, codigo):
    """A narração de um passo só. Para todos os passos, use narrar_resultado."""
    if resultado["passos"] and "efeito" not in resultado["passos"][0]:
        anotar(resultado)
    return _Narrador(resultado, codigo).narrar(passo)


def _normalizar(codigo):
    return codigo.replace("\r\n", "\n").replace("\r", "\n")


# --- Texto: cortar, fechar parênteses, mostrar valores ---


def _cortar(texto, maximo, codigo=True):
    """Até `maximo` palavras; o que passar vira '…'. Em código, fecha parênteses e aspas."""
    palavras = texto.split()
    if len(palavras) <= maximo:
        return " ".join(palavras)
    cortado = " ".join(palavras[: max(maximo, 1)]) + "…"
    return _fechar(cortado) if codigo else cortado


def _com_ponto(texto):
    return texto if texto.endswith(("…", ".", "?", "!")) else texto + "."


def _fechar(texto):
    pilha = []
    aspas = None
    for letra in texto:
        if aspas:
            if letra == aspas:
                aspas = None
        elif letra in "\"'":
            aspas = letra
        elif letra in FECHA:
            pilha.append(FECHA[letra])
        elif pilha and letra == pilha[-1]:
            pilha.pop()
    return texto + (aspas or "") + "".join(reversed(pilha))


def _aspas(representacao):
    """'Ana' (repr do Python) vira "Ana", como os alunos escrevem."""
    try:
        texto = ast.literal_eval(representacao)
    except (ValueError, SyntaxError):
        return representacao
    if not isinstance(texto, str) or '"' in texto or "\\" in representacao:
        return representacao
    return f'"{texto}"'


def _mostrar(valor):
    """Valor (de valores.py) como texto de código: [1, 2], "Ana", função dobro."""
    tipo = valor["tipo"]
    if "itens" in valor:
        itens = [_mostrar(item) for item in valor["itens"]] + (["…"] if valor.get("cortado") else [])
        if tipo == "tuple":
            return "(" + ", ".join(itens) + ("," if len(itens) == 1 else "") + ")"
        if tipo == "set":
            return "{" + ", ".join(itens) + "}" if itens else "set()"
        return "[" + ", ".join(itens) + "]"
    if "pares" in valor:
        pares = [f"{_mostrar(chave)}: {_mostrar(item)}" for chave, item in valor["pares"]]
        return "{" + ", ".join(pares + (["…"] if valor.get("cortado") else [])) + "}"
    texto = valor.get("valor", "")
    if tipo == "str":
        return _aspas(texto)
    if texto == "...":
        return "…"
    if texto.startswith("<") and " at 0x" in texto:
        return f"um objeto {tipo}"  # o endereço de memória muda a cada execução
    return texto


def _curto(valor):
    """Valor para a frase curta: 7.666666666666667 vira 7.66… (o valor inteiro fica na longa)."""
    if valor["tipo"] == "float" and not valor.get("cortado"):
        texto = valor["valor"]
        inteiro, ponto, decimais = texto.partition(".")
        if ponto and len(decimais) > 4 and decimais.isdigit():
            return f"{inteiro}.{decimais[:2]}…"
    return _mostrar(valor)


def _longo(valor):
    """Valor para a frase longa: inteiro, até um tamanho que ainda se lê."""
    return _cortar(_mostrar(valor), 15)


def _maiuscula(texto):
    return texto[:1].upper() + texto[1:]


def _tipo_legivel(valor):
    nome = NOMES_DE_TIPO.get(valor["tipo"])
    return f" ({nome})" if nome else ""


def _plural(n, palavra):
    return f"{n} {palavra}" if n == 1 else f"{n} {palavra}s"


def _e_conteiner(valor):
    return valor["tipo"] in CONTEINERES or "itens" in valor or "pares" in valor


def _literal(no):
    """Um valor escrito direto no código: 5, "Ana", -1, [1, 2], {"a": 1}."""
    if isinstance(no, ast.Constant):
        return True
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
        return isinstance(no.operand, ast.Constant)
    if isinstance(no, (ast.List, ast.Tuple, ast.Set)):
        return all(_literal(e) for e in no.elts)
    if isinstance(no, ast.Dict):
        return all(k is not None and _literal(k) for k in no.keys) and all(_literal(v) for v in no.values)
    return False


def _chamada_de(no, *nomes):
    return isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in nomes


def _tem_chamada(no):
    return any(isinstance(filho, ast.Call) for filho in ast.walk(no))


# --- O código do aluno ---


class _Fonte:
    """O código do aluno, para citar trechos como ele escreveu (com as aspas dele)."""

    def __init__(self, texto):
        self.linhas = [linha.encode("utf-8") for linha in texto.split("\n")]

    def trecho(self, no, trocas=()):
        """O texto do nó numa linha só. `trocas`: [(linha, col, col_fim, texto novo)].

        As colunas da AST contam bytes em UTF-8, por isso as linhas ficam em bytes.
        """
        pedacos = []
        for numero in range(no.lineno, no.end_lineno + 1):
            linha = self.linhas[numero - 1]
            inicio = no.col_offset if numero == no.lineno else 0
            fim = no.end_col_offset if numero == no.end_lineno else len(linha)
            pedaco = linha[inicio:fim]
            for _, col, col_fim, novo in sorted((t for t in trocas if t[0] == numero), key=lambda t: -t[1]):
                pedaco = pedaco[: col - inicio] + novo.encode("utf-8") + pedaco[col_fim - inicio :]
            pedacos.append(pedaco.decode("utf-8", "replace"))
        if len(pedacos) == 1:
            return pedacos[0].strip()
        if any("#" in pedaco for pedaco in pedacos[:-1]) or any(aspas in "".join(pedacos) for aspas in ('"""', "'''")):
            return ast.unparse(no)  # um comentário ou um texto de várias linhas quebraria a linha única
        # Junta as linhas numa só, sem espaço depois de abrir ou antes de fechar parênteses.
        texto = ""
        for pedaco in pedacos:
            pedaco = pedaco.strip().removesuffix("\\").strip()
            if pedaco and texto and texto[-1] not in "([{" and pedaco[0] not in ")]}":
                texto += " "
            texto += pedaco
        return texto


def _nomes_lidos(no):
    """Nomes lidos pela expressão, fora de compreensões, lambdas e f-strings.

    Dentro delas, um nome pode ser a variável da própria compreensão.
    """
    nomes = []
    pendentes = [no]
    while pendentes:
        atual = pendentes.pop()
        if isinstance(atual, NOS_INTERNOS + (ast.JoinedStr,)):
            continue
        if isinstance(atual, ast.Name):
            if isinstance(atual.ctx, ast.Load) and atual.lineno == atual.end_lineno:
                nomes.append((atual.lineno, atual.col_offset, atual.end_col_offset, atual.id))
            continue
        if isinstance(atual, ast.Call) and isinstance(atual.func, ast.Name):
            pendentes.extend(atual.args)
            pendentes.extend(palavra.value for palavra in atual.keywords)
            continue  # o nome da função fica como está
        pendentes.extend(ast.iter_child_nodes(atual))
    return nomes


# --- Leitura de cada comando (uma vez só) ---


def _ler(no, comando, fonte):
    tipo = comando["tipo"]
    literal = None
    traduzida = None
    if tipo == "atrib":
        alvos, valor = _alvos_e_valor(no)
        literal = f"{_texto_dos_alvos(alvos, fonte)} {_verbo(alvos)} {fonte.trecho(valor)}"
    elif tipo == "aug":
        literal = _aug_expandido(no, fonte)
    elif tipo in ("if", "while"):
        literal = f"{'se' if tipo == 'if' else 'enquanto'} {fonte.trecho(no.test)}"
    elif tipo == "elif":
        literal = f"senão, se {fonte.trecho(no.test)}"
    elif tipo == "for":
        alvo = fonte.trecho(no.target)
        literal = f"para cada {alvo} em {fonte.trecho(no.iter)}"
        faixa = _traduzir_range(no.iter, fonte)
        if faixa:
            traduzida = f"para cada {alvo} {faixa}"
    elif tipo == "print":
        argumentos = _argumentos(no.value, fonte)
        literal = f"mostra na tela {argumentos}" if argumentos else "mostra uma linha vazia na tela"
    elif tipo == "expr":
        literal = f"{'chama' if isinstance(no.value, ast.Call) else 'calcula'} {fonte.trecho(no.value)}"
    elif tipo == "def":
        literal = f"cria a função {no.name}({ast.unparse(no.args)})"
    elif tipo == "return":
        literal = f"devolve {fonte.trecho(no.value)}" if no.value is not None else "sai da função"
    elif tipo == "break":
        literal = "sai do laço"
    elif tipo == "continue":
        literal = "pula para a próxima volta"
    else:
        literal = _ler_outro(no, comando, fonte)
    return {"literal": literal, "traduzida": traduzida or literal, "traduzida_depende_de": []}


def _ler_outro(no, comando, fonte):
    if isinstance(no, ast.Pass):
        return "não faz nada"
    if isinstance(no, ast.Import):
        return "importa " + ", ".join(nome.name for nome in no.names)
    if isinstance(no, ast.ImportFrom):
        return f"importa {', '.join(nome.name for nome in no.names)} de {no.module or '.'}"
    if isinstance(no, ast.ClassDef):
        return f"cria a classe {no.name}"
    if isinstance(no, (ast.Global, ast.Nonlocal)):
        return "usa a variável de fora " + ", ".join(no.names)
    if isinstance(no, ast.Try):
        return "tenta rodar o bloco"
    if isinstance(no, ast.ExceptHandler):
        return "se deu erro no try, roda este bloco"
    if isinstance(no, ast.Delete):
        return "apaga " + ", ".join(fonte.trecho(alvo) for alvo in no.targets)
    if isinstance(no, ast.Raise):
        return "levanta um erro"
    if isinstance(no, ast.Assert):
        return f"confere se {fonte.trecho(no.test)}"
    linha = fonte.linhas[comando["linhas"][0] - 1].decode("utf-8", "replace").strip()
    return linha.rstrip(":")


def _alvos_e_valor(no):
    if isinstance(no, ast.AnnAssign):
        return [no.target], no.value
    return no.targets, no.value


def _texto_dos_alvos(alvos, fonte):
    return " e ".join(fonte.trecho(alvo) for alvo in alvos)


def _nomes_dos_alvos(alvos):
    """Os nomes de `a, b = ...` ou `a = b = ...`; None se algum alvo não é um nome."""
    nomes = []
    for alvo in alvos:
        partes = alvo.elts if isinstance(alvo, (ast.Tuple, ast.List)) else [alvo]
        if not all(isinstance(parte, ast.Name) for parte in partes):
            return None
        nomes += [parte.id for parte in partes if parte.id not in nomes]
    return nomes


def _verbo(alvos):
    if len(alvos) > 1 or isinstance(alvos[0], (ast.Tuple, ast.List)):
        return "recebem"
    return "recebe"


def _aug_expandido(no, fonte):
    """`total += n` lido como `total recebe total + n`."""
    alvo = fonte.trecho(no.target)
    simbolo, precedencia, _ = BINARIOS.get(type(no.op), ("?", 0, None))
    valor = fonte.trecho(no.value)
    # x -= a + b é x - (a + b): o lado direito é calculado primeiro.
    if isinstance(no.value, ast.BinOp) and BINARIOS.get(type(no.value.op), (None, 0))[1] <= precedencia:
        valor = f"({valor})"
    elif isinstance(no.value, (ast.BoolOp, ast.Compare, ast.IfExp, ast.Lambda, ast.NamedExpr)):
        valor = f"({valor})"
    return f"{alvo} recebe {alvo} {simbolo} {valor}"


def _argumentos(chamada, fonte):
    partes = [fonte.trecho(argumento) for argumento in chamada.args]
    partes += [f"{palavra.arg}={fonte.trecho(palavra.value)}" for palavra in chamada.keywords if palavra.arg]
    return ", ".join(partes)


def _inteiro(no):
    if isinstance(no, ast.Constant) and type(no.value) is int:
        return no.value
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        valor = _inteiro(no.operand)
        return -valor if valor is not None else None
    return None


def _traduzir_range(no, fonte):
    """range(1, 5) -> 'de 1 até 4'. Sem tradução segura, None."""
    if not (_chamada_de(no, "range") and not no.keywords and 1 <= len(no.args) <= 3):
        return None
    if any(isinstance(argumento, ast.Starred) for argumento in no.args):
        return None
    inicio = no.args[0] if len(no.args) >= 2 else None
    fim = no.args[1] if len(no.args) >= 2 else no.args[0]
    passo = no.args[2] if len(no.args) == 3 else None
    a = 0 if inicio is None else _inteiro(inicio)
    b = _inteiro(fim)
    s = 1 if passo is None else _inteiro(passo)
    if s == 0:
        return None
    if a is not None and b is not None and s is not None:
        valores = range(a, b, s)
        if not valores:
            return None  # um range vazio fica com a leitura literal
        ultimo = valores[-1]
        if s == 1:
            return f"de {a} até {ultimo}"
        if s > 0:
            return f"de {a} até {ultimo}, de {s} em {s}"
        return f"de {a} até {ultimo}, descendo de {-s} em {-s}"
    if s != 1:
        return None  # com passo e limites que só se sabe rodando, a leitura fica literal
    texto_inicio = "0" if inicio is None else fonte.trecho(inicio)
    if isinstance(fim, ast.BinOp) and isinstance(fim.op, ast.Add) and _inteiro(fim.right) == 1:
        ultimo = fonte.trecho(fim.left)  # range(1, n + 1) vai de 1 até n
    elif b is not None:
        ultimo = str(b - 1)
    else:
        ultimo = fonte.trecho(fim)
        if not isinstance(fim, (ast.Name, ast.Call, ast.Subscript, ast.Attribute, ast.BinOp)):
            ultimo = f"({ultimo})"
        ultimo += " - 1"
    return f"de {texto_inicio} até {ultimo}"


# --- Frases em partes ---


def _sem_ponto_duplo(texto):
    # Um valor cortado já termina em '…': o ponto final da frase sobraria ('7.66….').
    return texto.replace("….", "…")


class _Frase:
    def __init__(self):
        self.partes = []

    def fixa(self, texto):
        if texto:
            self.partes.append({"texto": _sem_ponto_duplo(texto), "campos": []})

    def revela(self, campos, texto, oculto=""):
        if texto or oculto:
            parte = {"texto": _sem_ponto_duplo(texto), "campos": list(campos)}
            if oculto:
                parte["oculto"] = _sem_ponto_duplo(oculto)
            self.partes.append(parte)

    def completa(self):
        return "".join(parte["texto"] for parte in self.partes).strip()


def _maior_combinacao(partes):
    """O maior número de palavras entre todas as combinações de partes visíveis ou não."""
    grupos = sorted({tuple(parte["campos"]) for parte in partes if parte["campos"]})
    maior = 0
    for mascara in range(2 ** len(grupos)):
        visiveis = {grupo for indice, grupo in enumerate(grupos) if mascara >> indice & 1}
        texto = "".join(
            parte["texto"] if not parte["campos"] or tuple(parte["campos"]) in visiveis else parte.get("oculto", "")
            for parte in partes
        )
        maior = max(maior, contar_palavras(texto))
    return maior


class _Contexto:
    """O que se sabe de um passo: o estado antes, o estado depois e as chamadas no meio."""

    def __init__(self, narrador, passo):
        self.passo = passo
        self.comando = narrador.comandos[passo["comando"]]
        self.no = narrador.nos[passo["comando"]]
        self.efeito = passo.get("efeito")
        depois, self.parcial = estado_depois(passo, narrador.passos, narrador.retornos)
        self.depois = depois if self.efeito is not None else None
        self.chamadas = narrador.chamadas(passo)
        self.erro = narrador.erro_no_passo(passo)

    def _procurar(self, estado, nome):
        # Dentro de uma função, um nome que não é local só pode ser o de fora (global).
        if self.passo["funcao"] is not None and nome in estado["locais"]:
            return "locais", estado["locais"][nome]
        if nome in estado["globais"]:
            return "globais", estado["globais"][nome]
        return None, None

    def antes(self, nome):
        return self._procurar(self.passo, nome)[1]

    def mudanca(self, nome):
        """(antes, depois) de uma variável, ou None quando não dá para saber."""
        if self.depois is None:
            return None
        if self.parcial:
            # No último comando de uma função, as variáveis locais já sumiram:
            # só dá para afirmar o que mudou nas globais.
            if nome not in self.efeito["criadas"] and all(m["nome"] != nome for m in self.efeito["mudadas"]):
                return None
            return self.passo["globais"].get(nome), self.depois["globais"][nome]
        escopo, depois = self._procurar(self.depois, nome)
        if depois is None:
            return None
        return self.passo[escopo].get(nome), depois


class _Narrador:
    def __init__(self, resultado, codigo):
        texto = _normalizar(codigo)
        self.fonte = _Fonte(texto)
        analise = Analise(texto)
        self.nos = analise.nos
        self.passos = resultado["passos"]
        self.comandos = resultado["estrutura"]["comandos"]
        if len(self.nos) != len(self.comandos):
            raise ValueError("o código não é o mesmo que gerou o resultado")
        self.id_do_no = {id(no): indice for indice, no in enumerate(self.nos)}
        self.retornos = passos_de_retorno(self.passos)
        self.erro = resultado.get("erro")
        self.leituras = [_ler(no, comando, self.fonte) for no, comando in zip(self.nos, self.comandos)]
        self._nomes = {}

    def chamadas(self, passo):
        """Funções do aluno que o comando chamou (os passos logo depois, num quadro mais fundo)."""
        nomes = []
        indice = passo["i"] + 1
        while indice < len(self.passos) and self.passos[indice]["profundidade"] > passo["profundidade"]:
            seguinte = self.passos[indice]
            if seguinte["profundidade"] == passo["profundidade"] + 1 and seguinte["funcao"] not in nomes:
                nomes.append(seguinte["funcao"])
                if len(nomes) == 2:
                    break
            indice += 1
        return nomes

    def erro_no_passo(self, passo):
        """'erro' (o programa para aqui), 'limite', 'tratado' (um except pegou) ou None."""
        if passo is self.passos[-1]:
            if self.erro is None:
                return None
            return "limite" if self.erro["tipo"] == "LimiteDePassos" else "erro"
        seguinte = passo["proximo_no_quadro"]
        if seguinte is not None:
            # Do comando direto para um except: foi ele que deu erro.
            comando = self.passos[seguinte]["comando"]
            return "tratado" if comando is not None and isinstance(self.nos[comando], ast.ExceptHandler) else None
        # A função acabou sem return e sem passo seguinte: saiu por um erro,
        # que alguém de fora tratou. Geradores e classes também acabam assim.
        terminou_normal = self.erro is None and self.passos[-1]["evento"] == "fim"
        if passo["funcao"] is None or passo["quadro"] in self.retornos or not terminou_normal:
            return None
        return "tratado" if self._funcao_comum(passo["comando"]) else None

    def _funcao_comum(self, comando):
        while comando is not None:
            no = self.nos[comando]
            if isinstance(no, ast.ClassDef):
                return False
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return not any(isinstance(filho, (ast.Yield, ast.YieldFrom, ast.Await)) for filho in ast.walk(no))
            comando = self.comandos[comando]["pai"]
        return False

    def com_valores(self, no, passo):
        """O trecho com os valores de agora no lugar dos nomes ('total + numero' -> '3 + 3')."""
        chave = id(no)
        if chave not in self._nomes:
            self._nomes[chave] = _nomes_lidos(no)
        estado = passo["locais"] if passo["funcao"] is not None else passo["globais"]
        trocas = []
        for linha, coluna, coluna_fim, nome in self._nomes[chave]:
            valor = estado.get(nome)
            if valor is not None and valor["tipo"] in SIMPLES:
                texto = _mostrar(valor)
                if len(texto) <= 20:
                    trocas.append((linha, coluna, coluna_fim, texto))
        return self.fonte.trecho(no, trocas) if trocas else None

    def narrar(self, passo):
        if passo["evento"] != "linha":
            curta, longa = _Frase(), _Frase()
            curta.fixa("O programa terminou.")
            longa.fixa("Não há mais comandos para rodar: o programa terminou.")
        else:
            contexto = _Contexto(self, passo)
            construir = getattr(self, "_" + contexto.comando["tipo"], self._outro)
            curta, longa = construir(contexto)
            if _maior_combinacao(curta.partes) > LIMITE_PALAVRAS:
                curta = self._reserva(contexto)
        retornos = retornos_do_passo(passo)
        if retornos:
            # Na recursão, vários quadros terminam juntos: os últimos três, do mais fundo ao de fora.
            antes = _Frase()
            devolveram = " ".join(f"{r['funcao']} devolveu {_mostrar(r['valor'])}." for r in retornos[-3:])
            antes.revela(["retorno"], devolveram + " ")
            antes.partes += longa.partes
            longa = antes
        return {
            "curta": curta.completa(),
            "longa": longa.completa(),
            "partes_curta": curta.partes,
            "partes_longa": longa.partes,
        }

    # --- Desfechos comuns ---

    def _erro_curto(self, contexto):
        if contexto.erro == "limite":
            return ": o programa parou aqui."
        if contexto.erro:
            return ": aqui dá erro."
        return None

    def _erro_longo(self, contexto):
        if contexto.erro == "limite":
            return " O programa passou do limite de passos e foi parado aqui."
        if contexto.erro == "tratado":
            return " Aqui acontece um erro, mas um except trata o erro e o programa continua."
        if contexto.erro:
            return " Aqui acontece um erro, e o programa para."
        return None

    def _antes_roda(self, contexto, para=""):
        if not contexto.chamadas:
            return ""
        return f" Antes, o Python roda {' e '.join(contexto.chamadas)}{para}."

    def _valor_novo(self, contexto, nome, orcamento, literal=False):
        """': vai valer 6.' para a variável `nome`, cabendo em `orcamento` palavras."""
        mudanca = contexto.mudanca(nome)
        if mudanca is None:
            return None
        antes, depois = mudanca
        if antes is not None and antes["h"] == depois["h"]:
            return f": continua valendo {_cortar(_curto(depois), orcamento - 2)}."
        if literal:
            if antes is None:
                return ": variável nova."
            return f": antes valia {_cortar(_curto(antes), orcamento - 2)}."
        verbo = "vai ficar" if _e_conteiner(depois) else "vai valer"
        return f": {verbo} {_cortar(_curto(depois), orcamento - contar_palavras(verbo))}."

    def _valor_novo_longo(self, contexto, nome):
        mudanca = contexto.mudanca(nome)
        if mudanca is None:
            return ""
        antes, depois = mudanca
        texto = _longo(depois)
        if antes is None:
            return f" {nome} é uma variável nova e vale {texto}{_tipo_legivel(depois)}."
        if antes["h"] == depois["h"]:
            return f" {nome} continua valendo {texto}."
        if _e_conteiner(depois):
            return f" {nome} passa a valer {texto}."  # repetir a lista antiga pesaria a frase
        return (
            f" {nome} passa a valer {texto}{_tipo_legivel(depois)}. O valor antigo, {_longo(antes)}, "
            "sai: uma variável guarda um valor só."
        )

    def _resumo(self, contexto, orcamento):
        """Desfecho genérico: o que mudou ou apareceu na tela, ou None se não dá para saber."""
        efeito = contexto.efeito
        if efeito is None:
            return None
        nomes = efeito["criadas"] + [m["nome"] for m in efeito["mudadas"] if m["nome"] not in efeito["criadas"]]
        if len(nomes) == 1:
            mudanca = contexto.mudanca(nomes[0]) or (None, None)
            if mudanca[1] is None and efeito["mudadas"]:
                mudanca = (None, efeito["mudadas"][0]["depois"])
            if mudanca[1] is not None:
                depois = mudanca[1]
                verbo = "vai ficar" if _e_conteiner(depois) else "vai valer"
                resto = orcamento - 1 - contar_palavras(verbo)
                return f": {nomes[0]} {verbo} {_cortar(_curto(depois), resto)}."
            return f": {nomes[0]} muda."
        if len(nomes) == 2:
            return f": {nomes[0]} e {nomes[1]} mudam."
        if len(nomes) > 2:
            return f": {nomes[0]}, {nomes[1]} e outras mudam."
        if efeito["saida_nova"]:
            return f": aparece na tela {self._saida(efeito['saida_nova'], orcamento - 3)}."
        if efeito["apagadas"]:
            return f": {efeito['apagadas'][0]} deixa de existir."
        if efeito["parcial"]:
            return None  # as variáveis locais sumiram junto com a função
        return ": nada muda."

    def _pares(self, contexto, nomes, orcamento):
        """'a vale 2 e b vale 1' para alvos como `a, b = b, a`, ou None se não couber."""
        if not nomes:
            return None
        pares = []
        for nome in nomes:
            mudanca = contexto.mudanca(nome)
            if mudanca is None:
                return None
            pares.append(f"{nome} vale {_mostrar(mudanca[1])}")
        texto = ", ".join(pares[:-1]) + " e " + pares[-1] if len(pares) > 1 else pares[0]
        return texto if contar_palavras(texto) <= orcamento else None

    def _posicao(self, contexto, valor):
        """`numeros[0]` numa lista: lembra que a contagem das posições começa no 0."""
        if not (isinstance(valor, ast.Subscript) and isinstance(valor.value, ast.Name)):
            return ""
        sequencia = contexto.antes(valor.value.id)
        if sequencia is None or sequencia["tipo"] not in ("list", "tuple", "str"):
            return ""
        indice = valor.slice
        posicao = _inteiro(indice)
        if posicao is None and isinstance(indice, ast.Name):
            atual = contexto.antes(indice.id)
            if atual is not None and atual["tipo"] == "int" and not atual.get("cortado"):
                posicao = int(atual["valor"])
        if posicao is None:
            return ""
        if posicao < 0:
            return f" {self.fonte.trecho(valor)} conta do fim: a posição -1 é a última."
        return f" {self.fonte.trecho(valor)} é o item na posição {posicao}: a primeira posição é a 0."

    def _resumo_longo(self, contexto):
        efeito = contexto.efeito
        if efeito is None:
            return ""
        texto = ""
        for nome in efeito["criadas"]:
            mudanca = contexto.mudanca(nome)
            if mudanca is not None:
                texto += f" {nome} é criada e vale {_longo(mudanca[1])}."
        for mudada in efeito["mudadas"]:
            texto += f" {mudada['nome']} passa a valer {_longo(mudada['depois'])}."
        if efeito["saida_nova"]:
            texto += f" Aparece na tela: {self._saida(efeito['saida_nova'], 40)}."
        for nome in efeito["apagadas"]:
            texto += f" {nome} deixa de existir."
        if not texto and not efeito["parcial"]:
            texto = " Nenhuma variável muda."
        return texto

    def _saida(self, saida, orcamento):
        linhas = saida[:-1] if saida.endswith("\n") else saida
        return "“" + _cortar(linhas.replace("\n", " / "), max(orcamento, 1)) + "”"

    def _base_e_desfecho(self, base, desfecho, campos=("efeito",)):
        """Frase curta = base fixa + desfecho revelado (escondido, fica só o ponto final)."""
        frase = _Frase()
        frase.fixa(base)
        ponto = "" if base.endswith("…") else "."
        frase.revela(campos, desfecho or ponto, ponto)
        return frase

    # --- Construções ---

    def _atrib(self, contexto):
        no = contexto.no
        alvos, valor = _alvos_e_valor(no)
        alvo = _texto_dos_alvos(alvos, self.fonte)
        nome = alvos[0].id if len(alvos) == 1 and isinstance(alvos[0], ast.Name) else None
        longa = _Frase()
        # Com uma pergunta aberta sobre o valor, 'devolve texto' e 'vira número' já dizem o tipo da
        # resposta: essas partes esperam junto com o efeito, e no lugar fica só o que o código diz.
        if nome and _chamada_de(valor, "input"):
            no_lugar = f"{nome} recebe {_cortar(self.fonte.trecho(valor), 6)}"
            base = f"input devolve {NOMES_DE_TIPO['str']} para {nome}"
            mudanca = contexto.mudanca(nome)
            desfecho = self._erro_curto(contexto)
            if desfecho is None and mudanca is not None:
                desfecho = f": chegou {_cortar(_mostrar(mudanca[1]), LIMITE_PALAVRAS - contar_palavras(base) - 1)}."
            curta = _Frase()
            curta.revela(["efeito"], base, no_lugar)
            curta.revela(["efeito"], desfecho or ".", ".")
            longa.fixa("O input lê o que foi digitado.")
            longa.revela(["efeito"], " Ele sempre devolve texto.")
            if mudanca is not None:
                longa.revela(["efeito"], f" Chegou {_mostrar(mudanca[1])}, que vai para {nome}.")
            longa.revela(["efeito"], self._erro_longo(contexto) or "")
            return curta, longa
        if nome and _chamada_de(valor, "int", "float") and len(valor.args) == 1 and _chamada_de(valor.args[0], "input"):
            no_lugar = f"{nome} recebe {_cortar(self.fonte.trecho(valor), 6)}"
            conversao = valor.func.id
            tipo = NOMES_DE_TIPO[conversao]
            base = f"input devolve {NOMES_DE_TIPO['str']}, {conversao} vira {tipo}"
            desfecho = self._erro_curto(contexto)
            mudanca = contexto.mudanca(nome)
            if desfecho is None and mudanca is not None:
                resto = LIMITE_PALAVRAS - contar_palavras(base) - 3
                desfecho = f": {nome} vai valer {_cortar(_curto(mudanca[1]), resto)}."
            curta = _Frase()
            curta.revela(["efeito"], base, no_lugar)
            curta.revela(["efeito"], desfecho or ".", ".")
            longa.fixa("O input lê o que foi digitado.")
            longa.revela(["efeito"], f" Ele devolve texto, e {conversao} transforma esse texto em {tipo}.")
            longa.revela(["efeito"], self._erro_longo(contexto) or self._valor_novo_longo(contexto, nome))
            return curta, longa

        literal = _literal(valor)
        expressao = self.fonte.trecho(valor)

        def desfecho_com(resto):
            desfecho = self._erro_curto(contexto)
            if desfecho is None:
                if nome:
                    desfecho = self._valor_novo(contexto, nome, resto - 1, literal)
                else:
                    pares = self._pares(contexto, _nomes_dos_alvos(alvos), resto)
                    desfecho = f": {pares}." if pares else self._resumo(contexto, resto)
            return desfecho

        # O código inteiro, se couber junto com o desfecho inteiro: código cortado no meio
        # ('celsius * 9 / 5…') se lê pior que uma frase um pouco mais cheia.
        inicio = f"{alvo} {_verbo(alvos)}"
        desfecho = desfecho_com(LIMITE_PALAVRAS)
        base = f"{inicio} {expressao}"
        if contar_palavras(base + (desfecho or ".")) > LIMITE_PALAVRAS:
            base = f"{inicio} {_cortar(expressao, 5)}"
            if contar_palavras(base) > 7:
                base = _cortar(base, 7)
            desfecho = desfecho_com(LIMITE_PALAVRAS - contar_palavras(base))
        if literal:
            longa.fixa(f"O Python guarda {expressao} em {alvo}.")
        elif isinstance(valor, ast.Name):
            longa.fixa(f"O Python copia o valor de {expressao} para {alvo}.")
        else:
            longa.fixa(f"O Python calcula {expressao} e guarda o resultado em {alvo}.")
            substituido = self.com_valores(valor, contexto.passo)
            if substituido:
                longa.fixa(f" Com os valores de agora: {_cortar(substituido, 15)}.")
            longa.fixa(self._posicao(contexto, valor))
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None:
            desfecho_longo = self._antes_roda(contexto, " para saber o valor")
            if nome:
                desfecho_longo += self._valor_novo_longo(contexto, nome)
            else:
                desfecho_longo += self._resumo_longo(contexto)
        longa.revela(["efeito"], desfecho_longo)
        return self._base_e_desfecho(base, desfecho), longa

    def _aug(self, contexto):
        no = contexto.no
        expandido = self.leituras[contexto.comando["id"]]["literal"]
        base = _cortar(expandido, 7)
        nome = no.target.id if isinstance(no.target, ast.Name) else None
        resto = LIMITE_PALAVRAS - contar_palavras(base)
        desfecho = self._erro_curto(contexto)
        if desfecho is None:
            desfecho = self._valor_novo(contexto, nome, resto - 1) if nome else self._resumo(contexto, resto)
        longa = _Frase()
        original = self.fonte.trecho(no)
        longa.fixa(f"{original} é o mesmo que {expandido.replace(' recebe ', ' = ', 1)}.")
        if nome:
            atual = contexto.antes(nome)
            substituido = self.com_valores(no.value, contexto.passo)
            if atual is not None and atual["tipo"] in SIMPLES:
                simbolo = expandido.split(" ")[len(nome.split()) + 2]
                direita = substituido or self.fonte.trecho(no.value)
                longa.fixa(f" Com os valores de agora: {_mostrar(atual)} {simbolo} {direita}.")
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None:
            desfecho_longo = self._antes_roda(contexto, " para saber o valor")
            desfecho_longo += self._valor_novo_longo(contexto, nome) if nome else self._resumo_longo(contexto)
        longa.revela(["efeito"], desfecho_longo)
        return self._base_e_desfecho(base, desfecho), longa

    def _if(self, contexto):
        return self._decisao(contexto)

    _elif = _while = _if

    def _decisao(self, contexto):
        no = contexto.no
        tipo = contexto.comando["tipo"]
        decisao = contexto.passo.get("decisao") or {}
        texto = decisao.get("texto")
        condicao = self.fonte.trecho(no.test)
        sempre = isinstance(no.test, ast.Constant)
        campos = ["decisao.valor"] + (["volta.n"] if tipo == "while" else [])
        acao = self._acao(contexto, tipo, decisao)
        # Uma chamada na condição pode precisar de mais palavras no desfecho.
        cabe = LIMITE_PALAVRAS - (8 if _tem_chamada(no.test) else 5)

        curta = _Frase()
        if tipo == "while" and sempre and no.test.value is True:
            curta.fixa("while True repete até um break.")
        elif texto is None or sempre:
            curta.fixa(_cortar(condicao, cabe) + "?")
        else:
            if contar_palavras(condicao) + contar_palavras(texto) <= cabe:
                visivel = f"{condicao}? {texto}"
            else:
                visivel = _cortar(texto, cabe)
            curta.revela(["decisao.texto"], visivel, _cortar(condicao, cabe) + "?")
            if acao:
                curta.revela(["decisao.texto", "decisao.valor"], ",")
        if acao:
            curta.revela(campos, " " + acao)

        longa = _Frase()
        if tipo == "while" and sempre and no.test.value is True:
            longa.fixa("while True repete para sempre. Só um break ou um erro param o laço.")
        elif tipo == "while":
            longa.fixa(f"O while testa {condicao} antes de cada volta.")
        elif tipo == "elif":
            longa.fixa(f"As condições de cima deram Falso, então o elif testa {condicao}.")
        else:
            longa.fixa(f"O if testa {condicao}.")
        if texto is not None and not sempre:
            longa.revela(["decisao.texto"], f" Com os valores de agora: {texto}.")
            pulados = [texto[inicio:fim] for inicio, fim in decisao.get("nao_calculado", [])]
            if pulados:
                longa.revela(
                    ["decisao.texto", "decisao.valor"],
                    f" O Python nem calculou {' e '.join(pulados)}: o resultado já estava decidido.",
                )
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None:
            desfecho_longo = self._antes_roda(contexto, " para calcular a condição") + self._acao_longa(
                contexto, tipo, decisao
            )
        longa.revela(campos, desfecho_longo)
        volta = contexto.passo.get("volta")
        if tipo == "while" and volta and volta["laco"] == contexto.comando["id"] and volta["total"] is not None:
            longa.revela(["volta.total"], f" Ao todo, o laço dá {_plural(volta['total'], 'volta')}.")
        return curta, longa

    def _senao_e_elif(self, contexto):
        senao = getattr(contexto.no, "orelse", None)
        if not senao:
            return False
        indice = self.id_do_no.get(id(senao[0]))
        return indice is not None and self.comandos[indice]["tipo"] == "elif"

    def _numero_da_volta(self, contexto):
        volta = contexto.passo.get("volta")
        if volta and volta["laco"] == contexto.comando["id"] and volta["n"]:
            return volta["n"]
        return None

    def _acao(self, contexto, tipo, decisao):
        if contexto.erro:
            return "O programa parou aqui." if contexto.erro == "limite" else "Aqui dá erro."
        ramo = decisao.get("ramo")
        bloco = "elif" if tipo == "elif" else "if"
        if ramo == "corpo":
            if tipo == "while":
                n = self._numero_da_volta(contexto)
                return f"Verdadeiro: começa a volta {n}." if n else "Verdadeiro: entra no laço."
            return f"Verdadeiro: entra no {bloco}."
        if ramo == "orelse":
            return "Falso: testa o elif." if self._senao_e_elif(contexto) else "Falso: vai para o else."
        if ramo == "sai":
            return "Falso: sai do laço." if tipo == "while" else f"Falso: não entra no {bloco}."
        valor = decisao.get("valor")
        if valor is None:
            return ""
        return "Verdadeiro." if valor else "Falso."

    def _acao_longa(self, contexto, tipo, decisao):
        ramo = decisao.get("ramo")
        bloco = "elif" if tipo == "elif" else "if"
        if ramo == "corpo":
            if tipo == "while":
                n = self._numero_da_volta(contexto)
                volta = f": é a volta {n}" if n else ""
                return f" Deu Verdadeiro, então o bloco do while roda mais uma vez{volta}."
            return f" Deu Verdadeiro, então o bloco do {bloco} roda."
        if ramo == "orelse":
            if tipo == "while":
                return " Deu Falso: o laço termina e o else roda."
            if self._senao_e_elif(contexto):
                return f" Deu Falso, então o Python pula o bloco do {bloco} e testa o elif."
            return f" Deu Falso, então o Python pula o bloco do {bloco} e roda o else."
        if ramo == "sai":
            if tipo == "while":
                return " Deu Falso, então o laço termina e o programa segue depois dele."
            return f" Deu Falso, então o Python pula o bloco do {bloco}."
        valor = decisao.get("valor")
        if valor is None:
            return ""
        return " Deu Verdadeiro." if valor else " Deu Falso."

    def _for(self, contexto):
        no = contexto.no
        leitura = self.leituras[contexto.comando["id"]]
        alvo = self.fonte.trecho(no.target)
        # A leitura deixa pelo menos 3 palavras para o desfecho ('i recebe 0.').
        cabe = LIMITE_PALAVRAS - 3
        literal = _com_ponto(_cortar(_maiuscula(leitura["literal"]), cabe))
        traduzida = None
        if leitura["traduzida"] != leitura["literal"] and contar_palavras(leitura["traduzida"]) <= cabe:
            traduzida = _maiuscula(leitura["traduzida"]) + "."
        resto = LIMITE_PALAVRAS - max(contar_palavras(literal), contar_palavras(traduzida or ""))
        campos = ["efeito", "volta.n"]

        curta = _Frase()
        if traduzida:
            curta.revela(["leitura.traduzida"], traduzida, literal)
        else:
            curta.fixa(literal)
        opcoes = self._volta_curta(contexto, alvo, resto)
        curta.revela(campos, next((" " + o for o in opcoes if contar_palavras(o) <= resto), ""))

        longa = _Frase()
        iteravel = self.fonte.trecho(no.iter)
        literal_longa = f"O for pega um valor de cada vez de {iteravel} e guarda em {alvo}."
        if leitura["traduzida"] != leitura["literal"]:
            faixa = leitura["traduzida"][len(f"para cada {alvo} ") :]
            longa.revela(
                ["leitura.traduzida"], f"O for pega um valor de cada vez, {faixa}, e guarda em {alvo}.", literal_longa
            )
        else:
            longa.fixa(literal_longa)
        longa.revela(campos, self._volta_longa(contexto, alvo))
        volta = contexto.passo.get("volta")
        if volta and volta["laco"] == contexto.comando["id"] and volta["total"] is not None:
            longa.revela(["volta.total"], f" Ao todo, o laço dá {_plural(volta['total'], 'volta')}.")
        return curta, longa

    def _volta_curta(self, contexto, alvo, resto):
        """Desfechos possíveis do cabeçalho do for, do mais completo ao mais curto."""
        if contexto.erro == "limite":
            return ["O programa parou aqui.", "Parou aqui."]
        if contexto.erro:
            return ["Aqui dá erro."]
        volta = contexto.passo.get("volta")
        if not volta or volta["laco"] != contexto.comando["id"]:
            return []
        if volta["saindo"]:
            return ["Acabou: sai do laço.", "Sai do laço."]
        n = volta["n"]
        nome = contexto.no.target.id if isinstance(contexto.no.target, ast.Name) else None
        if nome is None:
            pares = self._pares(contexto, _nomes_dos_alvos([contexto.no.target]), LIMITE_PALAVRAS)
            return [f"Volta {n}: {pares}.", f"{pares}.", f"Volta {n}."] if pares else [f"Volta {n}."]
        mudanca = contexto.mudanca(nome)
        if mudanca is None:
            return [f"Volta {n}."]
        valor = _mostrar(mudanca[1])
        cortado = _cortar(valor, max(resto - 2, 1))
        return [
            f"Volta {n}: {nome} recebe {valor}.",
            f"{nome} recebe {valor}.",
            f"{nome} recebe {cortado}.",
            f"Volta {n}.",
        ]

    def _volta_longa(self, contexto, alvo):
        erro = self._erro_longo(contexto)
        if erro:
            return erro
        volta = contexto.passo.get("volta")
        if not volta or volta["laco"] != contexto.comando["id"]:
            return ""
        texto = self._antes_roda(contexto, " para pegar o próximo valor")
        if volta["saindo"]:
            return texto + " Não há mais valores: o laço termina e o programa segue depois dele."
        alvos = contexto.no.target
        if isinstance(alvos, ast.Name):
            mudanca = contexto.mudanca(alvos.id)
            valores = f"{alvos.id} passa a valer {_longo(mudanca[1])}" if mudanca else None
        else:
            valores = self._pares(contexto, _nomes_dos_alvos([alvos]), 40)
        return texto + f" Volta {volta['n']}" + (f": {valores}." if valores else ".")

    def _print(self, contexto):
        chamada = contexto.no.value
        # O input também escreve na tela (a pergunta e o que foi digitado).
        com_input = any(_chamada_de(filho, "input") for filho in ast.walk(chamada))
        base = "input e print escrevem na tela" if com_input else "print escreve na tela"
        desfecho = self._erro_curto(contexto)
        efeito = contexto.efeito
        if desfecho is None and efeito is not None:
            if efeito["saida_nova"] in ("", "\n"):
                desfecho = ": uma linha vazia." if efeito["saida_nova"] else ": nada."
            else:
                desfecho = f": {self._saida(efeito['saida_nova'], LIMITE_PALAVRAS - contar_palavras(base))}."
        longa = _Frase()
        longa.fixa("print escreve na tela o que está entre os parênteses.")
        if com_input:
            longa.fixa(" Antes, o input mostra na tela a pergunta e o que foi digitado.")
        if len(chamada.args) > 1 and not any(palavra.arg == "sep" for palavra in chamada.keywords):
            longa.fixa(" Os valores aparecem separados por um espaço.")
        substituido = self.com_valores(chamada, contexto.passo)
        if substituido:
            longa.fixa(f" Com os valores de agora: {substituido}.")
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None and efeito is not None:
            desfecho_longo = self._antes_roda(contexto)
            if efeito["saida_nova"] in ("", "\n"):
                desfecho_longo += " Aparece uma linha vazia." if efeito["saida_nova"] else " Nada aparece."
            else:
                desfecho_longo += f" Aparece: {self._saida(efeito['saida_nova'], 40)}."
        longa.revela(["efeito"], desfecho_longo or "")
        return self._base_e_desfecho(base, desfecho), longa

    def _return(self, contexto):
        no = contexto.no
        funcao = contexto.passo["funcao"] or "a função"
        longa = _Frase()
        if no.value is None:
            longa.fixa(f"return termina a função {funcao}. Sem valor, ela devolve None.")
            return self._base_e_desfecho(f"{funcao} termina e devolve None", self._erro_curto(contexto)), longa
        expressao = self.fonte.trecho(no.value)
        base = _cortar(f"{funcao} devolve {_cortar(expressao, 5)}", 7)
        indice = self.retornos.get(contexto.passo["quadro"])
        retorno = retorno_do_quadro(self.passos[indice], contexto.passo["quadro"]) if indice is not None else None
        devolvido = retorno["valor"] if retorno is not None and not contexto.erro else None
        desfecho = self._erro_curto(contexto)
        if desfecho is None and devolvido is not None and not _literal(no.value):
            resto = LIMITE_PALAVRAS - contar_palavras(base) - 2
            desfecho = f", que vale {_cortar(_mostrar(devolvido), resto)}."
        longa.fixa(f"return termina a função {funcao} e devolve {expressao} para quem chamou.")
        substituido = self.com_valores(no.value, contexto.passo)
        if substituido:
            longa.fixa(f" Com os valores de agora: {substituido}.")
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None and devolvido is not None:
            desfecho_longo = self._antes_roda(contexto) + f" O valor devolvido é {_mostrar(devolvido)}."
        longa.revela(["efeito"], desfecho_longo or "")
        return self._base_e_desfecho(base, desfecho), longa

    def _def(self, contexto):
        no = contexto.no
        curta, longa = _Frase(), _Frase()
        curta.fixa(f"Cria a função {no.name}. Ela só roda quando for chamada.")
        longa.fixa(
            f"O Python guarda a função {no.name}({ast.unparse(no.args)}), mas ainda não roda o que está dentro dela. "
            f"Isso só acontece quando {no.name} for chamada."
        )
        return curta, longa

    def _break(self, contexto):
        curta, longa = _Frase(), _Frase()
        curta.fixa("break: sai do laço agora.")
        longa.fixa("break interrompe o laço na hora, mesmo no meio da volta. O programa segue depois do laço.")
        return curta, longa

    def _continue(self, contexto):
        curta, longa = _Frase(), _Frase()
        curta.fixa("continue: pula para a próxima volta.")
        longa.fixa("continue pula o resto desta volta. O laço vai direto para a próxima.")
        return curta, longa

    def _expr(self, contexto):
        valor = contexto.no.value
        longa = _Frase()
        if isinstance(valor, ast.YieldFrom):
            # yield from não entrega o iterável: entrega cada item dele, um pedido por vez.
            fonte = self.fonte.trecho(valor.value)
            curta = _Frase()
            curta.fixa(f"yield from entrega os itens de {_cortar(fonte, 4)}, um por vez.")
            longa.fixa(
                f"yield from entrega os itens de {fonte}, um de cada vez, para quem pede o próximo valor. "
                "A função só continua depois que todos forem entregues."
            )
            return curta, longa
        if isinstance(valor, ast.Yield):
            entregue = self.fonte.trecho(valor.value) if valor.value is not None else "None"
            curta = _Frase()
            curta.fixa(f"yield entrega {_cortar(entregue, 5)} e pausa a função.")
            longa.fixa(
                f"yield entrega {entregue} para quem pediu o próximo valor. A função pausa aqui e continua depois."
            )
            return curta, longa
        if not isinstance(valor, ast.Call):
            expressao = self.fonte.trecho(valor)
            curta = _Frase()
            curta.fixa(f"Calcula {_cortar(expressao, 5)}, mas não guarda o resultado.")
            longa.fixa(f"O Python calcula {expressao}, mas o resultado não vai para nenhuma variável e se perde.")
            longa.revela(["efeito"], self._erro_longo(contexto) or "")
            return curta, longa
        if _chamada_de(valor, "exit", "quit"):
            curta = _Frase()
            curta.fixa(f"{valor.func.id}() encerra o programa aqui.")
            longa.fixa(f"{valor.func.id}() encerra o programa aqui, sem rodar o resto.")
            return curta, longa
        base = self._base_da_chamada(contexto, valor)
        resto = LIMITE_PALAVRAS - contar_palavras(base)
        desfecho = self._erro_curto(contexto) or self._resumo(contexto, resto)
        funcao = valor.func.id if isinstance(valor.func, ast.Name) else None
        if funcao and base.startswith("Chama "):
            longa.fixa(f"O Python chama a função {funcao}: entra nela, roda os comandos dela e depois volta para cá.")
        elif base.startswith("Roda "):
            longa.fixa(f"O Python roda {self.fonte.trecho(valor)}.")
        else:
            lista = valor.func.value.id
            longa.fixa(f"{base}. O método {valor.func.attr} muda a própria lista {lista}, sem criar outra.")
        desfecho_longo = self._erro_longo(contexto)
        if desfecho_longo is None:
            desfecho_longo = self._resumo_longo(contexto)
        longa.revela(["efeito"], desfecho_longo)
        return self._base_e_desfecho(base, desfecho), longa

    def _base_da_chamada(self, contexto, chamada):
        funcao = chamada.func
        if isinstance(funcao, ast.Attribute) and isinstance(funcao.value, ast.Name) and not chamada.keywords:
            lista = contexto.antes(funcao.value.id)
            frase = METODOS_DE_LISTA.get((funcao.attr, len(chamada.args)))
            if lista is not None and lista["tipo"] == "list" and frase:
                # O argumento inteiro até 3 palavras ('i * 2'): o que se corta depois é o valor da lista.
                argumentos = [_cortar(self.fonte.trecho(argumento), 3) for argumento in chamada.args]
                return _cortar(frase.format(*argumentos, lista=funcao.value.id), 8)
        if isinstance(funcao, ast.Name):
            alvo = contexto.antes(funcao.id)
            if alvo is not None and alvo["tipo"] == "function":
                return f"Chama {_cortar(self.fonte.trecho(chamada), 5)}"
        return f"Roda {_cortar(self.fonte.trecho(chamada), 5)}"

    def _outro(self, contexto):
        no = contexto.no
        longa = _Frase()
        fixas = {
            ast.Pass: ("pass: não faz nada", "pass não faz nada. Ele só ocupa o lugar de um bloco vazio."),
            ast.Try: (
                "try: tenta rodar o bloco",
                "O Python tenta rodar o bloco do try. Se der erro, ele vai para o except.",
            ),
            ast.ExceptHandler: (
                "Deu erro no try: roda o except",
                "Aconteceu um erro no bloco do try. Em vez de parar o programa, o Python roda o except.",
            ),
            ast.Raise: (
                "Levanta um erro de propósito",
                "raise cria um erro de propósito. Se ninguém tratar, o programa para.",
            ),
        }
        if type(no) in fixas:
            base, explicacao = fixas[type(no)]
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            modulos = ", ".join(nome.name for nome in no.names)
            if isinstance(no, ast.Import):
                base = f"Importa o módulo {_cortar(modulos, 4)}"
                explicacao = f"import traz o módulo {modulos} para o programa poder usar."
            else:
                base = f"Importa {_cortar(modulos, 3)} de {no.module or '.'}"
                explicacao = f"import traz {modulos} do módulo {no.module or '.'} para o programa poder usar."
        elif isinstance(no, ast.ClassDef):
            base = f"Cria a classe {no.name}"
            explicacao = f"O Python guarda a classe {no.name}, um molde para criar objetos."
        elif isinstance(no, (ast.Global, ast.Nonlocal)):
            nomes = ", ".join(no.names)
            base = f"Avisa que {_cortar(nomes, 2)} é a variável de fora"
            explicacao = f"Dentro desta função, {nomes} é a variável de fora, e não uma variável nova."
        elif isinstance(no, ast.Delete):
            alvos = ", ".join(self.fonte.trecho(alvo) for alvo in no.targets)
            base = f"Apaga {_cortar(alvos, 4)}"
            explicacao = f"del apaga {alvos}."
        elif isinstance(no, ast.Assert):
            base = f"Confere se {_cortar(self.fonte.trecho(no.test), 5)} é verdade"
            explicacao = "assert confere uma condição. Se der Falso, o programa para com um erro."
        else:
            base = f"Roda a linha {contexto.comando['linhas'][0]}"
            explicacao = f"O Python roda o comando da linha {contexto.comando['linhas'][0]}."
            resto = LIMITE_PALAVRAS - contar_palavras(base)
            desfecho = self._erro_curto(contexto) or self._resumo(contexto, resto)
            longa.fixa(explicacao)
            longa.revela(["efeito"], self._erro_longo(contexto) or self._resumo_longo(contexto))
            return self._base_e_desfecho(base, desfecho), longa
        longa.fixa(explicacao)
        longa.revela(["efeito"], self._erro_longo(contexto) or "")
        return self._base_e_desfecho(base, self._erro_curto(contexto)), longa

    def _reserva(self, contexto):
        """Frase curta de segurança, se alguma construção passar de 12 palavras."""
        resto = LIMITE_PALAVRAS - 4
        desfecho = self._erro_curto(contexto) or self._resumo(contexto, resto)
        return self._base_e_desfecho(f"Roda a linha {contexto.passo['linha']}", desfecho)
