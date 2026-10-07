# Bom dia ou boa tarde, conforme o relógio.
# @entradas: []
# @pontos: decisao 7; voltas 12; valor 13 contagem @1
# @concepcoes: C04, C05
import time
hora = time.localtime().tm_hour
if hora < 12:
    print("Bom dia, robô!")
else:
    print("Boa tarde, robô!")
contagem = 3
while contagem > 0:
    contagem = contagem - 1
print("Pronto")
