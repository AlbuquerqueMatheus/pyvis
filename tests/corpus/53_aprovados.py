# Robôs aprovados e reprovados numa lista de notas.
# @entradas: []
# @pontos: decisao 9 @1; valor 10 aprovados @1; saida 14; saida tudo
# @concepcoes: C05, C04
notas = [7, 4, 9]
aprovados = 0
reprovados = 0
for nota in notas:
    if nota >= 6:
        aprovados = aprovados + 1
    else:
        reprovados = reprovados + 1
print("Aprovados:", aprovados)
print("Reprovados:", reprovados)
