// Formato do resultado que o motor Python (pyvis_motor/rastreador.py) devolve.

export type Valor = {
  tipo: string;
  valor?: string;
  itens?: Valor[];
  pares?: [Valor, Valor][];
  cortado?: boolean;
};

export type Variaveis = Record<string, Valor>;

export type Passo = {
  linha: number;
  evento: "linha" | "fim";
  globais: Variaveis;
  funcao: string | null;
  locais: Variaveis;
  saida: string;
};

export type ErroDoAluno = {
  tipo: string;
  linha: number | null;
  mensagem: string;
  original: string;
};

export type Resultado = {
  passos: Passo[];
  saida: string;
  erro: ErroDoAluno | null;
};
