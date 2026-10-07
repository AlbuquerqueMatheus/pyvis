"""Calcula a condição de um if/elif/while sem mexer no programa do aluno.

Não usa eval nem compile: percorre a AST nó a nó e só calcula com valores
de tipos simples (o tipo exato, nunca uma subclasse). Um `map`, um gerador
ou um objeto do aluno fazem o avaliador desistir, porque calcular com eles
poderia consumir o iterador ou rodar código do aluno uma vez a mais.
O curto-circuito do `and`/`or` é respeitado: o que o Python não calculou
fica marcado, em vez de aparecer com valores que nunca existiram.
"""

import ast
import builtins
import operator

from .valores import com_aspas

TIPOS_SEGUROS = frozenset({int, float, str, bool, type(None), list, tuple, dict, set, range})
NUMEROS = frozenset({int, float, bool})
SEQUENCIAS = frozenset({str, list, tuple})
COLECOES = frozenset({str, list, tuple, dict, set, range})
INDEXAVEIS = frozenset({list, tuple, str, dict})

LIMITE_REPR = 30
LIMITE_ITENS = 2000  # quantos itens de coleções o avaliador aceita conferir por condição
LIMITE_TAMANHO = 10_000  # tamanho máximo de texto ou lista criados por + e *
LIMITE_BITS = 100_000  # tamanho máximo de um inteiro criado por *, ** ou <<

FUNCOES = {"len": builtins.len, "abs": builtins.abs, "min": builtins.min, "max": builtins.max}

# Precedência para recolocar parênteses no texto (maior = liga mais forte).
OU, E, NAO, COMPARA, BIT_OU, BIT_XOU, BIT_E, DESLOCA, SOMA, PRODUTO, SINAL, POTENCIA, ATOMO = range(1, 14)

BINARIOS = {
    ast.Add: ("+", SOMA, operator.add),
    ast.Sub: ("-", SOMA, operator.sub),
    ast.Mult: ("*", PRODUTO, operator.mul),
    ast.Div: ("/", PRODUTO, operator.truediv),
    ast.FloorDiv: ("//", PRODUTO, operator.floordiv),
    ast.Mod: ("%", PRODUTO, operator.mod),
    ast.Pow: ("**", POTENCIA, operator.pow),
    ast.BitOr: ("|", BIT_OU, operator.or_),
    ast.BitXor: ("^", BIT_XOU, operator.xor),
    ast.BitAnd: ("&", BIT_E, operator.and_),
    ast.LShift: ("<<", DESLOCA, operator.lshift),
    ast.RShift: (">>", DESLOCA, operator.rshift),
}

COMPARACOES = {
    ast.Eq: ("==", operator.eq),
    ast.NotEq: ("!=", operator.ne),
    ast.Lt: ("<", operator.lt),
    ast.LtE: ("<=", operator.le),
    ast.Gt: (">", operator.gt),
    ast.GtE: (">=", operator.ge),
    ast.Is: ("is", operator.is_),
    ast.IsNot: ("is not", operator.is_not),
    ast.In: ("in", lambda a, b: a in b),
    ast.NotIn: ("not in", lambda a, b: a not in b),
}

UNARIOS = {
    ast.Not: ("not ", NAO, operator.not_),
    ast.USub: ("-", SINAL, operator.neg),
    ast.UAdd: ("+", SINAL, operator.pos),
    ast.Invert: ("~", SINAL, operator.invert),
}

DESISTIU = {"texto": None, "valor": None, "nao_calculado": [], "nao_calculado_codigo": []}


class _Desiste(Exception):
    """Não dá para mostrar o valor sem risco: o balão fica só com o resultado."""


def avaliar(no_test, f_globals, f_locals):
    """Devolve {texto, valor, nao_calculado, nao_calculado_codigo} da condição.

    `texto` é a condição com os valores no lugar dos nomes ('7 >= 6'), ou None
    quando não é seguro calcular. `nao_calculado` são faixas [ini, fim) de
    `texto` que o curto-circuito pulou; `nao_calculado_codigo` são as mesmas
    partes no código do aluno, como [linha, col, linha_fim, col_fim] da AST.
    """
    try:
        avaliador = _Avaliador(f_globals, f_locals)
        valor, partes, _ = avaliador.calcular(no_test, True)
        resultado = bool(valor)
    except Exception:  # qualquer surpresa vira desistência, nunca erro no programa do aluno
        return dict(DESISTIU)
    texto = ""
    faixas = []
    for pedaco, pulado in partes:
        if pulado and faixas and faixas[-1][1] == len(texto):
            faixas[-1][1] += len(pedaco)
        elif pulado:
            faixas.append([len(texto), len(texto) + len(pedaco)])
        texto += pedaco
    return {"texto": texto, "valor": resultado, "nao_calculado": faixas, "nao_calculado_codigo": avaliador.pulados}


