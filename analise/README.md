# Análise

Scripts de pesquisa do TCC. Rodam fora do navegador, com o Python do computador.

## Sonda de cobertura (`cobertura.py`)

Mede quantos pontos de previsão ganham um distrator de modelo, isto é, uma
alternativa errada produzida ao rodar o programa transformado por uma
concepção equivocada (`pyvis_motor/concepcoes.py`). É a QP1 da tese.

```
python3 analise/cobertura.py                 # pontos rotulados à mão
python3 analise/cobertura.py --candidatos    # também todos os candidatos do rastro
python3 analise/cobertura.py --programas     # lista cada ponto com as alternativas
python3 analise/cobertura.py --json medicao.json --limite 200
```

A saída traz:

- a cobertura por tipo de pergunta: pontos com 1 ou mais e com 2 ou mais
  distratores de modelo, e a parte das respostas dos modelos descartada por
  ser igual à certa ou repetida;
- a coluna "sem C04", porque a concepção C04 (a atribuição não muda) dá
  sempre o valor antigo e infla a cobertura dos pontos de valor;
- a cobertura por concepção;
- o critério pré-registrado: pelo menos 30% dos pontos de saída, voltas e
  decisão com um distrator de modelo;
- a concordância, por programa, entre os rótulos à mão e as concepções que
  geraram distrator;
- o tempo de geração e o custo do `rastrear_leve` comparado ao rastro completo.

## Corpus (`tests/corpus/`)

São programas típicos de aula, com metadados nos comentários do começo do arquivo:

```
# Contagem regressiva do foguete com while.
# @entradas: []
# @pontos: voltas 6; valor 8 contagem; saida 7 @2; decisao 6 @6; saida tudo
# @concepcoes: C04
```

- `@entradas`: lista JSON com as respostas dos `input()`.
- `@semente`: semente do `random` (opcional, padrão 0).
- `@pontos`: lista de `tipo linha [nome] [@ocorrência]`, separada por `;`.
  - A linha é a do arquivo, contando o cabeçalho.
  - `@2` é a 2ª vez que aquela linha roda; num ponto de voltas, é a 2ª vez que o laço começa.
  - `saida tudo` é a saída do programa inteiro.
- `@concepcoes`: as concepções que um professor espera observar nesses pontos, ou `nenhuma`.

Os rótulos `@concepcoes` desta versão foram escritos por quem implementou os
modelos e por isso concordam demais com eles. Para medir precisão e revocação
de verdade, refaça esses rótulos sem olhar a saída do script, de preferência
com dois avaliadores.
