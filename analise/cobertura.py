"""Sonda de cobertura (Onda 1.5): quantos pontos de previsão ganham distrator de modelo.

Lê os programas de tests/corpus, com os pontos de previsão e as concepções
rotulados à mão nos comentários do começo de cada arquivo, roda os modelos
de concepção (pyvis_motor/concepcoes.py) e imprime:
- a cobertura por tipo de pergunta (pontos com 1 ou mais e com 2 ou mais
  distratores de modelo, e alternativas descartadas por serem iguais à
  certa ou repetidas);
- a cobertura por concepção;
- o critério pré-registrado (saída, voltas e decisão, limite de 30%);
- a concordância entre os rótulos à mão e os modelos, por programa;
- o tempo de geração.

Com --candidatos, mede também todos os candidatos a ponto que o rastro
oferece (até 3 ocorrências por comando), sem depender do rótulo à mão.

Uso: python3 analise/cobertura.py [--corpus PASTA] [--limite N] [--candidatos] [--programas] [--json ARQUIVO]
"""

import argparse
import ast
import gc
import json
import re
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from pyvis_motor.concepcoes import (  # noqa: E402
    CATALOGO,
    LIMITE_LEVE,
    TIPOS_DE_PONTO,
    gerar_modelos,
    inicios_de_laco,
    rastrear_leve,
)
from pyvis_motor.estrutura import Analise  # noqa: E402
from pyvis_motor.rastreador import rastrear  # noqa: E402

CORPUS = RAIZ / "tests" / "corpus"
CRITERIO = 0.30
TIPOS_DO_CRITERIO = ("saida", "voltas", "decisao")
MAXIMO_DE_OCORRENCIAS = 3  # candidatos: as primeiras vezes de cada comando
IDS = [c["id"] for c in CATALOGO]

_METADADO = re.compile(r"#\s*@(\w+)\s*:\s*(.*)")
_PONTO = re.compile(r"(valor|decisao|voltas|saida)\s+(\d+|tudo)(?:\s+([A-Za-z_]\w*))?(?:\s+@(\d+))?")


# --- Leitura do corpus ---------------------------------------------------------


def ler_programa(caminho):
    """Programa e metadados: # @entradas (JSON), # @semente, # @pontos e # @concepcoes.

    Cada ponto é `tipo linha [nome] [@ocorrência]`, separado por `;`:
    `valor 8 total @2` é o valor de total depois da 2ª vez que a linha 8
    roda; `voltas 6 @2` é a 2ª vez que o laço da linha 6 começa; `saida tudo`
    é a saída do programa inteiro. A linha é a do arquivo, com o cabeçalho.
    """
    caminho = Path(caminho)
    codigo = caminho.read_text(encoding="utf-8")
    programa = {"nome": caminho.stem, "codigo": codigo, "entradas": [], "semente": 0, "pontos": [], "concepcoes": []}
    for linha in codigo.splitlines():
        if not linha.startswith("#"):
            break  # os metadados ficam no bloco de comentários do começo
        achado = _METADADO.match(linha)
        if achado is None:
            continue
        chave, valor = achado.group(1), achado.group(2).strip()
        if chave == "entradas":
            programa["entradas"] = [str(item) for item in json.loads(valor)]
        elif chave == "semente":
            programa["semente"] = int(valor)
        elif chave == "pontos":
            programa["pontos"] += [_ler_ponto(caminho.name, item) for item in valor.split(";") if item.strip()]
        elif chave == "concepcoes":
            rotulos = [] if valor == "nenhuma" else [c.strip() for c in valor.split(",") if c.strip()]
            desconhecidos = [c for c in rotulos if c not in IDS]
            if desconhecidos:
                raise ValueError(f"{caminho.name}: concepção desconhecida {desconhecidos}")
            programa["concepcoes"] = rotulos
        else:
            raise ValueError(f"{caminho.name}: metadado desconhecido @{chave}")
    return programa


