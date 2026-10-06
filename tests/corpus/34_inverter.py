# Invertendo uma lista com while e posições.
# @entradas: []
# @pontos: voltas 8; valor 10 i @1; saida 11
# @concepcoes: C07, C04
letras = ["a", "b", "c", "d"]
invertida = []
i = len(letras) - 1
while i >= 0:
    invertida.append(letras[i])
    i = i - 1
print(invertida)
