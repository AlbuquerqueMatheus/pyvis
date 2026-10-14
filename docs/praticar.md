# Área Praticar

Este documento explica a área Praticar para quem mantém o PyVis: o que ela faz, como uma família de exercícios é escrita e revisada, o que o verificador confere, como gerar e conferir o banco de sementes e o que ficou de fora.

## O que a área faz

O aluno abre `#/praticar` (o link "Praticar" é o primeiro do menu "Outras páginas"), escolhe um tema (Variáveis, Condições ou Laços), o conteúdo e o formato das perguntas (Alternativas ou Resposta livre). A página monta uma série de 5 exercícios curtos. Cada exercício é um programa pequeno com uma frase de contexto, aberto no Palco no modo Prever: o motor faz as perguntas de sempre, o aluno dá o palpite e depois vê a execução.

- **Níveis pelo nome:** o aluno vê o nome do conteúdo ("Guardar e mudar valores", "Vários caminhos com elif", "Listas, saltos e paradas"), nunca um número de nível.
- **Sem contagem:** não há pontos, placar, sequência de acertos, medalhas nem contagem de acertos na tela. A tela final diz "Por hoje é isso." e oferece "Mais 5 deste tema", "Escolher outro tema" e "Voltar ao início". Nada avança sozinho.
- **"Outro exercício":** troca só o exercício atual por um que o aluno ainda não viu naquela visita. A página avisa "Exercício trocado." (o título continua "Exercício k de 5", então o aviso é o que o leitor de tela ouve).
- **Link do professor:** "Para o professor: copiar o link desta série" copia o endereço com o tema, o nível, a semente da série e o formato. Quem abre esse link recebe os mesmos 5 exercícios, na mesma ordem, em qualquer aparelho. Se a área de transferência não estiver disponível, o link aparece num campo só de leitura, já selecionado. Depois de um "Outro exercício", o aviso muda para "Ele abre esta série como começou, antes das trocas.": o link não guarda as trocas.
- **Nenhuma IA:** os exercícios saem de modelos escritos à mão (as famílias), preenchidos por sorteio determinístico e conferidos pelo próprio motor do PyVis.

### Fora da avaliação do TCC

A área Praticar fica fora das salas e fora da coleta de dados do TCC. Ela não grava nada: não usa localStorage, não manda eventos e não cria nada no aparelho. O que o aluno já viu fica só na memória da página e some quando ele fecha a aba. Os dados da avaliação continuam vindo só das atividades dentro de uma sala.

### O endereço

```
#/praticar?t=<tema>&n=<1|2|3>&s=<semente da série>&f=<familia>&p=<a|l>
```

| Parâmetro | O que é | Regra |
| --- | --- | --- |
| `t` | id do tema (`variaveis`, `condicoes`, `lacos`) | letras minúsculas, números e `_` |
| `n` | nível | 1, 2 ou 3 |
| `s` | semente da série | inteiro de 0 a 2³²−1 |
| `f` | prende a série numa família (opcional) | precisa ser do tema `t` |
| `p` | formato das perguntas | `a` (alternativas) ou `l` (resposta livre) |

Um parâmetro inválido é ignorado. Sem tema conhecido, sem nível válido ou sem semente, a página abre a escolha de tema com o que deu para aproveitar já marcado. Um `f` de outro tema é ignorado.

O link só leva tema, nível, semente e formato, então ele só reproduz uma série que saiu da semente sem nada pulado. Por isso "Mais 5 deste tema" sorteia uma **semente nova** e confere a série dela: se ela não tem nenhum exercício já visto, é essa (o endereço e o link passam a ser os dela, e recarregar a página volta para ela). Se tiver, a página sorteia outra, até 8 vezes. Quando o aluno já viu quase tudo daquele tema e nível e nenhuma semente serve, a série pula os vistos (`excluir`) e fica **sem link**: o botão do professor some e o endereço volta para a escolha do tema, para recarregar não trazer de volta o que o aluno já fez. "Escolher outro tema" e "Começar" seguem a mesma regra.

Colar um link na barra de endereço da mesma aba sempre recomeça a página, mesmo que seja o link de uma série aberta antes nessa aba (a página reescreve o endereço com `history.replaceState`, que não avisa a rota; a rota conta as navegações de verdade e a página recomeça a cada uma).

## Como funciona por dentro

