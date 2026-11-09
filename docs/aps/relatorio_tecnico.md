# EcoScan: processamento de imagens e reconhecimento assistido de resíduos

**Base técnica para revisão pelo grupo e pela professora — não é entrega acadêmica homologada.**

Instituição, curso, campus, turma, disciplina e docente: **preencher em cópia privada com dados reais**.
Autores e RAs: **preencher em cópia privada**. Cidade e data de entrega: confirmar.
Não usar o endereço GitHub como nome de autor. Não publicar RAs ou assinaturas neste repositório.

Código descrito: [89622ec714b815c216a9215ab9ba69999b39c6b8](https://github.com/Gabrielhamad/ecoscan/tree/89622ec714b815c216a9215ab9ba69999b39c6b8).
Revisão documental: 08/11/2026, America/Sao_Paulo. A data planejada do Prompt 11 não é registro de execução em 10/11.
SHA implantado no site público: **não verificado por este relatório**.

Manual oficial 2026 e ficha institucional: **dependência pendente**. O arquivo
original não está no workspace e a busca pública não localizou uma versão
institucional confirmada. O [plano versionado](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/plano_validacao_aps_4_dias.md#L7)
registra o nome `ManualAPS-5oe6oCCI-PI-2026 2.pdf`, mas informa cabeçalho interno
2025/2. Este texto usa esse resumo e as instruções recebidas; não apresenta uma
ficha inventada como oficial nem certifica conformidade integral com ABNT 2026.
O grupo confirmou que não há URL institucional pública e orientou usar o resumo
com essa ressalva. A conferência do modelo oficial continua pendente.

Resumo: o projeto recebe uma fotografia, executa operações de PDI e produz uma
hipótese visual entre seis categorias, seguida de confirmação humana e orientação
ambiental. O relatório descreve o código congelado e resultados históricos
rastreáveis. A reprodução dos 145 vetores históricos mantém `independent_test=false`.
Faltam novas fotografias autorizadas, avaliação independente por objeto/sessão,
comparações visuais reais completas, ficha oficial e aceite no equipamento da apresentação.

Palavras-chave: processamento digital de imagens; resíduos; reconhecimento assistido; sustentabilidade.

## 1. Problema

### 1.1 Introdução e sustentabilidade

A separação de resíduos envolve distinguir categorias e consultar a rota de
destinação disponível. A Política Nacional de Resíduos Sólidos estabelece uma
ordem que começa pela não geração, redução e reutilização, antes de reciclagem,
tratamento e disposição dos rejeitos (BRASIL, 2010). O EcoScan se insere como apoio
educativo à consulta de materiais; não mede massa recuperada, economia de energia
ou emissões evitadas. Não houve estudo de usuários que demonstre mudança de
comportamento ou impacto ambiental decorrente do aplicativo.

### 1.2 Formulação

Entrada: imagem I de um resíduo principal, com rótulo de referência y disponível
somente nos conjuntos avaliados. O classificador produz um vetor de scores s(I)
e uma primeira escolha argmax(s). A decisão do produto também depende de validade
do arquivo, qualidade de captura, compatibilidade do processamento, escopo e
confirmação humana. A orientação g(c) recebe uma categoria c confirmada; não pode
ser avaliada como se fosse a previsão original do modelo.

Problema técnico: produzir uma hipótese útil sem transformar semelhança visual em
prova de composição, conteúdo ou segurança. Plástico e vidro transparentes, metal
refletivo, fundo, sombra e enquadramento são cenários a examinar; não se atribui
causa a um erro específico sem examinar sua fotografia.

## 2. Objetivos e proposta

O objetivo é implementar aquisição, manipulação, filtragem, segmentação e
reconhecimento assistido em uma aplicação Streamlit executável com Python 3.12.
O grupo deve demonstrar o efeito das operações sobre fotos reais, explicar erros
e permitir correção humana antes da orientação completa de descarte.

A proposta mantém o classificador separado das regras de destino. A interface
oferece câmera/upload, laboratório PDI, hipótese, confirmação e consulta de
coleta. Supabase é opcional; as capacidades persistentes dependem de identidade
verificada e configuração do servidor. Não há exigência comprovada de `.exe`.

## 3. Escopo e rastreabilidade

Classes: `battery`, `electronic`, `glass`, `metal`, `paper_cardboard`, `plastic`.
`unknown` representa a saída fora das seis categorias. Metal, plástico e vidro
são prioritários para nova coleta. Alimentos, orgânicos, óleo e medicamentos
não são reconhecimento automático deste modelo; podem ter conteúdo educativo.
Componentes segmentados não constituem detecção supervisionada de vários objetos.

O [índice de evidências](indice_evidencias.md) relaciona 18 requisitos a arquivos,
linhas, testes, hashes, resultados e pendências. Os identificadores APS-01..18
são rastreabilidade deste pacote, não códigos de requisito atribuídos ao manual.
O manifesto `evidencias.json` fixa 48 arquivos de referência. O gerador recusa
evidência alterada e não lê fotos, perfis, backups ou relatórios privados locais.

Os PRs [#20](https://github.com/Gabrielhamad/ecoscan/pull/20) a
[#29](https://github.com/Gabrielhamad/ecoscan/pull/29) foram consultados como
desenvolvimento ainda não integrado. Separação total entre filtro didático e
inferência, novo motor de decisão e pacote de execução desses PRs **não são
atribuídos ao código congelado ou ao site publicado**. Depois de integrar código,
será necessário revisar este texto e registrar novo SHA e novas evidências.

## 4. Referencial teórico

Uma imagem RGB possui três canais; operações de intensidade usam também uma
representação de cinza. Filtros locais podem reduzir variações ou destacar
gradientes, alterando informações úteis. Gaussianas e medianas têm efeitos
diferentes sobre ruído e bordas, conforme a documentação OpenCV (OPENCV, s.d.).
Nenhuma dessas operações garante aumento de acurácia por si só.

Otsu (1979) seleciona um limiar a partir da distribuição de intensidades.
GrabCut combina modelos de aparência e cortes em grafo para estimar primeiro
plano e fundo (ROTHER; KOLMOGOROV; BLAKE, 2004). No aplicativo, seu retângulo
central é inicialização automática; isso não torna a máscara uma anotação humana.

CLIP aprende representações associando imagens e textos (RADFORD et al., 2021).
O EcoScan reutiliza um encoder congelado e ajusta uma cabeça supervisionada;
não treinou a arquitetura CLIP do zero. TACO fornece contexto para pesquisa de
resíduos em cenas (PROENÇA; SIMÕES, 2020), com domínio diferente das fotografias
sobre fundo branco de TrashNet. A origem externa de uma base não comprova sua
independência em relação a todo o desenvolvimento do projeto.

## 5. Arquitetura e fluxos de dados

| Etapa | Entrada e saída | Responsabilidade real |
| --- | --- | --- |
| Entrada | `streamlit_app.py` → `ui.bootstrap` → `ui.streamlit_app` | Inicialização e composição das páginas |
| Captura | Arquivo/câmera → arquivo temporário e sessão | `ui.analysis_controller` e `ui.session_state` |
| Aquisição | Bytes → RGB orientado | `image_processing.image_io` e validação |
| PDI | RGB → filtro, máscaras, componentes e prévia | `app.pipeline`, filtros e segmentação |
| Inferência | RGB 224×224 → scores e top-1 | `classification.runtime` e `semantic_onnx` |
| Segurança | Predição + contrato + qualidade → sugestão/abstenção | Serviço de análise e `recognition_safety` |
| Confirmação | Categoria selecionada → orientação | Controlador de análise e `disposal` |
| Persistência opcional | Ação autorizada → tabelas/Storage privados | Serviços Supabase no servidor |

O fluxo de inferência começa no serviço de análise, que executa o pipeline e
carrega o bundle. O controlador chama a política de segurança para a apresentação.
Não se afirma que toda regra de interface foi removida na versão congelada.
O servidor Live, quando usado, é processo separado e não acompanha automaticamente
o deploy gratuito Streamlit. Sem teste desse servidor/aparelho, não declarar vídeo validado.

## 6. Aquisição e manipulação

JPG/PNG são validados antes da inferência: existência, bytes vazios, tamanho,
resolução, corrupção e dimensão mínima. Os limites padrão são 15 MiB e 40 milhões
de pixels. Pillow verifica o arquivo, aplica orientação EXIF, converte para RGB
e compõe transparência sobre branco (PILLOW, s.d.). Metadados originais não são
evidência de consentimento para publicar a imagem.

A imagem de trabalho preserva a proporção, reduz o maior lado a até 640 pixels
e não amplia nessa etapa. O cinza usa 0,299R + 0,587G + 0,114B. Normalização de
referência para PDI usa float32 em [0,1]. A entrada do encoder segue outra etapa:
letterbox 224×224, padding RGB 127 e normalização específica CLIP. A conversão
cinza de laboratório não substitui automaticamente os três canais do encoder.

Para cada foto autorizada, registrar hash do arquivo, dimensões antes/depois,
orientação, parâmetros e SHA do processamento. O histograma auxilia a inspeção
da distribuição de intensidade; não comprova sozinho que o objeto foi segmentado.

## 7. Processamento digital de imagens

| Operação | Implementação no snapshot | Parâmetros/limitação |
| --- | --- | --- |
| Controle `none` | Cópia NumPy | Permite comparação sem filtro |
| Gaussiano | `cv2.GaussianBlur`; fallback Pillow | Kernel ímpar, sigma; fallback não é identidade numérica com OpenCV |
| Mediana | `cv2.medianBlur`; fallback Pillow | Kernel ímpar; detalhes finos podem desaparecer |
| Sobel | Kernels e convolução NumPy no projeto | Borda replicada, magnitude normalizada; visualização de gradientes |
| CLAHE e bilateral | Operações OpenCV configuradas pelo projeto | Preservar cor e declarar dependência |
| Automático | Diagnóstico e escolha de sequência do projeto | Heurística; não foi validada como calibrador de reconhecimento |

Gaussianas, medianas, CLAHE e GrabCut não são apresentados como algoritmos
inventados pelo grupo. A contribuição do projeto está na integração, contratos,
seleção, explicações, exportação e testes. As rotinas NumPy de Sobel, limiar Otsu,
morfologia e componentes são implementações do projeto de métodos conhecidos.
A atribuição nominal aos integrantes exige o registro real de contribuições.

**Limite do SHA congelado:** a máscara é diagnóstica e não entra no encoder,
mas `recognition_source = filter_result.image` para filtros comuns; Sobel/Canny
retornam à imagem de trabalho. Mudar um filtro manual pode alterar pixels da
inferência e o checksum do contrato. A separação proposta no PR #21 não está
integrada. Para medir o modelo deste relatório, manter o perfil oficial e
não misturar resultados de exploração de filtros com a avaliação homologada.

## 8. Segmentação

Otsu calcula um histograma de 256 níveis e maximiza a variância entre grupos.
A polaridade pode ser escolhida pelo usuário ou inferida da borda. A rotina HSV
usa limiares mínimos de saturação e brilho; não é uma classificação semântica
de material. GrabCut usa OpenCV, retângulo central, iterações e seed definida.

As máscaras binárias recebem erosão/dilatação, abertura e fechamento. Na rotina
NumPy, o exterior da imagem é fundo zero; footprint, tamanho, iterações e ordem
são registrados. Componentes conectados fornecem área e caixas de regiões.
Um reflexo pode criar mais de um componente no mesmo objeto; várias caixas não
são múltiplos materiais reconhecidos. O mapa de calor representa a máscara, sem
interpretação probabilística de confiança do modelo.

A exportação `processing_evidence_zip` utiliza os arrays da execução, PNG sem
perda, diferenças absolutas 0–255 e hashes incluindo shape/dtype. O JSON mede
pixels alterados quando os arrays são comparáveis. Isso comprova uma transformação,
não sua qualidade. IoU e Dice só podem comparar máscara prevista com referência
humana correspondente; **não foram medidos em novas fotos reais nesta etapa**.

## 9. Modelo de visão e orientação segura

O formato é `clip-probe-fp16-v1`, CLIP ViT-B/32 QuickGELU congelado, ONNX CPU.
O runtime pode selecionar uma cabeça remota se os serviços/configuração estiverem
ativados. O SHA do código, sozinho, não fixa esse artefato: registrar o hash do
modelo efetivamente carregado na demonstração e comparar com o manifesto. Os
resultados deste texto são da release local descrita, não de um modelo remoto
cuja identidade não foi conferida. Não se alterou modelo publicado nesta etapa.
O resolver verifica cada shard e o encoder reunido por SHA-256. A cabeça é lida
de `head.npz` com `allow_pickle=False`. A entrada exigida é uint8 RGB 224×224×3;
depois é normalizada pela média/desvio CLIP e transposta para NCHW.

Dois vetores softmax são combinados: prior de protótipos e cabeça linear
supervisionada com padronização das features. `prior_weight=0.5`; o maior score
define top-1. O limiar do artefato é **0,8**. O score não é uma probabilidade
calibrada de acerto em campo, e não há validação independente por classe nesta base.

O serviço mantém `confirmation_required=true` e converte mesmo uma aceitação do
artefato em `accepted=False` para a aplicação. Contrato incompatível, desconhecido
e captura inadequada também exigem abstenção ou nova captura. A política do motor
ativo pede confirmação; os novos estados/opt-in do PR #24 não são produto deste SHA.

Depois de confirmar, metal usa amarelo, plástico vermelho, vidro verde e
papel/papelão azul, conforme o padrão de identificação de coleta seletiva
(CONAMA, 2001). Pilhas e eletrônicos seguem coleta especializada, sujeita à
aceitação do ponto; a foto não comprova integridade, química, limpeza ou conteúdo.
O projeto não deve incentivar abrir, perfurar ou danificar objetos para fotografar.

## 10. Avaliação

### 10.1 Método e unidades

A unidade técnica pode ser pixel, arquivo ou chamada de serviço; a unidade de
generalização pretendida é um objeto físico em uma sessão independente. Fotos
do mesmo objeto não são réplicas independentes. A proposta de campo é obter
10–15 objetos distintos por classe prioritária e casos fora do escopo, com
consentimento/licença, hash, rótulo, `object_id` e `session_id`. É plano de coleta,
não contagem de objetos já obtidos. Separar treino/validação/teste antes de medir;
selecionar parâmetros apenas na validação e manter o teste final intocado.

Acurácia top-1 = acertos/N. Precisão = VP/(VP+FP), recall = VP/(VP+FN), F1 = média
harmônica entre precisão e recall; macro F1 dá peso igual às classes avaliadas.
Cobertura = aceitos/N e erro seletivo = erros entre aceitos/aceitos. Reportar
rejeições e matriz por classe. Avaliar `top_class_id` antes da confirmação,
separando cobertura do artefato e decisões aceitas pelo serviço do produto.

### 10.2 Testes de engenharia

O baseline foi novamente executado localmente nesta etapa: **496 testes e 108
subtestes passaram**, Ruff e `pip check` passaram. A CI da fonte oficial
[42513163053](https://github.com/Gabrielhamad/ecoscan/actions/runs/42513163053)
tem resultado success. Testes relevantes estão no índice: EXIF/limites, formas de
arrays, convolução, morfologia pixel a pixel, hashes/shards, confirmação,
identidade, isolamento e indisponibilidade com stubs. A CI testa migrações e
privilégios em PostgreSQL 16 isolado, sem contas reais ou produção.

Esses resultados não são acurácia visual nem aprovação de QA-09/QA-18..QA-21.
Os testes e a CI do PR documental são evidência adicional, identificada no próprio
PR; não aumentam retroativamente a contagem de testes do código congelado.

## 11. Comparações e resultados

### 11.1 Reconhecimento

Os números abaixo são derivados dos JSONs versionados e verificados por hash.
O conjunto de 145 vetores foi reutilizado durante desenvolvimento; foi reproduzido
nesta etapa pelo comando `evaluate_bundled_model.py`, sem nova coleta. O diagnóstico
TrashNet já estava registrado para 224 fotos de três classes sobre fundo branco;
nesta etapa verificou-se consistência dos registros, sem baixar/reexecutar as fotos.
Ambos mantêm **independent_test=false** e não são comparação antes/depois de modelo.

<!-- MODEL:BEGIN -->
| Métrica | Histórico reutilizado | TrashNet diagnóstico |
| --- | ---: | ---: |
| N | 145 | 224 |
| Top-1 correto | 101 | 186 |
| Acurácia top-1 | 69,66% | 83,04% |
| Precisão macro | 73,75% | 87,03% |
| Recall macro | 64,10% | 83,31% |
| F1 macro | 0.6510 | 0.8510 |
| Aceitos pelo artefato | 51 | 94 |
| Erros entre aceitos | 4 | 0 |
| Rejeitados | 94 | 130 |
| Precisão entre aceitos | 92,16% | 100,00% |
| Cobertura do artefato | 35,17% | 41,96% |
| Erro entre aceitos | 7,84% | 0,00% |
| Taxa de rejeição | 64,83% | 58,04% |

Histórico, por classe, antes da confirmação humana:

| Classe | N | Precisão top-1 | Recall top-1 | F1 |
| --- | ---: | ---: | ---: | ---: |
| battery | 14 | 75,00% | 21,43% | 0.3333 |
| electronic | 16 | 88,89% | 50,00% | 0.6400 |
| glass | 29 | 79,31% | 79,31% | 0.7931 |
| metal | 29 | 78,57% | 75,86% | 0.7719 |
| paper_cardboard | 29 | 55,00% | 75,86% | 0.6377 |
| plastic | 28 | 65,71% | 82,14% | 0.7302 |

Matriz histórica: linhas = rótulo de referência; colunas = top-1 previsto.
B=battery; E=electronic; G=glass; M=metal; P=paper_cardboard; L=plastic.

| Real | B | E | G | M | P | L |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B | 3 | 1 | 1 | 2 | 7 | 0 |
| E | 1 | 8 | 1 | 1 | 3 | 2 |
| G | 0 | 0 | 23 | 1 | 2 | 3 |
| M | 0 | 0 | 3 | 22 | 2 | 2 |
| P | 0 | 0 | 0 | 2 | 22 | 5 |
| L | 0 | 0 | 1 | 0 | 4 | 23 |
<!-- MODEL:END -->

Há erros reais no registro: **3 dos 29 metais tiveram top-1 vidro**, e **7 das 14
pilhas tiveram top-1 papel/papelão**. A matriz não permite diagnosticar reflexo ou
iluminação sem as fotos. O recall de pilhas é baixo; a hipótese visual não deve
ser usada como autorização de descarte comum. A precisão 100% entre os 94 aceitos
do recorte TrashNet não significa 100% de acerto em campo: rejeitou 130 e não
passou auditoria independente de origem/desenvolvimento.

Os 51 aceitos históricos são do artefato antes da confirmação. Com a configuração
atual, o produto não emite aceitação automática, mesmo nesses casos. Não confundir
acerto da orientação após correção humana com acerto original do classificador.
Latência de campo por dispositivo, calibração e efeito dos filtros na acurácia:
**não medidos neste relatório**.

### 11.2 PDI: comparativos históricos e resultado negativo

Os arquivos `default.json` e `sigma8.json` registram ensaios sobre 23 recortes
TACO por condição. As condições de ruído/baixo contraste são degradações
controladas sobre fotografias de origem, não novas capturas de campo.
As condições reutilizam os mesmos 23 recortes; o suporte não aumenta com a degradação.
`sigma8` registra override `min_noise_sigma=8`. ΔSSIM usa referência conhecida;
não é IoU, Dice ou precisão do reconhecedor. Os originais não acompanham este
workspace para reexecutar esses ensaios; são **resultados históricos consultados**.

<!-- PDI:BEGIN -->
| Registro histórico | Condição | N | ΔSSIM médio | Casos com queda de SSIM |
| --- | --- | ---: | ---: | ---: |
| default.json | unchanged | 23 | -0.007362 | 4 |
| default.json | gaussian_noise | 23 | +0.064246 | 1 |
| default.json | impulse_noise | 23 | +0.149011 | 0 |
| default.json | low_contrast | 23 | +0.040175 | 0 |
| sigma8.json | unchanged | 23 | +0.000000 | 0 |
| sigma8.json | gaussian_noise | 23 | +0.050679 | 1 |
| sigma8.json | impulse_noise | 23 | +0.149011 | 0 |
| sigma8.json | low_contrast | 23 | +0.040175 | 0 |
<!-- PDI:END -->

Resultado negativo preservado: no registro `default`, quatro imagens sem
degradação perderam SSIM após filtragem; a média ficou negativa. No ensaio
`sigma8`, as 23 imagens sem degradação permaneceram no controle. Isso não autoriza
promover parâmetros por ganho de reconhecimento: não houve essa medição e os
mesmos recortes foram usados para comparar a preparação.

### 11.3 Figuras de fotos reais — gate pendente

Não foram fornecidas novas fotos autorizadas do grupo. Nenhuma imagem fictícia
foi inserida para completar resultados. A prancha TACO derivada existente em
`docs/preparation_evidence/impulse_example.jpg` não é reproduzida neste documento:
a base declara CC BY 4.0, mas a revisão individual das licenças de origem é uma
pendência registrada. Não se afirma que os direitos individuais foram auditados.

| Figura reservada, ainda não produzida | Comparação exigida | Registro necessário |
| --- | --- | --- |
| F01 — foto real autorizada A | RGB/cinza/histograma, controle, Gaussiano e mediana | Fonte/licença, hash, parâmetros, tempo e diferença medida |
| F02 — foto real autorizada B | Controle, Sobel, Otsu/HSV, máscara e morfologia | Mesma imagem, kernel, etapas, limites; IoU/Dice só com referência |
| F03 — fracasso real autorizado | Sombra, reflexo ou transparência efetivamente observado | Predição/rejeição original, diagnóstico visual e correção humana |

Exportar com `python scripts/export_processing_evidence.py --image FOTO_LOCAL
--output reports/figuras/F01` em cópia local autorizada, registrar SHA, operações
e tempo; revisar o conteúdo antes de inserir na APS. Esse script usa os defaults;
para comparar alternativas escolhidas, usar o laboratório e exportar a mesma
execução. Não dizer que o script oferece flags de filtros inexistentes.
Registrar também versão das dependências e hash da configuração. Falha de
segmentação deve ser relatada, não excluída depois de observar a predição.

## 12. Banco, permissões e privacidade

As migrações `001`–`004` criam contribuições, pontos, testes de campo, campanhas,
relatos e auditoria. Ativam RLS, revogam acesso direto de `anon` e `authenticated`
às tabelas operacionais e concedem operações específicas a `service_role`.
Triggers verificam limites, transições e auditoria; constraints de identidade
verificada são aditivas e `NOT VALID`, protegendo novas alterações sem afirmar
que todas as linhas antigas foram saneadas.

Esse desenho **não é acesso direto ao banco com RLS por cidadão**. A chave de
serviço pode contornar RLS (SUPABASE, s.d.) e fica no servidor; os serviços devem
verificar sessão, papel, dono e revisão antes de escrever/consultar. As identidades
de administrador não vêm de parâmetros da URL ou do JSON de perfis de demonstração.
O fluxo com senha valida sessão no Supabase; há também resolução de claims OIDC.
O isolamento desses caminhos precisa ser validado na configuração de implantação.

Com Supabase/flags ativados, serviços usam tabelas e Storage privados; o código
também mantém caminhos locais de demonstração para certos registros. Portanto,
nem persistência garantida nem “tudo é CSV” descrevem a arquitetura. Visitantes
não recebem pontos permanentes; imagens de contribuição exigem autorização e
tratamento específico. Fotos de análise e fotos consentidas para aprendizagem
são finalidades diferentes.

O teste SQL usa fixtures e rollback no PostgreSQL da CI. Não foram usados tokens,
contas reais, produção ou ensaio de restore nesta etapa. O P1 de mensagem bruta
de erro relatado no [PR #28](https://github.com/Gabrielhamad/ecoscan/pull/28), com
correção proposta no [PR #26](https://github.com/Gabrielhamad/ecoscan/pull/26),
impede afirmar que todo caminho da main está livre de exposição em UI/log.

## 13. Limitações e ameaças à validade

O histórico reutiliza features; fotos e grupos originais não acompanham a semente.
Hashes sem interseção não provam ausência de cenas/objetos repetidos. Os 16 hashes
reservados sem rótulos/features não formam um teste calculável neste clone.
TrashNet cobre apenas três classes e um cenário controlado. TACO não contém
vidro no recorte de treino do projeto. Não há ensaio independente novo, calibração
por classe, avaliação de rejeição de objetos desconhecidos ou medida de impacto ambiental.

Continuam pendentes: F01–F03, direitos individuais das figuras, PC/Android/iPhone,
câmera física, rede indisponível no aparelho, contas A/B/analista, recuperação,
aceite do SHA publicado, ensaios cronometrados, nomes/RAs/contribuições reais,
ficha oficial e regras institucionais 2026. Não se substitui essa evidência por CI.

## 14. Conclusão

O código congelado implementa um fluxo de aquisição, PDI, classificação ONNX e
orientação condicionada à confirmação. Testes reproduzíveis e registros de
artefatos permitem auditar parte dessa implementação. A avaliação histórica
mostra acertos, erros e rejeições; não demonstra melhoria nova ou confiabilidade
independente de campo. O resultado acadêmico disponível é uma base técnica
rastreável para revisão. A entrega final depende das evidências reais e dos
elementos institucionais explicitamente pendentes.

## Referências

BRASIL. **Lei nº 12.305, de 2 de agosto de 2010**. Institui a Política Nacional de Resíduos Sólidos. Publicação original. Brasília, DF, 2010. Disponível em: <https://www2.camara.leg.br/legin/fed/lei/2010/lei-12305-2-agosto-2010-607598-publicacaooriginal-128609-pl.html>. Acesso em: 8 nov. 2026.

CONSELHO NACIONAL DO MEIO AMBIENTE (CONAMA). **Resolução nº 275, de 25 de abril de 2001**. Código de cores para identificação de resíduos. DOU, 19 jun. 2001, seção 1, p. 80. Disponível em: <https://conama.mma.gov.br/?id=273&option=com_sisconama&task=arquivo.download>. Acesso em: 8 nov. 2026.

OPENCV. **Smoothing Images; Image Thresholding**. Documentação 4.13.0, s.d. Disponível em: <https://docs.opencv.org/4.13.0/d4/d13/tutorial_py_filtering.html> e <https://docs.opencv.org/4.13.0/d7/d4d/tutorial_py_thresholding.html>. Acesso em: 8 nov. 2026. Referência dos métodos; a versão instalada deve constar da execução.

OTSU, N. **A Threshold Selection Method from Gray-Level Histograms**. IEEE Transactions on Systems, Man, and Cybernetics, v. 9, n. 1, p. 62–66, 1979. DOI: <https://doi.org/10.1109/TSMC.1979.4310076>. Metadados editoriais verificados; acesso integral ao editor exige verificação de navegador.

PILLOW. **ImageOps module**. Documentação Pillow 13.0.0, s.d. Disponível em: <https://pillow.readthedocs.io/en/stable/reference/ImageOps.html>. Acesso em: 8 nov. 2026.

PROENÇA, P. F.; SIMÕES, P. **TACO: Trash Annotations in Context for Litter Detection**. arXiv:2003.06975, 2020. Disponível em: <https://arxiv.org/abs/2003.06975>. Acesso em: 8 nov. 2026.

RADFORD, A. et al. **Learning Transferable Visual Models From Natural Language Supervision**. Proceedings of the 38th International Conference on Machine Learning, PMLR, v. 139, p. 8748–8763, 2021. Disponível em: <https://proceedings.mlr.press/v139/radford21a.html>. Acesso em: 8 nov. 2026.

ROTHER, C.; KOLMOGOROV, V.; BLAKE, A. **GrabCut: Interactive Foreground Extraction using Iterated Graph Cuts**. ACM Transactions on Graphics, SIGGRAPH, ago. 2004. Disponível em: <https://www.microsoft.com/en-us/research/publication/grabcut-interactive-foreground-extraction-using-iterated-graph-cuts/>. Acesso em: 8 nov. 2026.

SUPABASE. **Row Level Security**. Documentação, s.d. Disponível em: <https://supabase.com/docs/guides/database/postgres/row-level-security>. Acesso em: 8 nov. 2026.

TRASHNET. **Dataset and project documentation**. Repositório, commit `6fa2b878c6c1b4304b91109070ce0edf9279bb31`. Disponível em: <https://github.com/garythung/trashnet/tree/6fa2b878c6c1b4304b91109070ce0edf9279bb31>. Acesso em: 8 nov. 2026.

O manual 2026 não é incluído como referência consultada diretamente. Sua
identificação e o resumo recebido estão registrados no manifesto de evidências.
Revisar referências e citações segundo o modelo oficial antes da submissão.

## Apêndice A — código e autoria técnica

O código integral para auditoria é obtido do Git SHA congelado com a opção
`--code-appendix` do gerador. O ZIP contém fontes públicas, testes, migrações e
manifesto por arquivo; não contém contas, imagens, `.env`, Secrets, dados privados,
backups ou pesos ONNX. Não é pacote executável nem nova licença para o projeto.
Requer que o commit congelado esteja disponível no clone; um checkout raso pode
precisar de `git fetch origin 89622ec714b815c216a9215ab9ba69999b39c6b8`.

Trecho A1: orientação e conversão em `image_processing/image_io.py`, linhas 27–44;
trecho A2: Sobel em `image_processing/filters.py`, linhas 173–207;
trecho A3: Otsu em `segmentation/methods.py`, linhas 55–80;
trecho A4: normalização/inferência em `classification/semantic_onnx.py`, linhas 73–110.
As listagens e links imutáveis estão no índice. Os algoritmos conhecidos recebem
as referências acima; preencher contribuições individuais apenas com registros reais.

### load_rgb_image

Fonte: [src/ecoscan/image_processing/image_io.py:18](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/image_io.py#L18). Método/integração conforme atribuição no relatório.

```python
def load_rgb_image(
    path: str | Path,
    *,
    allowed_extensions: set[str] | frozenset[str],
    min_size: tuple[int, int],
) -> LoadedImage:
    info = validate_image_file(
        path,
        allowed_extensions=allowed_extensions,
        min_size=min_size,
    )
    with Image.open(info.path) as image:
        image = ImageOps.exif_transpose(image)
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            rgb = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            rgb = image.convert("RGB")
        array = np.asarray(rgb, dtype=np.uint8)
    return LoadedImage(info=info, array=array)
```

### _otsu_threshold

Fonte: [src/ecoscan/segmentation/methods.py:55](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/segmentation/methods.py#L55). Método/integração conforme atribuição no relatório.

```python
def _otsu_threshold(gray: np.ndarray) -> int:
    histogram = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    sum_total = np.dot(np.arange(256), histogram)

    sum_background = 0.0
    weight_background = 0.0
    best_variance = -1.0
    threshold = 0

    for level in range(256):
        weight_background += histogram[level]
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break

        sum_background += level * histogram[level]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = level
    return threshold
```

### image_features

Fonte: [src/ecoscan/classification/semantic_onnx.py:73](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/classification/semantic_onnx.py#L73). Método/integração conforme atribuição no relatório.

```python
def image_features(self, rgb):
        if rgb.shape != (224, 224, 3) or rgb.dtype != np.uint8:
            raise ValueError("Expected prepared RGB image")
        image = rgb.astype(np.float32) / 255.0
        image = (image - np.array([.48145466, .4578275, .40821073], dtype=np.float32)) / np.array(
            [.26862954, .26130258, .27577711], dtype=np.float32)
        with self.lock:
            feature = self.session.run(None, {"image": image.transpose(2, 0, 1)[None]})[0][0]
        return feature
```

## Apêndice B — ficha APS e revisão institucional

O arquivo [ficha preparatória](ficha_aps_preenchimento_privado.md) organiza campos
para preenchimento privado, sem datas, horas ou assinaturas inventadas. **Não é
o modelo oficial**. Quando o manual/ficha 2026 forem fornecidos, transcrever as
atividades comprovadas para o formulário institucional e validar identificação,+carga horária, assinatura, prazo e plataforma com a professora. Esta dependência
impede declarar a ficha final conforme o modelo oficial.
