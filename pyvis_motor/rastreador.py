"""Executa o código do aluno uma vez e grava uma "foto" do estado a cada comando.

A interface depois só navega por essas fotos, então avançar e voltar
um passo é instantâneo. É a mesma ideia do Python Tutor (Guo, 2013).

Um passo é um comando inteiro, no mesmo quadro (a execução de uma função).
O Python avisa por linha, e às vezes avisa várias vezes no mesmo comando:
uma lista escrita em 3 linhas, uma compreensão que dá voltas dentro da linha
ou o resto de uma conta depois de chamar uma função. Esses avisos seguidos
do mesmo comando viram um passo só, com o estado do primeiro.
"""

import ast
import builtins
import contextlib
import difflib
import dis
import gc
import inspect
import io
import random
import sys
import time
import traceback

from .avaliador import avaliar
from .erros import traduzir
from .estrutura import Analise
from .seguranca import isolar
from .valores import converter, esquecer_textos, variaveis_visiveis

ARQUIVO_DO_ALUNO = "<aluno>"
LIMITE_PADRAO = 1000
VERSAO = 2

# Quadros que o Python cria por dentro de uma linha: compreensões (até o 3.11) e geradores de expressão.
QUADROS_INTERNOS = frozenset({"<listcomp>", "<dictcomp>", "<setcomp>", "<genexpr>"})
GERADORES = inspect.CO_GENERATOR | inspect.CO_COROUTINE | inspect.CO_ASYNC_GENERATOR | inspect.CO_ITERABLE_COROUTINE
OPERACOES_DE_VOLTA = frozenset(dis.opmap[nome] for nome in ("FOR_ITER", "JUMP_BACKWARD") if nome in dis.opmap)
# Um quadro que termina num RETURN terminou bem; em qualquer outra instrução, saiu por um erro.
OPERACOES_DE_RETORNO = frozenset(dis.opmap[nome] for nome in ("RETURN_VALUE", "RETURN_CONST") if nome in dis.opmap)
LACOS = frozenset({"for", "while"})
DECISOES = frozenset({"if", "elif", "while"})
MODULOS_NAO_DETERMINISTICOS = frozenset({"time", "datetime", "secrets"})


class LimiteDePassos(BaseException):
    """BaseException para que um `except Exception:` do aluno não engula o limite."""


class _Quadro:
    __slots__ = ("numero", "profundidade", "funcao", "mapa", "comando", "lasti", "rastrear", "ultimo")


