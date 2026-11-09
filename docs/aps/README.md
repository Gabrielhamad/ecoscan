# Base acadêmica e seminário — Prompt 11

O [relatório técnico](relatorio_tecnico.md), o [índice de evidências](indice_evidencias.md)
e o [roteiro de 13 minutos](roteiro_seminario.md) descrevem exclusivamente o SHA
`89622ec714b815c216a9215ab9ba69999b39c6b8`. Os PRs #20–#29 estão separados, sem
integração presumida ou atribuição de melhorias à aplicação publicada.

Arquivos para revisão: [relatório Word](relatorio_aps.docx),
[ficha Word preparatória](ficha_aps_preparatoria.docx),
[apêndice do código](apendice_codigo.zip) e [manifesto de artefatos](artefatos.json).
As duas cópias Word não contêm identificação pessoal preenchida.

O gerador anterior inseria números literais e descrições antigas de perfis,
campanhas/CSV, além de concluir ausência de atenções a partir de relatórios
ausentes. Agora exporta texto revisado, verifica 48 arquivos e recalcula as
tabelas a partir de JSONs versionados. Não ingere contagens de fotos locais,
relatórios privados, `.env`, Secrets, nomes ou RAs. A API Markdown foi preservada.
Mudança do código/evidência exige nova revisão; não basta trocar o SHA no texto.

## Gerar a cópia de revisão

No branch deste pacote, com Python 3.12 e dependências do projeto instaladas:

Os checks de evidência comparam bytes com os blobs Git. Para um clone separado
de revisão em ambiente que converte LF/CRLF automaticamente, preservar os bytes:
`git -c core.autocrlf=false clone https://github.com/Gabrielhamad/ecoscan.git ecoscan-aps-revisao`.
Selecionar depois o branch deste PR. Abertura no Windows continua sem teste físico.

```bash
python scripts/generate_academic_report.py --output reports/aps_report/relatorio_aps.md
python scripts/generate_academic_report.py --output reports/aps_report/relatorio_aps.md --docx --code-appendix
```

DOCX requer `pandoc` no ambiente de desenvolvimento, sem nova dependência no
runtime Streamlit. O apêndice exige o objeto Git do SHA congelado; em checkout
raso, buscar esse SHA antes. A saída também copia o índice, roteiro, ficha e
manifestos para manter links locais. `apendice_codigo.zip` contém somente fontes
públicas, testes, migrações e metadados declarados, obtidos do commit, com hash por
entrada. Não inclui fotos, contas, dados, backups, Secrets ou pesos. Não é release
executável e não concede nova licença ao código do grupo.

Os DOCX de revisão e o apêndice anexados nesta pasta são artefatos acadêmicos
gerados; Markdown/JSON são a fonte revisável. Para reverter, descartar a cópia
gerada ou reverter este PR. Nenhum banco, deploy, autenticação ou modelo foi alterado.

## Formatação e dependências acadêmicas

O exportador declara Arial 12, espaço 1,5, A4 e **quatro margens de 2,5 cm** conforme
as instruções recebidas. Confere os valores OOXML efetivos e remove autoria
inferida da conta do sistema. Os JSONs `.format.json` registram os checks.
O ambiente possui Pandoc/LibreOffice, mas não possui Arial: o DOCX declara a fonte,
enquanto a visualização local pode substituí-la. Conferir fonte, quebras, tabelas,
numeração e capa no computador com Arial legítima. Não se publica PDF como se
fosse Arial homologada. Isso não certifica conformidade integral ABNT/institucional.

Não há PDF oficial 2026 nem ficha institucional acessíveis. O plano versionado
registra nome 2026 com cabeçalho 2025/2. A [ficha preparatória](ficha_aps_preenchimento_privado.md)
tem apenas campos vazios; não é formulário oficial. Preencher autores, RAs,
contribuições, datas, horas e assinaturas em cópia privada, com fatos reais,
e transpor para o modelo confirmado pela professora.
O grupo confirmou a ausência de URL institucional pública e autorizou o uso do
resumo com a ressalva; isso não substitui a aprovação do modelo da ficha.

F01–F03 (duas fotos autorizadas e um fracasso diagnosticado), comparação real
de segmentação, avaliação independente, PC/celulares, três ensaios e aceite
continuam pendentes. Os números do relatório são históricos qualificados;
nenhuma figura fictícia ou foto de licença individual não conferida foi incluída.
O roteiro mantém erros e rejeições, usa ordem de fotos congelada antes de inferir
e discute a confusão histórica metal→vidro sem inventar sua causa visual.

Pronto para **revisão técnica**; `academic_submission_ready=false` até completar
os gates do índice. CI verde não equivale à aprovação da APS ou ao aceite publicado.
