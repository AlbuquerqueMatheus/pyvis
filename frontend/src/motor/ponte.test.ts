// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErroDoMotor, lerMensagem, limiteDePassos, MENSAGEM_TEMPO_ESGOTADO, Ponte, TEMPO_LIMITE_ATIVIDADE_MS, type Canal, type Pedido } from "./ponte";
import { ACOES } from "./protocolo";

const API = Object.values(import.meta.glob("../../../pyvis_motor/api.py", { query: "?raw", import: "default", eager: true }))[0] as string;

/** Um canal de mentira: guarda os pedidos e deixa o teste responder quando quiser. */
function canalFalso() {
  const canais: { pedidos: Pedido[]; encerrado: boolean; responder: (mensagem: unknown) => void }[] = [];
  const criar = (aoReceber: (mensagem: unknown) => void): Canal => {
    const canal = { pedidos: [] as Pedido[], encerrado: false, responder: aoReceber };
    canais.push(canal);
    return {
      enviar: (pedido) => canal.pedidos.push(pedido),
      encerrar: () => {
        canal.encerrado = true;
      },
    };
  };
  return { criar, canais };
}

const resposta = (id: number, resultado: unknown) => JSON.stringify({ id, ok: true, resultado });

afterEach(() => vi.useRealTimers());

describe("Ponte", () => {
  it("espera o Python ficar pronto e entrega cada resposta à promessa certa", async () => {
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    const estados: string[] = [];
    ponte.observar((estado) => estados.push(estado));
    const hash = ponte.pedir("code_hash", { codigo: "x = 1" });
    const texto = ponte.pedir("higienizar", { codigo: "x = 'a'" });
    expect(canais[0].pedidos).toEqual([]); // ainda carregando
    canais[0].responder({ tipo: "pronto" });
    // Um pedido por vez vai ao Python.
    expect(canais[0].pedidos).toHaveLength(1);
    const [primeiro] = canais[0].pedidos;
    expect(primeiro).toMatchObject({ acao: "code_hash", dados: { codigo: "x = 1" } });
    canais[0].responder(resposta(primeiro.id, "8ff436def1451285"));
    await expect(hash).resolves.toBe("8ff436def1451285");
    const segundo = canais[0].pedidos[1];
    canais[0].responder(resposta(segundo.id, "x = <texto>"));
    await expect(texto).resolves.toBe("x = <texto>");
    // Pedidos do diário e da sala não deixam o motor 'ocupado'.
    expect(estados).toEqual(["pronto"]);
    const correcao = ponte.corrigir("p1", { alternativa: "p1a1" });
    expect(ponte.estado).toBe("ocupado");
    canais[0].responder(resposta(canais[0].pedidos[2].id, { certa: true }));
    await expect(correcao).resolves.toEqual({ certa: true });
    expect(estados).toEqual(["pronto", "ocupado", "pronto"]);
  });

  it("uma resposta com id de outro pedido é ignorada", async () => {
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    canais[0].responder({ tipo: "pronto" });
    const pedido = ponte.pedir("code_hash", { codigo: "x" });
    const { id } = canais[0].pedidos[0];
    canais[0].responder(resposta(id + 7, "errado"));
    canais[0].responder("isto não é JSON");
    canais[0].responder(resposta(id, "certo"));
    await expect(pedido).resolves.toBe("certo");
  });

  it("erro do motor vira ErroDoMotor do tipo 'Motor'", async () => {
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    canais[0].responder({ tipo: "pronto" });
    const pedido = ponte.corrigir("p1", { alternativa: "p1a1" });
    canais[0].responder(JSON.stringify({ id: canais[0].pedidos[0].id, ok: false, erro: "ValueError: ponto desconhecido" }));
    await expect(pedido).rejects.toMatchObject({ tipo: "Motor", message: "ValueError: ponto desconhecido" });
  });

  it("rastrear passa de 5 s: o Python é recriado e os outros pedidos esperam o novo", async () => {
    vi.useFakeTimers();
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    canais[0].responder({ tipo: "pronto" });
    const lento = ponte.rastrear("x = 10 ** 10 ** 9", []);
    const depois = ponte.pedir("code_hash", { codigo: "x" });
    vi.advanceTimersByTime(4999);
    expect(canais).toHaveLength(1);
    vi.advanceTimersByTime(1);
    await expect(lento).rejects.toEqual(new ErroDoMotor("TempoEsgotado", MENSAGEM_TEMPO_ESGOTADO));
    expect(canais[0].encerrado).toBe(true);
    expect(canais).toHaveLength(2);
    expect(ponte.estado).toBe("carregando");
    canais[1].responder({ tipo: "pronto" });
    expect(canais[1].pedidos[0]).toMatchObject({ acao: "code_hash" });
    canais[1].responder(resposta(canais[1].pedidos[0].id, "abc"));
    await expect(depois).resolves.toBe("abc");
  });

  it("o relógio só corre depois que o Python carregou, e corrigir e o diário não têm tempo limite", async () => {
    vi.useFakeTimers();
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    const atividade = ponte.prepararAtividade({ modo: "assistir" });
    const rastro = ponte.rastrear("x = 1", ["a"], 42);
    vi.advanceTimersByTime(20000); // carregando: nada vai ao Python nem conta tempo
    canais[0].responder({ tipo: "pronto" });
    vi.advanceTimersByTime(2999);
    expect(canais).toHaveLength(1);
    canais[0].responder(resposta(canais[0].pedidos[0].id, { versao: 1 }));
    await expect(atividade).resolves.toEqual({ versao: 1 });
    const pedido = canais[0].pedidos[1];
    expect(pedido).toMatchObject({ acao: "rastrear", dados: { codigo: "x = 1", entradas: ["a"], semente: 42 } });
    vi.advanceTimersByTime(4000);
    canais[0].responder(resposta(pedido.id, { versao: 2 }));
    await expect(rastro).resolves.toEqual({ versao: 2 });
    const correcao = ponte.corrigir("p1", { alternativa: "p1a1" });
    vi.advanceTimersByTime(20000);
    expect(canais).toHaveLength(1);
    canais[0].responder(resposta(canais[0].pedidos[2].id, { certa: true }));
    await expect(correcao).resolves.toEqual({ certa: true });
  });

  it("preparar_atividade passa de 3 s: o Python é recriado e a página segue sem perguntas", async () => {
    vi.useFakeTimers();
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    canais[0].responder({ tipo: "pronto" });
    const atividade = ponte.prepararAtividade({ modo: "prever" });
    const hash = ponte.pedir("code_hash", { codigo: "x" });
    vi.advanceTimersByTime(TEMPO_LIMITE_ATIVIDADE_MS - 1);
    expect(canais).toHaveLength(1);
    vi.advanceTimersByTime(1);
    await expect(atividade).rejects.toMatchObject({ tipo: "TempoEsgotado" });
    expect(canais[0].encerrado).toBe(true);
    canais[1].responder({ tipo: "pronto" });
    canais[1].responder(resposta(canais[1].pedidos[0].id, "abc"));
    await expect(hash).resolves.toBe("abc");
  });

  it("falha ao carregar rejeita tudo e os próximos pedidos", async () => {
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    const pedido = ponte.pedir("code_hash", { codigo: "x" });
    canais[0].responder({ tipo: "falha", mensagem: "sem wasm" });
    await expect(pedido).rejects.toMatchObject({ tipo: "Falha" });
    expect(ponte.estado).toBe("falhou");
    await expect(ponte.pedir("code_hash", { codigo: "y" })).rejects.toBeInstanceOf(ErroDoMotor);
  });

  it("encerrar fecha o canal e rejeita o que estava pendente", async () => {
    const { criar, canais } = canalFalso();
    const ponte = new Ponte(criar);
    const pedido = ponte.pedir("code_hash", { codigo: "x" });
    ponte.encerrar();
    expect(canais[0].encerrado).toBe(true);
    await expect(pedido).rejects.toMatchObject({ tipo: "Reiniciado" });
  });
});

