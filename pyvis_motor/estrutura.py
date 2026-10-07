"""Lê a estrutura do programa (a AST) uma vez, antes de executar.

Cada comando ganha um número (id). O rastreador usa esse mapa para que um
passo seja sempre um comando inteiro, mesmo quando ele ocupa várias linhas,
e as próximas etapas usam as faixas de cabeçalho, corpo e senão para saber
que ramo um if tomou ou quando começa uma nova volta de um laço.
"""

import ast
import io
import tokenize

TIPOS = {
    ast.Assign: "atrib",
    ast.AugAssign: "aug",
    ast.While: "while",
    ast.For: "for",
    ast.FunctionDef: "def",
    ast.AsyncFunctionDef: "def",
    ast.Return: "return",
    ast.Break: "break",
    ast.Continue: "continue",
}

# Laços e funções escritos dentro de uma expressão: as voltas deles não são voltas do comando.
NOS_INTERNOS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Lambda)
ESCOPOS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
LACOS = (ast.For, ast.While, ast.AsyncFor)
BLOCOS = ("body", "handlers", "orelse", "finalbody", "cases")


def analisar(codigo):
    """Devolve {comandos, linha_para_comando} do código (que precisa compilar)."""
    return Analise(codigo).publico()


class Analise:
    """O resultado de analisar(), com o que o rastreador precisa a mais.

    `nos[id]` é o nó da AST do comando, `internos[id]` são os trechos de
    compreensões e lambdas dentro dele e `por_escopo` separa as linhas por
    função, para que `def f(): return 1` (numa linha só) tenha um comando
    para quem define a função e outro para quem a executa.
    """

    def __init__(self, codigo, arvore=None):
        self.arvore = arvore if arvore is not None else ast.parse(codigo)
        self.comandos = []
        self.nos = []
        self.internos = []
        self.linha_para_comando = {}
        self.por_escopo = {"<module>": {}}
        # O Python aceita \r e \r\n como fim de linha; aqui tudo vira \n para as linhas baterem com a AST.
        self._linhas = io.StringIO(codigo.replace("\r\n", "\n").replace("\r", "\n")).readlines()
        self._dois_pontos, self._senoes = self._ler_fichas()
        self._visitar_bloco(self.arvore.body, pai=None, escopo="<module>", em_laco=False)

    def publico(self):
        return {"comandos": self.comandos, "linha_para_comando": self.linha_para_comando}

    def mapa_do_codigo(self, nome, primeira_linha):
        """Mapa linha -> comando de um objeto de código (módulo, função ou classe)."""
        if nome == "<module>":
            return self.por_escopo["<module>"]
        return self.por_escopo.get((nome, primeira_linha), self.linha_para_comando)

    def _visitar_bloco(self, corpo, pai, escopo, em_laco):
        for no in corpo:
            self._visitar(no, pai, escopo, em_laco)

    def _visitar(self, no, pai, escopo, em_laco):
        id_ = len(self.comandos)
        inicio = _primeira_linha(no)
        cabecalho = self._cabecalho(no)
        corpo = _faixa(getattr(no, "body", None))
        comando = {
            "id": id_,
            "tipo": self._tipo(no),
            "linhas": [inicio, _ultima_linha(no)],
            "cabecalho": cabecalho,
            "corpo": corpo,
            "orelse": self._faixa_senao(no),
            "corpo_mesma_linha": bool(cabecalho and corpo and corpo[0] == cabecalho[1]),
            "pai": pai,
            "acumulador": _acumulador(no) if em_laco else None,
        }
        self.comandos.append(comando)
        self.nos.append(no)
        self.internos.append(_trechos_internos(no))

        # As linhas "próprias" do comando: o cabeçalho de um bloco ou o comando
        # simples inteiro. Em pré-ordem, quem chega primeiro fica com a linha,
        # então em `if x: y = 1` a linha é do if.
        proprias = cabecalho or comando["linhas"]
        for linha in range(proprias[0], proprias[1] + 1):
            self.linha_para_comando.setdefault(linha, id_)
            self.por_escopo[escopo].setdefault(linha, id_)

        if isinstance(no, ESCOPOS):
            escopo = (no.name, inicio)  # é o co_name e o co_firstlineno da função
            self.por_escopo[escopo] = {}
            em_laco = False
        em_laco = em_laco or isinstance(no, LACOS)
        for campo in BLOCOS:
            self._visitar_bloco(getattr(no, campo, None) or (), id_, escopo, em_laco)

    def _tipo(self, no):
        if isinstance(no, ast.If):
            linha = self._linhas[no.lineno - 1].encode() if no.lineno <= len(self._linhas) else b""
            return "elif" if linha[no.col_offset:].startswith(b"elif") else "if"
        if isinstance(no, ast.Expr):
            chamada = no.value
            if isinstance(chamada, ast.Call) and isinstance(chamada.func, ast.Name) and chamada.func.id == "print":
                return "print"
            return "expr"
        if isinstance(no, ast.AnnAssign) and no.value is not None:
            return "atrib"
        return TIPOS.get(type(no), "outro")

    def _cabecalho(self, no):
        """Faixa de linhas do cabeçalho de um bloco (até os dois-pontos), ou None."""
        if not hasattr(no, "body") and not isinstance(no, ast.Match):
            return None
        inicio = _primeira_linha(no)
        # Os dois-pontos do cabeçalho vêm depois da condição ou do iterável;
        # antes deles pode haver outros (num lambda, por exemplo).
        if isinstance(no, ast.match_case):
            depois = no.guard or no.pattern
        elif isinstance(no, ast.Match):
            depois = no.subject
        else:
            depois = getattr(no, "test", None) or getattr(no, "iter", None) or getattr(no, "type", None)
        if depois is not None:
            posicao = (depois.end_lineno, depois.end_col_offset)
        else:
            posicao = (no.lineno, no.col_offset)
        fim = next((linha for linha, coluna in self._dois_pontos if (linha, coluna) >= posicao), None)
        if fim is None or fim < inicio:
            fim = depois.end_lineno if depois is not None else no.lineno
        filhos = getattr(no, "body", None) or getattr(no, "cases", None)
        if filhos and _primeira_linha(filhos[0]) < fim:
            fim = _primeira_linha(filhos[0])
        return [inicio, fim]

    def _faixa_senao(self, no):
        senao = getattr(no, "orelse", None)
        if not senao:
            return None
        fim = senao[-1].end_lineno
        if isinstance(no, ast.If) and isinstance(senao[0], ast.If) and self._tipo(senao[0]) == "elif":
            return [senao[0].lineno, fim]
        # A faixa começa na linha do `else:`, para a interface poder esmaecer o bloco todo.
        antes = no.handlers[-1] if getattr(no, "handlers", None) else no.body[-1]
        depois_do_corpo = (antes.end_lineno, antes.end_col_offset)
        inicio_do_senao = (senao[0].lineno, senao[0].col_offset)
        for lugar in self._senoes:
            if depois_do_corpo <= lugar < inicio_do_senao:
                return [lugar[0], fim]
        return [senao[0].lineno, fim]

    def _ler_fichas(self):
        """Posições dos dois-pontos fora de parênteses e das palavras `else`.

        As colunas viram bytes em UTF-8, como as da AST: um acento antes
        dos dois-pontos (`if nome == "João":`) não pode desalinhar a busca.
        """
        dois_pontos, senoes = [], []
        profundidade = 0
        leitor = io.StringIO("".join(self._linhas)).readline
        try:
            for ficha in tokenize.generate_tokens(leitor):
                if ficha.type == tokenize.OP and ficha.string in "([{":
                    profundidade += 1
                elif ficha.type == tokenize.OP and ficha.string in ")]}":
                    profundidade -= 1
                elif profundidade == 0 and ficha.string in (":", "else") and ficha.type in (tokenize.OP, tokenize.NAME):
                    linha, coluna = ficha.start
                    lugar = (linha, len(self._linhas[linha - 1][:coluna].encode()))
                    (dois_pontos if ficha.string == ":" else senoes).append(lugar)
        except (tokenize.TokenError, SyntaxError, IndexError):
            pass  # sem as fichas, as faixas usam só as posições da AST
        return dois_pontos, senoes


