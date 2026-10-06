# Cofrinho: soma moedas até digitar 0.
# @entradas: ["5", "10", "2", "0"]
# @pontos: voltas 7; valor 8 total @2; saida 10
# @concepcoes: C04
total = 0
valor = int(input("Moedas (0 para parar): "))
while valor != 0:
    total = total + valor
    valor = int(input("Moedas (0 para parar): "))
print("Total no cofrinho:", total)
