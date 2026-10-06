# Contando os dígitos de um número com while.
# @entradas: []
# @pontos: valor 8 numero @1; voltas 7; saida 10; valor 9 digitos @4
# @concepcoes: C06, C04
numero = 4096
digitos = 0
while numero > 0:
    numero = numero // 10
    digitos = digitos + 1
print("O número tem", digitos, "dígitos")
