# Contando as vogais de uma palavra digitada.
# @entradas: ["arara"]
# @pontos: decisao 8 @2; valor 9 vogais @3; saida 10; voltas 7
# @concepcoes: C04
palavra = input("Palavra: ")
vogais = 0
for letra in palavra:
    if letra in "aeiou":
        vogais = vogais + 1
print(palavra, "tem", vogais, "vogais")