```
familias_*.py (dados) ──> gerador.py ──> verificador.py ──> analise/verificar_familias.py ──> banco.py
                                                                                                  │
página: catalogo_praticar ──> montar_serie (só sementes do banco) ──> gerar_exercicio ──> Palco (Prever)
```

1. **Famílias** (`pyvis_motor/familias_variaveis.py`, `familias_condicoes.py`, `familias_lacos.py`): modelos de exercício, só dados.
2. **Gerador** (`pyvis_motor/gerador.py`): `gerar(familia, nivel, semente)` escolhe um esqueleto e preenche as lacunas. Toda escolha sai do sha256 de um texto como `"pet_lanche@1:1:0:0:pet"`, nunca do `random`, porque a sequência do `random.Random` não é garantida entre versões do Python. O mesmo trio dá o mesmo programa no 3.11, no 3.14 e no Pyodide.
3. **Verificador** (`pyvis_motor/verificador.py`): `verificar(exercicio)` roda o programa no motor e confere tudo o que está em [As conferências](#as-conferências).
4. **Banco** (`pyvis_motor/banco.py`): para cada família, versão e nível, as 40 primeiras sementes que passaram na conferência completa e são programas diferentes entre si. É gerado por `analise/verificar_familias.py`.
5. **Ações do motor** (`pyvis_motor/praticar.py`, expostas em `api.ACOES` e no `ponte.ts`):
   - `catalogo_praticar()`: temas, nomes dos níveis e famílias (id, versão e tema).
   - `montar_serie(tema, nivel, semente, quantidade=5, familia=None, excluir=())`: os itens da série, só do banco. A ordem vem do sha256 de (semente da série, chave do item): as famílias do tema se alternam e, dentro de cada família, os esqueletos também, então o mesmo programa com outros números só volta depois de todos os esqueletos da família (numa série de 5, nenhum esqueleto se repete). `excluir` só pula itens, sem mudar a ordem dos outros: é assim que funciona "Outro exercício". O teste `test_montar_serie_tem_valor_fixo` fixa uma série inteira: ele é o contrato do link do professor, no CPython e no Pyodide. Quando o banco acaba, a lista vem menor ou vazia.
   - `gerar_exercicio(familia, nivel, semente)`: o exercício pronto. Semente do banco passa só pela conferência barata (escada e textos); qualquer outra semente passa pela conferência completa e, se falhar, dá `ValueError("este exercício não passou na conferência")`.

A chave de um item é `"familia@versao:nivel:semente"`, por exemplo `"pet_lanche@1:1:32"`.

## Como uma família é escrita

Cada tema tem um arquivo. O arquivo tem só uma docstring, comentários e uma atribuição `FAMILIAS = {...}` com um literal puro. O teste `tests/test_familias.py` lê o arquivo com `ast` e roda `ast.literal_eval` no valor: qualquer outro comando (um `import`, uma função, uma conta) faz o teste falhar. Assim uma família proposta por qualquer pessoa, inclusive gerada por uma IA, entra como dado revisável e nunca como código que roda.

### Formato

Uma família:

```python
"id_da_familia": {
    "versao": 1,
    "tema": "variaveis",          # ou "condicoes" ou "lacos"; precisa ser o tema do arquivo
    "niveis": {1: (esqueleto, ...), 2: (...), 3: (...)},
}
```

- A família pode cobrir só alguns níveis, mas cada nível que ela tem precisa de pelo menos 3 esqueletos.
- Ids de família e de esqueleto seguem `[a-z][a-z0-9_]*`. O id do esqueleto é único dentro da família, somando todos os níveis.

Um esqueleto tem exatamente estas chaves:

| Chave | O que é |
| --- | --- |
| `id` | nome interno do esqueleto |
| `contexto` | uma frase de até 12 palavras depois de preenchida, sem `?` (quem pergunta é o motor). Pode ter acento. |
| `codigo` | o programa em Python, terminando em `\n`, com marcadores `{nome}`. Textos entre aspas e o que o programa escreve só têm letras sem acento. |
| `lacunas` | `{nome: lacuna}`, uma para cada marcador |
| `regras` | tupla de `("diferentes", a, b)` ou `("menor", a, b)` |

Os tipos de lacuna:

| Lacuna | Exemplo | Sorteia |
| --- | --- | --- |
| `("lista", "<chave>")` | `("lista", "pets")` | um item de `familias.LISTAS` |
| `("inteiro", min, max, passo)` | `("inteiro", 8, 20, 1)` | um inteiro de `min` a `max` (inclusive), de `passo` em `passo` |
| `("opcao", ("txt", ...))` | `("opcao", ("2", "4", "5"))` | um dos textos, colado no código como está (só ASCII) |

As regras comparam duas lacunas: `"diferentes"` pede valores diferentes; `"menor"` pede `a < b` e só vale para lacunas inteiras. Se o sorteio não cumpre as regras, o gerador sorteia de novo, até 20 vezes; se nenhuma tentativa cumprir, dá `ValueError` (a família pede o impossível).

`gerador.problemas()` recusa: marcador sem lacuna, lacuna que nunca aparece, chave desconhecida, tipo de lacuna ou de regra desconhecido, lista que não existe, menos de 3 esqueletos num nível e família no arquivo de outro tema.

As listas fechadas ficam em `pyvis_motor/familias.py` (`LISTAS`): `robos`, `pets`, `comidas`, `lugares`, `series`, `sons_de_robo`, `sons_de_pet`, `cores`, `frutas`, `plantas` e `estacoes`. Todos os nomes são inventados e sem acento, então nenhum exercício fala de uma pessoa de verdade. Os temas e os nomes dos níveis ficam em `TEMAS`, no mesmo arquivo.

### Exemplo completo: `pet_lanche` (Variáveis)

Esta é a família `pet_lanche` exatamente como está em `pyvis_motor/familias_variaveis.py`:

```python
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
```

O que vale notar nesse exemplo:

- **O engano aparece na resposta.** Em `petiscos`, a pergunta "quanto vale petiscos?" depois de `petiscos = petiscos - c` tem como distrator o valor antigo, que vem do modelo C04 (a atribuição não muda o valor). Em `tigelas`, `prato` é montado antes e depois da troca: quem acha que `a, b = b, a` não mudou nada responde a frase de antes, e esse é o distrator da C04 na pergunta sobre `prato` (sem isso, as alternativas da troca só tinham ±1 e a linha a menos, e dava para acertar por eliminação). Em `porcoes`, o `/` com `p` em 2, 4 ou 5 dá uma decimal curta (`3.75`, `5.2`) e abre espaço para o engano do `/` que corta (C08), sem decimal ambígua.
- **Nem todo esqueleto tem distrator de modelo.** Em `frase`, `nome` muda depois de montar a frase. Quem acha que a frase acompanha a variável erraria, mas esse engano não está no catálogo de concepções (C01 a C08): as alternativas de `frase` são só de regra (o nome no lugar do valor, a linha a menos). É por isso que `pet_lanche` nível 1 fica em 30 de 40 com distrator de modelo, todos de `petiscos` e `passeio`.
- **As regras evitam exercício sem graça.** `("menor", "c", "p")` impede comer mais petiscos do que havia; `("diferentes", "pet", "outro")` impede a troca de tigela entre o mesmo pet.
- **Textos que o aluno digita não levam acento nenhum.** O aluno digita a resposta livre, então o que o programa escreve só usa palavras que não têm acento em português ("comida", "parte", "Figuras bordadas"). Uma palavra escrita sem o acento que ela pede ("racao", "porcao") faria a resposta certa em português ("ração") virar erro; por isso ela é trocada, nunca escrita sem acento. A frase de contexto, que o aluno só lê, mantém "ração".
- **Plural com 1.** Nenhuma saída diz "1 copos" ou "1 dias", nem nas alternativas erradas (que somam ou tiram 1 da resposta certa): quando o número conta alguma coisa, a saída põe o rótulo antes e o número no fim ("Petiscos de Mel na tigela: 11", "Sobra: 1").

`gerar("pet_lanche", 1, 0)` dá:

```python
pet = "Mel"
petiscos = 13
petiscos = petiscos - 2
print("Petiscos de", pet, "na tigela:", petiscos)
```

com o contexto "Mel comeu alguns petiscos da tigela." O verificador aprova com `medidas` = 4 linhas, 4 passos, 0 voltas e 1 operação, 2 pontos de previsão, distrator do modelo C04 e chave `8f9e8325d8866f27`.

### Como revisar uma família

Antes de aceitar uma família nova (ou uma versão nova de uma família), confira:

1. **Formato e escada.** Rode `python3 analise/verificar_familias.py --familia <id>`. O relatório tem que sair sem "FALHOU" e com código 0.
2. **Leia 5 ou 6 programas gerados** de cada nível, de esqueletos diferentes. Por exemplo:

   ```bash
   python3 -c "from pyvis_motor import gerador; [print(gerador.gerar('pet_lanche', 2, s)['codigo']) for s in range(6)]"
   ```

   Pergunte: um aluno de 10 anos entende o contexto? O programa é Python que você mostraria numa aula? A saída faz sentido em português, sem palavra cortada?
3. **Textos.** Nada de nomes de pessoas de verdade, nada de vocabulário de jogo de azar, de violência ou de placar, nada de dado pessoal. O verificador pega as palavras proibidas (com as flexões) e os padrões de telefone, CPF e e-mail, mas não pega um texto estranho, uma história que não fecha ("a luz desligada e o sol subindo"), um "1 copos" ou uma palavra que perdeu o acento ("racao", "posicao"). Esse olho é seu. Para ver todas as palavras que uma família escreve na tela, gere umas 200 sementes e junte as palavras da saída.
4. **Distrator de modelo.** No relatório, a linha "com distrator de modelo" mostra quantos itens do banco têm um palpite errado que vem de uma concepção do catálogo (C01 a C08). A porta exige 25%; abaixo de uns 40% vale pensar em mudar o esqueleto para o engano aparecer na resposta.
5. **Todos os esqueletos no banco.** A linha "esqueletos" lista quantos itens do banco vieram de cada um. Um esqueleto que quase não aparece (como `energia` em `robo_oficina` nível 3, com 3 de 40) é recusado na maior parte das sementes e merece uma olhada nas faixas das lacunas.
6. **Só "o if vai entrar?".** A linha "só \"o if vai entrar?\" nas alternativas" conta os itens em que as alternativas são só Verdadeiro ou Falso, um cara ou coroa. A porta deixa no máximo 25%. Para sair dela, faça a condição mudar um número que o programa escreve (como `regador` e `farol`).
7. **Grave o banco** (`--gravar`) e rode os testes.

## As conferências

`verificador.verificar(exercicio)` devolve `{ok, motivos, medidas, concepcoes, pontos, so_decisao, chave}`. O exercício passa só se todos os 7 grupos passarem.

1. **Sintaxe e escada do tema.** A árvore do programa só pode ter conceitos permitidos no tema e nível (tabela abaixo). A escada é uma lista do que pode: o que não está em nenhum degrau é proibido em qualquer nível. Isso inclui `import`, `def`, `lambda`, `class`, `try`, `with`, `global`, compreensões, f-strings, texto com `%` (`"Restam %d" % n`, que é interpolação como a f-string, e não o resto da divisão), dicionários e conjuntos, `input()`, `eval`, `exec`, `open`, `getattr`, nomes com `__`, `while True`, métodos, argumentos nomeados, mais de 3 caminhos num if, if três níveis para dentro e laço dentro de laço.
2. **Roda bem.** Até 300 passos (o limite dos aparelhos fracos), sem erro, igual em duas execuções e com outra semente do motor, saída de no máximo 10 linhas e 300 caracteres, e nenhuma decimal ambígua como `0.30000000000000004`.
3. **Cabe no orçamento** do tema e nível (tabela abaixo).
4. **Tem o que perguntar.** `preparar_atividade` acha pelo menos 1 ponto de previsão nos dois formatos (alternativas com palpite inicial, e resposta livre). As concepções que deram distrator ficam em `concepcoes`, e `so_decisao` diz se as alternativas só perguntam "o if vai entrar?".
5. **Mutação: o conceito do tema importa.** Em Variáveis, trocar um valor atribuído muda a saída. Em Condições, negar uma condição muda a saída. Em Laços, mexer no limite do laço muda a saída. Um programa em que o laço "não faz diferença" é recusado com `resposta_nao_depende_do_conceito`.
6. **Textos.** A frase de contexto, cada texto entre aspas, os nomes de variáveis e a saída não podem ter palavras de jogo de azar, de violência ou de placar (sorte, vida, pontos, prêmio, medalha, ouro, ganhar, perder, vencer, inimigo, arma, tiro, bomba, luta e outras; a lista está em `PALAVRAS_PROIBIDAS`), comparadas sem acento e por palavra inteira, com as flexões ("ganha", "ganhou", "perde", "matou", "sortudo", "pontuou"). Os radicais ambíguos ficam numa lista fechada de flexões, para "morro" e "parte" passarem. Nos nomes de variável, `_`, letra maiúscula e número separam palavras (`vidas_extras`, `vidasExtras` e `vidas2` são recusados). Também não podem ter telefone (com ou sem DDD, como "3333 4444" e "9 8765-4321"), CPF, e-mail ou 8 dígitos seguidos. Textos entre aspas e a saída só têm letras sem acento. O contexto tem até 12 palavras e nenhum `?`.
7. **Chave do programa:** `sha256(codigo)[:16]`. É ela que diz se dois programas são iguais. O `ast.dump` não serve, porque mudou entre o Python 3.12 e o 3.14.

`verificador.conferir_rapido(exercicio)` roda só os grupos 1 e 6, sem executar o programa. É o que `gerar_exercicio` usa para sementes do banco.

O verificador não mexe em `api.ultimo`: ele chama o rastreador e `montar_atividade` direto.

### Escada por tema

Cada nível permite os próprios conceitos e os de todos os degraus que ele pede.

| Tema e nível | Pede | Acrescenta |
| --- | --- | --- |
| Variáveis 1 | nada | atribuição e reatribuição, `+` e `-` com inteiros, juntar textos com `+`, `print` |
| Variáveis 2 | Variáveis 1 | `*`, `//`, `%`, texto × inteiro, `len`, `+=` |
| Variáveis 3 | Variáveis 2 | troca `a, b = b, a`, `int()`, `str()`, `/`, decimais |
| Condições 1 | Variáveis 1 | `if`/`else` com uma comparação, `True`/`False` |
| Condições 2 | Condições 1 e Variáveis 2 | cadeia com `elif` (no máximo 3 caminhos); o `%` no teste (como `dia % 3 == 0`), o `//` e o `*` vêm do degrau Variáveis 2 |
| Condições 3 | Condições 2 | `and`, `or`, `not`, um if dentro de outro |
| Laços 1 | Condições 1 | `while` com contador simples |
| Laços 2 | Laços 1 | `for` com `range(a, b)` ou por um texto, acumulador |
| Laços 3 | Laços 2 | listas, índice, `range` com passo, `break`, condição composta no `while` |

Uma consequência importante para quem escreve famílias de Laços: como Laços pede Condições 1 (que pede Variáveis 1), Laços não tem `*`, `//`, `%`, `+=` nem `len()`. O contador se escreve `i = i + 1`. Laços 1 também recusa `elif`, `and` e `or`; Laços 3 aceita condição composta só dentro do `while`.

### Orçamento por tema e nível

Os tetos foram tirados do maior item do banco de cada tema e nível, com folga de 1 ou 2. Linhas e operações vêm da árvore do programa; passos e voltas vêm do rastro.

| Tema e nível | Linhas | Passos | Voltas | Operações | Maior item do banco (linhas / passos / voltas / operações) |
| --- | --- | --- | --- | --- | --- |
| Variáveis 1 | 7 | 7 | 0 | 4 | 6 / 6 / 0 / 2 |
| Variáveis 2 | 7 | 7 | 0 | 5 | 6 / 6 / 0 / 3 |
| Variáveis 3 | 8 | 8 | 0 | 5 | 7 / 7 / 0 / 3 |
| Condições 1 | 10 | 8 | 0 | 4 | 9 / 6 / 0 / 2 |
| Condições 2 | 11 | 9 | 0 | 7 | 10 / 7 / 0 / 6 |
| Condições 3 | 12 | 9 | 0 | 5 | 11 / 8 / 0 / 4 |
| Laços 1 | 8 | 22 | 6 | 5 | 7 / 19 / 5 / 4 |
| Laços 2 | 9 | 32 | 9 | 5 | 8 / 28 / 8 / 3 |
| Laços 3 | 9 | 32 | 9 | 7 | 7 / 17 / 5 / 5 |

Em Laços, os passos e as voltas não descem do nível 2 para o 3: o nível 3 ainda pode andar por um texto inteiro, como o 2. O teste `test_onze_operacoes_estouram_o_orcamento_mesmo_so_com_soma` garante que uma conta de 11 operações em Variáveis 1 continua recusada. Os 16 exercícios ruins do protótipo (em `tests/test_verificador.py`) continuam recusados, cada um pelo motivo esperado, e `MUTACOES`, no mesmo arquivo, tem um caso por tema em que o conceito não muda a resposta (ou não aparece): sem eles, um defeito na mutação de Laços ou de Variáveis passaria pelos testes.

Se uma família nova não couber, ajuste o teto em `ORCAMENTO` (em `pyvis_motor/verificador.py`) só depois de olhar o programa: um teto que sobe demais deixa passar exercício grande para o nível.

## O banco de sementes

A página só abre sementes do banco. Assim ela nunca mostra um exercício que não passou na conferência completa, e o trabalho pesado fica fora do navegador.

### Comandos

```bash
python3 analise/verificar_familias.py                      # só o relatório, não grava nada
python3 analise/verificar_familias.py --gravar             # grava pyvis_motor/banco.py
python3 analise/verificar_familias.py --conferir           # falha se banco.py estiver velho
python3 analise/verificar_familias.py --tema lacos         # só um tema (pode repetir)
python3 analise/verificar_familias.py --familia pet_lanche # só uma família (pode repetir)
python3 analise/verificar_familias.py --gravar --familia-nao-publicada  # só para família que não chegou à main
```

Com `--tema` ou `--familia`, `--gravar` troca só as entradas dessas famílias no banco e mantém as outras.

O CI roda `--conferir` no job do motor com Python 3.12, logo depois de `casos_revelacao.py --conferir`. Se alguém mudar uma família ou o verificador e esquecer de gerar o banco de novo, o CI falha. Além das sementes (`BANCO`), o `banco.py` guarda em `IMPRESSOES` o sha256 dos contextos e códigos que essas sementes geram (`gerador.impressao`); ver [Por que as versões ficam congeladas](#por-que-as-versões-ficam-congeladas). O `tests/test_banco.py` gera de novo cada semente do banco e confere que ela passa em `verificar`, em todos os Pythons do CI e também no Pyodide (`node scripts/pytest_pyodide.mjs`): é a prova de que o mesmo banco vale no navegador.

### As portas

O script falha (código 1) quando alguma destas não passa:

- toda família tem formato válido e pelo menos 3 esqueletos por nível;
- cada família e nível chega a 40 sementes no banco, com pelo menos 30 programas distintos, testando no máximo 400 sementes;
- todo esqueleto aparece no banco;
- pelo menos 25% dos itens do banco têm um distrator de modelo;
- no máximo 25% dos itens do banco só perguntam "o if vai entrar?" nas alternativas;
- nenhuma família@versão que já está no banco gera outra coisa nas mesmas sementes ("mudou a família publicada sem subir a versao");
- todo tema e nível tem pelo menos uma família.

### O relatório de agora

Gerado com `python3.12 analise/verificar_familias.py --gravar`: 6 famílias, 720 sementes em 18 entradas, 10,0 s ao todo. Nenhuma família recusou um exercício por texto, escada, orçamento ou execução: as únicas recusas foram programas repetidos e, em Laços, exercícios em que o limite do laço não mudava a resposta.

| Família | Nível | Aceitas | Recusas | Itens com distrator de modelo | Só "o if vai entrar?" | Concepções | Esqueletos no banco |
| --- | --- | --- | --- | --- | --- | --- | --- |
| robo_energia | 1 | 40 de 40 | nenhuma | 33 de 40 (82%) | 0 | C04 33 | gasto 8, passos 17, recarga 8, serie 7 |
| robo_energia | 2 | 42 de 42 | repetido 2 | 40 de 40 (100%) | 0 | C04 40 | bipes 7, caixas 13, letras 8, turbo 12 |
| robo_energia | 3 | 42 de 42 | repetido 2 | 40 de 40 (100%) | 0 | C04 22, C08 18 | codigo 12, media 18, troca 10 |
| pet_lanche | 1 | 40 de 40 | nenhuma | 30 de 40 (75%) | 0 | C04 30 | frase 10, passeio 13, petiscos 17 |
| pet_lanche | 2 | 44 de 44 | repetido 4 | 40 de 40 (100%) | 0 | C04 40 | coleira 12, latidos 15, racao 13 |
| pet_lanche | 3 | 42 de 42 | repetido 2 | 30 de 40 (75%) | 0 | C04 14, C08 16 | aniversario 10, porcoes 16, tigelas 14 |
| tempo_jardim | 1 | 41 de 41 | repetido 1 | 29 de 40 (72%) | 3 | C04 7, C05 29 | guarda_chuva 9, janela 13, luz 11, rega 7 |
| tempo_jardim | 2 | 41 de 41 | repetido 1 | 30 de 40 (75%) | 0 | C04 12, C05 26 | cestas 11, ceu 8, dias_de_rega 13, roupa 8 |
| tempo_jardim | 3 | 43 de 43 | repetido 3 | 28 de 40 (70%) | 0 | C04 18, C05 21 | estufa 9, geada 11, passeio 11, regador 9 |
| trem_estacao | 1 | 46 de 46 | repetido 6 | 36 de 40 (90%) | 4 | C04 16, C05 25 | atraso 8, lotacao 14, portas 10, velocidade 8 |
| trem_estacao | 2 | 41 de 41 | repetido 1 | 29 de 40 (72%) | 0 | C04 6, C05 26 | carros 9, freio 6, plataforma 12, sinal 13 |
| trem_estacao | 3 | 41 de 41 | repetido 1 | 35 de 40 (88%) | 0 | C04 22, C05 23 | chuva_no_trilho 13, embarque 5, farol 9, partida 13 |
| robo_oficina | 1 | 44 de 46 | repetido 4, laço não importa 2 | 40 de 40 (100%) | 0 | C04 40, C05 13, C06 11 | andares 13, bipes 7, contagem 16, recarga 4 |
| robo_oficina | 2 | 45 de 45 | repetido 5 | 40 de 40 (100%) | 0 | C01 33, C02 16, C04 30 | bateria 15, caixas 8, soletrar 7, treino 10 |
| robo_oficina | 3 | 40 de 42 | laço não importa 2 | 35 de 40 (88%) | 0 | C01 4, C02 13, C04 18, C06 3, C07 27 | elevador 9, energia 3, fila 15, sensor 13 |
| jardim_pets | 1 | 49 de 59 | laço não importa 10, repetido 9 | 40 de 40 (100%) | 0 | C04 40, C05 1, C06 23 | crescer 4, latidos 19, passeio 12, petiscos 5 |
| jardim_pets | 2 | 47 de 47 | repetido 7 | 40 de 40 (100%) | 0 | C01 26, C02 11, C04 40, C05 6 | folhas 10, fornadas 16, invertido 4, letras_da_cor 10 |
| jardim_pets | 3 | 40 de 42 | laço não importa 2 | 35 de 40 (88%) | 0 | C01 2, C02 8, C04 5, C07 33 | fila_de_pets 11, frutas 9, regar 5, tigelas 8, trem 7 |

"Aceitas" conta as sementes que passaram no verificador entre as testadas; "repetido" é um programa que já estava no banco; "laço não importa" é o motivo `resposta_nao_depende_do_conceito`. Cada família e nível tem 40 programas distintos no banco. As concepções são as do catálogo do motor: C01 (o range inclui o fim), C02 (o range começa em 1), C04 (a atribuição não muda o valor), C05 (o else também roda), C06 (o while para no meio da volta), C07 (o índice começa em 1) e C08 (o `/` corta a decimal).

A menor parte com distrator de modelo é 70% (tempo_jardim nível 3), acima da porta de 25%. Em Condições 3, antes da porta do "o if vai entrar?", 24 dos 40 itens de tempo_jardim e 10 dos 40 de trem_estacao só tinham essa pergunta; os esqueletos `regador`, `passeio`, `geada`, `estufa`, `partida` e `farol` passaram a escrever um número que a condição muda, e agora são 0. Os poucos que sobram (3 em tempo_jardim nível 1, 4 em trem_estacao nível 1) são `guarda_chuva` e `portas`, que escrevem só um texto fixo de cada caminho.

### Tempo

No CPython 3.12, a conferência completa leva de 8 a 18 ms por exercício, e a varredura das 6 famílias leva uns 10 s.

No Pyodide (Python 3.14.2, rodando no Node do jeito que o worker carrega o motor), medido em todas as 720 sementes do banco e em 180 séries:

| Ação | Mediana | p90 |
| --- | --- | --- |
| `catalogo_praticar` (primeira chamada) | 1,2 ms | |
| `montar_serie` (5 itens; agora também sorteia o esqueleto de cada item do banco) | 0,9 ms | 1,4 ms |
| `montar_serie` ("Outro exercício", 1 item com 5 excluídos) | 0,8 ms | 1,3 ms |
| `gerar_exercicio` com semente do banco | 0,8 ms | 1,0 ms |
| `gerar_exercicio` com semente fora do banco (conferência completa) | 26 ms | 40 ms |
| `rastrear` + `preparar_atividade` do exercício (o que o Palco faz depois) | 7,4 ms | 8,5 ms |

"Mais 5" pode chamar `montar_serie` até 8 vezes procurando uma semente sem exercício já visto: menos de 12 ms no pior caso.

Ou seja: o banco deixa abrir um exercício quase de graça, e o tempo que o aluno espera é o do Palco, igual ao de qualquer outro programa.

## Por que as versões ficam congeladas

O banco e o link do professor guardam só `familia@versao`, o nível e a semente. O programa é gerado de novo a cada vez a partir da família. Se alguém mudar um esqueleto publicado (o código, a ordem dos esqueletos, uma faixa de lacuna, uma lista usada por ele), a mesma semente passa a dar outro programa: o link que o professor mandou na semana anterior mostraria outros exercícios, e o banco poderia apontar para sementes que não passam mais na conferência.

Por isso a regra é: **família publicada não muda. Para mudar, suba a `versao` e rode `--gravar`.** As chaves do banco mudam junto (`pet_lanche@2:1`). A regra está escrita na docstring de cada arquivo de famílias.

A regra é conferida, não só escrita. O `banco.py` guarda, para cada entrada, a impressão digital do que as sementes dela geram (`IMPRESSOES`, o sha256 dos contextos e códigos, de `gerador.impressao`). Se alguém muda um texto, uma faixa ou uma lista de uma família publicada e as mesmas sementes continuam passando, o banco ficaria igual e nada avisaria; com a impressão, o `--conferir` (e o `--gravar`) falham com "mudou a família publicada sem subir a versao", e o `tests/test_banco.py` também (em todos os Pythons e no Pyodide).

O mesmo vale para `familias.LISTAS`: mudar uma lista muda todos os programas que a usam, de várias famílias de uma vez. Trocar um nome em `pets`, por exemplo, pede subir a versão de toda família que sorteia pets, e a impressão acusa todas elas.

A única exceção é uma família que ainda não chegou à `main`, porque nenhum link dela foi mandado: `--gravar --familia-nao-publicada` regrava a impressão na mesma versão. Foi o que aconteceu antes da primeira entrega, quando "Pacoca", "racao", "abobora" e "maca" saíram das listas e vários textos foram reescritos, tudo ainda na versão 1.

## Limites conhecidos

- **Break no meio do laço.** A mutação de Laços só mexe nos limites do laço. Um `break` que acontece antes da última volta faz o limite não importar, e o item é recusado. Por isso os esqueletos com `break` (`sensor`, `tigelas`) só param na última volta ou não param.
- **while que cai exatamente no limite.** Pelo mesmo motivo, `recarga` e `crescer` só entram no banco quando o valor bate exatamente no limite. É o caso interessante do "erro por um", mas reduz a variedade desses esqueletos.
- **Só duas regras.** As regras de lacuna são só `diferentes` e `menor`. Uma regra nova pede mudar `gerador.REGRAS` e `_cumpre`, com teste. Sem uma regra "a letra está na palavra", `letras_da_cor` às vezes sorteia uma letra que a cor não tem; o contexto diz "tenta trocar", e o exercício vira "nada muda", que também vale.
- **Enganos sem modelo.** O catálogo C01 a C08 não tem "a frase acompanha a variável" (`frase`) nem "a troca acontece uma de cada vez". A troca só ganhou distrator de modelo porque o esqueleto calcula o mesmo valor antes e depois dela (a C04 responde o de antes).
- **Esqueletos parecidos em famílias diferentes.** A série nunca repete um esqueleto, mas `passos` (robo_energia) e `passeio` (pet_lanche) têm a mesma forma e podem cair lado a lado.

## Fora do escopo

Ficaram de fora desta entrega, de propósito:

- **Funções:** o catálogo de concepções (C01 a C08) quase não tem modelos de funções, então os distratores seriam quase todos de regra.
- **Atividades de sala com programas gerados:** link de atividade com `g=`, a tela CriarAtividade e qualquer exercício gerado dentro de uma sala.
- **Nível adaptativo** (uma regra de domínio que sobe ou desce o nível sozinha).
- **Campos novos de evento:** a área Praticar não manda eventos.
- **Outros tipos de exercício:** achar o erro e completar a linha. A área tem só Prever e Rodar.
