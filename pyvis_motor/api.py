"""O que o worker chama: entradas e saídas que viram JSON sem conversão.

O worker manda {acao, dados} e recebe {ok, resultado} ou {ok: false, erro}.
O caminho mais simples é executar_json(texto), que lê e devolve texto JSON:
nada de objetos do Pyodide atravessando a ponte. Cada ação também é uma
função comum, com os mesmos nomes de parâmetro dos `dados`.

O último rastro fica aqui, no Python (ultimo["resultado"]): a atividade e a
correção de um palpite usam o rastro que já existe, sem a página reenviar
nada. Rodar de novo apaga a atividade anterior.
"""

import json

from . import apelido as apelidos
from . import privacidade, registro
from .anotar import anotar
from .narrador import narrar_resultado
from .previsao import corrigir as _corrigir
from .previsao import montar_atividade
from .rastreador import LIMITE_PADRAO
from .rastreador import rastrear as _rastrear

LIMITE_MAXIMO = 10_000

ultimo = {"codigo": None, "entradas": [], "resultado": None, "atividade": None, "pontos": {}}


def _texto(valor, nome):
    if not isinstance(valor, str):
        raise ValueError(f"{nome} precisa ser texto")
    return valor


def rastrear(codigo, entradas=(), semente=None, limite=None):
    """Executa o código e devolve o Resultado v2 já anotado e narrado.

    `limite` é o número máximo de passos (300 em aparelhos fracos, 1000 por
    padrão). `semente` repete os sorteios de uma execução anterior.
    """
    codigo = _texto(codigo, "codigo")
    entradas = [_texto(entrada, "cada entrada") for entrada in (entradas or ())]
    if limite is None:
        limite = LIMITE_PADRAO
    if type(limite) is not int or not 1 <= limite <= LIMITE_MAXIMO:
        raise ValueError(f"limite precisa ser um inteiro de 1 a {LIMITE_MAXIMO}")
    if semente is not None and type(semente) is not int:
        raise ValueError("semente precisa ser um inteiro")
    resultado = _rastrear(codigo, entradas, limite, semente)
    try:
        narrar_resultado(resultado, codigo)
    except Exception:  # um defeito do narrador não pode impedir o aluno de ver a execução
        _narracao_de_reserva(resultado)
    ultimo.update(codigo=codigo, entradas=entradas, resultado=resultado, atividade=None, pontos={})
    return resultado


def _narracao_de_reserva(resultado):
    passos = resultado["passos"]
    if passos and "efeito" not in passos[0]:
        anotar(resultado)
    for comando in resultado["estrutura"]["comandos"]:
        comando.setdefault("leitura", {"literal": "", "traduzida": "", "traduzida_depende_de": []})
    for passo in passos:
        frase = "O programa terminou." if passo["evento"] == "fim" else f"Roda a linha {passo['linha']}."
        partes = [{"texto": frase, "campos": []}]
        passo["narracao"] = {"curta": frase, "longa": frase, "partes_curta": partes, "partes_longa": list(partes)}


def preparar_atividade(config=None):
    """A Atividade (previsao.preparar_atividade) do último rastro.

    config = {modo, formato, max_pontos, semente, palpite_inicial, orcamento_ms}.
    Os campos depende_de_por_passo e traduzida_depende_de devem ser aplicados à
    cópia do Resultado que a página já tem.
    """
    if ultimo["resultado"] is None:
        raise ValueError("rode o programa antes de preparar a atividade")
    if config is not None and not isinstance(config, dict):
        raise ValueError("config precisa ser um objeto")
    completa = montar_atividade(ultimo["resultado"], ultimo["codigo"], ultimo["entradas"], config)
    ultimo.update(atividade=completa["atividade"], pontos=completa["pontos"])
    return completa["atividade"]


def corrigir(ponto_id, resposta):
    """Correcao de um palpite do último ponto preparado (previsao.corrigir)."""
    ponto = ultimo["pontos"].get(ponto_id)
    if ponto is None:
        raise ValueError("ponto desconhecido: prepare a atividade antes de corrigir")
    return _corrigir(ponto, resposta)


# --- Sala, apelido e diário (2.5) ---------------------------------------------


def gerar_apelido(semente=None):
    """Apelido como 'Tucano Azul 7'; com o sujeito como semente, o mesmo aluno ganha sempre o mesmo."""
    return apelidos.gerar(semente)


def sugerir_apelidos(semente, quantidade=4):
    return apelidos.sugestoes(semente, quantidade)


def validar_apelido(apelido):
    return apelidos.validar(apelido)


def code_hash(codigo):
    """O code_hash do diário: o código higienizado e normalizado, em 16 dígitos hexadecimais."""
    return registro.hash_do_codigo(_texto(codigo, "codigo"))


def higienizar(codigo):
    """O código sem comentários e com <texto> no lugar dos textos: obrigatório antes de sair do aparelho."""
    return privacidade.higienizar(_texto(codigo, "codigo"))


def validar_evento(evento):
    return registro.validar_evento(evento)


def montar_evento(tipo, contexto, ts=None, campos=None):
    return registro.montar_evento(tipo, contexto, ts, **(campos or {}))


def resumo(eventos, atividade=None):
    return registro.resumo(eventos, atividade)


def sortear_condicoes(sujeito, atividade):
    return registro.sortear_condicoes(sujeito, atividade)


def montar_entrega(apelido, eventos):
    return registro.montar_entrega(apelido, eventos)


ACOES = {
    "rastrear": rastrear,
    "preparar_atividade": preparar_atividade,
    "corrigir": corrigir,
    "gerar_apelido": gerar_apelido,
    "sugerir_apelidos": sugerir_apelidos,
    "validar_apelido": validar_apelido,
    "code_hash": code_hash,
    "higienizar": higienizar,
    "validar_evento": validar_evento,
    "montar_evento": montar_evento,
    "resumo": resumo,
    "sortear_condicoes": sortear_condicoes,
    "montar_entrega": montar_entrega,
}


def executar(acao, dados=None):
    """Chama a ação com os `dados` como parâmetros nomeados."""
    funcao = ACOES.get(acao)
    if funcao is None:
        raise ValueError(f"ação desconhecida: {acao}")
    if dados is None:
        dados = {}
    if not isinstance(dados, dict):
        raise ValueError("dados precisa ser um objeto")
    return funcao(**dados)


def executar_json(pedido):
    """Pedido JSON {id?, acao, dados} -> resposta JSON {id?, ok, resultado} ou {id?, ok: false, erro}.

    Erros do motor viram {ok: false}; o erro no código do aluno não é um
    deles: ele vem dentro do Resultado.
    """
    identificador = None
    try:
        lido = json.loads(pedido)
        if not isinstance(lido, dict):
            raise ValueError("o pedido precisa ser um objeto")
        if isinstance(lido.get("id"), (str, int)):
            identificador = lido["id"]
        resposta = {"ok": True, "resultado": executar(lido.get("acao"), lido.get("dados"))}
        if identificador is not None:
            resposta["id"] = identificador
        return json.dumps(resposta, allow_nan=False)
    except Exception as erro:  # a página precisa de uma resposta, mesmo quando o motor falha
        resposta = {"ok": False, "erro": _mensagem(erro)}
        if identificador is not None:
            resposta["id"] = identificador
        return json.dumps(resposta)


def _mensagem(erro):
    if isinstance(erro, json.JSONDecodeError):
        return "pedido não é JSON"
    if isinstance(erro, (ValueError, TypeError)):
        return f"{type(erro).__name__}: {erro}"
    return type(erro).__name__
