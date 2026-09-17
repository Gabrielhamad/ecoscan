# Piloto publico e aprendizado supervisionado

URL: https://ecoscan-gabrielhamad.streamlit.app/

## Escopo atual

| Categoria | Itens para coleta e testes |
|---|---|
| Metal | Latas de bebida e de conserva vazias, inteiras e amassadas |
| Plastico | Garrafas PET, frascos e potes rigidos vazios |
| Papel/papelao | Folhas, jornais e caixas |
| Vidro | Garrafas e potes inteiros |
| Pilhas/baterias | Pilhas cilindricas e baterias portateis |
| Eletronicos | Celulares, mouses, carregadores e pequenos aparelhos |

Alimentos e organicos estao excluidos. Lampadas, remedios, oleo, aerossol e
embalagens quimicas ficam fora da identificacao automatica desta fase.
Orientacoes e pontos de coleta de residuos especiais podem continuar no mapa.
Foto de embalagem nao identifica com seguranca seu conteudo.

O modelo existente classifica materiais, nao reconhece cada subtipo da tabela
como uma classe treinada. A tabela delimita o objetivo da coleta. Nao ha nova
acuracia comprovada nem promessa de detectar todos os itens.
As classes antigas continuam no artefato para evitar converter uma previsao
fora do escopo na segunda colocada. Quando a primeira categoria esta fora da
lista ativa, a analise e recusada, inclusive no backend Live. Isso nao garante
rejeicao de todo objeto desconhecido: continua sendo necessario testar negativos.

## Ciclo de contribuicao

1. Enviar foto e analisar.
2. Abrir o formulario de correcao, escolher o objeto real e autorizar uso da foto.
3. Baixar a contribuicao em ZIP para preservar o exemplo e entrega-lo ao grupo.
4. Gestor autenticado revisa imagem e rotulo na fila administrativa.
5. Exportar aprovadas; separar por objeto e origem, eliminar duplicatas e comparar
   com os exemplos de treino existentes antes de importar as imagens.
6. Usar scripts/ingest_dataset_folder.py por categoria para importar imagens
   revisadas; seguir a curadoria, divisao e treino existentes. Nao importar os
   diretorios unknown/out_of_scope como uma categoria reciclavel.
7. Comparar o candidato no conjunto de teste reservado, por classe, e nos casos
   de lata/vidro e PET/papelao antes de substituir o modelo publicado.

Contribuicoes nao alteram pesos ou vizinhos automaticamente. Desconhecidos e
fora do escopo servem para avaliar rejeicao; nao sao aprovados para treino das
seis categorias. Hash do modelo, filtro, segmentacao e previsao acompanham o envio.
Uma foto ja enviada pelo mesmo visitante nao e adicionada duas vezes.

## Armazenamento e privacidade

A fila atual usa disco temporario do Streamlit, com ate 200 contribuicoes por
instancia e intervalo de 15 segundos por visitante. Isso limita uso acidental;
nao substitui protecao contra abuso em producao, pois uma nova sessao pode gerar
outro visitante. Uma unica instancia/processo usa trava para coordenar envios.
As fotos sao reduzidas a 1280 pixels e regravadas sem EXIF/GPS.
Nao envie pessoas, documentos, enderecos ou dados pessoais visiveis nas imagens.
O ZIP omite identificadores de conta e caminhos locais, mas inclui a observacao
que o participante escolheu compartilhar. O formulario nao solicita nome.

Os pacotes precisam ser guardados pelo grupo antes de reinicios/redeploy.
O armazenamento persistente externo ainda precisa ser conectado. O download
individual torna o fluxo utilizavel para a rodada atual, mas nao e backup
automatico nem aprendizado continuo autogerenciado.

## Proxima validacao

Coletar objetos fisicos distintos, marcas, cores, deformacoes, fundos e luzes.
Variacoes da mesma foto ou do mesmo objeto nao devem atravessar treino e teste.
Usar fotos negativas (alimentos, objetos comuns e residuos fora da lista),
avaliar falso descarte e publicar precisao/recall por categoria, abstencoes e
matriz de confusao. Pilhas e eletronicos exigem confirmacao de descarte especial.
