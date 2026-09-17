# Resultado da captura web

## Atualização em 10/09/2026

O dataset semente foi ampliado com Wikimedia Commons, Openverse e TACO:

- imagens brutas válidas em `data/raw`: 504;
- imagens preparadas em `data/processed`: 499;
- imagens em quarentena por ruído, falso positivo ou ausência de utilidade para treino: `data/quarantine`;
- classes no alvo bruto de 50 imagens: 8/12.

Classes ainda abaixo do alvo de 50 imagens brutas:

- `medicine`: 41;
- `cooking_oil`: 22;
- `aerosol`: 21;
- `chemical_packaging`: 20.

O split provisório atual usa `data/processed`, não `data/raw`, para preservar a etapa APS de tratamento antes do reconhecimento.

## Captura realizada

Em 04/09/2026 foi executado `scripts/capture_wikimedia_dataset.py` com alvo de 20 imagens por classe.

Resultado:

- `plastic`: 20 imagens;
- `paper_cardboard`: 20 imagens;
- `metal`: 20 imagens;
- `glass`: 20 imagens;
- `organic`: 20 imagens;
- `battery`: 20 imagens;
- `electronic`: 20 imagens.

Total: 140 imagens capturadas em `data/raw`.

## Validação automática

O script `scripts/analyze_dataset.py` validou as imagens capturadas:

- imagens válidas: 140;
- imagens inválidas: 0;
- distribuição: balanceada em 20 imagens por classe;
- relatórios gerados em `reports/dataset_analysis`.

## Licenças encontradas no manifesto

O manifesto `reports/web_capture/wikimedia_capture_manifest.csv` registrou os seguintes tipos de licença:

- CC BY-SA 4.0: 61;
- CC BY-SA 3.0: 20;
- CC BY 2.0: 19;
- CC0: 12;
- Public domain: 12;
- CC BY 3.0: 5;
- CC BY 4.0: 5;
- CC BY-SA 2.0: 5;
- GFDL 1.2: 1.

Cada arquivo deve manter sua atribuição se for publicado, apresentado fora do ambiente acadêmico ou redistribuído.

## Revisão visual inicial

A análise por grade mostrou que a captura é suficiente para desenvolver o pipeline, mas ainda não é dataset final de treinamento.

Observações:

- `metal`: classe mais coerente nesta captura, com muitas imagens de latas e material reciclável.
- `electronic`: boa para demonstrar resíduo eletrônico, mas contém peças isoladas e cenas de descarte.
- `glass`: utilizável, mas algumas imagens têm cenário dominante ou garrafas históricas/decorativas.
- `plastic`: contém bons frascos e garrafas, mas também cenas nas quais o objeto principal não é plástico.
- `paper_cardboard`: contém caixas e papelão, mas também imagens urbanas amplas e objetos misturados.
- `organic`: contém restos de comida, mas também pôsteres e cenas de compostagem/lixo amplo.
- `battery`: precisa de maior limpeza; a primeira captura trouxe experimentos de bateria com frutas, pesquisadores e equipamentos grandes.

## Conclusão técnica

Este conjunto deve ser tratado como dataset semente para:

- testar validação de imagem;
- demonstrar redimensionamento;
- comparar filtros;
- experimentar segmentação;
- construir a tela "Ver Processamento";
- preparar o fluxo de inferência antes do modelo final.

Antes de treinar o modelo final, é necessário:

1. revisar as grades por classe;
2. remover imagens fora do domínio;
3. substituir a classe `battery` por imagens mais próximas de pilhas/baterias domésticas;
4. preferir datasets maiores como MWCD, NexTech14 ou Kaggle Garbage Dataset PlusYaml quando o grupo tiver acesso;
5. separar treino, validação e teste sem vazamento.