class _Gravador:
    def __init__(self, analise, limite, saida):
        self.analise = analise
        self.limite = limite
        self.saida = saida
        self.passos = []
        self.quadros = {}  # frame -> _Quadro, enquanto o frame existe
        self.contador = 0  # o módulo é o quadro 0; cada chamada ganha o próximo número
        # Os returns que ainda vão aparecer no próximo passo gravado. Vários quadros
        # podem terminar sem passo entre eles (recursão, `return g(x) * 2`).
        self.retornos = []
        self.estourou = False
        self._codigos = {}  # objeto de código -> (bytes, posições), lidos uma vez só

    def chamada(self, frame, evento, arg):
        """Rastreador global: o Python chama em cada função que começa (ou volta de um yield)."""
        codigo = frame.f_code
        if codigo.co_filename != ARQUIVO_DO_ALUNO or codigo.co_name in QUADROS_INTERNOS:
            return None
        quadro = self.quadros.get(frame)
        if quadro is None:
            quadro = self._novo_quadro(frame)
        quadro.profundidade = self._profundidade(frame)
        return quadro.rastrear

    def _novo_quadro(self, frame):
        codigo = frame.f_code
        quadro = _Quadro()
        quadro.numero = self.contador
        self.contador += 1
        quadro.funcao = None if codigo.co_name == "<module>" else codigo.co_name
        quadro.mapa = self.analise.mapa_do_codigo(codigo.co_name, codigo.co_firstlineno)
        quadro.comando = None
        quadro.lasti = -1
        quadro.ultimo = None  # o último passo gravado neste quadro

        def rastrear_quadro(frame, evento, arg):
            if evento == "line":
                self._linha(quadro, frame)
            elif evento == "return":
                self._fim_do_quadro(quadro, frame, arg)
            return rastrear_quadro

        quadro.rastrear = rastrear_quadro
        self.quadros[frame] = quadro
        return quadro

    def _profundidade(self, frame):
        pai = frame.f_back
        while pai is not None:
            quadro = self.quadros.get(pai)
            if quadro is not None:
                return quadro.profundidade + 1
            pai = pai.f_back
        return 0

    def _linha(self, quadro, frame):
        lasti = frame.f_lasti
        comando = quadro.mapa.get(frame.f_lineno)
        if comando is None:
            return  # linha sem comando do aluno, como o preparo do corpo de uma classe
        if comando == quadro.comando and not self._nova_volta(quadro, frame, comando, lasti):
            quadro.lasti = lasti  # continuação do mesmo comando: fica o estado do primeiro aviso
            return
        quadro.comando = comando
        quadro.lasti = lasti
        self.gravar(frame, quadro, comando, "linha")

    def _nova_volta(self, quadro, frame, comando, lasti):
        """O mesmo laço avisou de novo: é uma volta nova ou ainda o mesmo comando?"""
        info = self.analise.comandos[comando]
        if info["tipo"] not in LACOS:
            return False
        bytecode, posicoes = self._ler_codigo(frame.f_code)
        pulou_para_tras = lasti <= quadro.lasti
        # Num laço de uma linha só (`for i in l: print(i)`), cada volta aparece
        # como um aviso no FOR_ITER (3.11) ou no JUMP_BACKWARD (3.12+).
        volta_na_mesma_linha = (
            info["corpo_mesma_linha"] and 0 <= lasti < len(bytecode) and bytecode[lasti] in OPERACOES_DE_VOLTA
        )
        if not (pulou_para_tras or volta_na_mesma_linha):
            return False
        # Voltas de uma compreensão ou de um lambda no cabeçalho não são voltas do laço.
        indice = lasti // 2
        posicao = posicoes[indice] if 0 <= indice < len(posicoes) else None
        if posicao is None or posicao[0] is None or posicao[2] is None:
            return True
        ponto = (posicao[0], posicao[2])
        return not any((l0, c0) <= ponto < (l1, c1) for l0, c0, l1, c1 in self.analise.internos[comando])

    def _ler_codigo(self, codigo):
        lido = self._codigos.get(codigo)
        if lido is None:
            lido = self._codigos[codigo] = (codigo.co_code, list(codigo.co_positions()))
        return lido

    def _fim_do_quadro(self, quadro, frame, valor):
        codigo = frame.f_code
        bytecode = self._ler_codigo(codigo)[0]
        terminou_bem = 0 <= frame.f_lasti < len(bytecode) and bytecode[frame.f_lasti] in OPERACOES_DE_RETORNO
        if quadro.funcao is None:
            if terminou_bem:
                self.gravar(frame, quadro, None, "fim")
            return
        if codigo.co_flags & GERADORES:
            return  # um yield também avisa "return", mas o quadro continua vivo
        del self.quadros[frame]
        # Só funções devolvem valor (o corpo de uma classe também "retorna").
        if terminou_bem and codigo.co_flags & inspect.CO_OPTIMIZED:
            self.retornos.append(self._retorno(quadro, frame, valor))

    def _retorno(self, quadro, frame, valor):
        """{funcao, valor, quadro, saida_ate, mudancas_globais, globais_apagadas}.

        O passo que recebe o retorno vem depois do comando inteiro de quem
        chamou: a saída e as globais dele já incluem o que esse comando fez
        depois da chamada. Por isso o estado no momento do return fica aqui:
        o tamanho da saída e as globais que mudaram desde o último passo do quadro.
        """
        retorno = {"funcao": quadro.funcao, "valor": converter(valor), "quadro": quadro.numero}
        retorno["saida_ate"] = self.saida.tell()
        if quadro.ultimo is not None:
            antes = self.passos[quadro.ultimo]["globais"]
            agora = variaveis_visiveis(frame.f_globals)
            retorno["mudancas_globais"] = {
                nome: valor for nome, valor in agora.items() if nome not in antes or antes[nome]["h"] != valor["h"]
            }
            retorno["globais_apagadas"] = [nome for nome in antes if nome not in agora]
        return retorno

    def gravar(self, frame, quadro, comando, evento):
        info = self.analise.comandos[comando] if comando is not None else None
        passo = {
            "i": len(self.passos),
            # Um comando em várias linhas fica sempre na primeira delas.
            "linha": info["linhas"][0] if info else frame.f_lineno,
            "comando": comando,
            "evento": evento,
            "quadro": quadro.numero,
            "profundidade": quadro.profundidade,
            "funcao": quadro.funcao,
            "globais": variaveis_visiveis(frame.f_globals),
            "locais": variaveis_visiveis(frame.f_locals) if quadro.funcao is not None else {},
            "saida": self.saida.getvalue(),
            "proximo_no_quadro": None,
        }
        if self.retornos:
            # `retorno` é o do quadro que chamou o deste passo (o último a terminar).
            passo["retornos"] = self.retornos
            passo["retorno"] = self.retornos[-1]
            self.retornos = []
        quadro.ultimo = passo["i"]
        if info is not None and info["tipo"] in DECISOES:
            # Calculado agora, antes da condição rodar: a Onda 2 transforma em `decisao`.
            passo["_decisao_bruta"] = avaliar(self.analise.nos[comando].test, frame.f_globals, frame.f_locals)
        self.passos.append(passo)
        if evento == "linha" and len(self.passos) > self.limite:
            self.estourou = True
            raise LimiteDePassos()


