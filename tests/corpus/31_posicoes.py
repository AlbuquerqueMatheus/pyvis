# Posições da lista de animais com range(len(...)).
# @entradas: []
# @pontos: saida 7 @1; saida 7 @2; voltas 6; saida tudo
# @concepcoes: C07, C02
animais = ["gato", "cachorro", "coelho", "tartaruga"]
for i in range(len(animais)):
    print(i, animais[i])