def _primeira_linha(no):
    if isinstance(no, ast.match_case):
        return no.pattern.lineno
    decoradores = getattr(no, "decorator_list", None)
    if decoradores:
        return min([no.lineno] + [d.lineno for d in decoradores])
    return no.lineno


def _ultima_linha(no):
    if isinstance(no, ast.match_case):
        return no.body[-1].end_lineno
    return no.end_lineno


def _faixa(bloco):
    if not bloco:
        return None
    return [_primeira_linha(bloco[0]), _ultima_linha(bloco[-1])]


def _e_bloco(valor):
    return isinstance(valor, list) and valor and isinstance(valor[0], (ast.stmt, ast.excepthandler, ast.match_case))


def _trechos_internos(no):
    """Trechos (linha, col, linha_fim, col_fim) de compreensões e lambdas do próprio comando."""
    trechos = []
    pendentes = [no]
    while pendentes:
        atual = pendentes.pop()
        for _campo, valor in ast.iter_fields(atual):
            if _e_bloco(valor):
                continue  # os comandos de dentro de um bloco são comandos próprios
            for filho in valor if isinstance(valor, list) else [valor]:
                if isinstance(filho, NOS_INTERNOS):
                    trechos.append((filho.lineno, filho.col_offset, filho.end_lineno, filho.end_col_offset))
                elif isinstance(filho, ast.AST):
                    pendentes.append(filho)
    return trechos


def _e_um(no):
    return isinstance(no, ast.Constant) and type(no.value) is int and no.value == 1


def _e_o_nome(no, nome):
    return isinstance(no, ast.Name) and no.id == nome


def _acumulador(no):
    """x = x + ... ou x += ... dentro de um laço. É contador quando o passo é 1.

    Também aceita - e * (contagem regressiva e produto acumulado).
    """
    operacoes = (ast.Add, ast.Sub, ast.Mult)
    if isinstance(no, ast.AugAssign) and isinstance(no.target, ast.Name) and isinstance(no.op, operacoes):
        contador = isinstance(no.op, (ast.Add, ast.Sub)) and _e_um(no.value)
        return {"nome": no.target.id, "contador": contador}
    if not (isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name)):
        return None
    nome = no.targets[0].id
    conta = no.value
    if not (isinstance(conta, ast.BinOp) and isinstance(conta.op, operacoes)):
        return None
    if _e_o_nome(conta.left, nome):
        outro = conta.right
    elif _e_o_nome(conta.right, nome) and not isinstance(conta.op, ast.Sub):
        outro = conta.left
    else:
        return None
    return {"nome": nome, "contador": isinstance(conta.op, (ast.Add, ast.Sub)) and _e_um(outro)}
