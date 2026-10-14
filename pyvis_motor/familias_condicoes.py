"""Famílias de exercícios do tema Condições (área Praticar).

Só dados, como familias_variaveis.py (o formato da família e do esqueleto
está explicado lá): um dicionário FAMILIAS escrito como literal, sem nenhum
outro comando. Toda família daqui tem "tema": "condicoes".

Escada do tema (pede Variáveis 1):
- 1: if/else com uma comparação (==, !=, <, <=, >, >=) e True/False;
- 2: cadeia com elif (no máximo 3 caminhos); % no teste (pede Variáveis 2);
- 3: and, or e not; um if dentro de outro.

Os esqueletos preferem if com else que muda uma variável ou escreve algo:
quem acha que o else também roda depois do if (C05) ou que a variável
continua com o valor de antes (C04) ganha um distrator que mostra esse
engano. As faixas das lacunas fazem o if entrar na maior parte das vezes,
porque é aí que a C05 aparece.

Versões publicadas ficam congeladas: mudar um esqueleto publicado sobe a
"versao" da família e o banco é gerado de novo
(python3 analise/verificar_familias.py --gravar). O banco guarda a impressão
digital do que cada família@versão gera: mudar sem subir a versão faz o
--conferir e o tests/test_banco.py falharem.
"""

