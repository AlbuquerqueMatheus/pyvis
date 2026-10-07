# O papagaio repete a frase várias vezes.
# @entradas: ["Olá!", "3"]
# @pontos: voltas 7; saida 8 @1; saida tudo
# @concepcoes: C01, C02
frase = input("Frase do papagaio: ")
vezes = int(input("Quantas vezes? "))
for i in range(vezes):
    print(i + 1, frase)
