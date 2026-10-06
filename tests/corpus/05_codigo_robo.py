# Código do robô: juntando textos que vieram do input.
# @entradas: ["Bipo", "3"]
# @pontos: valor 6 versao; valor 7 codigo; saida 8; saida 9
# @concepcoes: C03
nome = input("Nome do robô: ")
versao = input("Versão: ")
codigo = nome + "-" + versao
print("Código:", codigo)
print("Tamanho do código:", len(codigo))
