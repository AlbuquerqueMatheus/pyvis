"""Executa o código do aluno uma vez e grava uma "foto" do estado a cada linha.

A interface depois só navega por essas fotos, então avançar e voltar
um passo é instantâneo. É a mesma ideia do Python Tutor (Guo, 2013).
"""

import builtins
import io
import sys
import traceback

from .erros import traduzir
from .valores import variaveis_visiveis

ARQUIVO_DO_ALUNO = "<aluno>"
LIMITE_PADRAO = 1000


class LimiteDePassos(Exception):
    pass


class _Gravador:
    def __init__(self, limite, saida):
        self.limite = limite
        self.saida = saida
        self.passos = []
        self.erro_no_modulo = False

    def gravar(self, frame, evento):
        passo = {
            "linha": frame.f_lineno,
            "evento": evento,
            "globais": variaveis_visiveis(frame.f_globals),
            "funcao": None,
            "locais": {},
            "saida": self.saida.getvalue(),
        }
        if frame.f_code.co_name != "<module>":
            passo["funcao"] = frame.f_code.co_name
            passo["locais"] = variaveis_visiveis(frame.f_locals)
        self.passos.append(passo)
        if len(self.passos) > self.limite:
            raise LimiteDePassos()

    def tracer(self, frame, evento, arg):
        if frame.f_code.co_filename != ARQUIVO_DO_ALUNO:
            return None
        no_modulo = frame.f_code.co_name == "<module>"
        if evento == "line":
            self.erro_no_modulo = False
            self.gravar(frame, "linha")
        elif evento == "exception" and no_modulo:
            self.erro_no_modulo = True
        elif evento == "return" and no_modulo and not self.erro_no_modulo:
            self.gravar(frame, "fim")
        return self.tracer


def _linha_do_erro(erro):
    if isinstance(erro, SyntaxError):
        return erro.lineno
    linha = None
    for quadro in traceback.extract_tb(erro.__traceback__):
        if quadro.filename == ARQUIVO_DO_ALUNO:
            linha = quadro.lineno
    return linha


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


def rastrear(codigo, entradas=(), limite=LIMITE_PADRAO):
    """Executa `codigo` e devolve os passos gravados, a saída e o erro (se houver).

    `entradas` são os valores que o aluno digitou antes para os input() do programa.
    """
    saida = io.StringIO()
    gravador = _Gravador(limite, saida)
    meus_builtins = dict(vars(builtins))
    meus_builtins["input"] = _input_com_entradas(entradas, saida)
    meus_builtins["print"] = lambda *args, **kwargs: print(*args, **{"file": saida, **kwargs})
    escopo = {"__name__": "__main__", "__builtins__": meus_builtins}

    erro = None
    tracer_anterior = sys.gettrace()
    try:
        compilado = compile(codigo, ARQUIVO_DO_ALUNO, "exec")
        sys.settrace(gravador.tracer)
        try:
            exec(compilado, escopo)
        finally:
            sys.settrace(tracer_anterior)
    except SystemExit:
        pass  # exit() no código do aluno só encerra o programa
    except LimiteDePassos:
        erro = {
            "tipo": "LimiteDePassos",
            "linha": gravador.passos[-1]["linha"] if gravador.passos else None,
            "mensagem": (
                f"O programa passou de {limite} passos e foi parado. "
                "Será que tem um loop que nunca termina?"
            ),
            "original": "",
        }
    except Exception as e:  # o erro do aluno é parte do resultado, não uma falha do motor
        erro = {
            "tipo": type(e).__name__,
            "linha": _linha_do_erro(e),
            "mensagem": traduzir(e),
            "original": "".join(traceback.format_exception_only(type(e), e)).strip(),
        }

    return {"passos": gravador.passos, "saida": saida.getvalue(), "erro": erro}
