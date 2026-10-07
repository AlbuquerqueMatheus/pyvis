"""Gera os casos que os testes da página conferem contra o motor Python.

- src/testes/casos-revelacao.json: respostas da regra de revelação calculadas pelo Python;
- src/testes/rastros.json: Resultados completos de alguns programas, para os testes da tela;
- src/testes/previsoes.json: atividades de prever desses programas, nos dois formatos, e a
  correção do Python para cada resposta que os testes da tela usam.

src/motor/revelacao.ts copia pyvis_motor/revelacao.py linha a linha, e
revelacao.test.ts confere as duas com estes casos. Rode de novo sempre que
revelacao.py, anotar.py, narrador.py ou previsao.py mudarem:

    python3 frontend/scripts/casos_revelacao.py             # regrava o arquivo
    python3 frontend/scripts/casos_revelacao.py --conferir  # só confere (para a CI)

Há dois grupos de casos:
- sintéticos: passos sorteados com todas as combinações que a regra lê
  (chave ausente, null, dependências pendentes e respondidas);
- reais: programas do corpus e do site rodados com uma atividade de previsão,
  com a frase do narrador montada em alguns momentos.
"""

import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from analise.cobertura import ler_programa  # noqa: E402
from pyvis_motor import api  # noqa: E402
from pyvis_motor.revelacao import leitura_visivel, montar, visivel  # noqa: E402

DESTINO = RAIZ / "frontend" / "src" / "testes" / "casos-revelacao.json"
# Rastros completos de alguns programas, para os testes da tela.
RASTROS = RAIZ / "frontend" / "src" / "testes" / "rastros.json"
NOMES_DOS_RASTROS = (
    "if_else", "for", "while", "funcao", "elif", "curto_circuito", "input", "erro", "sintaxe", "conta", "troca", "maior",
    "recursao",
)
# Atividades de prever e correções gravadas, para o Python de mentira dos testes da tela.
PREVISOES = RAIZ / "frontend" / "src" / "testes" / "previsoes.json"
NOMES_DAS_PREVISOES = ("for", "if_else", "while", "input", "conta")

CAMPOS = [
    "efeito",
    "efeito.saida_nova",
    "decisao",
    "decisao.texto",
    "decisao.valor",
    "decisao.ramo",
    "decisao.nao_calculado",
    "volta",
    "volta.n",
    "volta.total",
    "volta.saindo",
    "leitura.traduzida",
    "retorno",
]

# Programas pequenos que cobrem o que o corpus tem pouco: função, recursão, elif, curto-circuito.
EXTRAS = {
    "if_else": (
        'nota = 7\nif nota >= 6:\n    resultado = "aprovado"\nelse:\n    resultado = "recuperação"\n'
        'print("Situação:", resultado)\n',
        [],
    ),
    "for": ('total = 0\nfor numero in range(1, 5):\n    total = total + numero\nprint("A soma é", total)\n', []),
    "while": (
        'energia = 3\nwhile energia > 0:\n    print("Energia:", energia)\n    energia = energia - 1\n'
        'print("O robô descansou!")\n',
        [],
    ),
    "funcao": ("def dobro(x):\n    return x * 2\ny = dobro(4)\nprint(y)\n", []),
    "recursao": ("def fat(n):\n    if n <= 1:\n        return 1\n    return n * fat(n - 1)\nprint(fat(3))\n", []),
    "elif": ("x = 3\nif x > 5:\n    y = 1\nelif x > 2:\n    y = 2\nelse:\n    y = 3\nprint(y)\n", []),
    "curto_circuito": (
        "lista = [3, 4, 5]\ni = 0\nwhile i < len(lista) and lista[i] > 0:\n    i = i + 1\nprint(i)\n",
        [],
    ),
    "input": (
        'nome = input("Qual é o nome do seu robô? ")\nidade = int(input("Quantos anos o robô tem? "))\n'
        'print("Olá,", nome)\nprint("Daqui a 5 anos ele terá", idade + 5)\n',
        ["Bip", "3"],
    ),
    "limite": ("x = 0\nwhile True:\n    x = x + 1\n", []),
}
LIMITES = {"extra:limite": 12}
SO_RASTRO = {
    "erro": ("pontos = 10\nbonus = 5\ntotal = pontos + bonu\nprint(total)\n", []),
    "sintaxe": ("x = (1\n", []),
    # O input devolve texto: "4" * 2 é "44" (o palpite 8 é o da concepção do input-número).
    "conta": ('a = input("? ")\nb = a * 2\nprint(b)\n', ["4"]),
    # Duas variáveis mudam no mesmo passo: só uma pode ganhar o destaque animado.
    "troca": ("a, b = 1, 2\na, b = b, a\nprint(a, b)\n", []),
    # O exemplo 6: um if dentro do for, com o ramo mudando de uma volta para outra.
    "maior": (
        "numeros = [4, 9, 2, 7]\nmaior = numeros[0]\nfor n in numeros:\n    if n > maior:\n        maior = n\n"
        'print("O maior é", maior)\n',
        [],
    ),
}
# Um em cada seis programas do corpus basta: os extras cobrem o resto.
CORPUS = sorted((RAIZ / "tests" / "corpus").glob("*.py"))[::6]


