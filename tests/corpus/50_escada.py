# Gato subindo a escada até a altura 12.
# @entradas: []
# @pontos: saida 11 @2; voltas 8; valor 9 altura @3; decisao 8 @4; saida tudo
# @concepcoes: C06, C07, C04
degraus = [3, 5, 2, 6, 4]
i = 0
altura = 0
while altura < 12:
    altura = altura + degraus[i]
    i = i + 1
    print("Subiu", i, "degraus, altura", altura)
print("Chegou ao topo!")
