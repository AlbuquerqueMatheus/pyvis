# Janelas de um prédio com dois for.
# @entradas: []
# @pontos: voltas 5; voltas 6 @2; saida 7 @1; saida tudo
# @concepcoes: C01, C02
for andar in range(3):
    for janela in range(andar):
        print("Andar", andar, "janela", janela)
