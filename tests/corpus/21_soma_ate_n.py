# Soma de 1 até o número digitado.
# @entradas: ["5"]
# @pontos: voltas 7; valor 8 soma @2; saida 9
# @concepcoes: C01, C04
n = int(input("Somar até: "))
soma = 0
for i in range(1, n + 1):
    soma = soma + i
print("A soma de 1 até", n, "é", soma)
