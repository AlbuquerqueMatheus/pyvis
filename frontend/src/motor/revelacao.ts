// Regra de revelação: quando um campo de um passo pode aparecer para o aluno.
//
// Cópia linha a linha de pyvis_motor/revelacao.py. O motor decide o que é
// revelado; a página só pergunta. Qualquer mudança aqui tem de ser feita lá
// também: revelacao.test.ts confere os dois com casos gerados pelo Python
// (scripts/casos_revelacao.py).

import type { Atividade, Comando, DependeDe, Parte, Resultado } from "./tipos";

/** O mínimo que a regra lê de um passo. */
export type PassoRevelavel = {
  i: number;
  comando?: number | null;
  depende_de?: DependeDe | null;
  desfecho_visivel_desde?: number | null;
  decisao?: { ramo_visivel_desde?: number | null } | null;
  volta?: { laco: number; total_visivel_desde?: number | null } | null;
  narracao?: { partes_curta: Parte[]; partes_longa: Parte[] } | null;
};

export const DESFECHO: readonly string[] = ["efeito", "decisao.valor", "decisao.ramo"];
// No cabeçalho de um laço, continuar ou sair também diz algo sobre o total de voltas.
export const DESFECHO_DO_CABECALHO: readonly string[] = [...DESFECHO, "volta.n", "volta.saindo", "volta.total"];

/** Um dos campos é o outro ou está dentro dele ('decisao' e 'decisao.valor'). */
export function relacionados(a: string, b: string): boolean {
  return a === b || a.startsWith(b + ".") || b.startsWith(a + ".");
}

/** Os campos que contam o que o comando do passo fez. */
export function desfecho(passo: PassoRevelavel): readonly string[] {
  const volta = passo.volta;
  if (volta != null && passo.comando === volta.laco) return DESFECHO_DO_CABECALHO;
  return DESFECHO;
}

/**
 * O campo do passo já pode aparecer?
 *
 * `respondidos` são os pontos já respondidos (ou pulados); `passoAtual` é o
 * passo mais adiante que o aluno já alcançou.
 */
export function visivel(passo: PassoRevelavel, campo: string, respondidos: ReadonlySet<string>, passoAtual: number): boolean {
  if (passoAtual < passo.i) return false;
  const proprios = desfecho(passo);
  const noDesfecho = proprios.some((d) => relacionados(campo, d));
  for (const [chave, pontos] of Object.entries(passo.depende_de ?? {})) {
    if (pontos.every((ponto) => respondidos.has(ponto))) continue;
    if (relacionados(chave, campo)) return false;
    if (noDesfecho && proprios.some((d) => relacionados(chave, d))) return false;
  }
  if (noDesfecho) {
    // Sem a chave vale o próprio passo; com a chave em null, nunca.
    const desde = passo.desfecho_visivel_desde === undefined ? passo.i : passo.desfecho_visivel_desde;
    if (desde == null || passoAtual < desde) return false;
  }
  const decisao = passo.decisao;
  if (decisao != null && relacionados(campo, "decisao.ramo")) {
    const desde = decisao.ramo_visivel_desde;
    if (desde == null || passoAtual < desde) return false;
  }
  const volta = passo.volta;
  if (volta != null && relacionados(campo, "volta.total")) {
    const desde = volta.total_visivel_desde;
    if (desde == null || passoAtual < desde) return false;
  }
  return true;
}

/** Junta as partes de uma narração: cada uma aparece se todos os seus campos são visíveis. */
export function montar(partes: readonly Parte[], passo: PassoRevelavel, respondidos: ReadonlySet<string>, passoAtual: number): string {
  let texto = "";
  for (const parte of partes) {
    if (parte.campos.every((campo) => visivel(passo, campo, respondidos, passoAtual))) {
      texto += parte.texto;
    } else {
      texto += parte.oculto ?? "";
    }
  }
  return texto;
}

/** A frase do narrador com só o que já pode aparecer. A página mostra com .trim(). */
export function narracaoVisivel(
  passo: PassoRevelavel,
  respondidos: ReadonlySet<string>,
  passoAtual: number,
  versao: "curta" | "longa" = "curta",
): string {
  const narracao = passo.narracao;
  if (!narracao) return "";
  return montar(versao === "curta" ? narracao.partes_curta : narracao.partes_longa, passo, respondidos, passoAtual);
}

/** A leitura de um comando fora do passo a passo (no editor, por exemplo). */
export function leituraVisivel(comando: Pick<Comando, "leitura">, respondidos: ReadonlySet<string>): string {
  const leitura = comando.leitura!;
  if (leitura.traduzida_depende_de.every((ponto) => respondidos.has(ponto))) return leitura.traduzida;
  return leitura.literal;
}

/**
 * Grava passo.depende_de a partir da atividade ({i: {campo: [ponto_id]}}) e
 * junta a ele o `traduzida_depende_de` da leitura do comando de cada passo.
 * Devolve um Resultado novo: a página nunca muda o que já mostrou.
 */
export function aplicarDependencias(resultado: Resultado, dependeDePorPasso: Record<string, DependeDe>): Resultado {
  const comandos = resultado.estrutura.comandos;
  const passos = resultado.passos.map((passo) => {
    const dependencias = dependeDePorPasso[String(passo.i)] ?? {};
    const juntas: DependeDe = {};
    for (const [campo, pontos] of Object.entries(dependencias)) juntas[campo] = [...pontos];
    if (passo.comando !== null) {
      const leitura = comandos[passo.comando]?.leitura;
      if (leitura && leitura.traduzida_depende_de.length > 0) {
        const lista = (juntas["leitura.traduzida"] ??= []);
        for (const ponto of leitura.traduzida_depende_de) if (!lista.includes(ponto)) lista.push(ponto);
      }
    }
    const { depende_de: _antigo, ...resto } = passo;
    return Object.keys(juntas).length > 0 ? { ...resto, depende_de: juntas } : resto;
  });
  return { ...resultado, passos };
}

/**
 * Aplica a Atividade à cópia do Resultado que a página tem: as leituras
 * traduzidas e as dependências de cada passo. No modo assistir tudo fica vazio.
 */
export function aplicarAtividade(resultado: Resultado, atividade: Pick<Atividade, "depende_de_por_passo" | "traduzida_depende_de">): Resultado {
  const comandos = resultado.estrutura.comandos.map((comando) =>
    comando.leitura
      ? { ...comando, leitura: { ...comando.leitura, traduzida_depende_de: [...(atividade.traduzida_depende_de[String(comando.id)] ?? [])] } }
      : comando,
  );
  return aplicarDependencias({ ...resultado, estrutura: { ...resultado.estrutura, comandos } }, atividade.depende_de_por_passo);
}
