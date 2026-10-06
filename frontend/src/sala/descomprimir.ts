// O decompressFromEncodedURIComponent do lz-string (1.5.0, MIT, Pieroxy), com um teto.
// O original monta o texto inteiro antes de devolver: um link de 200 mil letras pode virar
// centenas de milhões (uma 'bomba'), e o celular trava antes de qualquer conferência.
// Aqui a conta para assim que o texto passa do teto. Mesmo formato, mesmo resultado.

const ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$";
const VALOR = new Map([...ALFABETO].map((letra, k) => [letra, k]));

export type Descomprimido = { tipo: "texto"; texto: string } | { tipo: "cortado" } | { tipo: "grande" };

export function descomprimirComTeto(entrada: string, teto: number): Descomprimido {
  if (entrada === "") return { tipo: "cortado" };
  const texto = entrada.replace(/ /g, "+");
  // Cada letra do link guarda 6 bits, lidos do mais alto para o mais baixo.
  const proximo = (k: number) => VALOR.get(texto.charAt(k)) ?? 0;
  let valor = proximo(0);
  let posicao = 32;
  let indice = 1;

  function ler(bits: number): number {
    let lido = 0;
    for (let potencia = 1; potencia !== 2 ** bits; potencia *= 2) {
      const bit = valor & posicao;
      posicao >>= 1;
      if (posicao === 0) {
        posicao = 32;
        valor = proximo(indice++);
      }
      if (bit > 0) lido += potencia;
    }
    return lido;
  }

  const dicionario: string[] = ["", "", ""];
  let aumentarEm = 4;
  let tamanhoDoDicionario = 4;
  let largura = 3;

  const primeiro = ler(2);
  if (primeiro === 2) return { tipo: "texto", texto: "" };
  if (primeiro !== 0 && primeiro !== 1) return { tipo: "cortado" };
  let w = String.fromCharCode(ler(primeiro === 0 ? 8 : 16));
  dicionario[3] = w;
  const partes = [w];
  let tamanho = w.length;

  for (;;) {
    if (indice > texto.length) return { tipo: "cortado" };
    let codigo = ler(largura);
    if (codigo === 2) return { tipo: "texto", texto: partes.join("") };
    if (codigo === 0 || codigo === 1) {
      dicionario[tamanhoDoDicionario++] = String.fromCharCode(ler(codigo === 0 ? 8 : 16));
      codigo = tamanhoDoDicionario - 1;
      aumentarEm--;
    }
    if (aumentarEm === 0) {
      aumentarEm = 2 ** largura;
      largura++;
    }
    let entrada: string;
    if (dicionario[codigo]) entrada = dicionario[codigo];
    else if (codigo === tamanhoDoDicionario) entrada = w + w.charAt(0);
    else return { tipo: "cortado" };
    tamanho += entrada.length;
    if (tamanho > teto) return { tipo: "grande" };
    partes.push(entrada);
    dicionario[tamanhoDoDicionario++] = w + entrada.charAt(0);
    aumentarEm--;
    w = entrada;
    if (aumentarEm === 0) {
      aumentarEm = 2 ** largura;
      largura++;
    }
  }
}
