"""Confere as famílias da área Praticar e gera o banco de sementes (pyvis_motor/banco.py).

Para cada família@versão e nível, testa as sementes 0, 1, 2... no gerador e
no verificador e guarda as primeiras TAMANHO que passam e são programas
diferentes entre si. Imprime um relatório: aceitação, recusas por motivo,
programas distintos, esqueletos usados, parte com distrator de modelo, as
maiores medidas contra o orçamento do verificador e o tempo por exercício.

    python3 analise/verificar_familias.py             # só o relatório, não grava nada
    python3 analise/verificar_familias.py --gravar    # grava pyvis_motor/banco.py
    python3 analise/verificar_familias.py --conferir  # falha se banco.py estiver velho (CI)
    python3 analise/verificar_familias.py --tema lacos --familia robo_energia

Com --tema ou --familia, só essas famílias são conferidas; --gravar troca só
as entradas delas no banco e mantém as outras.

Versão congelada: o banco guarda também a impressão digital de cada entrada
(IMPRESSOES, o sha256 dos contextos e códigos que as sementes geram). Se uma
família@versão que já está no banco passa a gerar outra coisa nas mesmas
sementes (mudou um texto, uma faixa, uma lista de familias.LISTAS), o script
falha com "mudou a família publicada sem subir a versao". O certo é subir a
versao. Só uma família que ainda não chegou à main (nenhum link mandado) pode
ser regravada na mesma versão, com --familia-nao-publicada.

O script falha (código 1) quando uma porta não passa:
- toda família tem formato válido (gerador.problemas) e pelo menos 3 esqueletos por nível;
- cada família e nível chega a TAMANHO sementes no banco, com pelo menos
  MINIMO_DISTINTOS programas distintos, dentro de MAX_SEMENTES sementes;
- todo esqueleto aparece no banco;
- pelo menos MINIMO_COM_MODELO dos itens do banco têm um distrator de modelo;
- no máximo MAXIMO_SO_DECISAO dos itens do banco só perguntam "o if vai entrar?"
  nas alternativas (um cara ou coroa, sem prever saída nem valor);
- nenhuma família@versão do banco gera outra coisa nas mesmas sementes;
- todo tema e nível conferido tem pelo menos uma família.
"""

import argparse
import ast
import collections
import gc
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from pyvis_motor import gerador, verificador  # noqa: E402
from pyvis_motor.familias import FAMILIAS, NIVEIS, TEMAS  # noqa: E402

DESTINO = RAIZ / "pyvis_motor" / "banco.py"
TAMANHO = 40
MINIMO_DISTINTOS = 30
MAX_SEMENTES = 400
MINIMO_COM_MODELO = 0.25  # 1 em cada 4 itens do banco, por família e nível
MAXIMO_SO_DECISAO = 0.25  # no máximo 1 em cada 4 itens só com "o if vai entrar?"
MUDOU_SEM_VERSAO = "mudou a família publicada sem subir a versao"
LARGURA = 110

CABECALHO = '''"""Banco de sementes da área Praticar. Gerado por analise/verificar_familias.py: não edite à mão.

Para cada "familia@versao:nivel", as primeiras sementes (de 0 em diante) cujo
exercício passou na conferência (verificador.verificar) e é um programa
diferente dos anteriores. A página só abre sementes daqui, então só roda a
conferência barata (escada e textos). IMPRESSOES guarda o sha256 do que essas
sementes geram (gerador.impressao): a família publicada não pode mudar sem
subir a versão. Mudou uma família? Suba a versão dela e rode de novo:

    python3 analise/verificar_familias.py --gravar
"""
'''


def chave(familia, nivel):
    return f"{familia}@{FAMILIAS[familia]['versao']}:{nivel}"


def varrer(familia, nivel):
    """O banco de uma família e nível, com o que o relatório mostra."""
    sementes, chaves = [], set()
    motivos = collections.Counter()
    esqueletos = collections.Counter()
    concepcoes = collections.Counter()
    maiores = dict.fromkeys(verificador.ORCAMENTO[(FAMILIAS[familia]["tema"], nivel)], 0)
    com_modelo = so_decisao = testadas = aceitas = 0
    inicio = time.perf_counter()
    for semente in range(MAX_SEMENTES):
        if len(sementes) == TAMANHO:
            break
        testadas += 1
        exercicio = gerador.gerar(familia, nivel, semente)
        conferencia = verificador.verificar(exercicio)
        if not conferencia["ok"]:
            motivos.update(conferencia["motivos"])
            continue
        aceitas += 1
        if conferencia["chave"] in chaves:
            motivos["repetido"] += 1
            continue
        chaves.add(conferencia["chave"])
        sementes.append(semente)
        esqueletos[exercicio["esqueleto"]] += 1
        concepcoes.update(conferencia["concepcoes"])
        for medida in maiores:
            maiores[medida] = max(maiores[medida], conferencia["medidas"][medida])
        com_modelo += bool(conferencia["concepcoes"])
        so_decisao += conferencia["so_decisao"]
    return {
        "sementes": tuple(sementes),
        "testadas": testadas,
        "aceitas": aceitas,
        "motivos": motivos,
        "esqueletos": esqueletos,
        "concepcoes": concepcoes,
        "com_modelo": com_modelo,
        "so_decisao": so_decisao,
        "maiores": maiores,
        "ms": (time.perf_counter() - inicio) * 1000 / max(testadas, 1),
    }


