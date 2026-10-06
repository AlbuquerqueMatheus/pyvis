# Roteiro do PyVis: ondas 1 e 2 (especificação de implementação)

Gerado a partir do roteiro revisado (pesquisa em 5 lentes + 3 revisões adversariais). Este arquivo é a referência para implementar as ondas 1 e 2.

## Visão

O PyVis deixa de ser um filme da execução e vira um lugar onde o aluno aprende a pensar como o computador. Ele segue um ciclo único e visível, o PRIMM em pt-BR: Prever → Rodar → Investigar → Modificar → Criar. Em qualquer programa, inclusive o que o aluno acabou de escrever, a ferramenta pede um palpite nos momentos certos ('quanto vai valer total?', 'o if vai entrar?', 'o que aparece na tela?') e só depois mostra o que aconteceu. Quando o palpite erra, o PyVis reconhece a ideia provável por trás dele, porque executa uma versão do programa que segue essa ideia, e mostra a regra na própria execução. Tudo é gerado do rastro, em Python rodando no navegador, sem contas, sem IA generativa e com o código do aluno isolado. O que é revolucionário não é a quantidade de recursos, e sim transformar cada erro em diagnóstico. Cada onda seguinte só entra se servir a uma etapa do ciclo.

## Princípios (obrigatórios)

- Um ciclo só e visível: Prever → Rodar → Investigar → Modificar → Criar (PRIMM em pt-BR). 'Entender' é o feedback dentro de Rodar. Cada recurso pertence a uma única etapa; o recurso que não tem etapa sai.
- Palpite antes de ver, e nada entrega o palpite. Tudo o que vem do futuro do rastro declara de qual pergunta depende e só aparece depois da resposta: total de voltas, ramo não tomado, limites traduzidos do range, efeito da linha. Essa regra fica no motor e é testada.
- O rastro é a matéria-prima: perguntas, distratores, narração e feedback saem do mesmo rastro e da AST, para qualquer programa. O professor escolhe o programa e não escreve perguntas.
- Lógica pedagógica em Python (pyvis_motor), testada com pytest e rodando igual no Pyodide e no servidor. O TypeScript só desenha, anima e confere se um campo já pode aparecer.
- O erro é diagnóstico, não perda. O feedback diz a regra ('o range para antes do último número'), nunca o rótulo técnico da concepção, e vem em camadas. O elogio vai para o processo. Não há sequência de acertos, vidas nem porcentagem durante a atividade.
- Honestidade diagnóstica: quando nenhum modelo explica o erro, o PyVis explica pelo efeito real da linha e não inventa uma concepção. Distrator de regra nunca conta como diagnóstico.
- A atividade decide a tela: o link liga só os recursos da etapa, com um orçamento de no máximo 1 balão e 1 destaque animado por passo.
- Motivar sem manipular e sem imitar jogo de azar: 'palpite', nunca 'aposta'. Sem ranking, pontos, sequência, corações, contadores sociais nem recompensa aleatória.
- O código do aluno é código não confiável: roda isolado numa origem sem dados e sem acesso à rede.
- Privacidade desde o projeto: pseudônimo aleatório, diário sem código, sem entradas e sem texto livre, higiene de literais e comentários em tudo o que sai do aparelho, botão 'apagar deste aparelho' e expiração. Dado pseudonimizado continua sendo dado pessoal (LGPD).
- Python de verdade para todas as idades. O que muda é o andaime (alternativas ou resposta livre, frases curtas), definido pelo link durante as atividades.
- Acessível por padrão: nada indicado só pela cor, tudo operável pelo teclado, prefers-reduced-motion, frases curtas (até 12 palavras na versão padrão) e alvos de toque grandes.
- Medir antes de enfeitar: cada interação relevante vira um evento pseudonimizado, e a tese é decidida por dados do corpus antes da interface.

## Fora do escopo (nunca implementar)

- **Contas de aluno (login, e-mail, senha)**: A LGPD (art. 14) exige o mínimo necessário para dados de crianças e adolescentes. Código da sala, apelido gerado e progresso portátil por QR resolvem sem essa barreira.
- **Vocabulário de aposta ('Aposte!', 'apostas certas')**: Normaliza a linguagem de jogo de azar num país em que apostas por menores são proibidas (Lei 14.790/2023), e pais, escolas ou o CEP podem rejeitar a ferramenta só por isso. A ferramenta usa 'palpite' e 'previsão', e uma busca no código impede que 'apost' apareça em textos para o aluno.
- **Ranking, placar individual, pontos, sequência de acertos, corações e recompensa aleatória**: Placares e competição reduziram a motivação intrínseca e as notas num curso gamificado com ranking, medalhas e competição (Hanus & Fox, 2015). Recompensas esperadas minam a motivação (Deci, Koestner & Ryan, 1999). A sequência transforma o erro em perda e distorce os dados de pulos. O art. 20 do ECA Digital, que proíbe loot boxes em jogos para menores, entra só como analogia.
- **Chat livre e texto livre de alunos enviados ao servidor**: É um risco com menores e um peso de moderação para um desenvolvedor só. A ferramenta usa mensagens prontas e hipóteses estruturadas; a conversa acontece no Meet, sob supervisão do professor.
- **Executar o código dos alunos no servidor**: Exigiria uma sandbox cara e arriscada. Com o rastro determinístico, o professor reexecuta no próprio navegador, dentro do executor isolado.
- **Tutor de IA generativa (antiga onda 5)**: Ficou fora do TCC e do produto por enquanto. Sem guarda-corpos, a IA pode prejudicar a aprendizagem (Bastani et al., 2025, PNAS, doi:10.1073/pnas.2422633122). Mandar texto de menores a um provedor estrangeiro é transferência internacional (LGPD art. 33). Também faltaria um protocolo para revelações graves (ECA art. 13). Só poderia voltar com hipótese estruturada em vez de texto livre, retenção zero contratual, detector de risco que avisa só o professor, aviso antes de digitar e cota definida pelo professor, sem metáfora de vidas.
- **Linguagem própria em blocos ou linguagem gradual**: Foge do escopo de um TCC, e adolescentes acham pouco autênticos os ambientes de blocos (Weintrop & Wilensky, 2015). Parsons e alternativas reduzem a digitação mantendo o Python de verdade.
- **Modo dupla remota com edição sincronizada**: Custa muito (CRDT ou trava de turno) sem contribuir para a tese, e o Meet com compartilhamento de tela já permite trabalhar em dupla.
- **Bayesian Knowledge Tracing**: Regras transparentes são mais fáceis de explicar a alunos, pais e banca, e o BKT exige parâmetros ajustados com dados que ainda não existem.
- **Comunidade ou galeria pública aberta**: É problemática para a privacidade de menores. O PyVis tem só mural fechado por sala, moderado e sem métricas sociais.
- **Bibliotecas externas e GUI além do turtle (pygame, numpy, tkinter)**: Fogem do objetivo de rastrear conceitos básicos, pesam no download do Pyodide e quebram o modelo de passos.
- **Leitura em voz alta ao microfone para a turma e gravação de voz pela ferramenta**: Expõe alunos tímidos ou ansiosos. Swidan & Hermans (2019) só mostraram ganho na memória da sintaxe quando o próprio aluno lia, sem diferença na compreensão. SpeechRecognition envia áudio para fora.
- **Fonte 'para disléxicos' (OpenDyslexic)**: Não mostrou ganho de leitura (Rello & Baeza-Yates, 2013).
- **Celebrações frequentes e elogio à inteligência**: Elogiar a inteligência reduz a persistência após falhas em crianças (Mueller & Dweck, 1998). O feedback elogia o processo ('lembrou que a lista começa no 0').
- **Mapa narrativo extenso com história por capítulos**: O custo de produzir conteúdo é alto para uma pessoa só e não contribui para a tese.