describe("mensagens e limite", () => {
  it("as ações são as mesmas de pyvis_motor/api.py", () => {
    const bloco = API.slice(API.indexOf("ACOES = {"), API.indexOf("}", API.indexOf("ACOES = {")));
    const doPython = [...bloco.matchAll(/"(\w+)":/g)].map((achado) => achado[1]);
    expect(doPython.length).toBeGreaterThan(10);
    expect([...ACOES]).toEqual(doPython);
  });

  it("lerMensagem aceita só o formato do protocolo", () => {
    expect(lerMensagem({ tipo: "pronto" })).toEqual({ tipo: "pronto" });
    expect(lerMensagem('{"id": 3, "ok": true, "resultado": 1}')).toEqual({ id: 3, ok: true, resultado: 1 });
    expect(lerMensagem({ id: 3, ok: false, erro: "TypeError: x" })).toEqual({ id: 3, ok: false, erro: "TypeError: x" });
    expect(lerMensagem({ id: "3", ok: true, resultado: 1 })).toBeNull();
    expect(lerMensagem({ id: 3, ok: true })).toBeNull();
    expect(lerMensagem(null)).toBeNull();
    expect(lerMensagem("{")).toBeNull();
  });

  it("aparelho com até 2 GB de memória para em 300 passos", () => {
    expect(limiteDePassos(1)).toBe(300);
    expect(limiteDePassos(2)).toBe(300);
    expect(limiteDePassos(4)).toBeUndefined();
    expect(limiteDePassos(undefined)).toBeUndefined();
  });

  it("rastrear manda o limite menor quando o aparelho é fraco", () => {
    vi.stubGlobal("navigator", { deviceMemory: 2 });
    try {
      const { criar, canais } = canalFalso();
      const ponte = new Ponte(criar);
      canais[0].responder({ tipo: "pronto" });
      ponte.rastrear("x = 1", []).catch(() => {}); // encerrar rejeita o pedido pendente
      expect(canais[0].pedidos[0].dados).toEqual({ codigo: "x = 1", entradas: [], limite: 300 });
      ponte.encerrar();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
