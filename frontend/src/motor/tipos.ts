// Formatos que o motor Python devolve (contrato v2 de pyvis_motor/rastreador.py,
// com as anotações de anotar.py e narrador.py e a atividade de previsao.py).

/** Um valor do programa. `h` resume o conteúdo: dois valores iguais têm o mesmo `h`. */
export type Valor = {
  tipo: string;
  h: string;
  valor?: string;
  itens?: Valor[];
  pares?: [Valor, Valor][];
  cortado?: boolean;
};

export type Variaveis = Record<string, Valor>;

// --- Estrutura do programa (estrutura.py) ---

export type TipoDeComando =
  | "atrib"
  | "aug"
  | "if"
  | "elif"
  | "while"
  | "for"
  | "print"
  | "expr"
  | "def"
  | "return"
  | "break"
  | "continue"
  | "outro";

/** Faixa de linhas [primeira, última], contando a partir de 1. */
export type Faixa = [number, number];

export type Leitura = {
  literal: string;
  traduzida: string;
  /** Pontos que precisam estar respondidos para a leitura traduzida aparecer. */
  traduzida_depende_de: string[];
};

export type Comando = {
  id: number;
  tipo: TipoDeComando;
  linhas: Faixa;
  cabecalho: Faixa | null;
  corpo: Faixa | null;
  orelse: Faixa | null;
  corpo_mesma_linha: boolean;
  pai: number | null;
  acumulador: { nome: string; contador: boolean } | null;
  leitura?: Leitura;
};

// --- Anotações de cada passo (anotar.py) ---

export type Mudanca = { nome: string; escopo: "local" | "global"; antes: Valor; depois: Valor };

export type Efeito = {
  criadas: string[];
  mudadas: Mudanca[];
  apagadas: string[];
  saida_nova: string;
  /** Comparado com o passo que recebe o retorno: só globais e saída valem. */
  parcial: boolean;
};

export type Decisao = {
  texto: string | null;
  valor: boolean | null;
  ramo: "corpo" | "orelse" | "sai" | "desconhecido";
  /** Trechos de `texto` que o curto-circuito pulou, em posições do texto. */
  nao_calculado: [number, number][];
  /** Os mesmos trechos no código: [linha, coluna, linha_fim, coluna_fim], colunas em bytes UTF-8. */
  nao_calculado_codigo: [number, number, number, number][];
  ramo_visivel_desde: number | null;
};

export type Volta = {
  laco: number;
  n: number;
  total: number | null;
  total_visivel_desde: number | null;
  saindo: boolean;
};

export type Retorno = {
  funcao: string;
  valor: Valor;
  quadro: number;
  /** Instantâneo do fim do quadro (o efeito do último comando da função não leva o que veio depois). */
  saida_ate?: number;
  mudancas_globais?: Variaveis;
  globais_apagadas?: string[];
};

/** Pedaço de uma frase do narrador: aparece só quando todos os `campos` podem aparecer. */
export type Parte = { texto: string; campos: string[]; oculto?: string };

export type Narracao = {
  curta: string;
  longa: string;
  partes_curta: Parte[];
  partes_longa: Parte[];
};

/** Campo do passo (com ponto: 'decisao.valor') -> ids dos pontos de previsão de que ele depende. */
export type DependeDe = Record<string, string[]>;

export type Passo = {
  i: number;
  linha: number;
  comando: number | null;
  evento: "linha" | "fim";
  quadro: number;
  profundidade: number;
  funcao: string | null;
  globais: Variaveis;
  locais: Variaveis;
  saida: string;
  proximo_no_quadro: number | null;
  /** O último quadro que terminou antes deste passo (o mesmo que retornos[retornos.length - 1]). */
  retorno?: Retorno;
  /** Todos os quadros que terminaram antes deste passo, do mais interno ao mais externo (recursão). */
  retornos?: Retorno[];
  efeito?: Efeito | null;
  decisao?: Decisao | null;
  volta?: Volta | null;
  desfecho_visivel_desde?: number | null;
  narracao?: Narracao;
  depende_de?: DependeDe;
};

export type ErroDoAluno = {
  /** Nome da exceção do Python, 'LimiteDePassos' ou 'TempoEsgotado' (este vem da página). */
  tipo: string;
  linha: number | null;
  /** Curta (até 12 palavras); código entre crases. */
  mensagem: string;
  /** O resto da explicação, atrás de 'Mais detalhes' (pode ser vazio; a página não manda). */
  detalhe?: string;
  original: string;
};

export type Resultado = {
  versao: 2;
  semente: number;
  deterministico: boolean;
  passos: Passo[];
  saida: string;
  erro: ErroDoAluno | null;
  estrutura: { comandos: Comando[] };
};

