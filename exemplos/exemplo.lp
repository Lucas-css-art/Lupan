mostre("Olá do Lupan!")
nome = pergunte("Qual é seu nome? ")
se nome == "":
    mostre("Você não digitou um nome.")
senão:
    mostre("Prazer, " + nome)

lista = [1, 2, 3, 4, 5]
mostre("Soma da lista:", sum(lista))

contador = 0
enquanto contador < 3:
    mostre("Contador =", contador)
    contador = contador + 1

função saudacao(nome):
    retorne "Bem-vindo, " + nome

mostre(saudacao("Aluno do Lupan"))
