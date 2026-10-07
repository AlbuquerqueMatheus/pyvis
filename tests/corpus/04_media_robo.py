# Média das notas do robô em três provas.
# @entradas: []
# @pontos: valor 8 media; saida 9; decisao 10; saida tudo
# @concepcoes: C08, C05
nota1 = 8
nota2 = 7
nota3 = 8
media = (nota1 + nota2 + nota3) / 3
print("Média:", media)
if media >= 7.5:
    print("Passou de fase!")
else:
    print("Tente de novo")
