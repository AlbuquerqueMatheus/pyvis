"""Diário da atividade: eventos pseudonimizados, resumo do aluno e sorteio do estudo.

Cada interação relevante vira um Evento, num formato inspirado no ProgSnap2
(Price et al., 2020). O diário fica no aparelho e só sai na entrega ao
professor. Por isso validar_evento() é uma lista branca: cada campo tem tipo
e formato fechados e nenhum aceita texto livre, então o evento nunca leva
código, entradas, texto digitado pelo aluno nem o apelido. A resposta de um
palpite livre só entra quando não tem letras (um número, "11"); o resto do
palpite fica registrado em certa e concepcao.

Regras do resumo, simples para explicar a aluno, pais e banca:
- um palpite certo mostra que o aluno entendeu cada ideia testada no ponto
  (as ideias cujo modelo dava outra resposta ali);
- um palpite errado que uma ideia explica é sinal para revisar essa ideia;
- vale o palpite mais recente: quem errou e depois acertou já entendeu.
O resumo mostra a regra da ideia (regra_para_aluno), nunca o id.
"""

import builtins
import hashlib
import math
import re
import time

from . import apelido as apelidos
from .privacidade import DIGITOS_DE_DOCUMENTO, forma_canonica

VERSAO = 1
TIPOS = ("Session.Start", "Run.Program", "Step", "Prediction", "Prediction.Skip", "Feedback.Layer", "Error")
MODOS = ("assistir", "prever", "estudo")
CONDICOES = ("prever", "assistir")
FORMATOS = ("alternativas", "livre")
TIPOS_ESCOLHIDOS = ("numero", "texto")

TITULO_ENTENDIDAS = "Ideias que você já entendeu"
TITULO_REVISAR = "Ideias para revisar"

COMUNS = ("v", "ts", "sala", "sujeito", "atividade", "programa", "condicao", "tipo", "code_hash")
# No começo da sessão ainda não há programa: esses três podem vir null.
SEM_PROGRAMA_NO_INICIO = ("programa", "condicao", "code_hash")
EXTRAS = {
    "Session.Start": (),
    "Run.Program": ("ms",),
    "Step": ("passo", "ms"),
    "Prediction": ("ponto", "formato", "resposta", "certa", "concepcao", "testadas", "ms"),
    "Prediction.Skip": ("ponto", "formato", "ms"),
    "Feedback.Layer": ("ponto", "camada", "concepcao"),
    "Error": ("erro",),
}
OBRIGATORIOS = {
    "Prediction": ("ponto", "formato", "resposta", "certa"),
    "Prediction.Skip": ("ponto",),
    "Feedback.Layer": ("ponto", "camada"),
}
# Palpites e o Detetive só existem em Prever.
SO_EM_PREVER = ("Prediction", "Prediction.Skip", "Feedback.Layer")

# Erros do Python e do PyVis; uma classe criada pelo aluno vira "Outro" (o nome dela é texto dele).
ERROS = frozenset(
    nome
    for nome, valor in vars(builtins).items()
    if isinstance(valor, type) and issubclass(valor, BaseException) and not nome.startswith("_")
) | {"LimiteDePassos", "TempoEsgotado", "Outro"}

TAMANHO_DO_TEXTO = 60
ITENS_DA_LISTA = 20

_SALA = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{1,15}")  # '8A', 'TURMA-8A'...
_SUJEITO = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_ATIVIDADE = re.compile(r"[A-Za-z0-9_-]{1,32}")
_CODE_HASH = re.compile(r"[0-9a-f]{16}")
_PONTO = re.compile(r"p[1-9][0-9]{0,2}")
_ALTERNATIVA = re.compile(r"(?=.)[A-Za-z]{0,2}[0-9]{0,3}(?:[A-Za-z][0-9]{1,3})?")  # 'a1', 'B', 'p3a2'
_CONCEPCAO = re.compile(r"C[0-9]{2}")
_DOCUMENTO = re.compile(r"\d{%d}" % DIGITOS_DE_DOCUMENTO)


