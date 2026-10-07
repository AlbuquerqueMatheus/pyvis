// As ações que a página pode pedir ao motor (as mesmas de ACOES em pyvis_motor/api.py).
// Fica num arquivo à parte porque o worker também o importa, e o worker não pode
// importar a ponte (ela é quem cria o worker).
import type { Acoes } from "./ponte";

export const ACOES = [
  "rastrear",
  "preparar_atividade",
  "corrigir",
  "gerar_apelido",
  "sugerir_apelidos",
  "validar_apelido",
  "code_hash",
  "higienizar",
  "validar_evento",
  "montar_evento",
  "resumo",
  "sortear_condicoes",
  "montar_entrega",
] as const satisfies readonly (keyof Acoes)[];
