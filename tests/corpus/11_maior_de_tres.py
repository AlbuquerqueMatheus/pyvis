# O maior de três números, sem else.
# @entradas: []
# @pontos: decisao 9; valor 10 maior; decisao 11; saida 13
# @concepcoes: C04
a = 12
b = 25
c = 18
maior = a
if b > maior:
    maior = b
if c > maior:
    maior = c
print("O maior é", maior)
