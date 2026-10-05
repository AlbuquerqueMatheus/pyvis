# PyVis

Ferramenta web para ensinar Python a crianças e adolescentes (10 a 17 anos). O aluno escreve código no navegador e vê a execução passo a passo, com as variáveis e listas desenhadas a cada linha. TCC de Bacharelado em Ciência da Computação.

## Como rodar

Você só precisa do Python 3.10 ou mais novo. Na pasta do projeto:

```bash
python -m http.server 8000
```

Abra http://localhost:8000/web/ no navegador. Na primeira vez, o Python do navegador (Pyodide, cerca de 10 MB) é baixado da internet e fica em cache.

## Como testar o motor

```bash
python -m pip install pytest
python -m pytest
```

## Como está organizado

| Pasta | O que tem |
| --- | --- |
| `pyvis_motor/` | O motor em Python: executa o código do aluno, grava cada passo (`rastreador.py`), converte valores (`valores.py`) e traduz erros para português (`erros.py`). Roda igual no computador e no navegador. |
| `tests/` | Testes do motor com pytest. |
| `web/` | A página: `worker.js` carrega o Pyodide e o motor fora da tela principal; `app.js` desenha os passos. |

## Como funciona

1. O aluno clica em Executar e o código vai para o `worker.js`.
2. O motor liga o `sys.settrace` e executa o código uma vez, gravando a cada linha: o número da linha, as variáveis e a saída do `print` até ali.
3. Se der erro, ele grava a linha e uma mensagem em português.
4. A página recebe a lista de passos e o aluno avança e volta por ela.

Um loop infinito é parado depois de 1.000 passos, e um programa que demora mais de 10 segundos tem o Python reiniciado.
