"""Catálogo da área Praticar: temas, listas fechadas de nomes e as famílias.

Os temas e as listas são dados. As famílias moram em um arquivo por tema
(familias_variaveis.py, familias_condicoes.py, familias_lacos.py), também só
dados, e aqui só se juntam num dicionário. O gerador (gerador.py) sorteia
dentro destas listas; nenhum nome sai de fora delas, então nenhum exercício
fala de pessoas de verdade.

Os níveis aparecem para o aluno pelo nome do conteúdo, nunca pelo número.
As listas só têm palavras que não levam acento nenhum: o aluno digita a
resposta livre, e uma palavra sem o acento que ela pede ("Pacoca", "racao")
faria a resposta certa em português virar erro. Palavra com acento é trocada
por outra que não tem, nunca escrita sem ele.
"""

from .familias_condicoes import FAMILIAS as _CONDICOES
from .familias_lacos import FAMILIAS as _LACOS
from .familias_variaveis import FAMILIAS as _VARIAVEIS

LISTAS = {
    "robos": ("Nino", "Bip", "Tico", "Lumi", "Byte", "Pixel", "Volt", "Chip", "Dex", "Zip"),
    "pets": ("Rex", "Mimi", "Bolinha", "Pipoca", "Thor", "Luna", "Lola", "Bidu", "Fred", "Mel", "Pingo", "Nina"),
    "comidas": ("feno", "cenoura", "alpiste", "petisco", "banana", "milho", "pepino"),
    "lugares": ("parque", "jardim", "quintal", "bosque", "campo"),
    "series": ("X1", "Z9", "K2", "T7", "R5", "M3"),
    "sons_de_robo": ("bip", "pi", "zum", "tic"),
    "sons_de_pet": ("au", "miau", "piu", "oinc", "rrr"),
    "cores": ("azul", "verde", "laranja", "roxo", "amarelo", "vermelho"),
    "frutas": ("figo", "uva", "pera", "manga", "kiwi", "caju"),
    "plantas": ("rosa", "cacto", "girassol", "samambaia", "violeta", "tulipa", "margarida"),
    "estacoes": ("Centro", "Porto", "Lago", "Serra", "Vila", "Ponte", "Mirante"),
}

TEMAS = (
    {
        "id": "variaveis",
        "nome": "Variáveis",
        "descricao": "Guardar valores com nomes, mudar e juntar.",
        "niveis": {1: "Guardar e mudar valores", 2: "Contas e textos", 3: "Trocar e converter"},
    },
    {
        "id": "condicoes",
        "nome": "Condições",
        "descricao": "O programa escolhe um caminho com if e else.",
        "niveis": {1: "Se e senão", 2: "Vários caminhos com elif", 3: "Juntar condições"},
    },
    {
        "id": "lacos",
        "nome": "Laços",
        "descricao": "Repetir comandos com while e for.",
        "niveis": {1: "Repetir com while", 2: "Repetir com for", 3: "Listas, saltos e paradas"},
    },
)

NIVEIS = (1, 2, 3)

FAMILIAS = {**_VARIAVEIS, **_CONDICOES, **_LACOS}
