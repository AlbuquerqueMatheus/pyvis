"""Famílias de exercícios do tema Variáveis (área Praticar).

Este arquivo é só dados: um dicionário FAMILIAS escrito como literal, sem
nenhum outro comando. O teste (tests/test_familias.py) lê o arquivo com ast
e confere que o valor sai de ast.literal_eval. Assim uma família proposta por
qualquer pessoa (ou por uma IA) entra como dado revisável, nunca como código.

Formato de uma família (o mesmo em familias_condicoes.py e familias_lacos.py):

    "id_da_familia": {
        "versao": 1,
        "tema": "variaveis",
        "niveis": {1: (esqueleto, ...), 2: (...), 3: (...)},
    }

Formato de um esqueleto:

    {
        "id": "gasto",                               # único dentro da família
        "contexto": "O robô {robo} andou e gastou energia.",
        "codigo": 'robo = "{robo}"\\nenergia = {e}\\n...',
        "lacunas": {
            "robo": ("lista", "robos"),              # um item de familias.LISTAS
            "e": ("inteiro", 50, 90, 5),             # de 50 a 90 (inclusive), de 5 em 5
            "op": ("opcao", ("+", "-")),             # um destes textos, como está
        },
        "regras": (("diferentes", "a", "b"), ("menor", "g", "e")),
    }

O contexto é uma frase curta (até 12 palavras, sem pergunta: quem pergunta é
o motor). Os textos entre aspas no código e o que o programa escreve só usam
palavras que não levam acento nenhum: o aluno digita a resposta livre, e uma
palavra escrita sem o acento que ela pede ("racao") faria a resposta certa
("ração") virar erro. Troque a palavra ("comida"), nunca tire o acento. Nem
"1 copos": a faixa da lacuna ou um rótulo ("Sobra: 1") evita o plural com 1.

Escada do tema (o verificador recusa o que passar do nível):
- 1: atribuição, reatribuição, + e - com inteiros, juntar textos com +, print;
- 2: acrescenta *, //, %, texto * inteiro, len e +=;
- 3: acrescenta a troca a, b = b, a, int(), str() e /.

Versões publicadas ficam congeladas: o banco (banco.py) e os links do
professor guardam "familia@versao" e a semente. Mudar um esqueleto publicado
(ou a ordem, ou as lacunas) muda o exercício de quem já tem o link; por isso
qualquer mudança numa família publicada sobe a "versao" e o banco é gerado de
novo (python3 analise/verificar_familias.py --gravar). O banco guarda a
impressão digital do que cada família@versão gera: mudar sem subir a versão
faz o --conferir e o tests/test_banco.py falharem.
"""