def hash_do_codigo(codigo):
    """O code_hash: sha256 do código higienizado e normalizado, em 16 dígitos hexadecimais."""
    forma = forma_canonica(codigo)
    return hashlib.sha256(forma.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def tipo_de_erro(nome):
    return nome if nome in ERROS else "Outro"


def registravel(valor):
    """Se o valor pode ir em resposta.valor_normalizado: número, verdadeiro/falso ou texto sem letras."""
    return _registravel(valor, 0)


def _registravel(valor, profundidade):
    if valor is None or isinstance(valor, bool):
        return True
    # Um número de 8 dígitos ou mais pode ser telefone ou documento.
    if isinstance(valor, int):
        return abs(valor) < 10 ** (DIGITOS_DE_DOCUMENTO - 1)
    if isinstance(valor, float):
        return math.isfinite(valor) and abs(valor) < 10 ** (DIGITOS_DE_DOCUMENTO - 1)
    if isinstance(valor, str):
        return (
            len(valor) <= TAMANHO_DO_TEXTO
            and not any(c.isalpha() for c in valor)
            and not _DOCUMENTO.search(valor)
        )
    if isinstance(valor, list) and profundidade < 2:
        return len(valor) <= ITENS_DA_LISTA and all(_registravel(item, profundidade + 1) for item in valor)
    return False


def _inteiro(valor, minimo, maximo):
    return type(valor) is int and minimo <= valor <= maximo


def _casa(padrao, valor):
    return isinstance(valor, str) and padrao.fullmatch(valor) is not None


def _escolha(opcoes, valor):
    return isinstance(valor, str) and valor in opcoes


_VALIDADORES = {
    "v": lambda valor: _inteiro(valor, VERSAO, VERSAO),
    "ts": lambda valor: _inteiro(valor, 0, 2**53 - 1),  # milissegundos desde 1970, como Date.now()
    "sala": lambda valor: _casa(_SALA, valor),
    "sujeito": lambda valor: _casa(_SUJEITO, valor),
    "atividade": lambda valor: _casa(_ATIVIDADE, valor),
    "programa": lambda valor: _inteiro(valor, 0, 99),
    "condicao": lambda valor: _escolha(CONDICOES, valor),
    "tipo": lambda valor: _escolha(TIPOS, valor),
    "code_hash": lambda valor: _casa(_CODE_HASH, valor),
    "ponto": lambda valor: _casa(_PONTO, valor),
    "formato": lambda valor: _escolha(FORMATOS, valor),
    "certa": lambda valor: isinstance(valor, bool),
    "concepcao": lambda valor: valor is None or _casa(_CONCEPCAO, valor),
    "testadas": lambda valor: (
        isinstance(valor, list)
        and len(valor) <= 10
        and all(_casa(_CONCEPCAO, item) for item in valor)
        and len(set(valor)) == len(valor)
    ),
    "camada": lambda valor: _inteiro(valor, 1, 3),
    "ms": lambda valor: _inteiro(valor, 0, 2**31 - 1),
    "passo": lambda valor: _inteiro(valor, 0, 99_999),
    "erro": lambda valor: _escolha(ERROS, valor),
}


def _nome_do_campo(campo):
    # O motivo pode ir para um log: só repete nomes que parecem nome de campo.
    return campo if isinstance(campo, str) and campo.isidentifier() and len(campo) <= 30 else "(nome escondido)"


def validar_evento(evento):
    """Lista de problemas do evento; vazia quando ele pode ser guardado e entregue.

    Os motivos citam só nomes de campo, nunca os valores, que podem ser dados do aluno.
    """
    if not isinstance(evento, dict):
        return ["o evento precisa ser um objeto"]
    tipo = evento.get("tipo")
    if not _escolha(TIPOS, tipo):
        return ["tipo desconhecido"]

    problemas = []
    permitidos = set(COMUNS) | set(EXTRAS[tipo])
    for campo in evento:
        if campo not in permitidos:
            problemas.append(f"campo não permitido em {tipo}: {_nome_do_campo(campo)}")
    for campo in COMUNS + OBRIGATORIOS.get(tipo, ()):
        if campo not in evento:
            problemas.append(f"falta o campo {campo}")

    for campo, valor in evento.items():
        if campo not in permitidos or campo == "resposta":
            continue
        if valor is None and tipo == "Session.Start" and campo in SEM_PROGRAMA_NO_INICIO:
            continue
        if not _VALIDADORES[campo](valor):
            problemas.append(f"valor inválido em {campo}")

    if "resposta" in evento and "resposta" in permitidos:
        problemas += _problemas_da_resposta(evento["resposta"], evento.get("formato"))
    if evento.get("certa") is True and evento.get("concepcao") is not None:
        problemas.append("concepcao só vale para palpite errado (o certo usa testadas)")
    if tipo in SO_EM_PREVER and evento.get("condicao") == "assistir":
        problemas.append(f"{tipo} só acontece na condição prever")
    return problemas


def _problemas_da_resposta(resposta, formato):
    if not isinstance(resposta, dict) or not resposta:
        return ["resposta precisa ser um objeto com alternativa, valor_normalizado ou tipo_escolhido"]
    problemas = []
    for campo in resposta:
        if campo not in ("alternativa", "valor_normalizado", "tipo_escolhido"):
            problemas.append(f"campo não permitido em resposta: {_nome_do_campo(campo)}")
    if "alternativa" in resposta:
        alternativa = resposta["alternativa"]
        if not (_inteiro(alternativa, 0, 99) or _casa(_ALTERNATIVA, alternativa)):
            problemas.append("valor inválido em resposta.alternativa")
    if "tipo_escolhido" in resposta and not _escolha(TIPOS_ESCOLHIDOS, resposta["tipo_escolhido"]):
        problemas.append("valor inválido em resposta.tipo_escolhido")
    if "valor_normalizado" in resposta and not registravel(resposta["valor_normalizado"]):
        problemas.append("resposta.valor_normalizado não pode sair do aparelho (texto com letras ou número longo)")
    # Na múltipla escolha basta o id da alternativa: o texto dela pode vir do código do aluno.
    if formato == "alternativas" and set(resposta) != {"alternativa"}:
        problemas.append("na múltipla escolha a resposta é só {alternativa}")
    if formato == "livre" and "alternativa" in resposta:
        problemas.append("na resposta livre não há alternativa")
    return problemas


def montar_evento(tipo, contexto, ts=None, **campos):
    """Monta um evento válido a partir do contexto do programa, ou levanta ValueError.

    Do contexto saem só sala, sujeito, atividade, programa, condicao e code_hash
    (um apelido que venha junto fica para trás). Um valor_normalizado que não
    pode sair do aparelho é tirado da resposta, e o nome de um erro criado pelo
    aluno vira "Outro". Campos extras com valor None são omitidos.
    """
    evento = {"v": VERSAO, "ts": int(time.time() * 1000) if ts is None else ts}
    for campo in ("sala", "sujeito", "atividade", "programa", "condicao", "code_hash"):
        evento[campo] = contexto.get(campo)
    evento["tipo"] = tipo
    for campo, valor in campos.items():
        if campo in COMUNS:
            raise ValueError(f"{campo} vem do contexto, não dos campos extras")
        if valor is not None:
            evento[campo] = valor
    resposta = evento.get("resposta")
    if isinstance(resposta, dict) and not registravel(resposta.get("valor_normalizado")):
        evento["resposta"] = {chave: valor for chave, valor in resposta.items() if chave != "valor_normalizado"}
    if tipo == "Error" and "erro" in evento:
        evento["erro"] = tipo_de_erro(evento["erro"])
    problemas = validar_evento(evento)
    if problemas:
        raise ValueError("; ".join(problemas))
    return evento


def montar_entrega(apelido, eventos):
    """O arquivo 'Entregar ao professor': o apelido fica fora dos eventos, num envelope.

    Levanta ValueError se o apelido não for da lista ou se algum evento for inválido.
    """
    if not apelidos.validar(apelido):
        raise ValueError("o apelido precisa ser um dos gerados pelo PyVis")
    for posicao, evento in enumerate(eventos):
        problemas = validar_evento(evento)
        if problemas:
            raise ValueError(f"evento {posicao}: " + "; ".join(problemas))
    # Num aparelho dividido, a entrega leva só os eventos de quem está entregando.
    if len({evento["sujeito"] for evento in eventos}) > 1:
        raise ValueError("a entrega mistura eventos de mais de um aluno")
    return {"v": VERSAO, "apelido": apelido, "eventos": list(eventos)}


def resumo(eventos, atividade=None, regras=None):
    """'Meu resumo': as ideias entendidas e as para revisar, e só depois os números.

    Devolve {entendidas: [regra], revisar: [regra], numeros: {programas, palpites,
    pulados, explicacoes}}. As regras são frases para o aluno, na ordem em que
    cada ideia apareceu. `regras` mapeia id -> frase (o padrão é o catálogo de
    concepcoes); ideia sem frase não aparece, para nunca mostrar um id.
    """
    if regras is None:
        # Importado aqui: o servidor da Onda 3 valida eventos sem carregar os modelos.
        from .concepcoes import POR_ID

        regras = {cid: concepcao["regra_para_aluno"] for cid, concepcao in POR_ID.items()}

    validos = [
        evento
        for evento in eventos
        if not validar_evento(evento) and (atividade is None or evento["atividade"] == atividade)
    ]
    validos.sort(key=lambda evento: evento["ts"])  # sort é estável: empates ficam na ordem recebida

    # id -> o palpite mais recente sobre a ideia foi certo? O dict guarda a ordem
    # da primeira vez que cada ideia apareceu.
    ultima = {}
    for evento in validos:
        if evento["tipo"] != "Prediction":
            continue
        if evento["certa"]:
            for cid in evento.get("testadas", ()):
                ultima[cid] = True
        elif evento.get("concepcao"):
            ultima[evento["concepcao"]] = False

    def contar(tipo):
        return sum(evento["tipo"] == tipo for evento in validos)

    return {
        "entendidas": [regras[cid] for cid, certo in ultima.items() if certo and cid in regras],
        "revisar": [regras[cid] for cid, certo in ultima.items() if not certo and cid in regras],
        "numeros": {
            "programas": len({evento["programa"] for evento in validos if evento["programa"] is not None}),
            "palpites": contar("Prediction"),
            "pulados": contar("Prediction.Skip"),
            "explicacoes": contar("Feedback.Layer"),
        },
    }


def _sorteio(*partes):
    return hashlib.sha256("|".join(str(parte) for parte in partes).encode("utf-8", "surrogatepass")).hexdigest()


def sortear_condicoes(sujeito, atividade):
    """A condição de cada programa da atividade, na ordem dos programas.

    No modo 'estudo', metade dos programas fica em 'prever' e metade em
    'assistir'; com número ímpar, o do meio é sorteado. Quais programas caem em
    cada condição muda de aluno para aluno, mas é sempre o mesmo para o mesmo
    aluno, atividade e semente. Nos outros modos, todos seguem o modo.
    """
    programas = atividade.get("programas")
    if not isinstance(programas, list) or not programas:
        raise ValueError("a atividade precisa de pelo menos um programa")
    modo = atividade.get("modo")
    if not _escolha(MODOS, modo):
        raise ValueError("modo desconhecido")
    if modo != "estudo":
        return [modo] * len(programas)

    base = (atividade.get("semente"), atividade.get("id"), sujeito)
    ordem = sorted(range(len(programas)), key=lambda k: _sorteio(*base, k))
    metade = len(programas) // 2
    condicoes = [None] * len(programas)
    for posicao, k in enumerate(ordem):
        if posicao < metade:
            condicoes[k] = "prever"
        elif posicao >= len(programas) - metade:
            condicoes[k] = "assistir"
        else:
            condicoes[k] = "prever" if int(_sorteio(*base, "meio")[0], 16) < 8 else "assistir"
    return condicoes
