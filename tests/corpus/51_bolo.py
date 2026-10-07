# Cortando o bolo ao meio até sobrar pouco.
# @entradas: []
# @pontos: voltas 7; valor 8 bolo @2; saida 10
# @concepcoes: C08, C06, C04
bolo = 10
cortes = 0
while bolo > 1:
    bolo = bolo / 2
    cortes = cortes + 1
print("Cortes:", cortes, "pedaço final:", bolo)