FAMILIAS = {
    # Robôs que gastam e recarregam energia, montam códigos de série e guardam peças.
    "robo_energia": {
        "versao": 1,
        "tema": "variaveis",
        "niveis": {
            1: (
                {
                    "id": "gasto",
                    "contexto": "O robô {robo} andou pela sala e gastou energia.",
                    "codigo": (
                        'robo = "{robo}"\n'
                        "energia = {e}\n"
                        "gasto = {g}\n"
                        "energia = energia - gasto\n"
                        'print(robo, "ficou com", energia)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "e": ("inteiro", 50, 90, 5),
                        "g": ("inteiro", 5, 30, 5),
                    },
                    "regras": (),
                },
                {
                    "id": "recarga",
                    "contexto": "{robo} carregou a bateria e depois fez uma tarefa.",
                    "codigo": (
                        "energia = {e}\n"
                        "energia = energia + {c}\n"
                        "energia = energia - {g}\n"
                        'print("{robo} tem", energia, "de energia")\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "e": ("inteiro", 10, 40, 5),
                        "c": ("inteiro", 10, 50, 10),
                        "g": ("inteiro", 3, 9, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "serie",
                    "contexto": "O robô {robo} recebeu um código de série.",
                    "codigo": (
                        'nome = "{robo}"\n'
                        'serie = "{serie}"\n'
                        'codigo = nome + "-" + serie\n'
                        'nome = "{outro}"\n'
                        "print(codigo)\n"
                        "print(nome)\n"
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "outro": ("lista", "robos"),
                        "serie": ("lista", "series"),
                    },
                    "regras": (("diferentes", "robo", "outro"),),
                },
                {
                    "id": "passos",
                    "contexto": "{robo} deu alguns passos para a frente e voltou.",
                    "codigo": (
                        "passos = {a}\n"
                        "passos = passos + {b}\n"
                        "passos = passos - {c}\n"
                        'print("{robo} parou. Passos para a porta:", passos)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "a": ("inteiro", 2, 9, 1),
                        "b": ("inteiro", 3, 8, 1),
                        "c": ("inteiro", 1, 3, 1),
                    },
                    "regras": (),
                },
            ),
            2: (
                {
                    "id": "turbo",
                    "contexto": "{robo} ligou o turbo e depois dividiu a energia.",
                    "codigo": (
                        "energia = {e}\n"
                        "energia = energia * 2\n"
                        "energia = energia - {g}\n"
                        "energia = energia // {d}\n"
                        'print("Energia de {robo}:", energia)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "e": ("inteiro", 10, 30, 2),
                        "g": ("inteiro", 1, 9, 1),
                        "d": ("inteiro", 2, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "bipes",
                    "contexto": "O robô {robo} repete o mesmo som algumas vezes.",
                    "codigo": (
                        'som = "{som}"\n'
                        "vezes = {v}\n"
                        "vezes += 1\n"
                        "barulho = som * vezes\n"
                        'print("{robo} diz", barulho)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "som": ("lista", "sons_de_robo"),
                        "v": ("inteiro", 1, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "caixas",
                    "contexto": "{robo} guarda blocos em caixas do mesmo tamanho.",
                    "codigo": (
                        "blocos = {p}\n"
                        "blocos = blocos + {n}\n"
                        "caixas = blocos // {c}\n"
                        "sobra = blocos % {c}\n"
                        'print("{robo} encheu", caixas, "caixas")\n'
                        'print("Blocos fora das caixas:", sobra)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "p": ("inteiro", 10, 30, 1),
                        "n": ("inteiro", 2, 6, 1),
                        "c": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "letras",
                    "contexto": "O nome do robô {robo} vai ficar mais comprido.",
                    "codigo": (
                        'nome = "{robo}"\n'
                        "letras = len(nome)\n"
                        'nome = nome + "{serie}"\n'
                        "letras = letras * 2\n"
                        "print(nome, letras)\n"
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "serie": ("lista", "series"),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    # A carga é calculada antes e depois da troca: quem acha que a troca
                    # não mudou nada responde a carga de antes (o distrator da C04).
                    "id": "troca",
                    "contexto": "{robo} usa a bateria A, mas antes troca com {outro}.",
                    "codigo": (
                        "bateria_a = {a}\n"
                        "bateria_b = {b}\n"
                        "carga = bateria_a - {g}\n"
                        "bateria_a, bateria_b = bateria_b, bateria_a\n"
                        "carga = bateria_a - {g}\n"
                        'print("{robo} fica com", carga)\n'
                        'print("{outro} tem", bateria_b)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "outro": ("lista", "robos"),
                        "a": ("inteiro", 20, 90, 10),
                        "b": ("inteiro", 20, 90, 10),
                        "g": ("inteiro", 1, 9, 1),
                    },
                    "regras": (("diferentes", "robo", "outro"), ("diferentes", "a", "b")),
                },
                {
                    "id": "media",
                    "contexto": "{robo} e {outro} juntaram a energia e dividiram igualmente.",
                    "codigo": (
                        "energia_a = {a}\n"
                        "energia_b = {b}\n"
                        "total = energia_a + energia_b\n"
                        "metade = total / 2\n"
                        "total = total - {g}\n"
                        'print("Cada um ficou com", metade)\n'
                        'print("Total agora:", total)\n'
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "outro": ("lista", "robos"),
                        "a": ("inteiro", 11, 40, 1),
                        "b": ("inteiro", 11, 40, 1),
                        "g": ("inteiro", 1, 9, 1),
                    },
                    "regras": (("diferentes", "robo", "outro"), ("diferentes", "a", "b")),
                },
                {
                    "id": "codigo",
                    "contexto": "O robô {robo} monta o próprio código com números.",
                    "codigo": (
                        "numero = {n}\n"
                        "texto = str(numero)\n"
                        'codigo = "{robo}-" + texto + texto\n'
                        "numero = int(texto) + {k}\n"
                        "print(codigo)\n"
                        "print(numero)\n"
                    ),
                    "lacunas": {
                        "robo": ("lista", "robos"),
                        "n": ("inteiro", 2, 9, 1),
                        "k": ("inteiro", 1, 5, 1),
                    },
                    "regras": (),
                },
            ),
        },
    },
    # Pets que comem petiscos, passeiam, fazem barulho e trocam de tigela.
    "pet_lanche": {
        "versao": 1,
        "tema": "variaveis",
        "niveis": {
            1: (
                {
                    "id": "petiscos",
                    "contexto": "{pet} comeu alguns petiscos da tigela.",
                    "codigo": (
                        'pet = "{pet}"\n'
                        "petiscos = {p}\n"
                        "petiscos = petiscos - {c}\n"
                        'print("Petiscos de", pet, "na tigela:", petiscos)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "p": ("inteiro", 8, 20, 1),
                        "c": ("inteiro", 1, 7, 1),
                    },
                    "regras": (("menor", "c", "p"),),
                },
                {
                    "id": "frase",
                    "contexto": "O programa monta uma frase sobre o pet {pet}.",
                    "codigo": (
                        'nome = "{pet}"\n'
                        'comida = "{comida}"\n'
                        'frase = nome + " adora " + comida\n'
                        'nome = "{outro}"\n'
                        "print(frase)\n"
                        "print(nome)\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "outro": ("lista", "pets"),
                        "comida": ("lista", "comidas"),
                    },
                    "regras": (("diferentes", "pet", "outro"),),
                },
                {
                    "id": "passeio",
                    "contexto": "{pet} fez dois passeios no {lugar}.",
                    "codigo": (
                        "passos = {a}\n"
                        "passos = passos + {b}\n"
                        "passos = passos + {c}\n"
                        'print("{pet} andou", passos, "passos no {lugar}")\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "lugar": ("lista", "lugares"),
                        "a": ("inteiro", 10, 50, 10),
                        "b": ("inteiro", 5, 25, 5),
                        "c": ("inteiro", 1, 9, 1),
                    },
                    "regras": (),
                },
            ),
            2: (
                {
                    "id": "latidos",
                    "contexto": "{pet} fez barulho no quintal.",
                    "codigo": (
                        'som = "{som}"\n'
                        "vezes = {v}\n"
                        "barulho = som * vezes\n"
                        "vezes = vezes + 1\n"
                        'print("{pet} faz", barulho)\n'
                        "print(vezes)\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "som": ("lista", "sons_de_pet"),
                        "v": ("inteiro", 2, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "racao",
                    "contexto": "A ração de {pet} precisa durar alguns dias.",
                    "codigo": (
                        "racao = {r}\n"
                        "racao = racao - {c}\n"
                        "dias = racao // {d}\n"
                        "resto = racao % {d}\n"
                        'print("{pet} tem comida para", dias, "dias")\n'
                        'print("Sobra:", resto)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "r": ("inteiro", 20, 40, 1),
                        "c": ("inteiro", 1, 6, 1),
                        "d": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "coleira",
                    "contexto": "A coleira de {pet} tem o nome duas vezes e {n} estrelas.",
                    "codigo": (
                        'nome = "{pet}"\n'
                        "bordado = nome * 2\n"
                        "figuras = len(bordado)\n"
                        "figuras += {n}\n"
                        "print(bordado)\n"
                        'print("Figuras bordadas:", figuras)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "n": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    # Como em robo_energia/troca: a frase é montada antes e depois da troca,
                    # e quem acha que a troca não mudou nada responde a frase de antes.
                    "id": "tigelas",
                    "contexto": "{pet} e {outro} trocaram de tigela no almoço.",
                    "codigo": (
                        'tigela_a = "{comida}"\n'
                        'tigela_b = "{outra}"\n'
                        'prato = "{pet} come " + tigela_a\n'
                        "tigela_a, tigela_b = tigela_b, tigela_a\n"
                        'prato = "{pet} come " + tigela_a\n'
                        "print(prato)\n"
                        'print("{outro} come", tigela_b)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "outro": ("lista", "pets"),
                        "comida": ("lista", "comidas"),
                        "outra": ("lista", "comidas"),
                    },
                    "regras": (("diferentes", "pet", "outro"), ("diferentes", "comida", "outra")),
                },
                {
                    "id": "aniversario",
                    "contexto": "{pet} faz aniversário e o programa conta os anos.",
                    "codigo": (
                        'idade = "{i}"\n'
                        "anos = int(idade) + {k}\n"
                        "texto = idade + str({k})\n"
                        'print("{pet} vai ter", anos, "anos")\n'
                        "print(texto)\n"
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "i": ("inteiro", 1, 9, 1),
                        "k": ("inteiro", 1, 3, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "porcoes",
                    "contexto": "A ração de {pet} virou partes iguais, e ele comeu uma.",
                    "codigo": (
                        "racao = {r}\n"
                        "partes = {p}\n"
                        "cada = racao / partes\n"
                        "racao = racao - cada\n"
                        'print("Cada parte tem", cada)\n'
                        'print("Ainda tem", racao)\n'
                    ),
                    "lacunas": {
                        "pet": ("lista", "pets"),
                        "r": ("inteiro", 10, 30, 1),
                        "p": ("opcao", ("2", "4", "5")),
                    },
                    "regras": (),
                },
            ),
        },
    },
}
