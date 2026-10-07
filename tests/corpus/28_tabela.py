# Tabela de multiplicar 3 por 3 com dois for.
# @entradas: []
# @pontos: voltas 5; voltas 7 @2; valor 8 texto @2; saida 9 @1; saida tudo
# @concepcoes: C01, C04
for linha in range(1, 4):
    texto = ""
    for coluna in range(1, 4):
        texto = texto + str(linha * coluna) + " "
    print(texto)