def _ler_ponto(arquivo, texto):
    achado = _PONTO.fullmatch(texto.strip())
    if achado is None:
        raise ValueError(f"{arquivo}: ponto ilegível {texto.strip()!r}")
    tipo, linha, nome, ocorrencia = achado.groups()
    if linha == "tudo" and tipo != "saida":
        raise ValueError(f"{arquivo}: só a saída pode ser do programa inteiro ({texto.strip()!r})")
    if tipo == "valor" and not nome:
        raise ValueError(f"{arquivo}: ponto de valor sem o nome da variável ({texto.strip()!r})")
    return {"tipo": tipo, "linha": None if linha == "tudo" else int(linha), "nome": nome,
            "ocorrencia": int(ocorrencia) if ocorrencia else 1}


def ler_corpus(pasta=CORPUS):
    return [ler_programa(caminho) for caminho in sorted(Path(pasta).glob("*.py"))]


TIPOS_DE_COMANDO = {"decisao": ("if", "elif", "while"), "voltas": ("for", "while")}


def resolver_pontos(programa, analise):
    """Os pontos rotulados viram pontos de gerar_modelos (linha -> comando)."""
    pontos = []
    for numero, rotulo in enumerate(programa["pontos"], 1):
        comando = None
        if rotulo["linha"] is not None:
            comando = analise.linha_para_comando.get(rotulo["linha"])
            if comando is None or analise.comandos[comando]["linhas"][0] != rotulo["linha"]:
                raise ValueError(f"{programa['nome']}: nenhum comando começa na linha {rotulo['linha']}")
            esperados = TIPOS_DE_COMANDO.get(rotulo["tipo"])
            if esperados and analise.comandos[comando]["tipo"] not in esperados:
                raise ValueError(f"{programa['nome']}: a linha {rotulo['linha']} não serve para {rotulo['tipo']}")
        pontos.append({"id": f"p{numero}", "tipo": rotulo["tipo"], "alvo": {"comando": comando, "nome": rotulo["nome"]},
                       "ocorrencia": rotulo["ocorrencia"], "linha": rotulo["linha"]})
    return pontos


def _nome_atribuido(no):
    if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
        return no.targets[0].id
    if isinstance(no, (ast.AugAssign, ast.AnnAssign)) and isinstance(no.target, ast.Name):
        return no.target.id
    return None


def _trivial(no):
    """x = 3 ou x = [1, 2]: a resposta está escrita no próprio código."""
    valor = getattr(no, "value", None)
    if isinstance(no, ast.AugAssign) or valor is None:
        return False
    return all(isinstance(n, (ast.Constant, ast.List, ast.Tuple, ast.Load, ast.UnaryOp, ast.USub)) for n in ast.walk(valor))


def candidatos(analise, resultado):
    """Todos os candidatos a ponto que o rastro oferece, como em 2.2 (a)-(d), sem escolha."""
    pontos = []
    contagem = {}
    passos = resultado["passos"]
    for passo in passos:
        comando = passo["comando"]
        if comando is None:
            continue
        n = contagem[comando] = contagem.get(comando, 0) + 1
        if n > MAXIMO_DE_OCORRENCIAS:
            continue
        tipo, no = analise.comandos[comando]["tipo"], analise.nos[comando]
        if tipo in ("atrib", "aug") and _nome_atribuido(no) and not _trivial(no):
            pontos.append(("valor", comando, _nome_atribuido(no), n))
        elif tipo in ("if", "elif", "while"):
            pontos.append(("decisao", comando, None, n))
        elif tipo == "print":
            pontos.append(("saida", comando, None, n))
    for (laco, k) in inicios_de_laco(passos, analise.comandos):
        if k <= 2:
            pontos.append(("voltas", laco, None, k))
    if resultado["erro"] is None:
        pontos.append(("saida", None, None, 1))
    return [{"id": f"c{i}", "tipo": tipo, "alvo": {"comando": comando, "nome": nome}, "ocorrencia": k,
             "linha": analise.comandos[comando]["linhas"][0] if comando is not None else None}
            for i, (tipo, comando, nome, k) in enumerate(pontos, 1)]


# --- Medição -------------------------------------------------------------------