def portas(familia, nivel, varredura):
    """Os problemas que fazem o script falhar, para uma família e nível."""
    falhas = []
    sementes = varredura["sementes"]
    if len(sementes) < TAMANHO:
        falhas.append(f"só {len(sementes)} sementes no banco (precisa de {TAMANHO} em {MAX_SEMENTES})")
    if len(sementes) < MINIMO_DISTINTOS:
        falhas.append(f"só {len(sementes)} programas distintos (precisa de {MINIMO_DISTINTOS})")
    todos = [e["id"] for e in FAMILIAS[familia]["niveis"][nivel]]
    faltando = [e for e in todos if e not in varredura["esqueletos"]]
    if faltando:
        falhas.append(f"esqueletos fora do banco: {', '.join(faltando)}")
    if sementes and varredura["com_modelo"] / len(sementes) < MINIMO_COM_MODELO:
        falhas.append(f"só {varredura['com_modelo']} de {len(sementes)} itens com distrator de modelo")
    if sementes and varredura["so_decisao"] / len(sementes) > MAXIMO_SO_DECISAO:
        falhas.append(f"{varredura['so_decisao']} de {len(sementes)} itens só com \"o if vai entrar?\" nas alternativas")
    return falhas


def congeladas(atual, impressoes, chaves):
    """As entradas já gravadas que, nas mesmas sementes, geram outra coisa sem a versão ter subido."""
    mudadas = []
    for chave_do_banco in chaves:
        if chave_do_banco not in atual or chave_do_banco not in impressoes:
            continue
        familia_e_versao, nivel = chave_do_banco.split(":")
        familia = familia_e_versao.split("@")[0]
        if gerador.impressao(familia, int(nivel), atual[chave_do_banco]) != impressoes[chave_do_banco]:
            mudadas.append(chave_do_banco)
    return mudadas


def escolher(temas, familias):
    """As famílias conferidas (as de --tema e as de --familia; sem filtro, todas)."""
    desconhecidas = [f for f in familias if f not in FAMILIAS]
    if desconhecidas:
        raise SystemExit(f"família desconhecida: {', '.join(desconhecidas)}")
    ids = [t["id"] for t in TEMAS]
    desconhecidos = [t for t in temas if t not in ids]
    if desconhecidos:
        raise SystemExit(f"tema desconhecido: {', '.join(desconhecidos)} (os temas são {', '.join(ids)})")
    if not temas and not familias:
        return sorted(FAMILIAS)
    return sorted(f for f, dados in FAMILIAS.items() if f in familias or dados["tema"] in temas)


def texto_do_banco(banco, impressoes):
    linhas = [CABECALHO, "BANCO = {"]
    for chave_do_banco, sementes in sorted(banco.items()):
        inicio = f'    "{chave_do_banco}": ('
        corpo = ", ".join(str(s) for s in sementes) + ("," if len(sementes) == 1 else "")
        if len(inicio) + len(corpo) + 2 <= LARGURA:
            linhas.append(f"{inicio}{corpo}),")
            continue
        linhas.append(inicio)
        atual = "       "
        for semente in sementes:
            pedaco = f" {semente},"
            if len(atual) + len(pedaco) > LARGURA:
                linhas.append(atual)
                atual = "       "
            atual += pedaco
        linhas.append(atual)
        linhas.append("    ),")
    linhas.append("}")
    linhas.append("")
    linhas.append("IMPRESSOES = {")
    linhas += [f'    "{chave_do_banco}": "{impressoes[chave_do_banco]}",' for chave_do_banco in sorted(banco)]
    linhas.append("}")
    return "\n".join(linhas) + "\n"


def banco_atual():
    """(BANCO, IMPRESSOES) que estão gravados (lidos como dado, sem importar o módulo)."""
    lidos = {"BANCO": {}, "IMPRESSOES": {}}
    if not DESTINO.exists():
        return lidos["BANCO"], lidos["IMPRESSOES"]
    arvore = ast.parse(DESTINO.read_text(encoding="utf-8"))
    for comando in arvore.body:
        nome = getattr(comando.targets[0], "id", None) if isinstance(comando, ast.Assign) else None
        if nome in lidos:
            lidos[nome] = ast.literal_eval(comando.value)
    return lidos["BANCO"], lidos["IMPRESSOES"]