## Onda 1: Fundação segura do motor (cerca de 2 semanas)

Corrigir as premissas do tracer que os revisores derrubaram, isolar o código do aluno, preparar o protocolo do worker e medir no corpus, já na semana 1 ou 2, se os distratores por modelo executável têm cobertura suficiente para sustentar a tese. Roda toda no navegador, sem servidor, sobre o código atual (rastreador.py, valores.py, erros.py, worker.ts, useMotor.ts).


### 1.1 Executor isolado: o código do aluno não enxerga nada

**O que o aluno vê.** Para o aluno, nada muda: ele escreve e executa. Por baixo, o programa roda numa caixa separada, que não vê os dados guardados no aparelho nem consegue mandar nada para a internet. Com import js, o aluno vê 'Esse módulo não está disponível no PyVis'. Com 10**10**9, depois de 5 s aparece 'O programa demorou demais e foi parado', e a página continua funcionando.

**Por quê.** As próximas ondas executam código de terceiros: links de atividade, código de colegas na galeria e reexecução no painel do professor. Hoje o worker roda na mesma origem do app, com os builtins completos, e import js funciona. Sem isolamento, um link malicioso poderia ler o diário de outro aluno e mandá-lo para fora.

**Implementação.**

HOSPEDAGEM: duas origens.
- O app.
- O executor (um subdomínio executor. ou um segundo site estático): HTML mínimo + worker + public/pyodide.
- O executor é servido com CSP "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; frame-ancestors <origem do app>". Confirmar se o Pyodide 314 exige mais alguma diretiva.
- O app carrega <iframe sandbox='allow-scripts allow-same-origin'>. Aqui o allow-same-origin vale para a origem do executor, que é diferente da do app, então o código do aluno não alcança o localStorage nem o IndexedDB do app.
- Em desenvolvimento, o executor roda numa segunda porta do Vite.

PONTE: novo frontend/src/motor/ponte.ts substitui o new Worker direto no useMotor.ts. Usa postMessage com conferência de event.origin e validação do formato da mensagem.

PYTHON: novo pyvis_motor/seguranca.py.
- Um finder em sys.meta_path recusa js, pyodide, pyodide_js, _pyodide, micropip e pyodide_http com ImportError amigável.
- É instalado só durante o exec do aluno, porque o motor já importou o que precisa.

TEMPO LIMITE: 5 s, do lado da página, só para a ação rastrear: terminate e recriação do worker.

SAÍDA: sempre como texto, sem transformar URL em link.

TESTES: tests/test_seguranca.py confere que import js e import pyodide são recusados e que o motor continua funcionando depois. Checagem manual: um código que tenta fetch é bloqueado pela CSP.


### 1.2 Rastro normalizado por comando (quadro, retorno e voltas)

**O que o aluno vê.** A linha destacada passa a seguir a ordem real do programa. Uma lista escrita em 3 linhas fica destacada inteira, uma vez, em vez de pular para a linha 2 antes da linha 1. Depois de chamar dobro(4), o passo seguinte mostra 'dobro devolveu 8'. Uma compreensão de lista conta como um passo só, e não como ×4.

**Por quê.** Previsões, efeito, decisão, voltas e narração dependem de 'um passo = um comando, no mesmo quadro'. A sonda dos revisores, no Pyodide 3.14.2, achou 6 casos em que isso falha hoje: comando em várias linhas, if com o corpo na mesma linha, chamada dentro da condição, return sem passo próprio, compreensões no 3.12+ (PEP 709) e for encerrado por break. Sem a correção, todo diagnóstico sai errado nesses casos.

**Implementação.**

PYTHON, novo pyvis_motor/estrutura.py: analisar(codigo) devolve {comandos: Comando[], linha_para_comando: {linha: id}}.

Comando = {id, tipo, linhas, cabecalho, corpo, orelse, corpo_mesma_linha, pai, acumulador}, em que:
- tipo: 'atrib' | 'aug' | 'if' | 'elif' | 'while' | 'for' | 'print' | 'expr' | 'def' | 'return' | 'break' | 'continue' | 'outro';
- linhas: [ini, fim];
- cabecalho, corpo e orelse: [ini, fim] ou null;
- corpo_mesma_linha: bool;
- pai: id do bloco que contém o comando, ou null;
- acumulador: {nome, contador: bool} ou null. Heurística: x = x + ... ou x += ... dentro de um laço; contador quando o incremento é 1. Dispensa a detecção de papéis.

