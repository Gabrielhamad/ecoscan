# Fluxo público: validação técnica e tolerância a falhas

Referência: `main` `89622ec714b815c216a9215ab9ba69999b39c6b8`, conferido em
08/11/2026. Prompt 07; SHA final e CI registrados no PR da etapa.

## Problemas reproduzidos e correções

Antes da alteração, dois testes de regressão falharam: o estado vazio não
oferecia seleção manual e `_render_user_error` incluía o texto original da
exceção tanto no log quanto no detalhe da UI. O teste usou identificadores
fictícios para verificar caminhos, token, e-mail e protocolo sem dados reais.

O reconhecimento era uma etapa obrigatória após PDI: uma falha de carregamento
ou inferência propagava a exceção e impedia retornar o processamento. A chamada
estrita continua com esse comportamento para avaliação offline; apenas a UI
opta por `allow_model_fallback=True`. Nesse modo, uma falha na etapa de
reconhecimento retorna o PDI real com modelo indisponível, sem hipótese,
pontuação, aceitação, orientação automática ou compatibilidade presumida.
Imagem inválida continua sendo recusada antes desse fallback.

| Cenário | Comportamento e evidência |
| --- | --- |
| Sem foto/câmera indisponível | Consulta manual permanece disponível; instrução para usar Enviar foto/Galeria |
| Upload inválido/vazio/extensão indevida | Mensagem pública estável, sem exceção crua; seleção manual continua funcionando |
| Arquivo acima de 15 MB | Limite no uploader e preflight antes de copiar os bytes; teste comprova ausência da leitura |
| Mais de 40 milhões de pixels | Gate existente recusa antes da decodificação RGB; integração preserva consulta manual |
| EXIF de rotação | Pixels orientados preservados, inclusive quando o modelo falha |
| Falha de carga/inferência/rede do modelo | `model_unavailable`; PDI preservado e botão Analisar novamente; serviço estrito permanece estrito |
| Contrato incompatível | Melhor hipótese explicitamente rotulada; confirmação automática não é liberada |
| Correção humana | “Material confirmado por você” e destino da categoria selecionada; não altera a hipótese do modelo |
| Pilhas/baterias/eletrônicos | Destino especial das regras existentes; seleção humana continua obrigatória |
| Nova foto | Limpa captura, resultado e confirmação anterior; preserva identidade e histórico |
| Reexecução/navegação | Reutiliza análise da mesma entrada; preserva escolha humana e tempo medido |
| Banco indisponível durante contribuição | Envio não confirmado; consultar protocolos antes de reenviar; sem retry automático e sem bloquear descarte |
| Dados locais de orientação ausentes | Estado vazio explícito, sem destino inventado ou erro de chave |

A UI diferencia hipótese automática, material selecionado pela pessoa e
orientação ambiental. A melhor correspondência não afirma composição, limpeza
ou conteúdo. Tempos só aparecem quando registrados pelo serviço, para a execução
inteira de processamento e tentativa de reconhecimento; não são benchmark de
latência nem confiança estatística.

Falhas são registradas com evento, código, contexto, categoria e tipo de erro.
A UI não escreve texto de exceção nem traceback nos logs dessa fronteira.
Payloads de erro guardados na sessão são públicos e não contêm detalhe técnico.
A seleção manual funciona com os arquivos locais de referência, sem banco;
mapas externos e consultas de CEP precisam de internet. Streamlit continua
precisando de conexão entre navegador e servidor: este trabalho não cria PWA
offline nem promete novas interações durante desconexão do websocket.

`navigation_controller.py` e `analysis_widgets.py` foram revisados; suas
responsabilidades e a navegação por papel foram preservadas. A montagem contínua
do widget de foto foi mantida. Autenticação, layout/CSS, pesos, limiares globais
e preparação do classificador não foram alterados.

## Execuções

Em Python 3.12:

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

Resultado local: **Ruff passou; 516 testes e 108 subtestes passaram; pip check
sem requisitos quebrados**. Vinte casos novos em `test_public_resilience.py`
utilizam pixels sintéticos e stubs de serviços; não medem acurácia de campo.
Os testes de recibo e importação leve existentes continuam passando.

Smoke real com Chromium instalado e Playwright 1.64.1, viewport **390×844**,
app completo em servidor local, visitante, sem banco de produção:

1. Estado vazio → seleção manual de vidro → lixeira verde.
2. PNG corrompido → erro IMG-001 → seleção manual de metal → lixeira amarela.
3. PNG sintético válido → ONNX local executado, hipótese exibida sem aceitação
   automática → correção humana para vidro. Nenhum acerto de campo foi inferido.
4. Mapa → Escanear: foto, escolha humana e tempo medido preservados.
5. Nova foto: upload, resultado e confirmação limpos.

**Passou, sem `stException` ou `pageerror`.** O ONNX local retornou
`accepted=False`; a imagem sintética serviu apenas para exercitar a interface.
O cache de montagem do encoder criado no smoke foi removido; nenhum arquivo de
modelo foi incluído na mudança. Playwright foi instalado apenas no ambiente de
teste, sem nova dependência de runtime.

## Gate manual que continua pendente

Não foram testados celular físico, permissão real de câmera, modo do seletor
nativo, banco de produção, rede móvel instável nem fotos reais de sustentabilidade.
Para validar no equipamento de apresentação:

1. Negar permissão da câmera e confirmar alternativa Galeria/Enviar foto e
   consulta manual; depois autorizar e capturar foto real consentida.
2. Testar JPG com EXIF, PNG, reenvio, foto grande e upload corrompido; conferir
   orientação, erro acionável e ausência de confirmação anterior na nova foto.
3. Navegar Escanear → Mapa → Escanear e confirmar preservação da sessão.
4. Interromper rede do aparelho: conferir aviso do Streamlit; restaurar conexão
   e verificar resultado/seleção. Não prometer interação enquanto desconectado.
5. Com conta autorizada em ambiente de teste, provocar timeout de banco durante
   contribuição; conferir protocolos antes de reenviar. Sem escrita em produção.

Rollback: reverter o PR; não há migração, mudança de autenticação, troca de modelo
ou modificação de dados de produção. Risco principal: novos estados de sessão e
novos controles de captura; os testes cobrem invalidação e preservação de identidade.
