# Revisao de qualidade e prontidao para publicacao

## Decisao

Atualizacao de robustez apta a seguir para homologacao do piloto. Nao representa
aceite de reconhecimento autonomo, capacidade de producao ou camera em tempo real.
Nao foram executadas operacoes de escrita nas contas ou no banco de producao.

## Correcoes

- Reuso do artefato neural local somente apos verificar SHA-256 do manifesto e
  da cabeca, compatibilidade de processamento e classes. Arquivos corrompidos
  sao baixados novamente. A verificacao de revisoes/consentimento no chamador
  permanece anterior ao cache, com a janela existente de 60 segundos.
- Uma segunda materializacao de uma versao intacta realiza zero downloads de
  manifesto/cabeca, contra dois anteriormente. Isso nao elimina consultas de
  autorizacao e nao mede latencia real de rede.
- Limites de 15 MiB por arquivo e 40 milhoes de pixels antes da decodificacao.
  Fotos acima do limite devem ser reduzidas pelo usuario. Erros de imagem
  descomprimida excessivamente grande sao tratados como entrada invalida.
- Diagnostico local passa a respeitar a prioridade do modelo semantico habilitado,
  em vez de indicar o SVM antigo. Nao comprova qual versao remota esta ativa.
- Pytest limitado a pasta tests, evitando coleta de ambientes temporarios.
- Metadados do pipeline incluem tempos de decodificacao, preparo, filtros,
  segmentacao e geracao de evidencias/entrada neural.

## Medicao local

Uma imagem revisada de papel, execucao unica, CPU local, sem concorrencia:

| Etapa | Tempo |
|---|---:|
| Decodificacao | 51 ms |
| Preparo | 85 ms |
| Filtros | 2359 ms |
| Segmentacao | 4408 ms |
| Evidencias e entrada neural | 855 ms |
| Total do processamento | 7759 ms |

Nao inclui rede, navegacao, inferencia ou latencia de upload. Nao e media nem
percentil de producao. Segmentacao e filtragem precisam de perfilamento em mais
imagens antes de escolher uma otimizacao que preserve o resultado academico.
O smoke test completo identificou papel/papelao como sugestao e manteve a
confirmacao do usuario; isso nao e avaliacao de acuracia.

## Aceite local

Diagnostico com amostra: 12 itens OK, 4 com atencao, 5 pendentes, zero falhas.
O relatorio detalhado esta em reports/readiness_20261023_sample/.
A primeira tentativa no ambiente de testes nao tinha ONNX Runtime; o smoke test
foi repetido no ambiente de inferencia que possui essa dependencia.
Contagens de diretorios raw/curated nao incluem a base de features usada no treino.

## Pendencias para uso publico definitivo

1. Homologar cadastro, recuperacao e isolamento entre contas reais na nuvem.
2. Confirmar persistencia de reportes, campanhas e pontos apos reinicio do app.
3. Medir concorrencia e tempos de resposta no Streamlit com carga controlada.
4. Testar camera, temas e navegacao em Android, iOS e computador reais.
5. Ensaiar restauracao de backup e retorno a uma versao anterior.
6. Aprovar reconhecimento em conjunto independente de fotos de celular.

Nao baixar limiares de confianca nem retirar a revisao de reportes para cumprir
uma meta de publicacao. O reconhecimento continua assistido.