PYTHON, rastreador.py (pós-processamento e tracer):
(a) Cada evento 'line' é mapeado para um comando. Eventos consecutivos do mesmo comando no mesmo quadro são fundidos, e fica o estado do primeiro. Nomes internos de compreensões são filtrados.
(b) O evento 'call' atribui quadro = contador sequencial. O passo ganha quadro e profundidade.
(c) O 'return' de um quadro do aluno anota retorno = {funcao, valor: Valor} no PRÓXIMO passo gravado, sem criar passo visível.
(d) Novo campo proximo_no_quadro: índice do próximo passo do mesmo quadro, ou null. Efeito e decisão usam esse índice, nunca i+1.
(e) Voltas: cabeçalho seguido de linha do corpo é uma nova volta; seguido de linha de fora do corpo é a saída do laço; alcançado vindo de fora do corpo é uma nova entrada no laço.
(f) random.seed(semente) antes do exec. O resultado devolve a semente e deterministico = false se o código importa time, datetime ou secrets.

CONTRATO v2 (Python e tipos.ts):
Resultado = {versao: 2, semente, deterministico, passos: Passo[], saida, erro, estrutura: {comandos}}
Passo = {i, linha, comando: number|null, evento: 'linha'|'fim', quadro, profundidade, funcao, globais, locais, saida, proximo_no_quadro, retorno?}
Os campos efeito, decisao, volta, narracao e depende_de entram na Onda 2.

TESTES: tests/test_estrutura.py com os 6 casos dos revisores e os 8 exemplos. Os testes atuais de test_rastreador.py continuam passando, ajustados só onde houver fusão de eventos.


### 1.3 Avaliador seguro de condições

**O que o aluno vê.** É o que permite, na Onda 2, mostrar no if o balão '7 >= 6 → Verdadeiro'. Em 'i < len(l) and l[i] > 0', quando o lado esquerdo é falso, o lado direito aparece marcado como 'nem foi calculado'. Se não for possível mostrar o valor sem risco, o balão diz só 'Verdadeiro'.

**Por quê.** Usar eval() em nós 'permitidos' não é seguro. Com numeros = map(int, ...), avaliar max(numeros) no tracer consome o iterador e quebra o programa do aluno, como os revisores reproduziram. O eval() também ignora o curto-circuito e mostraria valores que nunca existiram (equívoco NoShortCircuit).

**Implementação.**

PYTHON, novo pyvis_motor/avaliador.py: avaliar(no_test, f_globals, f_locals) devolve {texto: str|None, valor: bool|None, nao_calculado: [[col_ini, col_fim]]}.

Percorre a AST nó a nó, sem eval e sem compile:
- Name: só lê valores de tipo EXATO int, float, str, bool, NoneType, list, tuple, dict, set ou range.
- Constant.
- Compare encadeado, parando no primeiro falso.
- BoolOp com curto-circuito, marcando o que não foi calculado.
- BinOp e UnaryOp só entre tipos seguros, com limite de tamanho para str * int.
- Subscript só em list, tuple, str ou dict exatos.
- len, abs, min e max só com argumentos de tipo seguro, nunca iteradores.
- Qualquer outra coisa: desiste (texto None).
O repr é cortado em 30 caracteres.

USO: chamado no tracer, no evento 'line' do cabeçalho de if, elif e while, e gravado em passo['_decisao_bruta'] para a Onda 2.

RAMO: decidido pelo próximo passo do mesmo quadro e pelas faixas de estrutura.py. Se o corpo está na mesma linha do cabeçalho ou há chamada na condição, usa o valor do avaliador; sem valor, o ramo fica 'desconhecido'.

TESTES: tests/test_avaliador.py com map, gerador, defaultdict e um objeto com __getitem__. A saída do programa precisa ser idêntica com e sem anotação, e o curto-circuito tem de aparecer marcado.


### 1.4 Protocolo do worker, desempenho e higiene do repositório

**O que o aluno vê.** Executar responde rápido mesmo no celular, e uma correção nunca é confundida com uma execução. O exemplo 7 passa a perguntar o nome de um robô, não o nome do aluno, e o campo de entradas avisa 'não use seu nome de verdade'. Um erro de variável local dentro de função passa a ter uma explicação correta.

**Por quê.** A Onda 2 precisa de várias ações no worker. Hoje há um callback único e um relógio único, então uma resposta pode cair no lugar errado e o relógio de 10 s pode matar uma correção. As decorações do editor são recriadas a cada passo, o que pesa em celular fraco. O UnboundLocalError hoje mostra 'Você usou `esse nome`...', porque o regex não casa no 3.12+. O exemplo 7 coleta o nome real de menores.

**Implementação.**

PROTOCOLO:
- Pedido: {id, acao: 'rastrear' | 'preparar_atividade' | 'corrigir', dados}. Resposta: {id, ok, resultado | erro}.
- useMotor.ts guarda um Map de promessas pendentes.
- O tempo limite de 5 s vale só para rastrear.
- preparar_atividade tem orçamento interno de 500 ms: o Python corta e devolve o que tiver.
- O worker guarda o último resultado em Python (ultimo_resultado), para as ações seguintes não reenviarem o rastro.
- Duas fases: primeiro o rastro, depois a atividade.

EDITOR: em Editor.tsx, python() e lineWrapping ficam fixos. As decorações do passo vão para um StateField alimentado por um StateEffect irPara, e os widgets implementam eq().

TAMANHO: Variaveis.tsx deixa de fazer JSON.stringify a cada renderização e passa a comparar um hash curto calculado em valores.py (campo 'h' no Valor). Em aparelhos fracos (deviceMemory <= 2), o limite cai para 300 passos.