// --- Atividade de previsão (previsao.py) ---

export type TipoDePonto = "valor" | "decisao" | "voltas" | "saida";
export type TipoDeValor = "numero" | "texto" | "bool" | "lista" | "outro";
export type Modo = "assistir" | "prever";
export type Formato = "alternativas" | "livre";

export type Feedback = {
  onde: { passo: number | null; destacar: string | null };
  regra: string;
  resolvido: string;
  resumo?: string;
};

export type Alternativa = {
  id: string;
  texto: string;
  tipo_valor: TipoDeValor;
  certa: boolean;
  /** Id técnico da concepção: só para o registro, nunca para o aluno. */
  concepcao: string | null;
  origem: "correta" | "modelo" | "regra";
  feedback: Feedback | null;
};

export type Ponto = {
  id: string;
  passo: number;
  tipo: TipoDePonto;
  alvo: { comando: number | null; nome?: string };
  ocorrencia: number;
  pergunta: string;
  resposta: { texto: string; tipo_valor: TipoDeValor };
  formato: Formato;
  sensivel_a_tipo: boolean;
  concepcoes_observaveis: string[];
  testadas: string[];
  explicacao: string;
  elogio: string;
  alternativas?: Alternativa[];
};

export type ConfigDaAtividade = {
  modo?: Modo;
  formato?: Formato;
  max_pontos?: number;
  semente?: number;
  palpite_inicial?: boolean;
  orcamento_ms?: number;
};

export type Atividade = {
  versao: 1;
  modo: Modo;
  formato: Formato;
  semente: number;
  /** Ordenados por passo; não inclui o palpite inicial. */
  pontos: Ponto[];
  palpite_inicial: Ponto | null;
  /** Chaves são índices de passo em texto (JSON). */
  depende_de_por_passo: Record<string, DependeDe>;
  /** Chaves são ids de comando em texto. */
  traduzida_depende_de: Record<string, string[]>;
  cobertura: { pontos_com_modelo: number; total: number; candidatos: number; candidatos_com_modelo: number };
  /** false quando o orçamento de tempo dos modelos acabou antes. */
  completa: boolean;
  tempo_ms: number;
};

export type RespostaDoAluno = { alternativa: string } | { texto: string; tipo_escolhido?: "numero" | "texto" };

export type ValorRegistravel = null | boolean | number | string | ValorRegistravel[];

export type Correcao = {
  certa: boolean;
  legivel: boolean;
  valor_certo: boolean;
  tipo_certo: boolean;
  concepcao: string | null;
  feedback: Feedback | null;
  mensagem: string;
  explicacao: string;
  resposta: { texto: string; tipo_valor: TipoDeValor };
  palpite: string;
  valor_normalizado: ValorRegistravel;
  testadas: string[];
};

// --- Sala e diário (registro.py, apelido.py) ---

export type TipoDeEvento =
  | "Session.Start"
  | "Run.Program"
  | "Step"
  | "Prediction"
  | "Prediction.Skip"
  | "Feedback.Layer"
  | "Error";

export type ContextoDoEvento = {
  sala: string;
  sujeito: string;
  atividade: string;
  programa: number | null;
  condicao: Modo | null;
  code_hash: string | null;
};

export type Evento = ContextoDoEvento & {
  v: 1;
  ts: number;
  tipo: TipoDeEvento;
  ms?: number;
  passo?: number;
  ponto?: string;
  formato?: Formato;
  resposta?: { alternativa?: string | number; valor_normalizado?: ValorRegistravel; tipo_escolhido?: "numero" | "texto" };
  certa?: boolean;
  concepcao?: string | null;
  testadas?: string[];
  camada?: 1 | 2 | 3;
  erro?: string;
};

/** Um exemplo pelo id ('ex3') ou o código do professor; `entradas` troca as do exemplo. */
export type ProgramaDoLink = { ex: string; entradas?: string[] } | { codigo: string; entradas?: string[] };

export type AtividadeLink = {
  v: 1;
  /** Nome curto da atividade, que vai em cada evento ('aula3'). */
  id: string;
  programas: ProgramaDoLink[];
  modo: "assistir" | "prever" | "estudo";
  formato: Formato;
  /** Código da sala; vazio quando o link não traz, e o aluno digita o que o professor falar. */
  sala: string;
  semente: number;
};

export type Entrega = { v: 1; apelido: string; eventos: Evento[] };

export type Resumo = {
  entendidas: string[];
  revisar: string[];
  numeros: { programas: number; palpites: number; pulados: number; explicacoes: number };
};
