# Smoke da versão publicada — evidências e pendências

Data de preparação: 2026-11-08T20:02:13+00:00
Candidato: `89622ec714b815c216a9215ab9ba69999b39c6b8`.
URL: https://ecoscan-gabrielhamad.streamlit.app

**Sem aprovação formal automática. QA-09 e QA-18..QA-21 continuam manual_pending neste relatório.**
HTTP 200, fixtures, emulação e CI não comprovam o SHA publicado, contas, telefone real ou acurácia independente.

| Caso | Dispositivo / papel | Ambiente | Cenário | Estado / motivo | Execução / SHA observado | Navegador | Evidência |
| --- | --- | --- | --- | --- | --- | --- | --- |
| http | Codex Linux / visitor | published | Verificar resposta HTTP; não comprova renderização ou SHA. | passed / — | 2026-11-08T19:55:49+00:00 / não comprovado | HTTP 3.12.14 | EVID-001 (technical_http) |
| browser | Codex Linux / visitor | published | Abrir sessão anônima; verificar renderização, sem login nem dados reais. | manual_pending / browser_tls_error | tentativa 2026-11-08T19:55:53+00:00 / não comprovado | Chromium 156.0.8078.79 | EVID-002 (technical_browser) |
| published_sha | PC / operator | published | Conferir SHA completo no provedor/runtime e comparar com candidato; prefixo ou CI não bastam. | manual_pending / revision_unverified | não executado / não comprovado | —  | — (pendente) |
| published_model | PC / operator | published | Conferir hashes do modelo efetivamente carregado, inclusive override remoto e contrato. | manual_pending / runtime_model_unverified | não executado / não comprovado | —  | — (pendente) |
| local_model | Codex Linux / fixture | local_fixture | Verificar configuração, cabeça e montagem dos shards locais; não atesta deployment. | passed / — | 2026-11-08T20:02:13+00:00 / não comprovado | Python 3.12.14 | EVID-003 (technical_local) |
| local_error_privacy | Codex Linux / fixture | local_fixture | Usar marcador sintético para verificar se a fronteira de erro repassa detalhe bruto à UI/log; não é incidente observado em produção. | failed / raw_exception_exposed | 2026-11-08T20:02:13+00:00 / não comprovado | Python 3.12.14 | EVID-005 (technical_local) |
| local_rls | CI PostgreSQL 16 / fixture | local_fixture | Executar fixtures/RLS/permissões em PostgreSQL 16 descartável, sem dados reais. | manual_pending / not_executed | não executado / não comprovado | —  | — (pendente) |
| pc_visitor | PC / visitor | published | Abrir como visitante; navegar sem gestão/conta alheia e sem enviar contribuição. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| pc_capture | PC / visitor | published | Capturar/enviar foto real autorizada; conferir EXIF e alternativa após negar câmera. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| pc_analysis | PC / visitor | published | Analisar foto real; separar hipótese, rejeição, confirmação humana e limites do reconhecimento. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| pc_disposal | PC / visitor | published | Corrigir material; conferir lixeira/ponto e orientação especial de pilhas/eletrônicos. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| pc_accounts | PC / controlled_A_B | published | Com autorização, entrar A/B em sessões separadas; B não acessa protocolos/fotos/respostas de A. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| pc_analyst | PC / controlled_analyst | published | Com autorização, validar analista na allowlist e negar gestão a visitante/B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| pc_reopen | PC / controlled_A_B | published | Persistir evidência consentida de A; reabrir/login/recarregar, revisar e conferir isolamento em B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| android_visitor | Android / visitor | published | Abrir como visitante; navegar sem gestão/conta alheia e sem enviar contribuição. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| android_capture | Android / visitor | published | Capturar/enviar foto real autorizada; conferir EXIF e alternativa após negar câmera. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| android_analysis | Android / visitor | published | Analisar foto real; separar hipótese, rejeição, confirmação humana e limites do reconhecimento. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| android_disposal | Android / visitor | published | Corrigir material; conferir lixeira/ponto e orientação especial de pilhas/eletrônicos. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| android_accounts | Android / controlled_A_B | published | Com autorização, entrar A/B em sessões separadas; B não acessa protocolos/fotos/respostas de A. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| android_analyst | Android / controlled_analyst | published | Com autorização, validar analista na allowlist e negar gestão a visitante/B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| android_reopen | Android / controlled_A_B | published | Persistir evidência consentida de A; reabrir/login/recarregar, revisar e conferir isolamento em B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| iphone_visitor | iPhone / visitor | published | Abrir como visitante; navegar sem gestão/conta alheia e sem enviar contribuição. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| iphone_capture | iPhone / visitor | published | Capturar/enviar foto real autorizada; conferir EXIF e alternativa após negar câmera. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| iphone_analysis | iPhone / visitor | published | Analisar foto real; separar hipótese, rejeição, confirmação humana e limites do reconhecimento. | manual_pending / no_real_photo | não executado / não comprovado | —  | — (pendente) |
| iphone_disposal | iPhone / visitor | published | Corrigir material; conferir lixeira/ponto e orientação especial de pilhas/eletrônicos. | manual_pending / no_device | não executado / não comprovado | —  | — (pendente) |
| iphone_accounts | iPhone / controlled_A_B | published | Com autorização, entrar A/B em sessões separadas; B não acessa protocolos/fotos/respostas de A. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| iphone_analyst | iPhone / controlled_analyst | published | Com autorização, validar analista na allowlist e negar gestão a visitante/B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| iphone_reopen | iPhone / controlled_A_B | published | Persistir evidência consentida de A; reabrir/login/recarregar, revisar e conferir isolamento em B. | manual_pending / no_authorized_account | não executado / não comprovado | —  | — (pendente) |
| database_outage | PC / controlled_A_B | isolated_copy | Simular erro de banco somente em cópia isolada; nenhuma gravação incerta deve virar sucesso/reenvio automático. | manual_pending / isolated_environment_required | não executado / não comprovado | —  | — (pendente) |
| recovery | PC / operator | isolated_copy | Ensaiar reabertura/rollback/restore somente em cópia descartável autorizada; nunca produção. | manual_pending / isolated_environment_required | não executado / não comprovado | —  | — (pendente) |
| independent_recognition | PC / operator | field_evaluation | Exigir avaliação independente por classe e proveniência auditada; smoke, fixtures e CI não aprovam reconhecimento. | manual_pending / independent_evidence_required | não executado / não comprovado | —  | — (pendente) |

## Fingerprint local do candidato (não é leitura do deployment)

```json
{
  "scope": "local_candidate_only_not_deployment",
  "configured_artifact": "models/semantic-v1/semantic.json",
  "metadata_sha256": "5821ecf3ccc4e5b7dd807cab74978df14aae6e82a2360c765c7232bdf1fa75f2",
  "head_sha256": "5cc1aa6b5ee4d0e0ed74bca37a8510802f739b61c5e179165beae15c68e8386a",
  "encoder_sha256": "dfad0c5b643cc67908fbfc88b7ba5ecad10aa6567cc72bfced3a759baaf509bd",
  "processing_sha256": "2a1a47bad72255684a7a33a3f038d6b622f120ff5ee10c6597734e27fa46a61d",
  "threshold": 0.8,
  "shards_verified": 3,
  "remote_override_enabled": true,
  "confirmation_required": true
}
```

Referências EVID-001 são aliases para evidência anonimizada revisada pelo grupo. Não são protocolos, contas ou links assinados.
Não executar indisponibilidade, migrations de fixture ou restore em produção. Contas A/B/analista exigem autorização explícita.
