// Programas prontos para os alunos explorarem. `entradas` preenche os input().
export type Exemplo = { titulo: string; codigo: string; entradas?: string };

export const EXEMPLOS: Exemplo[] = [
  {
    titulo: "1. Variáveis",
    codigo: `nome = "Ana"
idade = 12
idade = idade + 1
print(nome, "vai fazer", idade, "anos")
`,
  },
  {
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
    titulo: "3. Repetição com for",
    codigo: `total = 0
for numero in range(1, 5):
    total = total + numero
print("A soma é", total)
`,
  },
  {
    titulo: "4. Repetição com while",
    codigo: `vidas = 3
while vidas > 0:
    print("Você tem", vidas, "vidas")
    vidas = vidas - 1
print("Fim de jogo!")
`,
  },
  {
    titulo: "5. Listas",
    codigo: `frutas = ["maçã", "banana"]
frutas.append("uva")
frutas[0] = "manga"
for fruta in frutas:
    print("Eu gosto de", fruta)
`,
  },
  {
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
    titulo: "7. Perguntando com input",
    codigo: `nome = input("Qual é o seu nome? ")
idade = int(input("Quantos anos você tem? "))
print("Olá,", nome)
print("Daqui a 5 anos você terá", idade + 5)
`,
    entradas: "Bia\n11",
  },
  {
    titulo: "8. Encontre o erro",
    codigo: `pontos = 10
bonus = 5
total = pontos + bonu
print(total)
`,
  },
];
