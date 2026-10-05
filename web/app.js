// Tela da prova de conceito: manda o código para o worker, recebe os passos
// gravados e deixa o aluno navegar por eles.
const TEMPO_MAXIMO_MS = 10000;

const el = (id) => document.getElementById(id);
const botoes = ["executar", "voltar", "avancar", "reiniciar"].map(el);

let worker;
let resultado = null;
let passoAtual = 0;
let codigoExecutado = "";

function iniciarWorker() {
  worker = new Worker(new URL("worker.js", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    if (data.tipo === "pronto") {
      el("status").textContent = "Python pronto!";
      el("executar").disabled = false;
    } else if (data.tipo === "falha") {
      el("status").textContent = "Não foi possível carregar o Python. Confira a internet e recarregue a página.";
    } else if (data.tipo === "resultado") {
      clearTimeout(worker.relogio);
      mostrarResultado(data.resultado);
    }
  };
}

function executar() {
  codigoExecutado = el("codigo").value;
  const entradas = el("entradas").value.split("\n").filter((linha) => linha !== "");
  botoes.forEach((b) => (b.disabled = true));
  el("status").textContent = "Executando...";
  worker.relogio = setTimeout(() => {
    // Programa pesado demais: descarta o Python e prepara outro do zero.
    worker.terminate();
    el("status").textContent = "O programa demorou demais e foi parado. Preparando o Python de novo...";
    iniciarWorker();
  }, TEMPO_MAXIMO_MS);
  worker.postMessage({ codigo: codigoExecutado, entradas });
}

function mostrarResultado(novo) {
  resultado = novo;
  passoAtual = 0;
  el("status").textContent = "Python pronto!";
  el("executar").disabled = false;
  desenhar();
}

function ir(delta) {
  passoAtual = Math.max(0, Math.min(resultado.passos.length - 1, passoAtual + delta));
  desenhar();
}

function textoDoValor(v) {
  if (v.itens) return `[${v.itens.map(textoDoValor).join(", ")}]`;
  if (v.pares) return `{${v.pares.map(([c, x]) => `${textoDoValor(c)}: ${textoDoValor(x)}`).join(", ")}}`;
  return v.valor;
}

function desenharValor(valor, anterior) {
  const mudou = anterior !== undefined && JSON.stringify(valor) !== JSON.stringify(anterior);
  if (valor.tipo === "list" && valor.itens) {
    const lista = document.createElement("div");
    lista.className = "lista";
    valor.itens.forEach((item, i) => {
      const celula = document.createElement("div");
      celula.className = "item";
      const caixa = document.createElement("div");
      const itemAnterior = anterior?.itens?.[i];
      caixa.className = "caixa" + (anterior && JSON.stringify(item) !== JSON.stringify(itemAnterior) ? " mudou" : "");
      caixa.textContent = textoDoValor(item);
      const indice = document.createElement("span");
      indice.className = "indice";
      indice.textContent = i;
      celula.append(caixa, indice);
      lista.append(celula);
    });
    return lista;
  }
  const caixa = document.createElement("div");
  caixa.className = "caixa" + (mudou ? " mudou" : "");
  caixa.textContent = textoDoValor(valor);
  return caixa;
}

function desenharVariaveis(destino, variaveis, anteriores) {
  for (const [nome, valor] of Object.entries(variaveis)) {
    if (valor.tipo === "function") continue;
    const bloco = document.createElement("div");
    bloco.className = "variavel";
    const rotulo = document.createElement("span");
    rotulo.className = "nome";
    rotulo.textContent = nome;
    bloco.append(rotulo, desenharValor(valor, anteriores?.[nome]));
    destino.append(bloco);
  }
}

function desenhar() {
  const { passos, erro } = resultado;
  const ultimo = passoAtual === passos.length - 1;
  const passo = passos[passoAtual];
  const anterior = passos[passoAtual - 1];

  el("linhas").replaceChildren(
    ...codigoExecutado.replace(/\n+$/, "").split("\n").map((texto, i) => {
      const li = document.createElement("li");
      li.textContent = texto || " ";
      if (passo && passo.linha === i + 1) li.className = "atual";
      if (erro && ultimo && erro.linha === i + 1) li.className = "com-erro";
      return li;
    }),
  );

  const variaveis = el("variaveis");
  variaveis.replaceChildren();
  if (passo) {
    desenharVariaveis(variaveis, passo.globais, anterior?.globais);
    if (passo.funcao) {
      const titulo = document.createElement("div");
      titulo.className = "funcao";
      titulo.textContent = `Dentro da função ${passo.funcao}:`;
      variaveis.append(titulo);
      desenharVariaveis(variaveis, passo.locais, anterior?.funcao === passo.funcao ? anterior.locais : undefined);
    }
  }

  el("saida").textContent = ultimo || !passo ? resultado.saida : passo.saida;

  const caixaErro = el("erro");
  caixaErro.hidden = !(erro && (ultimo || !passo));
  if (erro) {
    caixaErro.textContent = (erro.linha ? `Linha ${erro.linha}: ` : "") + erro.mensagem;
    if (erro.original) {
      const original = document.createElement("small");
      original.textContent = erro.original;
      caixaErro.append(original);
    }
  }

  el("contador").textContent = passos.length
    ? `Passo ${passoAtual + 1} de ${passos.length}` + (passo.evento === "fim" ? " (fim do programa)" : "")
    : "";
  el("voltar").disabled = passoAtual === 0;
  el("avancar").disabled = ultimo || !passo;
  el("reiniciar").disabled = passoAtual === 0;
}

el("executar").onclick = executar;
el("voltar").onclick = () => ir(-1);
el("avancar").onclick = () => ir(1);
el("reiniciar").onclick = () => ir(-passoAtual);
iniciarWorker();
