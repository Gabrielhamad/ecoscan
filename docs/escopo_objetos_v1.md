# Escopo de reconhecimento: objects-v1

Esta e a lista fechada de alvos para coleta de exemplos, anotacao e validacao
da primeira versao. Definir um alvo nao significa que o modelo ja o reconhece
com desempenho aprovado. O classificador atual prediz seis materiais, nao os
12 tipos de objeto individualmente. A validacao deve ser estratificada por objeto.

| Objeto | Material | Variacoes previstas |
| --- | --- | --- |
| Lata de bebida | Metal | Refrigerante e energetico; inteira e amassada |
| Lata de conserva vazia | Metal | Diferentes tamanhos, rotulos e deformacoes |
| Garrafa PET de bebida | Plastico | Transparente e colorida; com/sem rotulo; amassada |
| Frasco ou pote plastico rigido vazio | Plastico | Higiene e alimentos; formatos e tampas diferentes |
| Caixa de papelao | Papel/papelao | Montada, aberta, desmontada, dobrada e rasgada |
| Folha de papel ou jornal | Papel/papelao | Lisa, impressa, dobrada, amassada e rasgada |
| Garrafa de vidro | Vidro | Inteira, transparente e colorida; com/sem rotulo |
| Pote de vidro | Vidro | Inteiro; diferentes formatos e tampas |
| Pilha AA ou AAA | Pilha | Cilindrica, integra; diferentes marcas e angulos |
| Celular | Eletronico | Frente, verso, tela apagada e carcacas diferentes |
| Mouse de computador | Eletronico | Com fio e sem fio; diferentes cores e formatos |
| Carregador de celular | Eletronico | Adaptador de tomada; USB-A e USB-C |

## Limites da primeira versao

- Oleo de cozinha e medicamentos: orientacao escolhida manualmente. Uma foto
  da embalagem nao confirma seu conteudo. Nao sao novas classes do modelo.
- Cacos soltos, fragmentos sem forma identificavel e objetos parcialmente
  destruidos: revisao/manual, sem promessa de reconhecimento nesta versao.
- Baterias de carro, packs de litio, pilhas botao, pilhas danificadas e outros
  formatos: fora do reconhecimento automatico inicial.
- Sacolas, filmes plasticos, isopor, embalagens multicamadas, copos, ceramica,
  espelhos, lampadas, aerossois, organicos e tecidos: fora da lista inicial.
- Teclados, monitores, placas, cabos isolados e outros eletronicos: futuras
  expansoes, com dados e validacao proprios. Carregador nao significa qualquer cabo.
- Fotos com varios objetos nao comprovam deteccao individual. O primeiro aceite
  e um objeto principal por captura. Localizacao e rastreamento exigem outra avaliacao.

Cor, marca, tamanho na foto e angulo sao variacoes de um mesmo objeto, nao
classes novas. Sujidade deve ser anotada, mas a imagem nao certifica ausencia
de contaminacao nem composicao quimica. Identificar material nao garante que
todo ponto de coleta aceite aquele item; a orientacao deve consultar suas regras.

## Dados e compatibilidade

Novos reportes oferecem somente os 12 alvos, fora do escopo e nao identificado.
Os IDs antigos `battery` e `small_electronic` continuam legiveis para revisao
historica; nao devem ser reinterpretados automaticamente como AA/AAA ou celular.
O novo ID `household_cell` identifica especificamente AA/AAA e mapeia para a
classe de material `battery`. Nenhuma foto antiga foi apagada ou reclassificada.

Antes do proximo treino, revisar os exemplos existentes: prompts amplos e bases
por material podem conter itens fora desta lista. Nao modificar prompts do
candidato existente sem gerar uma nova versao e reavaliar seus resultados.

## Aceite por objeto

Registrar objeto, material, condicao, sessao e origem. Separar treino, validacao
e teste por objeto fisico/sessao antes de gerar variacoes. Incluir itens fora da
lista como negativos, sem forca-los a uma das seis classes. Publicar metricas
por objeto e material, cobertura e erros aceitos. Nao aprovar uma classe somente
pela media geral ou pela confianca que o proprio modelo informa.