def _tempo_ms(funcao, repeticoes=3):
    melhor = None
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        funcao()
        gasto = (time.perf_counter() - inicio) * 1000
        melhor = gasto if melhor is None else min(melhor, gasto)
    return melhor


def medir(programas, limite=LIMITE_LEVE, usar_candidatos=False, medir_tempo=True):
    """Roda os modelos em cada programa e junta os números por ponto, tipo e concepção."""
    pontos_medidos = []
    por_concepcao = {cid: {"aplicavel": 0, "geradas": 0, "iguais": 0, "repetidas": 0, "mantidas": 0, "exclusivas": 0,
                           "estouro": 0, "sem_resposta": 0, "erro": 0, "execucoes": 0}
                     for cid in IDS}
    programas_medidos = []
    for programa in programas:
        codigo, entradas, semente = programa["codigo"], programa["entradas"], programa["semente"]
        analise = Analise(codigo)
        resultado = rastrear(codigo, entradas, semente=semente)
        pontos = candidatos(analise, resultado) if usar_candidatos else resolver_pontos(programa, analise)
        modelos = gerar_modelos(codigo, entradas, pontos, semente, limite=limite)
        for cid, estatistica in modelos["concepcoes"].items():
            for campo in ("aplicavel", "geradas", "iguais", "repetidas", "mantidas", "estouro", "sem_resposta", "erro",
                          "execucoes"):
                por_concepcao[cid][campo] += estatistica[campo]
        previstas = set()
        for ponto in pontos:
            bloco = modelos["por_ponto"][ponto["id"]]
            alternativas = bloco["alternativas"]
            for alternativa in alternativas:
                previstas.update(alternativa["concepcoes"])
                if len(alternativa["concepcoes"]) == 1:
                    por_concepcao[alternativa["concepcoes"][0]]["exclusivas"] += 1
            pontos_medidos.append({
                "programa": programa["nome"],
                "ponto": ponto["id"],
                "tipo": ponto["tipo"],
                "linha": ponto["linha"],
                "ocorrencia": ponto["ocorrencia"],
                "certa": bloco["certa"],
                "alternativas": [{"texto": a["texto"], "concepcoes": a["concepcoes"]} for a in alternativas],
                "sem_c04": sum(1 for a in alternativas if a["concepcoes"] != ["C04"]),
                "geradas": bloco["descartadas"]["iguais"] + len(bloco["modelos"]),
                "descartadas": bloco["descartadas"]["iguais"] + bloco["descartadas"]["repetidas"],
            })
        tempos = {"geracao_ms": modelos["tempo_ms"]}
        if medir_tempo:
            tempos["geracao_ms"] = _tempo_ms(lambda: gerar_modelos(codigo, entradas, pontos, semente, limite=limite))
            tempos["completo_ms"] = _tempo_ms(lambda: rastrear(codigo, entradas, semente=semente))
            # Como em gerar_modelos: a análise é feita uma vez e os modelos só executam.
            tempos["analise_ms"] = _tempo_ms(lambda: Analise(codigo))
            tempos["leve_ms"] = _tempo_ms(lambda: rastrear_leve(codigo, entradas, (), semente, 1000, analise=analise))
        programas_medidos.append({"programa": programa["nome"], "rotulos": sorted(programa["concepcoes"]),
                                  "previstas": sorted(previstas), "deterministico": modelos["deterministico"],
                                  "passos": len(resultado["passos"]), "pontos": len(pontos), **tempos})
    return {"pontos": pontos_medidos, "concepcoes": por_concepcao, "programas": programas_medidos,
            "limite": limite, "candidatos": usar_candidatos}


def resumo_por_tipo(medicao):
    """{tipo: {pontos, um, dois, sem_c04, geradas, descartadas}}, só com pontos que têm resposta certa."""
    tabela = {tipo: {"pontos": 0, "um": 0, "dois": 0, "sem_c04": 0, "geradas": 0, "descartadas": 0, "sem_certa": 0}
              for tipo in (*TIPOS_DE_PONTO, "total")}
    for ponto in medicao["pontos"]:
        for chave in (ponto["tipo"], "total"):
            linha = tabela[chave]
            if ponto["certa"] is None:
                linha["sem_certa"] += 1
                continue
            linha["pontos"] += 1
            linha["um"] += len(ponto["alternativas"]) >= 1
            linha["dois"] += len(ponto["alternativas"]) >= 2
            linha["sem_c04"] += ponto["sem_c04"] >= 1
            linha["geradas"] += ponto["geradas"]
            linha["descartadas"] += ponto["descartadas"]
    return tabela


