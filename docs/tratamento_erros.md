# Tratamento de erros do EcoScan

O EcoScan usa um contrato central de erro para a interface, scripts e modo ao vivo. Cada falha conhecida deve ser apresentada com:

- código;
- título;
- mensagem amigável;
- ação recomendada;
- categoria;
- detalhe técnico controlado para log ou diagnóstico.

## Objetivo

Evitar que o usuário veja stack trace bruto e, ao mesmo tempo, manter evidência técnica suficiente para depuração e apresentação da APS.

## Categorias principais

| Prefixo | Área | Exemplo |
|---|---|---|
| `IMG` | validação de imagem | imagem vazia, corrompida, pequena ou em formato inválido |
| `MODEL` | modelo | baseline ou modelo final ausente |
| `PROC` | processamento | filtro indisponível por dependência opcional |
| `SEG` | segmentação | HSV/GrabCut indisponível sem OpenCV |
| `DATA` | dataset | classe inválida ou lote rejeitado |
| `CAM` | câmera | frame vazio, grande, incompleto ou webcam indisponível |
| `TRAIN` | treinamento | ambiente sem TensorFlow para modelo final |
| `CFG` | configuração | configuração inválida |
| `GUIDE` | descarte | orientação ambiental ausente |
| `IO` | arquivos | caminho inexistente ou permissão negada |
| `APP` | aplicação | erro inesperado ou parâmetro inválido |

## Onde aparece

- Interface principal: mensagens com código, explicação e ação recomendada.
- EcoScan Live: payload JSON estruturado para o navegador mobile.
- Scripts: saída de terminal sem stack trace bruto.
- Logs: detalhes técnicos ficam registrados em `logs/ecoscan.log`.
- Aceite: `scripts/run_acceptance_checks.py` valida o contrato de erro.

## Exemplo de payload público

```json
{
  "ok": false,
  "code": "IMG-001",
  "title": "Imagem inválida",
  "error": "A imagem enviada não pôde ser validada pelo EcoScan.",
  "message": "A imagem enviada não pôde ser validada pelo EcoScan.",
  "action": "Use uma imagem JPG, JPEG ou PNG legível, com boa resolução e um resíduo principal visível.",
  "category": "image"
}
```

O detalhe técnico só deve ser exibido quando a tela ou script estiver em contexto de diagnóstico.
