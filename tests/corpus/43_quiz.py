# Quiz de duas perguntas com input e if.
# @entradas: ["7", "Brasília"]
# @pontos: decisao 7; valor 8 acertos; decisao 10; saida 12
# @concepcoes: C03, C04
acertos = 0
resposta = input("Quanto é 3 + 4? ")
if resposta == "7":
    acertos = acertos + 1
resposta = input("Capital do Brasil? ")
if resposta == "Brasília":
    acertos = acertos + 1
print("Você acertou", acertos, "de 2")
