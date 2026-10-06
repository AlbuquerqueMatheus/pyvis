# Conceito do quiz de ciências: if, elif e else.
# @entradas: []
# @pontos: decisao 6; decisao 8; valor 9 conceito; saida 14
# @concepcoes: C05
acertos = 72
if acertos >= 90:
    conceito = "A"
elif acertos >= 70:
    conceito = "B"
elif acertos >= 50:
    conceito = "C"
else:
    conceito = "D"
print("Conceito:", conceito)