def _sintetico(sorteio, i):
    """Um passo com uma combinação sorteada de tudo o que a regra lê."""
    passo = {"i": i, "comando": sorteio.choice([None, 0, 1, 2])}
    escolha = sorteio.random()
    if escolha < 0.6:
        passo["desfecho_visivel_desde"] = i + sorteio.choice([0, 0, 1, 3])
    elif escolha < 0.8:
        passo["desfecho_visivel_desde"] = None
    # senão a chave fica ausente: vale o próprio passo
    if sorteio.random() < 0.5:
        passo["decisao"] = {"ramo_visivel_desde": sorteio.choice([None, i + 1, i + 2])}
    else:
        passo["decisao"] = None
    if sorteio.random() < 0.5:
        passo["volta"] = {
            "laco": sorteio.choice([0, 1, 2]),
            "total_visivel_desde": sorteio.choice([None, i + 1, i + 5]),
        }
    else:
        passo["volta"] = None
    if sorteio.random() < 0.8:
        chaves = sorteio.sample(CAMPOS + ["leitura", "efeito.criadas"], sorteio.randint(1, 3))
        passo["depende_de"] = {chave: sorteio.sample(["p1", "p2", "p3"], sorteio.randint(0, 2)) for chave in chaves}
    return passo


def _bits(passo, respondidos, atuais):
    """'0'/'1' para cada campo x respondidos x passo atual, nesta ordem."""
    return "".join(
        "1" if visivel(passo, campo, set(conjunto), atual) else "0"
        for campo in CAMPOS
        for conjunto in respondidos
        for atual in atuais
    )


def sinteticos():
    sorteio = random.Random(2026)
    casos = []
    respondidos = [[], ["p1"], ["p2"], ["p1", "p2"], ["p1", "p2", "p3"]]
    for _ in range(120):
        i = sorteio.randint(0, 6)
        passo = _sintetico(sorteio, i)
        atuais = sorted({max(i - 1, 0), i, i + 1, i + 2, i + 3, i + 6})
        casos.append(
            {
                "passo": passo,
                "respondidos": respondidos,
                "atuais": atuais,
                "esperado": _bits(passo, respondidos, atuais),
            }
        )
    return casos


def _programas():
    for caminho in CORPUS:
        programa = ler_programa(caminho)
        yield f"corpus:{programa['nome']}", programa["codigo"], programa["entradas"], programa["semente"] or 1
    for nome, (codigo, entradas) in EXTRAS.items():
        yield f"extra:{nome}", codigo, entradas, 1


