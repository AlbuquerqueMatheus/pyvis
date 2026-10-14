"""Famílias de exercícios do tema Laços (área Praticar).

Só dados, como familias_variaveis.py (o formato da família e do esqueleto
está explicado lá): um dicionário FAMILIAS escrito como literal, sem nenhum
outro comando. Toda família daqui tem "tema": "lacos".

Escada do tema (pede Condições 1, que pede Variáveis 1):
- 1: while com um contador simples;
- 2: for sobre range(a, b) ou sobre um texto; acumulador;
- 3: listas, índice, range com passo, break e condição composta no while.
Nada de elif, and/or fora do while, *, // ou %: são de outros temas e níveis.
Também não entram += nem len() (são de Variáveis 2): o contador anda com
"i = i + 1".

Os esqueletos foram pensados para as concepções do catálogo aparecerem como
distrator: o while que "para no meio da volta" (C06) quando o contador muda
antes de outro comando do corpo; o range que "chega até o fim" (C01) e o
que "começa no 1" (C02); a posição 1 como a do primeiro item (C07).

Versões publicadas ficam congeladas: mudar um esqueleto publicado sobe a
"versao" da família e o banco é gerado de novo
(python3 analise/verificar_familias.py --gravar). O banco guarda a impressão
digital do que cada família@versão gera: mudar sem subir a versão faz o
--conferir e o tests/test_banco.py falharem.
"""