def criterio(medicao):
    """Pontos de saída, voltas e decisão com pelo menos 1 distrator de modelo."""
    validos = [p for p in medicao["pontos"] if p["certa"] is not None and p["tipo"] in TIPOS_DO_CRITERIO]
    cobertos = sum(1 for p in validos if p["alternativas"])
    fracao = cobertos / len(validos) if validos else 0.0
    return {"cobertos": cobertos, "total": len(validos), "fracao": fracao, "atinge": fracao >= CRITERIO}


def concordancia(medicao):
    """Rótulo à mão x concepção que gerou distrator, por programa: precisão e revocação."""
    tabela = {}
    for cid in IDS:
        vp = fp = fn = 0
        for programa in medicao["programas"]:
            rotulada, prevista = cid in programa["rotulos"], cid in programa["previstas"]
            vp += rotulada and prevista
            fp += prevista and not rotulada
            fn += rotulada and not prevista
        tabela[cid] = {"vp": vp, "fp": fp, "fn": fn,
                       "precisao": vp / (vp + fp) if vp + fp else None,
                       "revocacao": vp / (vp + fn) if vp + fn else None}
    return tabela


# --- Impressão -----------------------------------------------------------------


def _pct(parte, total):
    if not total:
        return "   -  "
    return f"{100 * parte / total:5.1f}%".replace(".", ",")


def _fracao(valor):
    return "  -  " if valor is None else f"{valor:.2f}".replace(".", ",")


def imprimir(medicao, titulo):
    print(titulo)
    print("=" * len(titulo))
    tabela = resumo_por_tipo(medicao)
    print(f"{'tipo':<9}{'pontos':>7}{'>=1 modelo':>18}{'>=2 modelos':>18}{'>=1 sem C04':>18}{'descartadas':>22}")
    for tipo, linha in tabela.items():
        n = linha["pontos"]
        print(f"{tipo:<9}{n:>7}{linha['um']:>8} ({_pct(linha['um'], n)}){linha['dois']:>8} ({_pct(linha['dois'], n)})"
              f"{linha['sem_c04']:>8} ({_pct(linha['sem_c04'], n)})"
              f"{linha['descartadas']:>6} de {linha['geradas']:<4}({_pct(linha['descartadas'], linha['geradas'])})")
    sem_certa = tabela["total"]["sem_certa"]
    if sem_certa:
        print(f"({sem_certa} pontos sem resposta certa ficaram fora: o programa não chegou lá)")
    print()

    print(f"{'concepção':<26}{'aplicável':>10}{'com distrator':>20}{'diagnóstico':>13}{'iguais':>8}{'repet.':>8}"
          f"{'estouro':>9}{'sem resp.':>11}")
    nomes = {c["id"]: c["nome"] for c in CATALOGO}
    for cid, linha in medicao["concepcoes"].items():
        n = linha["aplicavel"]
        print(f"{cid + ' ' + nomes[cid]:<26}{n:>10}{linha['mantidas']:>11} ({_pct(linha['mantidas'], n)})"
              f"{linha['exclusivas']:>13}{linha['iguais']:>8}{linha['repetidas']:>8}{linha['estouro']:>9}"
              f"{linha['sem_resposta']:>11}")
    print("(aplicável: pontos de um tipo observável num programa com a construção; diagnóstico: alternativas"
          " explicadas só por essa concepção; sem resp.: o modelo não chegou ao ponto ou, na C04, a variável era nova)")
    print()

    decisao = criterio(medicao)
    veredito = "atinge o critério" if decisao["atinge"] else "abaixo do critério: a cobertura vira resultado da tese"
    print(f"Critério pré-registrado (saída, voltas e decisão com >=1 distrator de modelo): "
          f"{decisao['cobertos']} de {decisao['total']} = {_pct(decisao['cobertos'], decisao['total']).strip()}"
          f" (limite {int(CRITERIO * 100)}%) -> {veredito}")
    print()

    if not medicao["candidatos"]:
        print("Rótulos à mão x modelos, por programa")
        print(f"{'concepção':<10}{'VP':>4}{'FP':>4}{'FN':>4}{'precisão':>10}{'revocação':>11}")
        for cid, linha in concordancia(medicao).items():
            print(f"{cid:<10}{linha['vp']:>4}{linha['fp']:>4}{linha['fn']:>4}{_fracao(linha['precisao']):>10}"
                  f"{_fracao(linha['revocacao']):>11}")
        print()

    programas = medicao["programas"]
    geracao = [p["geracao_ms"] for p in programas]
    print(f"Tempo de geração por programa: mediana {statistics.median(geracao):.1f} ms, "
          f"máximo {max(geracao):.1f} ms ({len(programas)} programas, limite de {medicao['limite']} passos)")
    if all("completo_ms" in p for p in programas):
        completo = sum(p["completo_ms"] for p in programas)
        analise = sum(p["analise_ms"] for p in programas)
        leve = sum(p["leve_ms"] for p in programas)
        print(f"No corpus: rastrear completo {completo:.1f} ms, dos quais {analise:.1f} ms são a análise do código;"
              f" rastrear_leve com a análise pronta {leve:.1f} ms"
              f" ({(completo - analise) / leve:.1f} vezes mais barato que a execução completa)")
    nao_deterministicos = [p["programa"] for p in programas if not p["deterministico"]]
    if nao_deterministicos:
        print(f"Sem modelos por não serem determinísticos: {', '.join(nao_deterministicos)}")
    print()


