# Jogo do Pi-Pa: múltiplos de 3 e de 5.
# @entradas: []
# @pontos: voltas 5; decisao 6 @3; saida 7 @1; saida 11 @1; saida tudo
# @concepcoes: C01, C05
for n in range(1, 11):
    if n % 3 == 0:
        print("Pi")
    elif n % 5 == 0:
        print("Pa")
    else:
        print(n)
