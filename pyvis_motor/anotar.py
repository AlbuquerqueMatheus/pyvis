"""Anota cada passo com o que o comando fez: efeito, decisão e volta do laço.

O passo i guarda o estado ANTES do comando. O efeito sai da comparação com
o próximo passo do mesmo quadro (proximo_no_quadro), nunca com i + 1: entre
os dois podem estar os passos de uma função que o comando chamou.

Parte do que se anota vem do futuro do rastro (o ramo que o if tomou, o total
de voltas). Quando cada campo pode aparecer é decidido em revelacao.py.
"""

from .rastreador import calcular_voltas, retornos_do_passo

DECISOES = frozenset({"if", "elif", "while"})


def anotar(resultado):
    """Acrescenta `efeito`, `decisao`, `volta` e `desfecho_visivel_desde` a cada passo.

    Muda os passos no lugar e devolve o resultado. `decisao` só existe nos
    cabeçalhos de if, elif e while (None nos outros passos) e substitui o
    `_decisao_bruta` do rastreador. `volta` é None fora de laços. O `retorno`
    dos passos fica como está. Rodar de novo não muda nada.
    """
    passos = resultado["passos"]
    comandos = resultado["estrutura"]["comandos"]
    retornos = passos_de_retorno(passos)
    voltas = calcular_voltas(resultado)
    parou_no_limite = bool(resultado.get("erro")) and resultado["erro"]["tipo"] == "LimiteDePassos"
    for passo, volta in zip(passos, voltas):
        # No limite, o último passo foi gravado e o comando dele nem chegou a rodar.
        nao_rodou = parou_no_limite and passo is passos[-1]
        depois, parcial = estado_depois(passo, passos, retornos)
        if nao_rodou:
            depois = None
        passo["efeito"] = _efeito(passo, depois, parcial) if depois is not None else None
        bruta = passo.pop("_decisao_bruta", None)
        if bruta is not None:
            passo["decisao"] = _decisao(passo, bruta, passos, comandos, retornos, nao_rodou)
        else:
            passo.setdefault("decisao", None)
        passo["volta"] = volta
        passo["desfecho_visivel_desde"] = _desfecho_visivel_desde(passo, passos, retornos)
    return resultado


def _desfecho_visivel_desde(passo, passos, retornos):
    """A partir de que passo o desfecho do comando (efeito, valor da decisão) pode aparecer.

    Normalmente no próprio passo, junto com a linha destacada. Se o comando
    chamou funções do aluno, só depois que elas terminam: antes disso, o
    resultado entregaria o que acontece dentro delas.
    """
    seguinte = passo["i"] + 1
    if seguinte < len(passos) and passos[seguinte]["profundidade"] > passo["profundidade"]:
        return passo_depois(passo, retornos)[0]
    return passo["i"]


def passos_de_retorno(passos):
    """quadro -> índice do passo que traz o retorno dele (o primeiro passo depois do return)."""
    retornos = {}
    for passo in passos:
        for retorno in retornos_do_passo(passo):
            retornos.setdefault(retorno["quadro"], passo["i"])
    return retornos


def retorno_do_quadro(passo, quadro):
    """O retorno do `quadro` entre os que o passo recebeu, ou None."""
    return next((r for r in retornos_do_passo(passo) if r["quadro"] == quadro), None)


def estado_depois(passo, passos, retornos):
    """(estado logo depois do comando, parcial) ou (None, False). Estado = {globais, locais, saida}.

    Fora do último comando de uma função, é o próximo passo do quadro. No
    último, o passo que recebe o retorno já traz o que o comando de quem
    chamou fez depois (outro print, `t = f()`): o estado vem do instantâneo
    que o rastreador guardou no momento do return, só com as globais.
    """
    indice, parcial = passo_depois(passo, retornos)
    if indice is None:
        return None, False
    depois = passos[indice]
    if not parcial:
        return depois, False
    retorno = retorno_do_quadro(depois, passo["quadro"]) or {}
    globais = depois["globais"]
    if "mudancas_globais" in retorno:
        globais = {**passo["globais"], **retorno["mudancas_globais"]}
        for nome in retorno["globais_apagadas"]:
            globais.pop(nome, None)
    saida = depois["saida"]
    if "saida_ate" in retorno:
        saida = saida[: retorno["saida_ate"]]
    return {"globais": globais, "locais": {}, "saida": saida}, True