def _linha_do_erro(erro):
    if isinstance(erro, SyntaxError):
        return erro.lineno
    linha = None
    for quadro in traceback.extract_tb(erro.__traceback__):
        if quadro.filename == ARQUIVO_DO_ALUNO:
            linha = quadro.lineno
    return linha


def _sugestao_de_nome(erro, escopo):
    """Para um nome digitado errado, sugere o nome parecido que existe no programa."""
    if not isinstance(erro, NameError) or isinstance(erro, UnboundLocalError) or not getattr(erro, "name", None):
        return ""
    candidatos = [nome for nome in escopo if not nome.startswith("__")]
    parecidos = difflib.get_close_matches(erro.name, candidatos, n=1)
    return f" Você quis dizer `{parecidos[0]}`?" if parecidos else ""


def _input_com_entradas(entradas, saida):
    fila = list(entradas)

    def input_falso(mensagem=""):
        saida.write(str(mensagem))
        if not fila:
            raise EOFError("O programa pediu mais entradas do que foram digitadas.")
        valor = fila.pop(0)
        saida.write(valor + "\n")
        return valor

    return input_falso


def _deterministico(arvore):
    """O random usa a semente; o relógio e o secrets mudam a cada execução."""
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [apelido.name for apelido in no.names]
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes = [no.module]
        else:
            continue
        if any(nome.partition(".")[0] in MODULOS_NAO_DETERMINISTICOS for nome in nomes):
            return False
    return True


def _erro_de_limite(limite, passos):
    return {
        "tipo": "LimiteDePassos",
        "linha": passos[-1]["linha"] if passos else None,
        "mensagem": f"O programa passou de {limite} passos e foi parado.",
        "detalhe": "Será que tem um laço que nunca termina?",
        "original": "",
    }


def _esperar(segundos):
    """time.sleep sem esperar: o passo a passo já mostra o tempo passando, e a página tem só 5 s."""
    if not isinstance(segundos, (int, float)):
        raise TypeError(f"'{type(segundos).__name__}' object cannot be interpreted as an integer")
    if segundos < 0:
        raise ValueError("sleep length must be non-negative")


@contextlib.contextmanager
def _sem_espera():
    original = time.sleep
    time.sleep = _esperar
    try:
        yield
    finally:
        time.sleep = original


