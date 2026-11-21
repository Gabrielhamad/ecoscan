# Candidata integrada — correções críticas da APS

Data de execução: **21/11/2026 UTC**. Base oficial:
`89622ec714b815c216a9215ab9ba69999b39c6b8`. Esta branch é uma candidata de revisão;
o SHA final e sua CI ficam registrados no PR. Não foi publicada como release.

## Escopo e origem

Esta unidade consolida os reparos necessários para o fluxo assistido continuar
útil quando o modelo, arquivo ou apresentação de evidências falhar:

| Origem | Integração |
| --- | --- |
| PR #21, `504685a9382675c5201960eb931c9a518062ec1b` | Trilhas PDI/reconhecimento, contrato verificado e testes de invariância |
| PR #26, `91b985e6e96e90e3de0f711f15e98829822226ac` | Recuperação pública, confirmação manual independente, limites de upload e sanitização |
| PR #29, `6e6918cb291a60249897a5b8ca4b929580a7fd15` | Somente correção do cache frio e testes de relógio/revogação; não inclui o empacotador |
| Auditoria #31 | Corrige inventário `AC-10`, cobre falha do segundo renderer e disponibiliza consulta na aba Descarte |

O conflito em `analysis_service.py` foi resolvido mantendo as duas garantias:
validar checksum/perfil **antes da predição** e preservar o pipeline no fallback
público. `allow_model_fallback=False` continua sendo o padrão estrito para CLIs;
a UI habilita a recuperação e recebe um resultado sem classe/aceitação automática.
Um modelo incompatível não executa `predict_image`, mesmo quando há fallback.

`diagnostic_processing` conserva os filtros/máscaras escolhidos e as evidências;
`recognition_preparation` usa o perfil oficial RGB 224×224, seu contrato e checksum.
Mudar o laboratório reexecuta o PDI e invalida a confirmação anterior sem trocar
silenciosamente o RGB oficial. A máscara continua diagnóstica.

A consulta humana foi compartilhada entre Escanear e Descarte, sem duplicar as
regras ambientais. Ela funciona sem imagem/modelo/banco. Hipótese do modelo,
material confirmado pela pessoa e destinação continuam mensagens distintas.
Pilhas/eletrônicos seguem coleta especial. Uma foto não comprova composição,
conteúdo ou contaminação.

O boundary público usa mensagens estáticas do catálogo e logs com tipo/código/
categoria; não renderiza exceção bruta ou traceback. Isso não certifica todas
as telas privadas. Dois renderers opcionais foram protegidos: uma falha ao
mostrar/exportar PDI não impede chegar à escolha manual.

O inventário legado agora declara `release_acceptance="not_approved"` e mantém
`AC-10=pending` com ou sem artefato. A correção de cache aplica TTL somente a
chaves existentes, preservando verificação de consentimento/revogação.

## Evidências antes/depois

Foram instaladas dependências em venv novo Python 3.12.14; versões resolvidas em
[verification.json](integration/verification.json). Não houve mudança das
dependências declaradas. O snapshot de versões não é um lock de deploy.

Na baseline, a suíte existente passou com **496 testes e 108 subtestes**; as
sondas da auditoria #31 reproduziram **21 PASS, 5 FAIL e 6 BLOCKED**, incluindo
ONNX CPU real em fixture técnica. Não foi preciso inventar um defeito para corrigir.

| Achado da baseline | Evidência da candidata | Resultado técnico |
| --- | --- | --- |
| Filtro didático altera RGB/contrato | `test_processing_tracks.py`, 36 combinações em `test_integrated_recognition_flow.py`; dois ZIPs baixados no browser | PASS: RGB, contrato e decisão invariantes; saída didática muda |
| Falha do modelo impede correção | Loader com encoder realmente ausente em pasta isolada + AppTest; testes de load/inferência/rede com stubs | PASS: PDI preservado e consulta humana disponível; CLI permanece estrita |
| Upload inválido/aba Descarte sem consulta | `test_public_resilience.py` e smoke B01–B04 | PASS: arquivo recusado, consulta manual e coleta especial disponíveis |
| Exceção bruta chega à UI/log | Marcadores exclusivamente sintéticos e captura de logs/mocks | PASS: mensagem privada não chega à UI/log do boundary |
| Cache vazio respeita TTL indevidamente | Relógios 0/5/100 s, revogação e falha/expiração 0/30/61 s | PASS: primeira consulta ocorre; falha expira sem servir release revogada |
| Inventário aceita modelo pela presença | Modelo presente/ausente e JSON gerado | PASS: gate permanece pending; inventário não aprova release |
| Exportação opcional pode bloquear confirmação | Antes: **1 FAIL / 1 PASS** ao injetar falhas nos dois renderers; depois ambos passam | PASS: erro sanitizado e seletor preservado |