def passo_depois(passo, retornos):
    """(índice do passo com o estado DEPOIS do comando, parcial) ou (None, False).

    Normalmente é o próximo passo do mesmo quadro. No último comando de uma
    função, o quadro acaba logo depois: o estado seguinte é o do passo que
    recebe o retorno, e lá as variáveis locais da função já não existem
    (`parcial`). Se a função terminou com erro, não há estado depois.
    """
    if passo["evento"] != "linha":
        return None, False
    if passo["proximo_no_quadro"] is not None:
        return passo["proximo_no_quadro"], False
    if passo["funcao"] is not None and passo["quadro"] in retornos:
        return retornos[passo["quadro"]], True
    return None, False


def _efeito(antes, depois, parcial):
    criadas, mudadas, apagadas = [], [], []
    escopos = [("global", "globais")] if parcial else [("local", "locais"), ("global", "globais")]
    for escopo, chave in escopos:
        anteriores = antes[chave]
        atuais = depois[chave]
        for nome, valor in atuais.items():
            anterior = anteriores.get(nome)
            if anterior is None:
                if nome not in criadas:
                    criadas.append(nome)
            elif anterior["h"] != valor["h"]:
                mudadas.append({"nome": nome, "escopo": escopo, "antes": anterior, "depois": valor})
        apagadas += [nome for nome in anteriores if nome not in atuais and nome not in apagadas]
    saida_antes = antes["saida"]
    saida_depois = depois["saida"]
    saida_nova = saida_depois[len(saida_antes) :] if saida_depois.startswith(saida_antes) else saida_depois
    return {"criadas": criadas, "mudadas": mudadas, "apagadas": apagadas, "saida_nova": saida_nova, "parcial": parcial}


def _decisao(passo, bruta, passos, comandos, retornos, nao_rodou):
    comando = comandos[passo["comando"]]
    valor = bruta["valor"]
    if nao_rodou:
        ramo = "desconhecido"
        valor = None
    else:
        ramo = _ramo(passo, comando, valor, passos, comandos, retornos)
        # Sem valor do avaliador (uma chamada na condição, por exemplo), o
        # ramo tomado diz o resultado: o balão mostra só "Verdadeiro".
        if ramo == "corpo":
            valor = True
        elif ramo in ("orelse", "sai"):
            valor = False
    desde, _ = passo_depois(passo, retornos)
    return {
        "texto": bruta["texto"],
        "valor": valor,
        "ramo": ramo,
        "nao_calculado": bruta["nao_calculado"],
        "nao_calculado_codigo": bruta["nao_calculado_codigo"],
        # O ramo pulado só aparece depois que a decisão aconteceu.
        "ramo_visivel_desde": desde if ramo != "desconhecido" and not nao_rodou else None,
    }


def _ramo(passo, comando, valor, passos, comandos, retornos):
    """'corpo' | 'orelse' | 'sai' | 'desconhecido', pelo próximo passo do mesmo quadro.

    Um corpo escrito na linha do cabeçalho (`if x: y = 1`) roda sem passo
    próprio; aí, e quando o corpo não gera passo nenhum (`if x: ...`), quem
    decide é o valor do avaliador.
    """
    seguinte = passo["proximo_no_quadro"]
    if seguinte is None:
        if passo["funcao"] is None or passo["quadro"] not in retornos:
            # O quadro terminou com erro: só o corpo na mesma linha pode ter rodado.
            return "corpo" if comando["corpo_mesma_linha"] and valor is True else "desconhecido"
        lugar = "fora"  # a função terminou logo depois da decisão
    else:
        lugar = _lugar(passo, comando, passos[seguinte], comandos)
    if lugar in ("corpo", "orelse"):
        return lugar
    if lugar == "repete":
        return "corpo" if comando["tipo"] == "while" else "desconhecido"
    # O próximo passo está depois do comando inteiro.
    if valor is True:
        return "corpo"
    if valor is False:
        return "orelse" if comando["orelse"] else "sai"
    if comando["corpo_mesma_linha"] or comando["orelse"]:
        return "desconhecido"
    return "sai"


def _lugar(passo, comando, seguinte, comandos):
    if seguinte["comando"] is None:
        return "fora"
    if seguinte["comando"] == passo["comando"]:
        return "repete"  # um while de uma linha só dando outra volta
    inicio = comandos[seguinte["comando"]]["linhas"][0]
    corpo, senao = comando["corpo"], comando["orelse"]
    if corpo and corpo[0] <= inicio <= corpo[1]:
        return "corpo"
    if senao and senao[0] <= inicio <= senao[1]:
        return "orelse"
    return "fora"