def executar_isolado(compilado, escopo, rastreador, ao_errar, coletar=True):
    """Roda o código do aluno com `rastreador` ligado e devolve ao_errar(exceção), ou None.

    Tudo acontece dentro do isolamento (seguranca.isolar), com time.sleep sem
    espera: inclusive tratar o erro e soltar os objetos do aluno. Assim, um
    __del__ do aluno não roda depois, fora da caixa. No fim, o rastreador e o
    perfil do Python voltam a ser os de antes, mesmo que o aluno tenha trocado.
    """
    tracer_anterior = sys.gettrace()
    perfil_anterior = sys.getprofile()
    erro = None
    with isolar(), _sem_espera():
        try:
            sys.settrace(rastreador)
            try:
                exec(compilado, escopo)
            finally:
                sys.settrace(tracer_anterior)
                sys.setprofile(perfil_anterior)
        except BaseException as e:  # o erro do aluno é parte do resultado, não uma falha do motor
            erro = ao_errar(e)
        finally:
            escopo.clear()
            if coletar:
                # Inteira: um ciclo do aluno que já passou por uma coleta está na geração velha.
                # O worker congela (gc.freeze) o que existe depois de carregar o motor, então custa pouco.
                gc.collect()
            sys.settrace(tracer_anterior)
            sys.setprofile(perfil_anterior)
    return erro


def rastrear(codigo, entradas=(), limite=LIMITE_PADRAO, semente=None):
    """Executa `codigo` e devolve o Resultado (contrato v2).

    `entradas` são os valores que o aluno digitou antes para os input() do programa.
    `semente` alimenta o random do aluno; sem ela, uma nova é sorteada e devolvida,
    para que a mesma execução possa ser repetida.
    """
    if semente is None:
        semente = random.SystemRandom().randrange(2**31)
    saida = io.StringIO()
    meus_builtins = dict(vars(builtins))
    meus_builtins["input"] = _input_com_entradas(entradas, saida)
    meus_builtins["print"] = lambda *args, **kwargs: print(*args, **{"file": saida, **kwargs})
    escopo = {"__name__": "__main__", "__builtins__": meus_builtins}

    resultado = {
        "versao": VERSAO,
        "semente": semente,
        "deterministico": True,
        "passos": [],
        "saida": "",
        "erro": None,
        "estrutura": {"comandos": []},
    }
    gravador = None
    erro = None

    def ao_errar(e):
        # exit() só encerra o programa; o limite é tratado logo abaixo (o aluno pode tê-lo engolido).
        if isinstance(e, (SystemExit, LimiteDePassos)):
            return None
        mensagem, detalhe = traduzir(e)
        return {
            "tipo": type(e).__name__,
            "linha": _linha_do_erro(e),
            "mensagem": mensagem + _sugestao_de_nome(e, escopo),
            "detalhe": detalhe,
            "original": "".join(traceback.format_exception_only(type(e), e)).strip(),
        }

    estado_do_random = random.getstate()
    try:
        arvore = ast.parse(codigo, ARQUIVO_DO_ALUNO)
        compilado = compile(arvore, ARQUIVO_DO_ALUNO, "exec")
        analise = Analise(codigo, arvore)
        resultado["estrutura"]["comandos"] = analise.comandos
        resultado["deterministico"] = _deterministico(arvore)
        gravador = _Gravador(analise, limite, saida)
        random.seed(semente)
        erro = executar_isolado(compilado, escopo, gravador.chamada, ao_errar)
    except Exception as e:  # o programa nem começou: erro de sintaxe, byte nulo, aninhamento demais
        erro = ao_errar(e)
    finally:
        random.setstate(estado_do_random)
        esquecer_textos()

    if gravador is not None:
        if gravador.estourou:
            erro = _erro_de_limite(limite, gravador.passos)
        resultado["passos"] = gravador.passos
        _ligar_quadros(gravador.passos)
    resultado["saida"] = saida.getvalue()
    resultado["erro"] = erro
    return resultado