def _passo_minimo(passo):
    """Só o que a regra e a montagem leem: o arquivo fica pequeno."""
    minimo = {"i": passo["i"], "comando": passo["comando"]}
    if "desfecho_visivel_desde" in passo:
        minimo["desfecho_visivel_desde"] = passo["desfecho_visivel_desde"]
    decisao = passo.get("decisao")
    minimo["decisao"] = None if decisao is None else {"ramo_visivel_desde": decisao["ramo_visivel_desde"]}
    volta = passo.get("volta")
    minimo["volta"] = (
        None if volta is None else {"laco": volta["laco"], "total_visivel_desde": volta["total_visivel_desde"]}
    )
    if "depende_de" in passo:
        minimo["depende_de"] = passo["depende_de"]
    minimo["narracao"] = {
        "partes_curta": passo["narracao"]["partes_curta"],
        "partes_longa": passo["narracao"]["partes_longa"],
    }
    return minimo


def reais():
    programas = []
    for nome, codigo, entradas, semente in _programas():
        resultado = api.rastrear(codigo, entradas, semente=semente, limite=LIMITES.get(nome))
        # A atividade grava depende_de no próprio resultado (o mesmo objeto que rastrear devolveu).
        atividade = api.preparar_atividade({"modo": "prever", "formato": "alternativas", "semente": 1})
        pontos = sorted(
            {p for passo in resultado["passos"] for lista in passo.get("depende_de", {}).values() for p in lista}
        )
        ultimo = len(resultado["passos"]) - 1
        passos = []
        for passo in resultado["passos"]:
            i = passo["i"]
            minimo = _passo_minimo(passo)
            pendentes = sorted({p for lista in passo.get("depende_de", {}).values() for p in lista})
            respondidos = [[], pontos] + [[p for p in pontos if p != pendente] for pendente in pendentes]
            momentos = {max(i - 1, 0), i, i + 1, ultimo}
            for desde in (
                passo.get("desfecho_visivel_desde"),
                (passo.get("decisao") or {}).get("ramo_visivel_desde"),
                (passo.get("volta") or {}).get("total_visivel_desde"),
            ):
                if desde is not None:
                    momentos |= {desde - 1, desde}
            atuais = sorted(momentos)
            # Recém-chegado sem responder nada e no fim com tudo respondido. A frase
            # inteira (todas as partes à mostra) vira null, para o arquivo ficar menor.
            frases = []
            for versao in ("curta", "longa"):
                partes = passo["narracao"]["partes_" + versao]
                inteira = "".join(parte["texto"] for parte in partes)
                for conjunto, atual in (([], i), (pontos, ultimo)):
                    frase = montar(partes, passo, set(conjunto), atual)
                    frases.append([versao, conjunto, atual, None if frase == inteira else frase])
            passos.append(
                {
                    "passo": minimo,
                    "respondidos": respondidos,
                    "atuais": atuais,
                    "esperado": _bits(passo, respondidos, atuais),
                    "frases": frases,
                }
            )
        leituras = [
            [comando["id"], conjunto, leitura_visivel(comando, set(conjunto))]
            for comando in resultado["estrutura"]["comandos"]
            if comando["leitura"]["traduzida_depende_de"]
            for conjunto in ([], comando["leitura"]["traduzida_depende_de"][:1], pontos)
        ]
        programas.append(
            {
                "nome": nome,
                "comandos": [{"id": c["id"], "leitura": c["leitura"]} for c in resultado["estrutura"]["comandos"]],
                "depende_de_por_passo": atividade["depende_de_por_passo"],
                "traduzida_depende_de": atividade["traduzida_depende_de"],
                "passos": passos,
                "leituras": leituras,
            }
        )
    return programas


def rastros():
    """Resultado de cada programa no modo assistir e, no for, também a atividade de prever."""
    todos = {**EXTRAS, **SO_RASTRO}
    saida = {}
    for nome in NOMES_DOS_RASTROS:
        codigo, entradas = todos[nome]
        resultado = api.rastrear(codigo, entradas, semente=1)
        saida[nome] = {"codigo": codigo, "entradas": entradas, "resultado": json.loads(json.dumps(resultado))}
        if nome == "for":
            atividade = api.preparar_atividade({"modo": "prever", "formato": "alternativas", "semente": 1})
            saida[nome]["atividade"] = {**atividade, "tempo_ms": 0}  # o tempo muda a cada execução
    return json.dumps(saida, ensure_ascii=False, separators=(",", ":")) + "\n"


