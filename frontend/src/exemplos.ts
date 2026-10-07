// Programas prontos para os alunos explorarem. `entradas` preenche os input().
// Nenhum exemplo pede dados do aluno: o 7 pergunta o nome de um robô.
// O `id` vai nos links de atividade (#a=ex3): não muda, mesmo se a ordem mudar.
export type Exemplo = { id: string; titulo: string; codigo: string; entradas?: string };

export const EXEMPLOS: Exemplo[] = [
  {
    id: "ex1",
    titulo: "1. Variáveis",
    codigo: `nome = "Ana"
idade = 12
idade = idade + 1
print(nome, "vai fazer", idade, "anos")
`,
  },
  {
    id: "ex2",
    titulo: "2. Decisão com if",
    codigo: `nota = 7
if nota >= 6:
    resultado = "aprovado"
else:
    resultado = "recuperação"
print("Situação:", resultado)
`,
  },
  {
    id: "ex3",
    titulo: "3. Repetição com for",
    codigo: `total = 0
for numero in range(1, 5):
    total = total + numero
print("A soma é", total)
`,
  },
  {
    id: "ex4",
    titulo: "4. Repetição com while",
    codigo: `energia = 3
while energia > 0:
    print("Energia:", energia)
    energia = energia - 1
print("O robô descansou!")
`,
  },
  {
    id: "ex5",
    titulo: "5. Listas",
    codigo: `frutas = ["maçã", "banana"]
frutas.append("uva")
frutas[0] = "manga"
for fruta in frutas:
    print("Eu gosto de", fruta)
`,
  },
  {
    id: "ex6",
    titulo: "6. Maior número da lista",
    codigo: `numeros = [4, 9, 2, 7]
maior = numeros[0]
for n in numeros:
    if n > maior:
        maior = n
print("O maior é", maior)
`,
  },
  {
    id: "ex7",
    titulo: "7. Perguntando com input",
    codigo: `nome = input("Qual é o nome do seu robô? ")
idade = int(input("Quantos anos o robô tem? "))
print("Olá,", nome)
print("Daqui a 5 anos ele terá", idade + 5)
`,
    entradas: "Bip\n3",
  },
  {
    id: "ex8",
    titulo: "8. Encontre o erro",
    codigo: `pontos = 10
bonus = 5
total = pontos + bonu
print(total)
`,
  },
];

export function exemploPorId(id: string): Exemplo | undefined {
  return EXEMPLOS.find((exemplo) => exemplo.id === id);
}
