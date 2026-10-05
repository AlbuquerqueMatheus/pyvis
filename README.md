# PyVis

Ferramenta web para ensinar Python a crianças e adolescentes (10 a 17 anos). O aluno escreve código no navegador e vê a execução passo a passo, com as variáveis e listas desenhadas a cada linha. TCC de Bacharelado em Ciência da Computação.

## Como rodar

Você precisa do [Node.js](https://nodejs.org) 20 ou mais novo. Na pasta do projeto:

```bash
cd frontend
npm install
npm run dev
```

Abra o endereço que aparecer no terminal (normalmente http://localhost:5173). O Python do navegador (Pyodide, cerca de 10 MB) é servido pelo próprio site e fica em cache depois da primeira vez.

Para gerar a versão de publicação: `npm run build` (o resultado fica em `frontend/dist/`).

## Como testar o motor

Você precisa do Python 3.10 ou mais novo:

```bash
python -m pip install pytest
python -m pytest
```

O GitHub roda esses testes e o build da interface a cada pull request.

## Como está organizado

| Pasta | O que tem |
| --- | --- |
| `pyvis_motor/` | O motor em Python: executa o código do aluno, grava cada passo (`rastreador.py`), converte valores (`valores.py`) e traduz erros para português (`erros.py`). Roda igual no computador e no navegador. |
| `tests/` | Testes do motor com pytest. |
| `frontend/` | A interface em React + TypeScript: editor (CodeMirror), caixinhas animadas (Motion), estilos (Tailwind). |
| `frontend/src/motor/` | O worker que carrega o Pyodide e o motor Python fora da tela principal. |
| `frontend/src/exemplos.ts` | Os programas de exemplo do menu. |

## Como funciona

1. O aluno clica em Executar e o código vai para o worker, que roda o Pyodide.
2. O motor liga o `sys.settrace` e executa o código uma vez, gravando a cada linha: o número da linha, as variáveis e a saída do `print` até ali.
3. Se der erro, ele grava a linha e uma mensagem em português.
4. A interface recebe a lista de passos e o aluno avança, volta ou arrasta a linha do tempo.

Um loop infinito é parado depois de 1.000 passos, e um programa que demora mais de 10 segundos tem o Python reiniciado. O `input()` usa as respostas que o aluno digita antes de executar.
