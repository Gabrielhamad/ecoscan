# Avaliacao de aceitacao por material

## Objetivo e resultado

Foi implementada uma politica experimental que escolhe limites por material
usando exclusivamente a validacao. Tambem compara a margem entre as duas
melhores hipoteses. Classes sem evidencia suficiente exigem revisao.

O experimento foi **rejeitado para publicacao**. Nao houve troca do modelo ativo.
Nao houve novo treinamento do extrator nem melhoria da acuracia de classificacao.

| Medida no teste exploratorio de 145 fotos | Global anterior | Por material |
| --- | ---: | ---: |
| Fotos aceitas | 70 | 30 |
| Erros aceitos | 5 | 4 |
| Precisao entre aceitas | 92,86% | 86,67% |
| Cobertura | 48,28% | 20,69% |
| Acuracia de classificacao | 73,79% | 73,79% |

Na validacao, a politica por material parecia melhor: 32 acertos entre 33
aceitacoes. Esse resultado nao se repetiu no teste. Diminuir o numero absoluto
de erros rejeitando mais fotos nao significa melhorar a precisao.

## Procedimento reproduzivel

```powershell
tmp/finetune-env/Scripts/python.exe scripts/evaluate_selective_policy.py --run reports/contrastive_probe_20261017 --reference reports/training_curated_20261017 --output reports/nova_avaliacao/summary.json
```

O comando verifica hashes do modelo e manifesto, ordem dos exemplos e evidencia
de preparo. As caracteristicas sao reutilizadas, sem executar novamente o encoder.
O arquivo de saida deve ser novo. O joblib precisa ser um artefato local confiavel;
um hash nao autentica um arquivo recebido de terceiros.

## Proximos criterios de engenharia

1. Revisar exemplos de treino por material, especialmente pilhas AA/AAA e
   embalagens transparentes; distinguir objeto, material e conteudo.
2. Reunir fotos de novas sessoes e objetos fisicos, com rotulos revisados.
   Separar sessoes antes de treinar ou gerar variacoes; preservar um teste novo.
3. Acrescentar negativos: pessoas, alimentos, ambientes sem residuos, imagens
   ilegíveis e objetos fora do escopo. Medir falsas aceitacoes explicitamente.
4. Comparar preparo RGB preservado e filtros adaptativos no mesmo protocolo.
   Segmentar para demonstracao nao comprova deteccao de objetos individuais.
5. Treinar apenas com o conjunto de treino, selecionar com validacao e avaliar
   uma vez no novo teste. Publicar precisao, recall, cobertura e erros por classe.
6. Verificar memoria, latencia e equivalencia de inferencia na hospedagem antes
   de ativar o candidato. Avaliar camera separadamente de fotografias.

O teste atual foi reutilizado em experimentos anteriores e nao e independente.
Nao existe ainda evidência suficiente para declarar confiabilidade em todas as
classes, deteccao de multiplos objetos ou funcionamento robusto ao vivo.