def imprimir_programas(medicao):
    print("Pontos por programa (certa -> alternativas de modelo)")
    for ponto in medicao["pontos"]:
        onde = "tudo" if ponto["linha"] is None else f"linha {ponto['linha']} @{ponto['ocorrencia']}"
        certa = ponto["certa"]["texto"] if ponto["certa"] else "(sem resposta)"
        alternativas = ", ".join(f"{a['texto']!r} {'+'.join(a['concepcoes'])}" for a in ponto["alternativas"]) or "-"
        print(f"  {ponto['programa']:<22}{ponto['tipo']:<8}{onde:<16}{certa!r:<32} -> {alternativas}")
    print()


def main(argv=None):
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--corpus", default=str(CORPUS), help="pasta com os programas (padrão: tests/corpus)")
    argumentos.add_argument("--limite", type=int, default=LIMITE_LEVE, help="limite de passos de cada modelo")
    argumentos.add_argument("--candidatos", action="store_true", help="medir também todos os candidatos do rastro")
    argumentos.add_argument("--programas", action="store_true", help="listar cada ponto com as alternativas")
    argumentos.add_argument("--json", help="salvar as medições neste arquivo")
    opcoes = argumentos.parse_args(argv)

    programas = ler_corpus(opcoes.corpus)
    # Como no worker (worker.ts): o que já existe fica fora das coletas, e a coleta inteira que o
    # rastreador faz no fim de cada execução não pesa no tempo medido.
    gc.freeze()
    rotulados = medir(programas, opcoes.limite)
    print(f"Sonda de cobertura: {len(programas)} programas, Python {sys.version.split()[0]}")
    print()
    imprimir(rotulados, "Pontos rotulados à mão")
    if opcoes.programas:
        imprimir_programas(rotulados)
    saida = {"rotulados": rotulados}
    if opcoes.candidatos:
        todos = medir(programas, opcoes.limite, usar_candidatos=True)
        imprimir(todos, f"Todos os candidatos do rastro (até {MAXIMO_DE_OCORRENCIAS} ocorrências por comando)")
        if opcoes.programas:
            imprimir_programas(todos)
        saida["candidatos"] = todos
    if opcoes.json:
        Path(opcoes.json).write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
