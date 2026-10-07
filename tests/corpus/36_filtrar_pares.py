# Separando os números pares numa lista nova.
# @entradas: []
# @pontos: decisao 8 @2; voltas 7; saida 10; saida 11
# @concepcoes: nenhuma
numeros = [3, 8, 5, 12, 7, 4]
pares = []
for n in numeros:
    if n % 2 == 0:
        pares.append(n)
print("Pares:", pares)
print("Quantos:", len(pares))
