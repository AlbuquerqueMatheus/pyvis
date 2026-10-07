# Fatorial com for: multiplicando um acumulador.
# @entradas: []
# @pontos: valor 8 fatorial @3; voltas 7; saida 9
# @concepcoes: C01, C04
n = 5
fatorial = 1
for i in range(1, n + 1):
    fatorial = fatorial * i
print(n, "! =", fatorial)
