# Lista de compras do cachorro: append e posições.
# @entradas: []
# @pontos: saida 7; valor 10 ultimo; saida 11
# @concepcoes: C07
lista = ["ração", "osso"]
lista.append("bolinha")
print("Itens:", len(lista))
lista.append("coleira")
primeiro = lista[0]
ultimo = lista[len(lista) - 1]
print(primeiro, "e", ultimo)
