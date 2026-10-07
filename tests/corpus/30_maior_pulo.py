# O maior pulo do sapo numa lista.
# @entradas: []
# @pontos: decisao 8 @2; valor 9 maior @1; saida 10; voltas 7
# @concepcoes: C04
pulos = [12, 30, 25, 8]
maior = pulos[0]
for pulo in pulos:
    if pulo > maior:
        maior = pulo
print("O maior pulo do sapo foi", maior)