def retornos_do_passo(passo):
    """Os returns anotados num passo, do primeiro quadro que terminou ao último."""
    if "retornos" in passo:
        return passo["retornos"]
    return [passo["retorno"]] if "retorno" in passo else []


def _ligar_quadros(passos):
    """proximo_no_quadro: o próximo passo do mesmo quadro (efeito e decisão olham para ele, não para i+1)."""
    seguinte = {}
    for passo in reversed(passos):
        passo["proximo_no_quadro"] = seguinte.get(passo["quadro"])
        seguinte[passo["quadro"]] = passo["i"]


def calcular_voltas(resultado):
    """Para cada passo, a volta do laço mais interno em que ele está, ou None.

    volta = {laco, n, total, total_visivel_desde, saindo}. O cabeçalho seguido
    de um passo do corpo (no mesmo quadro) começa uma volta nova; seguido de um
    passo de fora, é a saída (`saindo`). Chegar ao cabeçalho vindo de fora é uma
    nova entrada no laço, que recomeça a contagem. Um `break` sai sem passar
    pelo cabeçalho: a saída é o primeiro passo do quadro fora do corpo.
    `total` só pode ser mostrado a partir do passo `total_visivel_desde`.
    """
    passos = resultado["passos"]
    comandos = resultado["estrutura"]["comandos"]
    pilhas = {}
    entradas = []
    marcas = [None] * len(passos)
    fim_do_quadro = {}
    for passo in passos:
        for retorno in retornos_do_passo(passo):
            fim_do_quadro.setdefault(retorno.get("quadro"), passo["i"])

    for passo in passos:
        pilha = pilhas.setdefault(passo["quadro"], [])
        comando = passo["comando"]
        while pilha and not _dentro_do_laco(comandos, pilha[-1]["laco"], comando):
            pilha.pop()["saida"] = passo["i"]
        if comando is not None and comandos[comando]["tipo"] in LACOS:
            if not pilha or pilha[-1]["laco"] != comando:
                pilha.append({"laco": comando, "n": 0, "saida": None, "quadro": passo["quadro"], "ultimo": None})
                entradas.append(pilha[-1])
            entrada = pilha[-1]
            seguinte = passo["proximo_no_quadro"]
            proximo_comando = passos[seguinte]["comando"] if seguinte is not None else None
            continua = seguinte is not None and (
                proximo_comando == comando or _dentro_do_laco(comandos, comando, proximo_comando)
            )
            if continua:
                entrada["n"] += 1
            marcas[passo["i"]] = (entrada, entrada["n"], not continua)
        elif pilha:
            entrada = pilha[-1]
            marcas[passo["i"]] = (entrada, entrada["n"], False)
        else:
            continue
        entrada["ultimo"] = passo["i"]

    for entrada in entradas:
        if entrada["saida"] is not None:
            entrada["total"], entrada["desde"] = entrada["n"], entrada["saida"]
        elif entrada["quadro"] in fim_do_quadro:
            entrada["total"], entrada["desde"] = entrada["n"], fim_do_quadro[entrada["quadro"]]
        elif resultado["erro"] is None and entrada["ultimo"] + 1 < len(passos):
            entrada["total"], entrada["desde"] = entrada["n"], entrada["ultimo"] + 1
        else:
            entrada["total"], entrada["desde"] = None, None  # o programa parou dentro do laço

    return [
        None
        if marca is None
        else {
            "laco": marca[0]["laco"],
            "n": marca[1],
            "total": marca[0]["total"],
            "total_visivel_desde": marca[0]["desde"],
            "saindo": marca[2],
        }
        for marca in marcas
    ]


def _dentro_do_laco(comandos, laco, comando):
    if comando is None:
        return False
    if comando == laco:
        return True
    corpo = comandos[laco]["corpo"]
    inicio = comandos[comando]["linhas"][0]
    return bool(corpo) and corpo[0] <= inicio <= corpo[1] and not comandos[laco]["corpo_mesma_linha"]
