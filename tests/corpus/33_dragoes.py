# Quantos dragões já podem voar sozinhos?
# @entradas: []
# @pontos: decisao 8 @1; decisao 8 @5; valor 9 podem_voar @2; saida 10; voltas 7
# @concepcoes: C04
idades = [9, 14, 11, 16, 12]
podem_voar = 0
for idade in idades:
    if idade >= 12:
        podem_voar = podem_voar + 1
print(podem_voar, "dragões já podem voar sozinhos")
