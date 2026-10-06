# Dias de calor no zoológico, percorrendo a lista com while.
# @entradas: []
# @pontos: decisao 10 @2; valor 11 quentes @1; voltas 9; saida 13
# @concepcoes: C07, C04
temperaturas = [18, 25, 31, 22, 29]
dia = 0
quentes = 0
limite = 24
while dia < len(temperaturas):
    if temperaturas[dia] > limite:
        quentes = quentes + 1
    dia = dia + 1
print("Dias quentes:", quentes)