FAMILIAS = {
    # Robôs na oficina e foguetes: contagens, recargas, filas e sensores.
    "robo_oficina": {
        "versao": 1,
        "tema": "lacos",
        "niveis": {
            1: (
                {
                    "id": "contagem",
                    "contexto": "O foguete {serie} faz a contagem antes de subir.",
                    "codigo": (
                        "contagem = {n}\n"
                        "while contagem {cmp} {fim}:\n"
                        "    print(contagem)\n"
                        "    contagem = contagem - 1\n"
                        'print("Foguete {serie} subiu")\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "n": ("inteiro", 3, 4, 1),
                        "cmp": ("opcao", (">", ">=")),
                        "fim": ("inteiro", 0, 1, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "recarga",
                    "contexto": "{robo} fica na tomada até a bateria chegar a 100.",
                    "codigo": (
                        "carga = {c}\n"
                        "minutos = 0\n"
                        "while carga < 100:\n"
                        "    carga = carga + {p}\n"
                        "    minutos = minutos + 1\n"
                        'print("Minutos de {robo} na tomada:", minutos)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "c": ("inteiro", 50, 70, 10),
                        "p": ("inteiro", 10, 20, 5),
                    },
                    "regras": (),
                },
                {
                    "id": "bipes",
                    "contexto": "O robô {robo} apita algumas vezes antes de desligar.",
                    "codigo": (
                        "vezes = 0\n"
                        'apitos = ""\n'
                        "while vezes < {n}:\n"
                        "    vezes = vezes + 1\n"
                        '    apitos = apitos + "{som}-"\n'
                        'print("{robo} fez", apitos)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "som": ("lista", "sons_de_robo"),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "andares",
                    "contexto": "{robo} sobe o prédio e desce em um andar só.",
                    "codigo": (
                        "andar = 1\n"
                        "while andar <= {n}:\n"
                        "    if andar == {p}:\n"
                        '        print("{robo} desceu no andar", andar)\n'
                        "    else:\n"
                        '        print("passou pelo andar", andar)\n'
                        "    andar = andar + 1\n"
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "n": ("inteiro", 3, 4, 1),
                        "p": ("inteiro", 1, 3, 1),
                    },
                    "regras": (("menor", "p", "n"),),
                },
            ),
            2: (
                {
                    "id": "soletrar",
                    "contexto": "{robo} soletra o próprio nome com um sinal entre as letras.",
                    "codigo": (
                        'nome = "{robo}"\n'
                        'codigo = ""\n'
                        "for letra in nome:\n"
                        '    codigo = codigo + letra + "{sinal}"\n'
                        "print(codigo)\n"
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "sinal": ("opcao", ("-", ".", "*")),
                    },
                    "regras": (),
                },
                {
                    "id": "caixas",
                    "contexto": "Em cada andar, o robô {robo} guarda mais caixas.",
                    "codigo": (
                        "caixas = 0\n"
                        "for andar in range({a}, {b}):\n"
                        "    caixas = caixas + andar\n"
                        'print("{robo} guardou", caixas, "caixas")\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "a": ("inteiro", 1, 3, 1),
                        "b": ("inteiro", 4, 7, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "treino",
                    "contexto": "{robo} treina dando voltas na pista da oficina.",
                    "codigo": (
                        "for volta in range({n}):\n"
                        '    print("{robo} na volta", volta)\n'
                        'print("{robo} {fim}")\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "n": ("inteiro", 2, 4, 1),
                        "fim": ("opcao", ("parou", "descansou", "voltou para a base")),
                    },
                    "regras": (),
                },
                {
                    "id": "bateria",
                    "contexto": "{robo} carrega a bateria por alguns minutos.",
                    "codigo": (
                        "bateria = {b}\n"
                        "for minuto in range({m}):\n"
                        "    bateria = bateria + {c}\n"
                        'print("Bateria de {robo}:", bateria)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "b": ("inteiro", 10, 40, 10),
                        "m": ("inteiro", 2, 5, 1),
                        "c": ("inteiro", 5, 15, 5),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    "id": "fila",
                    "contexto": "Três robôs esperam na fila da oficina.",
                    "codigo": (
                        'robos = ["{a}", "{b}", "{c}"]\n'
                        "i = 0\n"
                        "while i < {n}:\n"
                        "    print(i, robos[i])\n"
                        "    i = i + 1\n"
                        'print("Item 1 da fila:", robos[1])\n'
                    ),
                    "lacunas": {
                        "a": ("lista", "robos"),
                        "b": ("lista", "robos"),
                        "c": ("lista", "robos"),
                        "n": ("inteiro", 2, 3, 1),
                    },
                    "regras": (("diferentes", "a", "b"), ("diferentes", "a", "c"), ("diferentes", "b", "c")),
                },
                {
                    "id": "elevador",
                    "contexto": "O elevador do robô {robo} pula alguns andares.",
                    "codigo": (
                        "for andar in range({a}, {b}, {p}):\n"
                        '    print("{robo} parou no andar", andar)\n'
                        'print("{robo} chegou ao topo")\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "a": ("inteiro", 0, 2, 1),
                        "b": ("inteiro", 6, 10, 1),
                        "p": ("inteiro", 2, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "energia",
                    "contexto": "{robo} anda até cansar ou até completar o caminho.",
                    "codigo": (
                        "energia = {e}\n"
                        "passos = 0\n"
                        "while energia > {m} and passos < {t}:\n"
                        "    energia = energia - {g}\n"
                        "    passos = passos + 1\n"
                        'print("Passos de {robo}:", passos)\n'
                        'print("Energia:", energia)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "e": ("inteiro", 20, 40, 5),
                        "m": ("inteiro", 5, 15, 5),
                        "g": ("inteiro", 5, 10, 5),
                        "t": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "sensor",
                    "contexto": "O sensor de {robo} confere o calor das peças.",
                    "codigo": (
                        "leituras = [{a}, {b}, {c}, {d}]\n"
                        "for i in range(4):\n"
                        "    if leituras[i] > {lim}:\n"
                        '        print("{robo} parou na leitura", i)\n'
                        "        break\n"
                        '    print("leitura", leituras[i], "ok")\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        # As três primeiras leituras nunca passam do limite: o break, quando vem, vem
                        # na última. Assim mexer no range sempre muda a saída (a conferência de mutação).
                        "a": ("inteiro", 20, 30, 5),
                        "b": ("inteiro", 20, 30, 5),
                        "c": ("inteiro", 20, 30, 5),
                        "d": ("inteiro", 25, 45, 5),
                        "lim": ("inteiro", 30, 35, 5),
                    },
                    "regras": (),
                },
            ),
        },
    },
    # Um jardim com plantas e pets: crescer, passear, letras de nomes, um trem que passa.
    "jardim_pets": {
        "versao": 1,
        "tema": "lacos",
        "niveis": {
            1: (
                {
                    "id": "crescer",
                    "contexto": "A planta cresce um pouco por dia até chegar na cerca.",
                    "codigo": (
                        "altura = {a}\n"
                        "dias = 0\n"
                        "while altura < {cerca}:\n"
                        "    altura = altura + {c}\n"
                        "    dias = dias + 1\n"
                        'print("A planta chegou na cerca. Dias:", dias)\n'
                    ),
                    "lacunas": {
                        "a": ("inteiro", 2, 6, 2),
                        "cerca": ("inteiro", 12, 16, 2),
                        "c": ("inteiro", 3, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "passeio",
                    "contexto": "{pet} dá algumas voltas no {lugar} antes de voltar.",
                    "codigo": (
                        "volta = 1\n"
                        "while volta <= {n}:\n"
                        '    print("{pet} deu a volta", volta)\n'
                        "    volta = volta + 1\n"
                        'print("O contador parou em", volta)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "lugar": ("lista", "lugares"),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "petiscos",
                    "contexto": "{pet} come os petiscos do pote, um de cada vez.",
                    "codigo": (
                        "petiscos = {n}\n"
                        "while petiscos > 0:\n"
                        "    if petiscos == 1:\n"
                        '        print("{pet} limpou o pote")\n'
                        "    else:\n"
                        '        print("{pet} comeu um")\n'
                        "    petiscos = petiscos - 1\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "latidos",
                    "contexto": "{pet} faz barulho algumas vezes quando ouve a campainha.",
                    "codigo": (
                        "barulhos = 0\n"
                        'texto = ""\n'
                        "while barulhos < {n}:\n"
                        "    barulhos = barulhos + 1\n"
                        '    texto = texto + "{som} "\n'
                        'print(texto + "e {pet} ficou quieto")\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "som": ("lista", "sons_de_pet"),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
            ),
            2: (
                {
                    "id": "invertido",
                    "contexto": "O nome de {pet} vai ser escrito de trás para a frente.",
                    "codigo": (
                        'nome = "{pet}"\n'
                        'invertido = ""\n'
                        "for letra in nome:\n"
                        "    invertido = letra + invertido\n"
                        "print(invertido)\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                    },
                    "regras": (),
                },
                {
                    "id": "folhas",
                    "contexto": "A cada dia, a planta tem mais folhas novas.",
                    "codigo": (
                        "folhas = {f}\n"
                        "for dia in range({a}, {b}):\n"
                        "    folhas = folhas + dia\n"
                        'print("A planta tem", folhas, "folhas")\n'
                    ),
                    "lacunas": {
                        "f": ("inteiro", 0, 4, 2),
                        "a": ("inteiro", 1, 3, 1),
                        "b": ("inteiro", 4, 6, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "fornadas",
                    "contexto": "A padaria do bairro assa bolos em várias fornadas.",
                    "codigo": (
                        "bolos = 0\n"
                        "for fornada in range({n}):\n"
                        "    bolos = bolos + {p}\n"
                        '    print("fornada", fornada, "pronta")\n'
                        'print(bolos, "bolos de {sabor}")\n'
                    ),
                    "lacunas": {
                        "n": ("inteiro", 2, 4, 1),
                        "p": ("inteiro", 6, 12, 2),
                        "sabor": ("opcao", ("milho", "queijo", "banana", "cenoura")),
                    },
                    "regras": (),
                },
                {
                    "id": "letras_da_cor",
                    "contexto": "{pet} tenta trocar a letra {l} na cor {cor}.",
                    "codigo": (
                        'cor = "{cor}"\n'
                        'nova = ""\n'
                        "for letra in cor:\n"
                        '    if letra == "{l}":\n'
                        '        nova = nova + "{sinal}"\n'
                        "    else:\n"
                        "        nova = nova + letra\n"
                        "print(nova)\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "cor": ("lista", "cores"),
                        "l": ("opcao", ("a", "e", "o", "r")),
                        "sinal": ("opcao", ("*", "_", "#")),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    "id": "fila_de_pets",
                    "contexto": "Três pets esperam na fila do banho.",
                    "codigo": (
                        'pets = ["{a}", "{b}", "{c}"]\n'
                        'pets[{i}] = "{d}"\n'
                        "for pet in pets:\n"
                        '    print(pet, "tomou banho")\n'
                        'print("Item 1 da fila:", pets[1])\n'
                    ),
                    "lacunas": {
                        "a": ("lista", "pets"),
                        "b": ("lista", "pets"),
                        "c": ("lista", "pets"),
                        "d": ("lista", "pets"),
                        "i": ("inteiro", 0, 2, 1),
                    },
                    "regras": (
                        ("diferentes", "a", "b"), ("diferentes", "a", "c"), ("diferentes", "b", "c"),
                        ("diferentes", "a", "d"), ("diferentes", "b", "d"), ("diferentes", "c", "d"),
                    ),
                },
                {
                    "id": "trem",
                    "contexto": "O {veiculo} da cidade só para em algumas paradas.",
                    "codigo": (
                        "for parada in range({a}, {b}, {p}):\n"
                        '    print("O {veiculo} parou na parada", parada)\n'
                        'print("Fim da linha")\n'
                    ),
                    "lacunas": {
                        "veiculo": ("opcao", ("trem", "bonde")),
                        "a": ("inteiro", 1, 3, 1),
                        "b": ("inteiro", 7, 11, 1),
                        "p": ("inteiro", 2, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "regar",
                    "contexto": "Cada vaso da fileira pede alguns copos para regar.",
                    "codigo": (
                        "copos = [{a}, {b}, {c}, {d}]\n"
                        "i = 0\n"
                        "total = 0\n"
                        "while i < {n}:\n"
                        "    total = total + copos[i]\n"
                        "    i = i + 1\n"
                        'print("Os", i, "primeiros vasos usaram", total, "copos")\n'
                    ),
                    "lacunas": {
                        "a": ("inteiro", 1, 3, 1),
                        "b": ("inteiro", 1, 3, 1),
                        "c": ("inteiro", 1, 3, 1),
                        "d": ("inteiro", 1, 3, 1),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "frutas",
                    "contexto": "{pet} prova algumas frutas da cesta, pulando de duas em duas.",
                    "codigo": (
                        'frutas = ["{f0}", "{f1}", "{f2}", "{f3}", "{f4}"]\n'
                        "for i in range({ini}, 5, 2):\n"
                        '    print("{pet} provou", frutas[i])\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "ini": ("inteiro", 0, 1, 1),
                        "f0": ("opcao", ("uva", "pera")),
                        "f1": ("opcao", ("manga", "kiwi")),
                        "f2": ("opcao", ("caju", "banana")),
                        "f3": ("opcao", ("morango", "goiaba")),
                        "f4": ("opcao", ("melancia", "laranja")),
                    },
                    "regras": (),
                },
                {
                    "id": "tigelas",
                    "contexto": "{pet} procura comida nas tigelas da cozinha.",
                    "codigo": (
                        "tigelas = [{a}, {b}, {c}, {d}]\n"
                        "for i in range(4):\n"
                        "    if tigelas[i] == 0:\n"
                        '        print("{pet} achou a tigela vazia", i)\n'
                        "        break\n"
                        '    print("tigela", i, "tem", tigelas[i])\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        # Só a última tigela pode estar vazia, como no sensor de robo_oficina.
                        "a": ("inteiro", 1, 3, 1),
                        "b": ("inteiro", 1, 3, 1),
                        "c": ("inteiro", 1, 3, 1),
                        "d": ("inteiro", 0, 1, 1),
                    },
                    "regras": (),
                },
            ),
        },
    },
}
