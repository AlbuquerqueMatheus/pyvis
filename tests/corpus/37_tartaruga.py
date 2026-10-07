# Tempo médio da tartaruga na corrida.
# @entradas: []
# @pontos: valor 8 soma @2; valor 9 media; decisao 10; saida tudo
# @concepcoes: C08, C05, C04
tempos = [14, 15, 12, 13]
soma = 0
for t in tempos:
    soma = soma + t
media = soma / len(tempos)
if media > 13:
    print("A tartaruga foi devagar. Média:", media)
else:
    print("A tartaruga foi rápida! Média:", media)
