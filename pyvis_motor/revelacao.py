"""Regra de revelação: quando um campo de um passo pode aparecer para o aluno.

Nada que vem do futuro do rastro pode entregar um palpite. Esta é a regra
pura que o TypeScript copia linha a linha (visivel e montar): o motor decide
o que é revelado, a interface só pergunta.

Campos são caminhos com ponto: 'efeito', 'efeito.saida_nova', 'decisao.texto',
'decisao.valor', 'decisao.ramo', 'volta.n', 'volta.total', 'volta.saindo',
'leitura.traduzida', 'retorno'. Um campo esconde junto tudo o que está dentro
dele e tudo o que o contém: perguntar por 'decisao' só dá True quando todas as
partes da decisão já podem aparecer.
"""

DESFECHO = ("efeito", "decisao.valor", "decisao.ramo")
# No cabeçalho de um laço, continuar ou sair também diz algo sobre o total de voltas.
DESFECHO_DO_CABECALHO = DESFECHO + ("volta.n", "volta.saindo", "volta.total")


def relacionados(a, b):
    """Um dos campos é o outro ou está dentro dele ('decisao' e 'decisao.valor')."""
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def desfecho(passo):
    """Os campos que contam o que o comando do passo fez.

    Eles revelam a mesma coisa por caminhos diferentes (o ramo tomado diz o
    valor da condição; no cabeçalho de um laço, o número da volta diz se o
    laço continua, e um laço que nem começa já diz que deu 0 voltas), então
    uma pergunta pendente sobre um esconde todos.
    """
    volta = passo.get("volta")
    if volta is not None and passo.get("comando") == volta["laco"]:
        return DESFECHO_DO_CABECALHO
    return DESFECHO


def visivel(passo, campo, respondidos, passo_atual):
    """O campo do passo já pode aparecer?

    - `respondidos`: ids dos pontos de previsão já respondidos (ou pulados).
    - `passo_atual`: o passo mais adiante que o aluno já alcançou. Usar o passo
      exibido também é seguro, só esconde de novo o que ele já viu ao voltar.

    Regras, todas obrigatórias:
    1. Nada de um passo que ainda não chegou (passo_atual < passo.i).
    2. passo.depende_de = {campo: [ponto_id]} (preenchido pela atividade): um
       campo relacionado a um ponto não respondido fica escondido. Se o campo
       pedido é do desfecho do passo, qualquer campo do desfecho pendente
       também o esconde.
    3. O desfecho só a partir de passo.desfecho_visivel_desde (o próprio passo,
       ou o fim das funções que o comando chamou); decisao.ramo só a partir de
       decisao.ramo_visivel_desde (o passo depois da decisão); volta.total só a
       partir de volta.total_visivel_desde (a saída do laço). Sem o índice
       (None), nunca.
    """
    if passo_atual < passo["i"]:
        return False
    proprios = desfecho(passo)
    no_desfecho = any(relacionados(campo, d) for d in proprios)
    for chave, pontos in (passo.get("depende_de") or {}).items():
        if all(ponto in respondidos for ponto in pontos):
            continue
        if relacionados(chave, campo):
            return False
        if no_desfecho and any(relacionados(chave, d) for d in proprios):
            return False
    if no_desfecho:
        desde = passo.get("desfecho_visivel_desde", passo["i"])
        if desde is None or passo_atual < desde:
            return False
    decisao = passo.get("decisao")
    if decisao is not None and relacionados(campo, "decisao.ramo"):
        desde = decisao.get("ramo_visivel_desde")
        if desde is None or passo_atual < desde:
            return False
    volta = passo.get("volta")
    if volta is not None and relacionados(campo, "volta.total"):
        desde = volta.get("total_visivel_desde")
        if desde is None or passo_atual < desde:
            return False
    return True


def montar(partes, passo, respondidos, passo_atual):
    """Junta as partes de uma narração: cada uma aparece se todos os seus campos são visíveis.

    Parte = {texto, campos: [campo], oculto?}. Escondida, a parte vira `oculto`
    (ou nada). As partes já trazem os espaços e a pontuação: é só concatenar.
    """
    texto = ""
    for parte in partes:
        if all(visivel(passo, campo, respondidos, passo_atual) for campo in parte["campos"]):
            texto += parte["texto"]
        else:
            texto += parte.get("oculto", "")
    return texto


def narracao_visivel(passo, respondidos, passo_atual, versao="curta"):
    """A frase do narrador ('curta' ou 'longa') com só o que já pode aparecer."""
    narracao = passo.get("narracao")
    if not narracao:
        return ""
    return montar(narracao["partes_" + versao], passo, respondidos, passo_atual)


def leitura_visivel(comando, respondidos):
    """A leitura de um comando fora do passo a passo (no editor, por exemplo)."""
    leitura = comando["leitura"]
    if all(ponto in respondidos for ponto in leitura["traduzida_depende_de"]):
        return leitura["traduzida"]
    return leitura["literal"]


def aplicar_dependencias(resultado, depende_de_por_passo):
    """Grava passo.depende_de a partir da atividade: {i: {campo: [ponto_id]}}.

    Também copia o `traduzida_depende_de` da leitura de cada comando para o
    campo 'leitura.traduzida' dos passos desse comando, porque a narração do
    passo usa a leitura traduzida. Aceita índices como int ou como texto (JSON).
    """
    comandos = resultado["estrutura"]["comandos"]
    for passo in resultado["passos"]:
        dependencias = depende_de_por_passo.get(passo["i"]) or depende_de_por_passo.get(str(passo["i"])) or {}
        juntas = {campo: list(pontos) for campo, pontos in dependencias.items()}
        if passo["comando"] is not None:
            leitura = comandos[passo["comando"]].get("leitura")
            if leitura and leitura["traduzida_depende_de"]:
                lista = juntas.setdefault("leitura.traduzida", [])
                lista += [p for p in leitura["traduzida_depende_de"] if p not in lista]
        if juntas:
            passo["depende_de"] = juntas
        else:
            passo.pop("depende_de", None)
    return resultado
