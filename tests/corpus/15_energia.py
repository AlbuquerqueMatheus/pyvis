# Robô andando até a energia acabar.
# @entradas: []
# @pontos: voltas 7; valor 8 energia @2; saida 10 @1; decisao 7 @5; saida tudo
# @concepcoes: C06, C04
energia = 10
distancia = 0
while energia > 0:
    energia = energia - 3
    distancia = distancia + 1
    print("Andou", distancia, "metros, energia", energia)
print("Parou com energia", energia)
