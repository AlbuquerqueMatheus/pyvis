# Senha do cofre do robô: while com input.
# @entradas: ["abc", "123", "robo123"]
# @pontos: voltas 7; valor 9 senha @1; valor 10 tentativas @2; saida 11; decisao 7 @1
# @concepcoes: C03, C06, C04
senha = input("Senha: ")
tentativas = 1
while senha != "robo123":
    print("Senha errada!")
    senha = input("Senha: ")
    tentativas = tentativas + 1
print("Entrou depois de", tentativas, "tentativas")
