# Dividindo a pizza entre amigos: //, % e /.
# @entradas: []
# @pontos: valor 7 cada_um; valor 8 sobra; saida 9; valor 11 dividido; saida 12
# @concepcoes: C08
fatias = 8
amigos = 3
cada_um = fatias // amigos
sobra = fatias % amigos
print("Cada um come", cada_um, "fatias")
print("Sobram", sobra)
dividido = fatias / amigos
print("Dividindo tudo:", dividido)
