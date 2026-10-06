import { afterEach, describe, expect, it, vi } from "vitest";
import { rolarAcimaDaBarra } from "./rolar";

/** Um elemento com a base em `base` px e a margem de baixo do scroll em `margem` px. */
function elemento(base: number, margem: string) {
  const el = document.createElement("p");
  el.getBoundingClientRect = () => ({ top: base - 40, bottom: base, left: 0, right: 100, width: 100, height: 40, x: 0, y: base - 40, toJSON: () => ({}) });
  el.scrollIntoView = vi.fn();
  vi.spyOn(window, "getComputedStyle").mockReturnValue({ scrollMarginBottom: margem } as CSSStyleDeclaration);
  return el;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("rolarAcimaDaBarra", () => {
  it("dentro da janela mas embaixo da barra (a margem): alinha o fim, que respeita a margem", () => {
    // O 'nearest' do Chromium não rolaria: o elemento está dentro da janela.
    const el = elemento(window.innerHeight - 50, "192px");
    rolarAcimaDaBarra(el, "smooth");
    expect(el.scrollIntoView).toHaveBeenCalledWith({ block: "end", behavior: "smooth" });
  });

  it("já acima da barra: só o necessário (nearest)", () => {
    const el = elemento(window.innerHeight - 300, "192px");
    rolarAcimaDaBarra(el);
    expect(el.scrollIntoView).toHaveBeenCalledWith({ block: "nearest", behavior: "auto" });
  });

  it("sem margem (tela grande): rola só quando o elemento passa do fim da janela", () => {
    const dentro = elemento(window.innerHeight - 10, "0px");
    rolarAcimaDaBarra(dentro);
    expect(dentro.scrollIntoView).toHaveBeenCalledWith({ block: "nearest", behavior: "auto" });
    const fora = elemento(window.innerHeight + 10, "0px");
    rolarAcimaDaBarra(fora);
    expect(fora.scrollIntoView).toHaveBeenCalledWith({ block: "end", behavior: "auto" });
  });

  it("sem elemento ou sem scrollIntoView (jsdom), não faz nada", () => {
    expect(() => rolarAcimaDaBarra(null)).not.toThrow();
    expect(() => rolarAcimaDaBarra(document.createElement("p"))).not.toThrow();
  });
});
