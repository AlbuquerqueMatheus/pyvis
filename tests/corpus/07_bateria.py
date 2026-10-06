# Bateria do robô: if com else.
# @entradas: []
# @pontos: decisao 6; saida 7; valor 8 bateria; saida tudo
# @concepcoes: C05, C04
bateria = 15
if bateria < 20:
    print("Bateria fraca, hora de carregar")
    bateria = bateria + 50
else:
    print("Pode brincar!")
print("Bateria agora:", bateria)
