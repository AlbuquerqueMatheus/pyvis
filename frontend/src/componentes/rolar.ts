/**
 * Rola só o necessário para o elemento ficar à vista, acima da margem de baixo do scroll (o
 * scroll-mb: no celular, a barra fixa da linha do tempo cobre o fim da tela). O
 * scrollIntoView({ block: "nearest" }) do Chromium ignora essa margem quando o elemento já está
 * dentro da janela, mesmo que embaixo da barra; então, nesse caso, o fim dele é alinhado ao fim.
 */
export function rolarAcimaDaBarra(elemento: HTMLElement | null | undefined, comportamento: ScrollBehavior = "auto") {
  if (!elemento?.scrollIntoView) return;
  const margem = Number.parseFloat(getComputedStyle(elemento).scrollMarginBottom) || 0;
  const coberto = elemento.getBoundingClientRect().bottom > window.innerHeight - margem;
  elemento.scrollIntoView({ block: coberto ? "end" : "nearest", behavior: comportamento });
}