class _Avaliador:
    """Cada cálculo devolve (valor, partes do texto, precedência).

    As partes são pares (pedaço, pulado_pelo_curto_circuito). Com `texto`
    falso (dentro de len(...) ou l[...]), só o valor importa: o texto da
    chamada é o resultado dela, não os argumentos.
    """

    def __init__(self, f_globals, f_locals):
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.orcamento = LIMITE_ITENS
        self.pulados = []
        self.metodos = {
            ast.Constant: self._constante,
            ast.Name: self._nome,
            ast.List: self._lista,
            ast.Tuple: self._tupla,
            ast.Set: self._conjunto,
            ast.Subscript: self._indice,
            ast.Call: self._chamada,
            ast.BinOp: self._conta,
            ast.UnaryOp: self._unario,
            ast.BoolOp: self._logico,
            ast.Compare: self._comparacao,
        }

    def calcular(self, no, texto):
        metodo = self.metodos.get(type(no))
        if metodo is None:
            raise _Desiste()  # atributos, métodos, :=, f-strings, ... não são calculados
        return metodo(no, texto)

    def valor(self, no):
        return self.calcular(no, False)[0]

    def _folha(self, valor, texto):
        # Todo valor que circula tem tipo seguro; o conteúdo é conferido quando é usado.
        if type(valor) not in TIPOS_SEGUROS:
            raise _Desiste()
        if not texto:
            return valor, None, ATOMO
        escrito = self._repr_curto(valor)
        return valor, [(escrito, False)], SINAL if escrito.startswith("-") else ATOMO

    def _constante(self, no, texto):
        return self._folha(no.value, texto)

    def _nome(self, no, texto):
        return self._folha(self._buscar(no.id), texto)

    def _itens(self, elementos):
        if any(isinstance(e, ast.Starred) for e in elementos):
            raise _Desiste()
        return [self.valor(e) for e in elementos]

    def _lista(self, no, texto):
        return self._folha(self._itens(no.elts), texto)

    def _tupla(self, no, texto):
        return self._folha(tuple(self._itens(no.elts)), texto)

    def _conjunto(self, no, texto):
        itens = self._itens(no.elts)
        self._conferir(itens)  # o set chama __hash__ e __eq__ dos itens
        return self._folha(set(itens), texto)

    def _indice(self, no, texto):
        base = self.valor(no.value)
        if type(base) not in INDEXAVEIS:
            raise _Desiste()
        if isinstance(no.slice, ast.Slice):
            limites = [None if p is None else self.valor(p) for p in (no.slice.lower, no.slice.upper, no.slice.step)]
            if type(base) is dict or any(type(x) not in (int, bool, type(None)) for x in limites):
                raise _Desiste()
            return self._folha(base[slice(*limites)], texto)
        indice = self.valor(no.slice)
        if type(base) is dict:
            self._conferir(list(base))  # procurar a chave compara com as chaves que já estão lá
            self._conferir(indice)
        elif type(indice) not in (int, bool):
            raise _Desiste()
        return self._folha(base[indice], texto)

    def _chamada(self, no, texto):
        funcao = no.func
        if not isinstance(funcao, ast.Name) or funcao.id not in FUNCOES or no.keywords:
            raise _Desiste()
        if self._buscar(funcao.id) is not FUNCOES[funcao.id]:
            raise _Desiste()  # o aluno criou uma variável ou função com esse nome
        argumentos = self._itens(no.args)
        if funcao.id == "len":
            if len(argumentos) != 1 or type(argumentos[0]) not in COLECOES:
                raise _Desiste()
        elif funcao.id == "abs":
            if len(argumentos) != 1 or type(argumentos[0]) not in NUMEROS:
                raise _Desiste()
        else:
            # min e max comparam os itens: tudo precisa ser seguro e caber no orçamento.
            if len(argumentos) == 1:
                unico = argumentos[0]
                if type(unico) not in COLECOES or (type(unico) is range and len(unico) > self.orcamento):
                    raise _Desiste()
            self._conferir(argumentos)
        return self._folha(FUNCOES[funcao.id](*argumentos), texto)

    def _conta(self, no, texto):
        simbolo, precedencia, conta = BINARIOS.get(type(no.op), (None, None, None))
        if conta is None:
            raise _Desiste()
        esquerda, texto_e, prec_e = self.calcular(no.left, texto)
        direita, texto_d, prec_d = self.calcular(no.right, texto)
        self._conferir_conta(type(no.op), esquerda, direita)
        valor = self._folha(conta(esquerda, direita), False)[0]
        if not texto:
            return valor, None, precedencia
        if isinstance(no.op, ast.Pow):  # ** associa pela direita e liga mais que o sinal
            texto_e = _parenteses(texto_e, prec_e <= POTENCIA)
            texto_d = _parenteses(texto_d, prec_d < SINAL)
        else:
            texto_e = _parenteses(texto_e, prec_e < precedencia)
            texto_d = _parenteses(texto_d, prec_d <= precedencia)
        return valor, texto_e + [(f" {simbolo} ", False)] + texto_d, precedencia

    def _conferir_conta(self, op, a, b):
        tipos = (type(a), type(b))
        if tipos[0] in NUMEROS and tipos[1] in NUMEROS:
            inteiros = float not in tipos
            if op in (ast.Mult, ast.FloorDiv, ast.Mod) and inteiros and _bits(a) + _bits(b) > LIMITE_BITS:
                raise _Desiste()
            if op is ast.Pow and inteiros and b > 0 and _bits(a) * b > LIMITE_BITS:
                raise _Desiste()  # 10 ** 10 ** 9 travaria a página
            if op is ast.LShift and inteiros and b > LIMITE_BITS:
                raise _Desiste()
            if op in (ast.BitOr, ast.BitXor, ast.BitAnd, ast.LShift, ast.RShift) and not inteiros:
                raise _Desiste()
            return
        if op is ast.Add and tipos[0] is tipos[1] and tipos[0] in SEQUENCIAS:
            if len(a) + len(b) > LIMITE_TAMANHO:
                raise _Desiste()
            return
        if op is ast.Mult:
            if tipos[0] in SEQUENCIAS and tipos[1] in (int, bool):
                sequencia, vezes = a, b
            elif tipos[1] in SEQUENCIAS and tipos[0] in (int, bool):
                sequencia, vezes = b, a
            else:
                raise _Desiste()
            if len(sequencia) * max(vezes, 0) > LIMITE_TAMANHO:
                raise _Desiste()
            return
        raise _Desiste()  # % em texto, operações com conjuntos etc.

    def _unario(self, no, texto):
        simbolo, precedencia, conta = UNARIOS[type(no.op)]
        valor, partes, prec = self.calcular(no.operand, texto)
        if not isinstance(no.op, ast.Not) and type(valor) not in NUMEROS:
            raise _Desiste()
        resultado = conta(valor)
        if not texto:
            return resultado, None, precedencia
        partes = _parenteses(partes, prec < precedencia or (precedencia == SINAL and prec == SINAL))
        return resultado, [(simbolo, False)] + partes, precedencia

    def _logico(self, no, texto):
        e_ou = isinstance(no.op, ast.Or)
        precedencia = OU if e_ou else E
        conectivo = " or " if e_ou else " and "
        partes = []
        valor = None
        for posicao, operando in enumerate(no.values):
            if posicao:
                partes.append((conectivo, False))
            valor, pedaco, prec = self.calcular(operando, texto)
            if texto:
                partes += _parenteses(pedaco, prec <= precedencia)
            if bool(valor) == e_ou:
                # Curto-circuito: o resto nem foi calculado.
                for indice, pulado in enumerate(no.values[posicao + 1:]):
                    partes.append((conectivo, indice > 0))
                    partes += self._pulado(pulado, precedencia, texto)
                break
        return valor, partes if texto else None, precedencia

    def _comparacao(self, no, texto):
        esquerda, partes, prec = self.calcular(no.left, texto)
        partes = _parenteses(partes, prec <= COMPARA) if texto else None
        valor = True
        for posicao, (op, comparador) in enumerate(zip(no.ops, no.comparators)):
            simbolo, compara = COMPARACOES[type(op)]
            direita, pedaco, prec = self.calcular(comparador, texto)
            if not isinstance(op, (ast.Is, ast.IsNot)):
                self._conferir([esquerda, direita])
                if isinstance(op, (ast.In, ast.NotIn)) and type(direita) is range and type(esquerda) not in (int, bool):
                    raise _Desiste()  # `1.5 in range(...)` percorreria o range inteiro
            if texto:
                partes += [(f" {simbolo} ", False)] + _parenteses(pedaco, prec <= COMPARA)
            valor = compara(esquerda, direita)
            if not valor:
                # A comparação encadeada para no primeiro falso.
                restantes = zip(no.ops[posicao + 1:], no.comparators[posicao + 1:])
                for indice, (op_resto, resto) in enumerate(restantes):
                    if texto:
                        partes += [(" ", indice > 0), (COMPARACOES[type(op_resto)][0] + " ", True)]
                    partes = (partes or []) + self._pulado(resto, COMPARA, texto)
                break
            esquerda = direita
        return valor, partes, COMPARA

    def _pulado(self, no, precedencia_do_pai, texto):
        if not texto:
            return []
        self.pulados.append([no.lineno, no.col_offset, no.end_lineno, no.end_col_offset])
        escrito = ast.unparse(no)
        if _precedencia_no(no) <= precedencia_do_pai:
            escrito = f"({escrito})"
        return [(escrito, True)]

    def _buscar(self, nome):
        for escopo in (self.f_locals, self.f_globals):
            try:
                return escopo[nome]
            except KeyError:
                pass
        embutidos = self.f_globals.get("__builtins__", builtins)
        if not isinstance(embutidos, dict):
            embutidos = vars(embutidos)
        try:
            return embutidos[nome]
        except KeyError:
            raise _Desiste() from None

    def _conferir(self, valor):
        """Confere que o valor e tudo dentro dele têm tipo seguro, dentro do orçamento."""
        pendentes = [valor]
        while pendentes:
            atual = pendentes.pop()
            self.orcamento -= 1
            if self.orcamento < 0 or type(atual) not in TIPOS_SEGUROS:
                raise _Desiste()
            if type(atual) is dict:
                if 2 * len(atual) > self.orcamento:
                    raise _Desiste()
                pendentes.extend(atual.keys())
                pendentes.extend(atual.values())
            elif type(atual) in (list, tuple, set):
                if len(atual) > self.orcamento:
                    raise _Desiste()
                pendentes.extend(atual)

    def _repr_curto(self, valor):
        """repr do valor cortado em LIMITE_REPR caracteres, sem montar o repr inteiro.

        Só olha os itens que aparecem no começo, então uma lista enorme não pesa.
        """
        pedacos = []
        tamanho = 0
        pilha = [valor]
        while pilha and tamanho <= LIMITE_REPR:
            atual = pilha.pop()
            if type(atual) is _Texto:
                pedaco = atual.texto
            elif type(atual) not in TIPOS_SEGUROS:
                raise _Desiste()
            elif type(atual) in (list, tuple, set, dict) and atual:
                pilha.extend(reversed(self._partes_do_repr(atual)))
                continue
            elif type(atual) is str:
                pedaco = com_aspas(atual[: LIMITE_REPR * 2])  # "Ana", como no resto da tela
            elif type(atual) is int and atual.bit_length() > 4000:
                raise _Desiste()  # o repr de um número gigante é lento
            else:
                pedaco = repr(atual)
            pedacos.append(pedaco)
            tamanho += len(pedaco)
        texto = "".join(pedacos)
        if len(texto) > LIMITE_REPR or pilha:
            texto = texto[: LIMITE_REPR - 1] + "…"
        return texto

    def _partes_do_repr(self, colecao):
        if type(colecao) is dict:
            partes = [_Texto("{")]
            for indice, (chave, item) in enumerate(colecao.items()):
                if indice:
                    partes.append(_Texto(", "))
                if indice * 2 > LIMITE_REPR:
                    break
                partes += [chave, _Texto(": "), item]
            return partes + [_Texto("}")]
        if type(colecao) is set:
            self._conferir(colecao)  # ordenar chama repr de todos os itens
            itens = sorted(colecao, key=repr)
        else:
            itens = colecao
        abre, fecha = {list: "[]", tuple: "()", set: "{}"}[type(colecao)]
        if type(colecao) is tuple and len(colecao) == 1:
            fecha = ",)"
        partes = [_Texto(abre)]
        for indice, item in enumerate(itens):
            if indice:
                partes.append(_Texto(", "))
            if indice * 2 > LIMITE_REPR:
                break  # cada item ocupa pelo menos 2 caracteres: o resto não aparece
            partes.append(item)
        return partes + [_Texto(fecha)]


class _Texto:
    __slots__ = ("texto",)

    def __init__(self, texto):
        self.texto = texto


def _bits(numero):
    return abs(int(numero)).bit_length()


def _parenteses(partes, precisa):
    if not precisa:
        return partes
    return [("(", False)] + partes + [(")", False)]


def _precedencia_no(no):
    if isinstance(no, ast.BoolOp):
        return OU if isinstance(no.op, ast.Or) else E
    if isinstance(no, ast.UnaryOp):
        return UNARIOS[type(no.op)][1]
    if isinstance(no, ast.Compare):
        return COMPARA
    if isinstance(no, ast.BinOp):
        return BINARIOS.get(type(no.op), (None, ATOMO))[1]
    if isinstance(no, (ast.IfExp, ast.Lambda, ast.NamedExpr)):
        return 0
    return ATOMO