As fixtures validam contratos e recuperação, **não acurácia de campo**.
Ruff, pytest completo, pip check, testes específicos e nove cenários de Chromium
local foram executados; contagens e comandos constam no JSON e no PR. O smoke
inclui download de dois ZIPs pela UI, troca de filtro, reset de confirmação,
navegação, nova foto e query que não concede acesso de gestão.

O exportador oficial também produziu 22 artefatos mais `reproduction.json`, a
partir da mesma execução técnica. PNGs/ZIPs e logs brutos ficaram fora do Git.
Não há máscara humana: não se relata IoU/Dice real. A avaliação histórica foi
recalculada: **101/145 top-1, 51 aceitos pelo artefato, 47 corretos, 4 incorretos,
94 rejeitados**, `independent_test=false`. Pesos, contrato, encoder, limiar 0,8 e
`confirmation_required=true` permanecem inalterados; não há alegação de ganho ML.

## Reprodução

```bash
python -m pip install -e '.[dev]'
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python -m pytest tests/test_processing_tracks.py tests/test_public_resilience.py tests/test_integrated_recognition_flow.py tests/test_delivery_pack.py tests/test_published_model.py -q
```

Para o browser opcional, instalar Playwright **fora do runtime de deploy**, usar
Chromium local e iniciar o Streamlit desta candidata em `127.0.0.1:8519`, com
Secrets deliberadamente vazio e `ECOSCAN_*` herdados removidos. Desligar os stores
opcionais; não usar credenciais ou contas reais. A configuração oficial permite
modelo remoto: só `ECOSCAN_REMOTE_MODELS=false` não substitui esse booleano;
o perfil de teste também deve ter Secrets vazio para impedir store remoto.

```bash
python docs/integration/smoke_browser.py --url http://127.0.0.1:8519 --chromium /usr/bin/chromium --output reports/integration/browser.json
```

O script recusa URL de produção, usa contexto novo e bloqueia requests externos
do browser. `--no-sandbox` é específico do Chromium no container de QA. Não é
configuração do app publicado. Rede nativa do ONNX/SO não foi monitorada; não se
declara validação de operação integralmente offline ou disponibilidade de mapas.

## Próximo gate e rollback

O aceite estrito continua retornando **2**: 12 ok, 4 attention, 5 pending.
QA-09/QA-18..QA-21 não foram aprovados. Banco indisponível/identidades têm testes
com stubs; PostgreSQL 16 é repetido no banco descartável da CI do PR, não em
produção. Não há novas fotos reais consentidas/proveniência auditada fornecidas,
telefone/PC de apresentação, smoke publicado ou três ensaios cronometrados.
Esses itens permanecem **manual_pending/BLOCKED**. Não se alteraram contas,
migrações, configuração, segredos, modelo publicado ou deployment.

Os demais PRs continuam separados: motor assertivo #24, avaliação/experimentos,
hardening/locks #27 e pacotes acadêmico/executável ainda exigem revisão própria.
Não importar automaticamente suas conclusões nem marcar todos os PRs integrados.
Antes de release: revisão e CI deste SHA, evidências reais/ensaios e aceite do
responsável. O veredito de **release continua NO-GO**; os reparos técnicos desta
candidata não substituem evidência externa.

Rollback: reverter esta unidade por PR e repetir checks; sem migração ou troca
de pesos. Encerrar somente o servidor local criado para o teste e remover apenas
cache/outputs derivados de QA. Não apagar dados ou fotos preexistentes do grupo.