FAMILIAS = {
    # Tempo e jardim: chuva, sol, temperatura e plantas que pedem rega.
    "tempo_jardim": {
        "versao": 1,
        "tema": "condicoes",
        "niveis": {
            1: (
                {
                    "id": "guarda_chuva",
                    "contexto": "A previsão mediu a chuva de hoje no {lugar}.",
                    "codigo": (
                        "chuva = {c}\n"
                        "if chuva >= {lim}:\n"
                        "    guarda_chuva = True\n"
                        "else:\n"
                        "    guarda_chuva = False\n"
                        'print("No {lugar}, guarda-chuva:", guarda_chuva)\n'
                    ),
                    "lacunas": {
                        "lugar": ("lista", "lugares"),
                        "c": ("inteiro", 0, 20, 2),
                        "lim": ("inteiro", 2, 10, 2),
                    },
                    "regras": (),
                },
                {
                    "id": "rega",
                    "contexto": "A planta {planta} só recebe água quando a terra seca.",
                    "codigo": (
                        "umidade = {u}\n"
                        "copos = 0\n"
                        "if umidade < {lim}:\n"
                        "    copos = {k}\n"
                        "else:\n"
                        "    copos = 1\n"
                        'print("Copos para a planta {planta}:", copos)\n'
                    ),
                    "lacunas": {
                        "planta": ("lista", "plantas"),
                        "u": ("inteiro", 10, 60, 5),
                        "lim": ("inteiro", 40, 70, 10),
                        "k": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "janela",
                    "contexto": "A estufa abre a janela quando fica quente.",
                    "codigo": (
                        "graus = {g}\n"
                        "if graus > {lim}:\n"
                        '    janela = "aberta"\n'
                        "    graus = graus - {d}\n"
                        "else:\n"
                        '    janela = "fechada"\n'
                        'print("Janela", janela, "com", graus, "graus")\n'
                    ),
                    "lacunas": {
                        "g": ("inteiro", 20, 36, 2),
                        "lim": ("inteiro", 22, 30, 2),
                        "d": ("inteiro", 2, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "luz",
                    "contexto": "No fim da tarde, a luz do {lugar} acende sozinha.",
                    "codigo": (
                        "sol = {s}\n"
                        "if sol <= {lim}:\n"
                        '    luz = "ligada"\n'
                        "    espera = 0\n"
                        "else:\n"
                        '    luz = "desligada"\n'
                        "    espera = sol - {lim}\n"
                        'print("Luz do {lugar}:", luz)\n'
                        'print("Minutos para acender:", espera)\n'
                    ),
                    "lacunas": {
                        "lugar": ("lista", "lugares"),
                        "s": ("inteiro", 10, 50, 5),
                        "lim": ("inteiro", 30, 60, 10),
                    },
                    "regras": (),
                },
            ),
            2: (
                {
                    "id": "roupa",
                    "contexto": "O termômetro do {lugar} ajuda a escolher a roupa.",
                    "codigo": (
                        "graus = {g}\n"
                        "if graus >= {quente}:\n"
                        '    roupa = "camiseta"\n'
                        "elif graus >= {frio}:\n"
                        '    roupa = "blusa"\n'
                        "else:\n"
                        '    roupa = "casaco"\n'
                        'print("Para o {lugar}:", roupa)\n'
                    ),
                    "lacunas": {
                        "lugar": ("lista", "lugares"),
                        "g": ("inteiro", 10, 34, 2),
                        "quente": ("inteiro", 24, 30, 2),
                        "frio": ("inteiro", 14, 20, 2),
                    },
                    "regras": (),
                },
                {
                    "id": "dias_de_rega",
                    "contexto": "A rega da planta {planta} muda conforme o dia.",
                    "codigo": (
                        "dia = {d}\n"
                        "copos = {c}\n"
                        "if dia % 3 == 0:\n"
                        "    copos = copos * 2\n"
                        "elif dia % 3 == 1:\n"
                        "    copos = copos + 1\n"
                        "else:\n"
                        "    copos = 0\n"
                        'print("Dia", dia, "- copos para a planta {planta}:", copos)\n'
                    ),
                    "lacunas": {
                        "planta": ("lista", "plantas"),
                        "d": ("inteiro", 1, 30, 1),
                        "c": ("inteiro", 2, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "ceu",
                    "contexto": "O pluviômetro do {lugar} mediu a chuva da manhã.",
                    "codigo": (
                        "chuva = {c}\n"
                        "if chuva == 0:\n"
                        '    tempo = "sol"\n'
                        "elif chuva < {lim}:\n"
                        '    tempo = "garoa"\n'
                        "else:\n"
                        '    tempo = "temporal"\n'
                        "chuva = chuva * 2\n"
                        'print("Hoje tem", tempo, "no {lugar}")\n'
                        'print("Chuva do dia:", chuva)\n'
                    ),
                    "lacunas": {
                        "lugar": ("lista", "lugares"),
                        "c": ("inteiro", 0, 16, 2),
                        "lim": ("inteiro", 6, 12, 2),
                    },
                    "regras": (),
                },
                {
                    "id": "cestas",
                    "contexto": "A colheita de {fruta} vai para cestas iguais.",
                    "codigo": (
                        "frutas = {f}\n"
                        "cestas = frutas // {k}\n"
                        "sobra = frutas % {k}\n"
                        "if sobra == 0:\n"
                        '    aviso = "tudo nas cestas"\n'
                        "elif sobra == 1:\n"
                        '    aviso = "sobrou uma"\n'
                        "else:\n"
                        '    aviso = "sobraram algumas"\n'
                        'print("Cestas de {fruta}:", cestas, "-", aviso)\n'
                    ),
                    "lacunas": {
                        "fruta": ("opcao", ("uva", "pera", "manga", "kiwi", "caju")),
                        "f": ("inteiro", 12, 30, 1),
                        "k": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    "id": "passeio",
                    "contexto": "O passeio no {lugar} depende do sol e da chuva.",
                    "codigo": (
                        "sol = {s}\n"
                        "chuva = {c}\n"
                        "minutos = {m}\n"
                        "if sol and chuva < {lim}:\n"
                        "    minutos = minutos + {mais}\n"
                        "else:\n"
                        "    minutos = minutos - 10\n"
                        'print("Passeio no {lugar}:", minutos, "minutos")\n'
                    ),
                    "lacunas": {
                        "lugar": ("lista", "lugares"),
                        "s": ("opcao", ("True", "True", "False")),
                        "c": ("inteiro", 0, 10, 2),
                        "lim": ("inteiro", 4, 8, 2),
                        "m": ("inteiro", 20, 40, 10),
                        "mais": ("inteiro", 10, 30, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "estufa",
                    "contexto": "A estufa da planta {planta} confere calor e umidade.",
                    "codigo": (
                        "graus = {g}\n"
                        "umidade = {u}\n"
                        "if graus > {lim}:\n"
                        "    if umidade < {lu}:\n"
                        '        tarefa = "regar e abrir"\n'
                        "    else:\n"
                        '        tarefa = "abrir a janela"\n'
                        "    graus = graus - {d}\n"
                        "else:\n"
                        '    tarefa = "manter fechada"\n'
                        'print("Estufa:", tarefa, "com", graus, "graus")\n'
                    ),
                    "lacunas": {
                        "planta": ("lista", "plantas"),
                        "g": ("inteiro", 22, 36, 2),
                        "lim": ("inteiro", 24, 28, 2),
                        "u": ("inteiro", 20, 80, 10),
                        "lu": ("inteiro", 40, 60, 10),
                        "d": ("inteiro", 2, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "regador",
                    "contexto": "A planta {planta} recebe mais água em dias secos ou quentes.",
                    "codigo": (
                        "dias_sem_chuva = {d}\n"
                        "graus = {g}\n"
                        "if dias_sem_chuva >= {ld} or graus > {lg}:\n"
                        "    copos = {k}\n"
                        "else:\n"
                        "    copos = 2\n"
                        'print("Copos para a planta {planta}:", copos)\n'
                    ),
                    "lacunas": {
                        "planta": ("lista", "plantas"),
                        "d": ("inteiro", 0, 6, 1),
                        "ld": ("inteiro", 2, 4, 1),
                        "g": ("inteiro", 20, 34, 2),
                        "lg": ("inteiro", 28, 32, 2),
                        "k": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "geada",
                    "contexto": "Em noite fria e sem vento, a planta {planta} recebe capa.",
                    "codigo": (
                        "graus = {g}\n"
                        "vento = {v}\n"
                        "if graus < {lim} and not vento:\n"
                        '    capa = "sobre a planta"\n'
                        "    graus = graus + {k}\n"
                        "else:\n"
                        '    capa = "guardada"\n'
                        'print("A capa ficou", capa)\n'
                        'print("Graus perto da planta:", graus)\n'
                    ),
                    "lacunas": {
                        "planta": ("lista", "plantas"),
                        "g": ("inteiro", 0, 10, 1),
                        "lim": ("inteiro", 4, 8, 2),
                        "v": ("opcao", ("True", "False", "False")),
                        "k": ("inteiro", 2, 4, 1),
                    },
                    "regras": (),
                },
            ),
        },
    },
    # Trens: velocidade, portas, sinais, plataformas e partida na estação.
    "trem_estacao": {
        "versao": 1,
        "tema": "condicoes",
        "niveis": {
            1: (
                {
                    "id": "velocidade",
                    "contexto": "O trem {serie} passa por uma curva perto da estação {estacao}.",
                    "codigo": (
                        "velocidade = {v}\n"
                        "if velocidade > {lim}:\n"
                        "    velocidade = {lim}\n"
                        "else:\n"
                        "    velocidade = velocidade + {a}\n"
                        'print("O trem {serie} anda a", velocidade)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "v": ("inteiro", 30, 90, 10),
                        "lim": ("inteiro", 40, 60, 10),
                        "a": ("inteiro", 5, 15, 5),
                    },
                    "regras": (),
                },
                {
                    "id": "portas",
                    "contexto": "Na estação {estacao}, as portas do trem {serie} abrem com ele parado.",
                    "codigo": (
                        "velocidade = {v}\n"
                        "if velocidade > 0:\n"
                        '    portas = "fechadas"\n'
                        "else:\n"
                        '    portas = "abertas"\n'
                        'print("Trem {serie}: portas", portas)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "v": ("inteiro", 0, 30, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "lotacao",
                    "contexto": "Mais gente entrou no trem {serie} na estação {estacao}.",
                    "codigo": (
                        "passageiros = {p}\n"
                        "passageiros = passageiros + {e}\n"
                        "if passageiros > {cap}:\n"
                        '    aviso = "cheio"\n'
                        "else:\n"
                        '    aviso = "com lugar"\n'
                        'print("Trem {serie}:", passageiros, "pessoas,", aviso)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "p": ("inteiro", 20, 60, 10),
                        "e": ("inteiro", 5, 25, 5),
                        "cap": ("inteiro", 40, 70, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "atraso",
                    "contexto": "O painel da estação {estacao} confere a chegada do trem.",
                    "codigo": (
                        "previsto = {h}\n"
                        "chegada = {c}\n"
                        "if chegada > previsto:\n"
                        '    painel = "atrasado"\n'
                        "else:\n"
                        '    painel = "no tempo certo"\n'
                        'print("Trem {serie}:", painel)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "h": ("inteiro", 10, 30, 5),
                        "c": ("inteiro", 10, 40, 5),
                    },
                    "regras": (),
                },
            ),
            2: (
                {
                    "id": "sinal",
                    "contexto": "O sinal muda de cor conforme a distância do trem {serie}.",
                    "codigo": (
                        "metros = {d}\n"
                        "if metros > {longe}:\n"
                        '    sinal = "verde"\n'
                        "elif metros > {perto}:\n"
                        '    sinal = "amarelo"\n'
                        "else:\n"
                        '    sinal = "vermelho"\n'
                        'print("Sinal para o {serie}:", sinal)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "d": ("inteiro", 100, 900, 100),
                        "longe": ("inteiro", 400, 600, 100),
                        "perto": ("inteiro", 100, 300, 100),
                    },
                    "regras": (),
                },
                {
                    "id": "plataforma",
                    "contexto": "Na estação {estacao}, a linha do trem escolhe a plataforma.",
                    "codigo": (
                        "linha = {n}\n"
                        "resto = linha % 3\n"
                        "if resto == 0:\n"
                        '    plataforma = "A"\n'
                        "elif resto == 1:\n"
                        '    plataforma = "B"\n'
                        "else:\n"
                        '    plataforma = "C"\n'
                        'print("O trem da linha", linha, "para na plataforma", plataforma)\n'
                    ),
                    "lacunas": {
                        "estacao": ("lista", "estacoes"),
                        "n": ("inteiro", 101, 160, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "carros",
                    "contexto": "O trem {serie} recebe carros extras em dia cheio.",
                    "codigo": (
                        "passageiros = {p}\n"
                        "if passageiros > {grande}:\n"
                        "    carros = 4\n"
                        "elif passageiros > {medio}:\n"
                        "    carros = 3\n"
                        "else:\n"
                        "    carros = 2\n"
                        "lugares = carros * {cap}\n"
                        'print("Trem {serie}:", carros, "carros e", lugares, "lugares")\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "p": ("inteiro", 50, 250, 25),
                        "grande": ("inteiro", 150, 200, 25),
                        "medio": ("inteiro", 75, 125, 25),
                        "cap": ("inteiro", 40, 60, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "freio",
                    "contexto": "Perto da estação {estacao}, o trem {serie} reduz a velocidade.",
                    "codigo": (
                        "velocidade = {v}\n"
                        "if velocidade > {alta}:\n"
                        "    velocidade = velocidade // 2\n"
                        "elif velocidade > {media}:\n"
                        "    velocidade = velocidade - {f}\n"
                        "else:\n"
                        "    velocidade = velocidade + {f}\n"
                        'print("O trem {serie} chega a", velocidade)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "v": ("inteiro", 20, 100, 10),
                        "alta": ("inteiro", 60, 80, 10),
                        "media": ("inteiro", 30, 50, 10),
                        "f": ("inteiro", 5, 15, 5),
                    },
                    "regras": (),
                },
            ),
            3: (
                {
                    "id": "partida",
                    "contexto": "O trem {serie} só parte da estação {estacao} com tudo pronto.",
                    "codigo": (
                        "portas_fechadas = {p}\n"
                        'sinal = "{cor}"\n'
                        "atraso = {a}\n"
                        "if portas_fechadas and sinal == \"verde\":\n"
                        '    estado = "partiu"\n'
                        "else:\n"
                        '    estado = "espera"\n'
                        "    atraso = atraso + {m}\n"
                        'print("Trem {serie}:", estado)\n'
                        'print("Minutos de atraso:", atraso)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "p": ("opcao", ("True", "True", "False")),
                        "cor": ("opcao", ("verde", "verde", "amarelo", "vermelho")),
                        "a": ("inteiro", 0, 6, 2),
                        "m": ("inteiro", 3, 5, 1),
                    },
                    "regras": (),
                },
                {
                    "id": "farol",
                    "contexto": "O farol do trem {serie} acende com neblina ou à noite.",
                    "codigo": (
                        "neblina = {t}\n"
                        "hora = {h}\n"
                        "velocidade = {v}\n"
                        "if neblina or hora >= 18:\n"
                        '    farol = "aceso"\n'
                        "    velocidade = velocidade - {d}\n"
                        "else:\n"
                        '    farol = "apagado"\n'
                        'print("Farol do {serie}:", farol)\n'
                        'print("Velocidade:", velocidade)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "t": ("opcao", ("True", "False")),
                        "h": ("inteiro", 6, 22, 2),
                        "v": ("inteiro", 60, 90, 10),
                        "d": ("inteiro", 10, 20, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "embarque",
                    "contexto": "Na estação {estacao}, o trem {serie} confere a chegada e os passageiros.",
                    "codigo": (
                        "chegou = {c}\n"
                        "passageiros = {p}\n"
                        "if chegou:\n"
                        "    if passageiros > {lim}:\n"
                        '        aviso = "embarque pela porta 2"\n'
                        "    else:\n"
                        '        aviso = "embarque pela porta 1"\n'
                        "else:\n"
                        '    aviso = "aguarde na plataforma"\n'
                        'print("Trem {serie}:", aviso)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "estacao": ("lista", "estacoes"),
                        "c": ("opcao", ("True", "True", "False")),
                        "p": ("inteiro", 10, 90, 10),
                        "lim": ("inteiro", 30, 60, 10),
                    },
                    "regras": (),
                },
                {
                    "id": "chuva_no_trilho",
                    "contexto": "Com chuva, o trem {serie} anda mais devagar.",
                    "codigo": (
                        "chuva = {c}\n"
                        "velocidade = {v}\n"
                        "if not chuva:\n"
                        "    velocidade = velocidade + {a}\n"
                        "else:\n"
                        "    velocidade = velocidade - {a}\n"
                        'print("Trem {serie} a", velocidade)\n'
                    ),
                    "lacunas": {
                        "serie": ("lista", "series"),
                        "c": ("opcao", ("True", "False")),
                        "v": ("inteiro", 40, 80, 10),
                        "a": ("inteiro", 5, 20, 5),
                    },
                    "regras": (),
                },
            ),
        },
    },
}
