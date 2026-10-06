# Quantos meses até a toca ter 100 coelhos?
# @entradas: []
# @pontos: voltas 7; valor 8 coelhos @2; valor 9 meses @3; saida 10; decisao 7 @7
# @concepcoes: C06, C04
coelhos = 2
meses = 0
while coelhos < 100:
    coelhos = coelhos * 2
    meses = meses + 1
print("Depois de", meses, "meses há", coelhos, "coelhos")
