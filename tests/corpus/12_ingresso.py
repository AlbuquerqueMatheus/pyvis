# Preço do ingresso do parque dos dinossauros.
# @entradas: ["15"]
# @pontos: decisao 6; decisao 8; saida 12; valor 13 desconto; saida 14
# @concepcoes: C05, C08
idade = int(input("Idade do visitante: "))
if idade < 12:
    preco = 10
elif idade < 60:
    preco = 20
else:
    preco = 12
print("Ingresso: R$", preco)
desconto = preco / 2
print("Com meia-entrada: R$", desconto)