def _sem_aspas(texto):
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in "\"'":
        return texto[1:-1]
    return texto


def _respostas_livres(ponto, textos_das_alternativas):
    """As respostas livres que os testes usam: a certa, as das alternativas e uma ilegível."""
    tipo = ponto["tipo"]
    certa = ponto["resposta"]
    respostas = []
    if tipo == "valor":
        textos = [(certa["texto"], certa["tipo_valor"])] + textos_das_alternativas
        for texto, tipo_valor in textos:
            for escolhido in ("numero", "texto"):
                respostas.append({"texto": _sem_aspas(texto), "tipo_escolhido": escolhido})
        respostas.append({"texto": "abc", "tipo_escolhido": "numero"})
    elif tipo in ("voltas", "saida"):
        for texto, _ in [(certa["texto"], None)] + textos_das_alternativas:
            respostas.append({"texto": texto})
        if tipo == "voltas":
            respostas.append({"texto": "quatro"})
    unicas = []
    for resposta in respostas:
        if resposta not in unicas:
            unicas.append(resposta)
    return unicas


def previsoes():
    """Para cada programa: a atividade de prever nos dois formatos e as correções gravadas."""
    todos = {**EXTRAS, **SO_RASTRO}
    saida = {}
    for nome in NOMES_DAS_PREVISOES:
        codigo, entradas = todos[nome]
        api.rastrear(codigo, entradas, semente=1)
        atividades = {}
        correcoes = []
        textos = {}
        for formato in ("alternativas", "livre"):
            atividade = api.preparar_atividade({"modo": "prever", "formato": formato})
            atividades[formato] = {**atividade, "tempo_ms": 0}  # o tempo muda a cada execução
            pontos = ([atividade["palpite_inicial"]] if atividade["palpite_inicial"] else []) + atividade["pontos"]
            for ponto in pontos:
                alternativas = ponto.get("alternativas") or []
                if formato == "alternativas":
                    textos[ponto["id"]] = [(a["texto"], a["tipo_valor"]) for a in alternativas if not a["certa"]]
                respostas = [{"alternativa": a["id"]} for a in alternativas]
                if ponto["formato"] == "livre":
                    respostas += _respostas_livres(ponto, textos.get(ponto["id"], []))
                for resposta in respostas:
                    correcao = api.corrigir(ponto["id"], resposta)
                    correcoes.append({"formato": formato, "ponto": ponto["id"], "resposta": resposta, "correcao": correcao})
        saida[nome] = {"atividades": atividades, "correcoes": correcoes}
    return json.dumps({"aviso": "Gerado por frontend/scripts/casos_revelacao.py. Não edite à mão.", **saida},
                      ensure_ascii=False, separators=(",", ":")) + "\n"


def gerar():
    casos = {
        "aviso": "Gerado por frontend/scripts/casos_revelacao.py. Não edite à mão.",
        "campos": CAMPOS,
        "sinteticos": sinteticos(),
        "programas": reais(),
    }
    return json.dumps(casos, ensure_ascii=False, separators=(",", ":")) + "\n"


def main(argv):
    arquivos = {DESTINO: gerar(), RASTROS: rastros(), PREVISOES: previsoes()}
    if "--conferir" in argv:
        desatualizados = [
            c for c, texto in arquivos.items() if not c.exists() or c.read_text(encoding="utf-8") != texto
        ]
        for caminho in desatualizados:
            print(f"{caminho.relative_to(RAIZ)} está desatualizado: rode python3 frontend/scripts/casos_revelacao.py")
        if not desatualizados:
            print("casos da revelação em dia")
        return 1 if desatualizados else 0
    for caminho, texto in arquivos.items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8")
        print(f"{caminho.relative_to(RAIZ)}: {len(texto) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
