# Quantas vezes a letra a aparece em abacaxi?
# @entradas: []
# @pontos: decisao 8 @1; decisao 8 @2; valor 9 contador @2; saida 10; voltas 7
# @concepcoes: C04
palavra = "abacaxi"
contador = 0
for letra in palavra:
    if letra == "a":
        contador = contador + 1
print("A letra a aparece", contador, "vezes")
