# Semáforo do robô entregador: if, elif e else com input.
# @entradas: ["amarelo"]
# @pontos: decisao 6; decisao 8; valor 9 acao; saida 12
# @concepcoes: C05
cor = input("Cor do semáforo: ")
if cor == "verde":
    acao = "pode passar"
elif cor == "amarelo":
    acao = "atenção"
else:
    acao = "pare"
print("O robô vai:", acao)