ERROS: em erros.py, o UnboundLocalError é tratado antes do NameError, com o regex r"local variable '(\w+)'" e a mensagem 'Dentro da função, total = ... cria uma variável nova, só da função. Para usar a de fora, passe-a como parâmetro e devolva com return.' Teste em tests/test_erros.py.

EXEMPLOS: exemplos.ts troca o exemplo 7 por 'Qual é o nome do seu robô?'.

CI E VERSÕES:
- pyproject: requires-python >= 3.12.
- CI com matriz 3.12, 3.13 e 3.14.
- Um job que roda o pytest do motor dentro do Pyodide em Node, com um script de cerca de 15 linhas.

HOSPEDAGEM: brotli e Cache-Control longo para /pyodide/. É configuração, não feature.

MEDIÇÃO: tempo de rastrear e de JSON.parse com CPU 6x mais lenta no DevTools e num Android de entrada.


### 1.5 Corpus e sonda de cobertura: o número que decide a tese

**O que o aluno vê.** Não é uma tela para o aluno. São de 40 a 60 programas típicos das aulas do Matheus (variáveis, if, while, for/range, listas, input), cada um com os pontos de previsão e as concepções aplicáveis rotulados à mão. Um script mede quantos pontos ganham um distrator diagnóstico.

**Por quê.** Na sonda dos revisores com os 8 exemplos, 30 dos 35 pontos do tipo 'valor' não ganharam nenhum distrator diagnóstico, 5 ganharam um e nenhum ganhou dois. Esse número decide se a QP1 se sustenta e como os programas do estudo devem ser desenhados para tornar as concepções observáveis. É também o Plano B do TCC, que não depende de menores nem do CEP.

**Implementação.**

