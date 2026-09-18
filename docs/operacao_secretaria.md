# Operacao da secretaria e conscientizacao

## Decisao de escopo

A prioridade combina frequencia no cotidiano, beneficio ambiental, destino
existente e viabilidade visual. Nao e um ranking estatistico de poluicao.

| Prioridade do piloto | Itens-alvo | Missao educativa |
|---|---|---|
| Primeiro ciclo | Latas de bebida/conserva | Separar metal e confirmar coleta |
| Primeiro ciclo | Garrafas PET, potes e frascos rigidos vazios | Separar embalagens plasticas |
| Primeiro ciclo | Caixas, folhas e jornais | Manter papel/papelao separado |
| Segundo ciclo | Garrafas e potes de vidro inteiros | Identificar sem misturar com outros materiais |
| Frente especial | Pilhas e baterias portateis | Buscar coleta especifica, sem desmontagem |
| Frente especial | Celular, mouse e carregador | Considerar reuso e logistica reversa |

Papel, plastico, metais e vidro compoem as embalagens secas descritas pelo
[SINIR](https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/embalagens-em-geral/).
O [portal de coleta de Sao Paulo](https://coleta.prefeitura.sp.gov.br/) informa
as modalidades locais de coleta e entrega. Aceitacao e disponibilidade devem
ser confirmadas no ponto, sem inferir destino apenas pela cor de uma lixeira.

Pilhas/baterias e pequenos eletronicos recebem uma frente propria por seus
sistemas de logistica reversa:
[pilhas e baterias](https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/pilhas-e-baterias/)
e [eletroeletronicos](https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/eletroeletronicos/).
Nao tratar esses materiais como reciclaveis secos comuns.

Alimentos/organicos permanecem excluidos. Lampadas, medicamentos, oleos,
aerossois, embalagens quimicas e embalagens multicamadas ficam para pesquisa
futura: conteudo, contaminacao e risco nao sao confirmados por formato ou cor.

## Fluxo implementado

1. Cidadao envia a correcao com consentimento; recebe protocolo.
2. O registro entra na mesma fila do servidor usada pela secretaria.
3. Analista autenticado confirma/corrige o item, aprova/rejeita e responde.
4. O cidadao consulta o estado e a resposta em Perfil > Minhas contribuicoes.
5. Aprovacao pode gerar candidato automaticamente, ou aguardar treino em lote.
6. O treino usa filtragem/segmentacao adaptativa e os descritores do modelo
   visual atual, combinando base existente e exemplos aprovados.
7. Candidato fica aguardando validacao. O arquivo ativo nao e substituido.

Treino de kNN atualiza exemplos e normalizacao, nao pesos de uma rede neural.
Cada candidato registra hash do modelo-base, revisoes, fotos e resultado da
execucao. Uma revisao concorrente impede uso de um rotulo alterado; retirar a
aprovacao invalida o candidato na central. Lotes iguais nao geram novo treino.
O limite online e de 40 exemplos distintos; lotes maiores devem ser exportados.

## Validacao e publicacao

Separar um conjunto novo, independente, sem o mesmo objeto/origem no treino.
Medir precisao, recall e F1 por classe, matriz de confusao e abstencoes; incluir
latas/vidro, PET/papelao e negativos fora do escopo. Nao avaliar fotos usadas no
treino como prova de melhora. O modelo legado foi treinado com toda a base
processada; a divisao historica nao comprova independencia desse modelo.

Nao ha promocao automatica nem ganho de precisao comprovado por este fluxo.
O candidato deve ser avaliado pelo responsavel e publicado como versao nova,
com possibilidade de retorno a versao anterior.

## Governo, missoes e indicadores

As missoes sao de educacao/preparacao, nao comprovantes de coleta. Registrar
uma foto nao mede quilos reciclados nem confirma entrega. Medir separadamente:
participacao educativa, correcoes revisadas, taxa de rejeicao, erros por item e
acesso a orientacoes. Comprovacao de entrega exige integracao futura com pontos
de coleta, como protocolo de recebimento ou validacao do operador.

## Limites da simulacao atual

Cidadao e secretaria usam o mesmo backend; nao e necessario trocar arquivos
manualmente enquanto a instancia esta ativa. O disco da hospedagem continua
temporario, portanto pacotes/exportacoes ainda devem ser preservados pelo grupo.
Para operacao institucional: banco/armazenamento persistente, login OIDC dos
analistas, backups e trabalhador de treino separado do servidor publico.
Sem login OIDC configurado, a central administrativa permanece bloqueada.
Nao ha canal oficial municipal nem atendimento real de denuncias nesta simulacao.