def main(argv):
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = leitor.add_mutually_exclusive_group()
    modo.add_argument("--gravar", action="store_true", help="grava pyvis_motor/banco.py")
    modo.add_argument("--conferir", action="store_true", help="falha se banco.py estiver desatualizado")
    leitor.add_argument("--tema", action="append", default=[], help="só as famílias deste tema (pode repetir)")
    leitor.add_argument("--familia", action="append", default=[], help="só esta família (pode repetir)")
    leitor.add_argument(
        "--familia-nao-publicada", action="store_true",
        help="regrava uma família@versão que mudou, mas ainda não chegou à main (nenhum link mandado)",
    )
    argumentos = leitor.parse_args(argv)

    gc.freeze()  # como o worker: o motor carregado fica fora das coletas de cada execução
    escolhidas = escolher(argumentos.tema, argumentos.familia)
    filtro = bool(argumentos.tema or argumentos.familia)
    falhas = []
    novo = {}
    inicio = time.perf_counter()

    temas = argumentos.tema or ([] if filtro else [t["id"] for t in TEMAS])
    for tema in temas:
        for nivel in NIVEIS:
            if not any(d["tema"] == tema and nivel in d["niveis"] for d in FAMILIAS.values()):
                falhas.append(f"{tema} nível {nivel}: nenhuma família")

    for familia in escolhidas:
        dados = FAMILIAS[familia]
        problemas = gerador.problemas(familia, dados)
        if problemas:
            falhas += problemas
            continue
        print(f"\n{familia}@{dados['versao']} ({dados['tema']})")
        for nivel in sorted(dados["niveis"]):
            varredura = varrer(familia, nivel)
            novo[chave(familia, nivel)] = varredura["sementes"]
            banco = len(varredura["sementes"])
            print(
                f"  nível {nivel}: {varredura['aceitas']} de {varredura['testadas']} sementes aceitas "
                f"({100 * varredura['aceitas'] / varredura['testadas']:.0f}%), {banco} programas distintos no banco, "
                f"{varredura['ms']:.1f} ms por exercício"
            )
            print(f"    esqueletos: {', '.join(f'{e} {n}' for e, n in sorted(varredura['esqueletos'].items()))}")
            parte = varredura["com_modelo"] / banco if banco else 0
            concepcoes = ", ".join(f"{c} {n}" for c, n in sorted(varredura["concepcoes"].items())) or "nenhuma"
            print(f"    com distrator de modelo: {varredura['com_modelo']} de {banco} ({100 * parte:.0f}%): {concepcoes}")
            print(f"    só \"o if vai entrar?\" nas alternativas: {varredura['so_decisao']} de {banco}")
            orcamento = verificador.ORCAMENTO[(dados["tema"], nivel)]
            medidas = ", ".join(f"{m} {n} (teto {orcamento[m]})" for m, n in varredura["maiores"].items())
            print(f"    maiores medidas no banco: {medidas}")
            if varredura["motivos"]:
                recusas = ", ".join(f"{m} {n}" for m, n in varredura["motivos"].most_common())
                print(f"    recusas: {recusas}")
            falhas += [f"{chave(familia, nivel)}: {falha}" for falha in portas(familia, nivel, varredura)]

    atual, impressoes = banco_atual()
    mudadas = congeladas(atual, impressoes, sorted(novo))
    if mudadas and not argumentos.familia_nao_publicada:
        falhas += [f"{chave_do_banco}: {MUDOU_SEM_VERSAO}" for chave_do_banco in mudadas]

    print(f"\n{len(escolhidas)} famílias em {time.perf_counter() - inicio:.1f} s")
    for falha in falhas:
        print(f"FALHOU {falha}")
    if falhas:
        return 1

    # Com filtro, as entradas das outras famílias ficam como estão (se a família@versão ainda existe).
    validas = {chave(f, n) for f, d in FAMILIAS.items() for n in d["niveis"]}
    banco = {c: s for c, s in atual.items() if c in validas} if filtro else {}
    banco.update(novo)
    novas_impressoes = {c: impressoes[c] for c in banco if c not in novo and c in impressoes}
    for chave_do_banco in novo:
        familia_e_versao, nivel = chave_do_banco.split(":")
        novas_impressoes[chave_do_banco] = gerador.impressao(familia_e_versao.split("@")[0], int(nivel), novo[chave_do_banco])
    for chave_do_banco in banco:
        if chave_do_banco not in novas_impressoes:  # entrada antiga sem impressão (banco de antes delas)
            familia_e_versao, nivel = chave_do_banco.split(":")
            novas_impressoes[chave_do_banco] = gerador.impressao(familia_e_versao.split("@")[0], int(nivel), banco[chave_do_banco])
    texto = texto_do_banco(banco, novas_impressoes)
    if argumentos.conferir:
        if not DESTINO.exists() or DESTINO.read_text(encoding="utf-8") != texto:
            print("pyvis_motor/banco.py está desatualizado: rode python3 analise/verificar_familias.py --gravar")
            return 1
        print("banco em dia")
    elif argumentos.gravar:
        DESTINO.write_text(texto, encoding="utf-8")
        print(f"pyvis_motor/banco.py: {sum(len(s) for s in banco.values())} sementes em {len(banco)} entradas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
