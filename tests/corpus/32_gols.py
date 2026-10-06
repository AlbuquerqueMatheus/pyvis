# Gols do time de robôs: soma e média de uma lista.
# @entradas: []
# @pontos: valor 8 total @3; valor 9 media; saida 11; voltas 7
# @concepcoes: C04, C08
gols = [2, 0, 3, 1]
total = 0
for g in gols:
    total = total + g
media = total / len(gols)
print("Total de gols:", total)
print("Média por jogo:", media)