CORPUS: tests/corpus/*.py, com metadados em comentários: # @entradas, # @pontos (comando e tipo) e # @concepcoes.

PYTHON, pyvis_motor/concepcoes.py (esqueleto, completado em 2.3):
- As 8 transformações.
- rastrear_leve(codigo, entradas, alvos, semente, limite=200): sem fotos de estado; só conta ocorrências por comando e captura os valores-alvo. É cerca de 50 vezes mais barato.

ANÁLISE: analise/cobertura.py gera a tabela por concepção e por tipo de pergunta, com:
- % de pontos com pelo menos 1 distrator de modelo;
- % com 2 ou mais;
- % de alternativas descartadas por serem iguais à certa ou repetidas;
- tempo de geração.

CRITÉRIO DE DECISÃO, pré-registrado no OSF: se menos de 30% dos pontos de saída, voltas e decisão ganharem distrator de modelo, a tese passa a tratar a cobertura como resultado (e não como premissa), e os programas do estudo são desenhados para tornar as concepções observáveis.

PLAUSIBILIDADE: dois professores julgam uma amostra dos distratores (kappa de Cohen).


## Onda 2: Prever com diagnóstico (a intervenção do TCC, de 5 a 6 semanas)

Fazer o PyVis pedir palpites gerados do rastro, explicar o erro pela concepção provável e narrar em texto, sem que nenhuma anotação entregue a resposta. Inclui a distribuição por link e uma versão mínima da sala segura, porque a coleta começa aqui. Ordem de construção: 2.1 → 2.4 → 2.2 → 2.3 → 2.5 → 2.6. O narrador (2.4) vem cedo porque está presente nas duas condições do estudo e precisa estar congelado antes do piloto. Etapas do ciclo: Prever e Rodar. Sem servidor.


### 2.1 Execução que se explica, sem entregar o palpite

**O que o aluno vê.** No `if nota >= 6:` aparece o balão '7 >= 6 → Verdadeiro'. Só depois que a decisão acontece, o else fica esmaecido, com ícone e a etiqueta 'pulado'. No for, a pílula mostra 'volta 2'; o 'de 4' só aparece quando o laço termina. A caixinha que mudou mostra o novo valor com o antigo riscado ao lado, e o passo depois de uma chamada mostra 'dobro devolveu 8'. Etapa: Rodar.

**Por quê.** Swidan et al. (2018), com 145 alunos de 7 a 17 anos em Scratch, encontraram como equívocos mais comuns a sequência das instruções e a ideia de que a variável guarda vários valores. Pea (1986) descreve o bug do paralelismo. Tornar explícitos a decisão, o ramo e a volta mostra a regra que a seta do Python Tutor só sugere. A revelação controlada corrige o que os revisores apontaram: 'volta 2 de 4', o else esmaecido e a contagem total respondiam às perguntas antes do palpite.

**Implementação.**

PYTHON, novo pyvis_motor/anotar.py: anotar(resultado) acrescenta a cada passo:
- efeito = {criadas: [nome], mudadas: [{nome, escopo: 'global'|'local', antes: Valor, depois: Valor}], saida_nova: str}. É o diff entre passos[i] e passos[proximo_no_quadro], já que o passo i guarda o estado ANTES do comando.
- decisao = {texto: '7 >= 6' | null, valor: bool|null, ramo: 'corpo'|'orelse'|'sai'|'desconhecido', nao_calculado: [[col_ini, col_fim]]}, vinda do avaliador (1.3).
- volta = {laco: comando_id, n, total: number|null, total_visivel_desde: índice do passo de saída do laço}.

REGRA DE REVELAÇÃO (no motor):
- Cada passo ganha depende_de: {campo: [ponto_id]}, por exemplo {'decisao.ramo': ['p4'], 'volta.total': ['p2'], 'efeito': ['p5']}. A atividade (2.2) preenche esse campo.
- O TS só aplica a função pura visivel(passo, campo, respondidos, passoAtual). Além disso, o ramo pulado só aparece a partir do passo seguinte à decisão, e o total de voltas a partir de total_visivel_desde.

TYPESCRIPT:
- tipos.ts ganha os novos campos.
- Editor.tsx, no StateField de 1.4, ganha a linha esmaecida com ícone na margem e o widget inline do balão (aria-hidden; o mesmo conteúdo vai para o narrador).
- Variaveis.tsx mostra o valor antigo com <del>.
- Controles.tsx ganha a pílula da volta.

FICAM PARA DEPOIS: contagem ×N na margem, a fileira do iterável e o aviso do while no meio do corpo.

TESTES:
- tests/test_anotar.py, com os 8 exemplos e os 6 casos de 1.2.
- tests/test_revelacao.py: para cada ponto do corpus, nenhum campo visível antes da resposta contém o valor ou o texto da resposta.


### 2.2 Palpites gerados do rastro (modo Prever)

**O que o aluno vê.** Antes de rodar: 'Qual é o seu palpite? O que vai aparecer na tela?'. Durante o passo a passo, em até 6 momentos, a caixinha vira '?' e um balão pergunta 'Depois desta linha, quanto vale total?', 'O if vai entrar?', 'Quantas voltas o laço vai dar?' ou 'O que aparece na tela?'.

O formato é definido no link, não escolhido pelo aluno durante o estudo. Para 10 a 12 anos, alternativas. Para 13 a 17, resposta livre com dois botões grandes, 'número' e 'texto' (o texto ganha aspas sozinho).

Só depois da resposta a animação mostra o passo. Acertou: ✓ e 'Você lembrou que o range para antes do 5'. Errou: 'Seu palpite: 5. O Python guardou 6.', e entra o Detetive (2.3). O botão 'pular' fica sempre visível. Não há contagem de acertos durante a atividade nem sequência.

Os modos no link são Assistir (o de hoje, mais o narrador) e Prever. Etapa: Prever.

**Por quê.** Na meta-análise de Hundhausen et al. (2002), o que o aluno faz com a visualização pesou mais do que o que ela mostra, e a taxonomia de engajamento põe 'responder' acima de 'visualização controlada'. Prever e depois confrontar o resultado gera conflito cognitivo, estratégia proposta por Ma et al. (2011) para remediar modelos errados. Em física, assistir demonstrações sem prever rendeu pouco, e prever antes melhorou o resultado (Crouch et al., 2004). O PRIMM entra como enquadramento pedagógico, não como prova do efeito de prever isolado. Myller (2007) é o precedente direto de perguntas geradas automaticamente.

**Implementação.**

PYTHON, novo pyvis_motor/previsao.py.

preparar_atividade(resultado, codigo, entradas, config) devolve uma Atividade. config = {modo: 'assistir'|'prever', formato: 'alternativas'|'livre', max_pontos: 6, semente}.

escolher_pontos — os candidatos são os passos i com:
(a) mudança de variável não trivial, com prioridade ao acumulador ou contador de estrutura.py e às duas primeiras voltas de cada laço;
(b) decisão de if ou while;
(c) saída nova;
(d) saída do laço (pergunta de voltas).
O ponto ganha +2 se alguma concepção for observável naquele tipo de pergunta (concepcoes.observaveis). Densidade: no máximo 1 ponto a cada 3 passos e 6 por programa, sem repetir o par (tipo, comando).

CONTRATO:
Atividade = {versao: 1, modo, formato, pontos: Ponto[], depende_de_por_passo: {i: {campo: [ponto_id]}}, cobertura: {pontos_com_modelo, total}}
Ponto = {id: 'p1', passo: i, tipo: 'valor'|'decisao'|'voltas'|'saida', alvo: {nome?, comando}, pergunta, resposta: {texto, tipo_valor: 'numero'|'texto'|'bool'|'lista'}, formato, sensivel_a_tipo: bool, alternativas?: Alternativa[], concepcoes_observaveis: [id]}
O passo i do ponto é aquele em que a pergunta aparece, quando o aluno tenta avançar.
Alternativa = {id, texto, certa: bool, concepcao: id|null, origem: 'correta'|'modelo'|'regra', feedback: Feedback|null}
- São de 3 a 4 alternativas, embaralhadas com a semente.
- As de origem 'regra' (valor antigo, ±1, valor de outra variável) têm concepcao null e nunca contam como diagnóstico.
- Pontos sensíveis a tipo (texto vindo de input) são sempre de alternativas para 10 a 12 anos.

corrigir(ponto_id, {texto, tipo_escolhido}) é uma ação do worker, só para resposta livre (a múltipla escolha já vem corrigida na Atividade).
- Com 'número', normaliza com ast.literal_eval; com 'texto', compara a string.
- Devolve Correcao = {certa, valor_certo, tipo_certo, concepcao, feedback}.
- Valor certo com tipo errado gera uma mensagem pedagógica e só conta como 'input devolve número' se o aluno marcou 'número'.
- 7 contra 7.0 gera mensagem, não diagnóstico.

TYPESCRIPT:
- Novo BalaoPrevisao.tsx intercepta irPara quando o passo atual é um ponto sem resposta, e o autoplay pausa.
- Variaveis.tsx mostra a caixinha '?'.
- Teclado: as teclas de 1 a 4 escolhem a alternativa, Enter confirma e o foco é gerenciado.
- aria-live só no feedback.

REGISTRO: cada resposta vira um evento Prediction (2.5).

TESTES: tests/test_previsao.py, com os pontos esperados nos exemplos e no corpus, a densidade e a normalização das respostas.


### 2.3 Detetive: concepções como modelos executáveis observáveis

**O que o aluno vê.** Quando o palpite erra: 'Você respondeu 5 voltas, como se o range(1, 5) chegasse até o 5. O range para ANTES do último número.' O aluno abre as camadas se quiser:
(1) Onde olhar: a linha do tempo vai ao passo, e a caixinha certa ganha um contorno.
(2) A regra, explicada com os valores da execução.
(3) Me mostra: o passo resolvido.

O aluno nunca vê o nome técnico nem o id da concepção. Quando nenhum modelo explica o erro, o feedback é honesto e se baseia no efeito real: 'O Python guardou 6 porque total valia 3 e numero valia 3.' Etapa: Rodar.

**Por quê.** Concepções equivocadas são modelos coerentes, mas errados, e pedem intervenção direcionada (Qian & Lehman, 2017). Em Qian & Lehman (2019), o feedback direcionado aumentou as soluções melhoradas de 34% para 45%. O estudo teve 23 alunos de alta habilidade num programa de férias, em Java, então vale como indício e não como prova para este público. O feedback funciona quando é específico e dado na hora certa (Shute, 2008). Apenas reescrever mensagens de erro tem evidência mista (Becker et al., 2019), por isso aqui o feedback é ligado à execução. A base conceitual é a do bug executável (Brown & Burton, 1978).

**Implementação.**

PYTHON, pyvis_motor/concepcoes.py.

Concepcao = {id, regra_para_aluno (até 12 palavras), camadas: {onde, regra (modelo de frase com {valores}), resolvido}, transformar: NodeTransformer|None, regra_rastro: função|None, observavel_em: ['voltas'|'saida'|'valor'|'decisao'], padrao_ast: função, referencias}.

CATÁLOGO (8), priorizado a partir de Swidan (2018), Qian & Lehman (2017), progmiscon e Cortinovis (2023):
- C01 range-inclui-fim: range(a, b) → range(a, b + 1).
- C02 range-comeca-em-1: range(n) → range(1, n + 1).
- C03 input-e-numero: um input(...) que não esteja dentro de int() ou float() vira _num(input(...)).
- C04 atribuicao-nao-muda: congela a atribuição alvo naquela ocorrência.
- C05 else-tambem-roda: corpo e orelse executados em sequência.
- C06 while-vigia-condicao: insere 'if not (cond): break' depois de cada comando do corpo. Só é observável quando a condição fica falsa no meio do corpo.
- C07 indice-comeca-em-1: lista[i] em leitura vira lista[i - 1].
- C08 divisao-inteira: a / b entre ints vira a // b.

EXECUÇÃO:
- Cada transformação roda UMA vez por programa, e só se padrao_ast encontrar a construção.
- Usa rastrear_leve, com limite de 200 passos e a mesma semente e entradas. Se estourar o limite, a concepção fica sem alternativa.
- O alinhamento é por (comando, ocorrência).
- Alternativas iguais à certa ou repetidas são descartadas.
- Programas não determinísticos não geram alternativas de modelo.

diagnosticar(ponto, resposta) devolve uma concepção só quando um único modelo coincide com a resposta.

Feedback = {onde: {passo, destacar: nome|null}, regra: str, resolvido: str}.

FORA DESTA ONDA: lâmpada de alertas silenciosos (vai para 4.7), quadrado fantasma do IndexError e personagem Py.

TYPESCRIPT: PainelDetetive.tsx com 3 botões de camada; cada uso vira um evento Feedback.Layer.

TESTES: para cada concepção, programas positivos (que geram o distrator) e negativos (que não geram). Precisão e revocação entram na QP1.


### 2.4 Narrador em texto

**O que o aluno vê.** Embaixo dos controles aparece uma frase curta, de até 12 palavras: 'total recebe total + numero: agora vale 6.', 'nota >= 6? 7 >= 6, Verdadeiro: entra no if.', 'input devolve texto: chegou "11".'. O botão 'Mais detalhes' mostra a versão longa.

Enquanto há uma pergunta pendente sobre um laço, a leitura fica literal ('para cada numero em range(1, 5)'); a tradução ('de 1 até 4') só aparece depois. Com o balão de palpite aberto, o narrador não mostra o efeito. Não há voz nesta onda.

O narrador é a camada 2 do Detetive e está presente nas DUAS condições do estudo. Etapa: Rodar.

**Por quê.** A narração torna explícitas as regras da máquina nocional (Sorva, 2013) e descreve cada passo como uma ação mecânica, contra o superbug de achar que o computador entende a intenção (Pea, 1986). Ler '=' como 'recebe' ataca a confusão entre atribuição e igualdade. O PLTutor, que explica cada passo, é precedente, mas veio de um estudo pequeno com alunos de CS1 autosselecionados. As frases são curtas porque o público inclui leitores pouco fluentes.

**Implementação.**

PYTHON, novo pyvis_motor/narrador.py:
- ler_comando(comando) é calculado UMA vez por comando, a partir da AST, em duas versões: literal e traduzida.
- narrar(passo, resultado) é calculado por passo para cerca de 10 construções (Assign, AugAssign, If/elif, While, For, print, input, def, return e chamada), com uma frase genérica de reserva. Usa efeito, decisão, volta e retorno.
- Reaproveita NOMES_DE_TIPO de erros.py.

CONTRATO:
- estrutura.comandos[k].leitura = {literal, traduzida, traduzida_depende_de: [ponto_id]}
- passo.narracao = {curta, longa}. O TS esconde o efeito enquanto o ponto do passo estiver pendente (depende_de['efeito']).

TYPESCRIPT:
- Narracao.tsx com aria-live='polite', disparado só quando o aluno avança.
- Setas do teclado em Controles.tsx.
- MotionConfig reducedMotion='user' envolvendo o app.

TESTES: snapshot das frases, versão curta com até 12 palavras e teste de não-vazamento junto com test_revelacao.py.


### 2.5 Atividade por link, sala mínima segura e diário pseudonimizado

**O que o aluno vê.** O professor clica em 'Criar atividade' e escolhe os programas (exemplos pelo id ou código próprio), as entradas, o modo, o formato das perguntas e se a atividade é do estudo. Recebe um link.

O aluno abre o link e:
- lê uma tela de 3 frases ilustradas: 'O professor vê suas respostas desta aula. Não pedimos seu nome. Você pode apagar tudo deste aparelho.';
- recebe um apelido gerado, como 'Tucano Azul 7', que pode trocar por outro da lista;
- digita o código da sala e faz a atividade.

No fim, 'Meu resumo' mostra 'ideias que você já entendeu' e 'ideias para revisar', com as ideias antes de qualquer número. 'Entregar ao professor' baixa um arquivo; com a Onda 3 pronta, a entrega é automática. O botão 'Sair e apagar deste aparelho' fica sempre visível, e há uma página para os pais.

**Por quê.** A avaliação formativa só funciona quando a evidência chega a quem decide o próximo passo do ensino (Black & Wiliam, 1998). Eventos num formato inspirado no ProgSnap2 permitem comparar com a literatura. A LGPD (art. 14, §6º) exige informação adequada à idade, e dado pseudonimizado continua sendo dado pessoal para quem consegue reidentificá-lo. Como a coleta começa nesta onda, a versão mínima da sala segura não pode esperar a Onda 6.

**Implementação.**

LINK:
- Exemplos vão pelo id: #a=ex3&m=prever&f=alt.
- Código novo vai comprimido com lz-string (compressToEncodedURIComponent) no fragmento da URL, que não é enviado a nenhum servidor.
- Antes do piloto, medir o tamanho máximo aceito no chat do Meet; acima dele, a atividade vai como arquivo.

CONTRATO DA ATIVIDADE: AtividadeLink = {v: 1, id, programas: [{ex: 'ex3'} | {codigo, entradas}], modo: 'assistir'|'prever'|'estudo', formato: 'alternativas'|'livre', sala, semente}.
No modo 'estudo', sortear_condicoes(sujeito, atividade) atribui a cada programa Prever ou Assistir, balanceado e determinístico pela semente.

PYTHON:
- pyvis_motor/apelido.py: gerar(semente), com listas fechadas de animal, cor e número, e validar().
- pyvis_motor/registro.py: esquema de eventos e resumo(eventos).
- pyvis_motor/privacidade.py: higienizar(codigo) usa tokenize para remover comentários e trocar literais de texto e f-strings por '<texto>'. É obrigatória em qualquer código que saia do aparelho.

CONTRATO DO EVENTO: Evento = {v: 1, ts, sala, sujeito (UUID aleatório por sala), atividade, programa, condicao, tipo, code_hash, ponto?, formato?, resposta?: {alternativa?, valor_normalizado?, tipo_escolhido?}, certa?, concepcao?, camada?: 1|2|3, ms?}.
- tipo: 'Session.Start' | 'Run.Program' | 'Step' | 'Prediction' | 'Prediction.Skip' | 'Feedback.Layer' | 'Error'.
- O evento nunca contém código, entradas, texto livre nem apelido.

ARMAZENAMENTO:
- Memória, com cópia em localStorage (sempre dentro de try/catch), por sala.
- Expira em 30 dias, com limpeza ao abrir.
- Fora de uma sala, nada é salvo.

ENTREGA: um arquivo .json (lz-string) baixado. Reserva: o código colado num formulário sem login e sem coleta de e-mail. Nunca pelo chat do Meet.

TYPESCRIPT: CriarAtividade.tsx, Entrada.tsx (aviso e apelido), MeuResumo.tsx e a página /pais. A tela Entregas.tsx é substituída por scripts em analise/ (Onda 3).


### 2.6 Tela da atividade: orçamento de atenção, celular e acessibilidade

**O que o aluno vê.** A atividade decide a tela. No modo Prever aparecem só o editor, as caixinhas, a linha do tempo, um balão e o narrador, e nada pisca enquanto o palpite está aberto. No celular há duas abas, Código e Passos, a linha do tempo fica fixa embaixo, o balão flutua sobre a linha atual e os alvos de toque têm 44 px. Todo estado tem ícone e texto além da cor: ✓ certo, ✗ errado, 'pulado'.

**Por quê.** Muitos estímulos simultâneos dividem a atenção e sobrecarregam a memória de trabalho (Sweller, 1988), justamente no público com menos fluência de leitura. O celular é o principal aparelho de acesso para 98% dos usuários de 9 a 17 anos (TIC Kids Online Brasil 2024). Informação só por cor exclui daltônicos (WCAG 1.4.1), e animações precisam respeitar a preferência do aparelho (WCAG 2.3.3).

**Implementação.**

PALCO: um componente Palco.tsx monta só o que atividade.modo permite. A regra do orçamento (no máximo 1 balão e 1 destaque animado por passo) é testada com Vitest e Testing Library.

LAYOUT: responsivo em Tailwind, com abas abaixo do breakpoint lg. Na semana 1, perguntar aos alunos em que aparelho assistem às aulas. Se ninguém usar celular, o layout móvel se limita a não quebrar.

MOVIMENTO: Motion com reducedMotion='user'; nada pisca mais de 3 vezes por segundo.

ACESSIBILIDADE: alvos de pelo menos 24 px no desktop e 44 px no toque. Antes do piloto, testar com NVDA e com um simulador de daltonismo.

## Decisões para esta rodada de implementação

- **1.1 Executor isolado:** nesta rodada entram a parte em Python (`pyvis_motor/seguranca.py`, que recusa `js`, `pyodide`, `pyodide_js`, `_pyodide`, `micropip`, `pyodide_http`) e o tempo limite de 5 s para `rastrear`. A hospedagem em duas origens (iframe numa origem separada, com CSP) fica para a etapa de publicação do site, porque depende de onde o site será hospedado. Deixar a ponte (`frontend/src/motor/ponte.ts`) pronta para isso: toda comunicação com o motor passa por ela.
- **1.4 Medições em Android real e brotli/Cache-Control:** ficam para a publicação. O limite de 300 passos em aparelhos fracos (`navigator.deviceMemory <= 2`) entra.
- **1.5 Corpus:** entra, com 40 a 60 programas em `tests/corpus/` e `analise/cobertura.py`. O pré-registro no OSF e o julgamento por professores são tarefas do Matheus.
- **2.5:** entram o link de atividade (fragmento da URL com lz-string), apelido gerado, tela de aviso, "Meu resumo", entrega por arquivo, "Sair e apagar deste aparelho" e a página para os pais. A coleta automática por servidor é a Onda 3.
- **Linguagem:** todo texto para o aluno em pt-BR, frases curtas. Proibido usar "aposta", "apostar" ou derivados em qualquer texto mostrado ao aluno (há um teste que procura `apost` no frontend).
- **Python:** a lógica pedagógica fica em `pyvis_motor/` e é testada com pytest. O TypeScript só desenha e aplica a função pura `visivel(...)`.
- **Compatibilidade:** os 8 exemplos atuais continuam funcionando; o exemplo 7 passa a perguntar o nome de um robô.

## Desvios desta rodada (aceitos, ou à espera de decisão)

O que o código faz diferente do texto acima. Os marcados com **decidir** mudam dados da pesquisa e precisam da palavra do Matheus. Os outros já estão no código e nos testes.

- **2.2 Decisão com 2 alternativas (decidir).** Os pontos de if, elif e while têm só Verdadeiro e Falso, nessa ordem, sem sorteio (o texto pede 3 ou 4). O acaso é 50% e não 25% ou 33%: a análise de `Prediction.certa` precisa separar por tipo de ponto. No corpus, 13 dos outros 196 pontos também ficam com 2 alternativas, quando não há distratores diferentes o bastante. Para voltar a 33%, dá para pôr uma 3ª opção ('Dá erro').
- **2.2(d) Voltas perguntadas na entrada do laço.** O texto fala em perguntar na saída. Na entrada o aluno ainda não viu as voltas, e a pergunta mede previsão de verdade. 'Onde olhar' e o passo resolvido levam à última volta, onde o número aparece.
- **2.2 Palpite antes de rodar.** Não aparece em programa com `input()`: o aluno não sabe o que será digitado, e as alternativas repetiriam as perguntas do programa. Com alternativas, só aparece quando a tela tem até 2 linhas, para não virar leitura de blocos quase iguais. Quando aparece, o mesmo print não é perguntado de novo durante os passos.
- **2.2 Elogio (decidir).** Num ponto que testa uma concepção, o elogio é 'Isso!' e a regra ('Isso! O range para antes do último número.'). O texto pede um elogio de processo com os valores da execução ('Você lembrou que o range para antes do 5'). Os pontos de saída e o palpite antes de rodar já elogiam o processo ('Você leu o valor de total na hora do print.').
- **2.2 7 contra 7.0 (decidir).** Na resposta livre, '7' para um valor 7.0 conta como `certa=True`, com um recado sobre o decimal. O texto diz só 'gera mensagem, não diagnóstico'. Se a análise precisar separar os dois casos, `Prediction` ganha um campo novo (por exemplo `valor_certo`).
- **2.2 Total de passos escondido.** Com perguntas abertas, a linha do tempo mostra 'Passo 2', sem 'de 12', e o controle deslizante só vai até onde o aluno pode chegar. O total diria quantas voltas o laço dá.
- **2.3 Feedback.Layer a cada uso.** Abrir de novo a mesma camada também vira evento. Na análise, conte camadas distintas por ponto quando a pergunta for 'quantos alunos abriram'.
- **2.3 Camada 2 sem modelo.** Quando nenhum modelo explica o palpite, a camada 2 mostra a frase longa do narrador no passo da pergunta (com a regra da revelação), em vez de sumir.
- **2.4 'vai valer' no lugar de 'agora vale'.** A frase do narrador é lida com a linha destacada, antes de ela rodar, enquanto as caixinhas mostram o estado de antes. 'total recebe total + numero: vai valer 6.' não contradiz a caixinha que ainda mostra 5. Os erros têm uma frase curta (até 12 palavras) e o resto em 'Mais detalhes'.
- **2.6 Tela grande.** A linha do tempo e o narrador ficam no alto da coluna da execução, ao lado das caixinhas (o narrador continua embaixo dos controles). Assim os dois aparecem sem rolar a 1280x860, e o balão preso ao código não cobre os botões. O palpite antes de rodar abre nessa coluna, ao lado do código.
- **2.6 Celular.** A aba Passos mostra o balão da decisão e as linhas puladas junto da linha atual. Com uma pergunta de valor aberta, as caixinhas vêm antes do narrador.
- **2.5 'Sair e apagar' sempre à vista.** O cabeçalho da atividade fica preso no alto só na tela grande. No celular ele rola com a página: preso, ele tomaria uns 170 px dos 844, além da linha do tempo fixa embaixo.
- **2.6 Teclado.** O Tab sai do editor e não recua o código (senão o teclado fica preso nele). O Enter depois de ':' já recua, e Ctrl+] / Ctrl+[ mudam o recuo. Com alternativas, o foco abre no balão, e não na 1ª opção: as setas, que andam na linha do tempo, não marcam nada sem querer.
- **1.1 Origem separada (bloqueia a publicação).** O código do aluno roda num Web Worker da mesma origem do site. O bloqueio em Python (`seguranca.py`) é só uma camada a mais: quem conhece o Pyodide ainda alcança o módulo `js` (por exemplo procurando o dicionário dos módulos escondidos com `gc.get_objects()`). A proteção da spec (iframe numa origem separada, com CSP `connect-src 'self'`) precisa existir antes de o site ir ao ar.
- **1.2 Python mínimo 3.11.** O `pyproject.toml` pede `>=3.11`, e a CI roda 3.11 a 3.14 (o texto diz `>=3.12`). O motor funciona nas quatro versões e no Pyodide 3.14.
- **1.5 `rastrear_leve`.** No corpus ele sai só 2 a 4 vezes mais barato que o rastro completo (2,4 e 3,6 em duas medições), e não cerca de 50 (`analise/cobertura.py` mostra a conta). Para o orçamento do `preparar_atividade` (3 s na ponte), os modelos param no meio quando o tempo acaba (`sem_tempo`), e a atividade sai com os que deu tempo de rodar.
- **2.5 Esquema do Evento.** Ganhou `Step.passo`, `Error.erro` e `Prediction.testadas` (as concepções que o ponto testava, para o 'Meu resumo').
