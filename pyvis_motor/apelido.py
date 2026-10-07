"""Apelidos gerados: o aluno participa sem dizer o nome.

Um apelido é bicho + cor + número, como "Tucano Azul 7", tirado de listas
fechadas. Apelido livre permite ofensa e permite se passar por um colega;
com listas fechadas, validar() aceita só o que gerar() pode produzir.

As listas evitam o que vira apelido maldoso na escola: bichos usados como
xingamento, ofensa racista ou piada com o corpo (macaco, urubu, veado,
burro, baleia, girafa...), bichos que são nome de gente (Ema, Joaninha),
cores de pele (preto, branco, marrom) e números com sentido ruim.

O sorteio usa sha256 da semente, e não o random: o mesmo apelido sai igual
em qualquer versão do Python e pode ser refeito em outra linguagem.
"""

import hashlib
import random

# (nome, gênero): o gênero decide a forma da cor ("Coruja Amarela").
ANIMAIS = (
    ("Tucano", "m"), ("Lobo", "m"), ("Leão", "m"), ("Tigre", "m"), ("Golfinho", "m"),
    ("Pinguim", "m"), ("Panda", "m"), ("Coala", "m"), ("Canguru", "m"), ("Esquilo", "m"),
    ("Coelho", "m"), ("Castor", "m"), ("Falcão", "m"), ("Polvo", "m"), ("Tubarão", "m"),
    ("Flamingo", "m"), ("Cisne", "m"), ("Papagaio", "m"), ("Sabiá", "m"), ("Bem-te-vi", "m"),
    ("Tatu", "m"), ("Tamanduá", "m"), ("Quati", "m"), ("Sagui", "m"), ("Jacaré", "m"),
    ("Lince", "m"), ("Camaleão", "m"), ("Ouriço", "m"), ("Pelicano", "m"), ("Beija-flor", "m"),
    ("Jabuti", "m"), ("Texugo", "m"), ("Guepardo", "m"), ("Vaga-lume", "m"),
    ("Arara", "f"), ("Coruja", "f"), ("Onça", "f"), ("Raposa", "f"), ("Capivara", "f"),
    ("Lontra", "f"), ("Ariranha", "f"), ("Borboleta", "f"), ("Abelha", "f"), ("Zebra", "f"),
    ("Lhama", "f"), ("Alpaca", "f"), ("Gaivota", "f"), ("Garça", "f"), ("Seriema", "f"),
    ("Andorinha", "f"), ("Calopsita", "f"), ("Iguana", "f"), ("Lebre", "f"), ("Libélula", "f"),
    ("Pantera", "f"), ("Ararajuba", "f"),
)

# (masculino, feminino)
CORES = (
    ("Azul", "Azul"), ("Verde", "Verde"), ("Amarelo", "Amarela"), ("Vermelho", "Vermelha"),
    ("Laranja", "Laranja"), ("Roxo", "Roxa"), ("Lilás", "Lilás"), ("Dourado", "Dourada"),
    ("Prateado", "Prateada"), ("Turquesa", "Turquesa"), ("Cinza", "Cinza"), ("Anil", "Anil"),
)

# 24 e 69 viram piada maldosa; 14, 18 e 88 são códigos de ódio; 51 é marca de
# cachaça; 13, 17 e 22 são números de campanha presidencial recentes.
NUMEROS_EVITADOS = frozenset({13, 14, 17, 18, 22, 24, 51, 69, 88})
NUMEROS = tuple(n for n in range(1, 100) if n not in NUMEROS_EVITADOS)

_GENERO = dict(ANIMAIS)
_CORES = {"m": {m for m, _ in CORES}, "f": {f for _, f in CORES}}
_NUMEROS = {str(n) for n in NUMEROS}


def _escolher(lista, resumo, parte):
    return lista[int.from_bytes(resumo[4 * parte : 4 * parte + 4], "big") % len(lista)]


def gerar(semente=None):
    """Apelido da semente (int ou texto); sem semente, um apelido qualquer."""
    if semente is None:
        semente = random.SystemRandom().randrange(2**31)
    resumo = hashlib.sha256(f"apelido:{semente}".encode("utf-8", "surrogatepass")).digest()
    animal, genero = _escolher(ANIMAIS, resumo, 0)
    masculino, feminino = _escolher(CORES, resumo, 1)
    numero = _escolher(NUMEROS, resumo, 2)
    return f"{animal} {masculino if genero == 'm' else feminino} {numero}"


def sugestoes(semente, quantidade=4):
    """Apelidos diferentes para o aluno trocar; o primeiro é gerar(semente)."""
    if not 1 <= quantidade <= 20:
        raise ValueError("peça de 1 a 20 sugestões")
    vistos = [gerar(semente)]
    tentativa = 0
    while len(vistos) < quantidade:
        tentativa += 1
        apelido = gerar(f"{semente}:{tentativa}")
        if apelido not in vistos:
            vistos.append(apelido)
    return vistos


def validar(apelido):
    """True só para apelidos que gerar() pode produzir, escritos igualzinho."""
    if not isinstance(apelido, str):
        return False
    partes = apelido.split(" ")
    if len(partes) != 3:
        return False
    animal, cor, numero = partes
    genero = _GENERO.get(animal)
    return genero is not None and cor in _CORES[genero] and numero in _NUMEROS
