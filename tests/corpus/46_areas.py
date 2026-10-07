# Áreas de retângulo e triângulo com funções.
# @entradas: []
# @pontos: valor 11 r; valor 12 t; saida 13; saida 14
# @concepcoes: C08
def area_retangulo(base, altura):
    return base * altura

def area_triangulo(base, altura):
    return base * altura / 2

r = area_retangulo(4, 3)
t = area_triangulo(5, 3)
print("Retângulo:", r)
print("Triângulo:", t)
