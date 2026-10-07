# Jogo de adivinhar o número secreto do dragão.
# @entradas: ["1", "2", "3", "4", "5"]
# @semente: 0
# @pontos: valor 7 segredo; voltas 9; saida 12
# @concepcoes: nenhuma
import random
segredo = random.randint(1, 5)
palpite = int(input("Seu palpite: "))
while palpite != segredo:
    print("Errou!")
    palpite = int(input("Seu palpite: "))
print("Acertou! O número era", segredo)
