# Tratamento de erros

O contrato público central fica em `src/ecoscan/errors.py`. Erros conhecidos recebem código, mensagem simples, ação recomendada e categoria; detalhes técnicos ficam nos logs.

| Prefixo | Área | Exemplo |
| --- | --- | --- |
| `IMG` | imagem | arquivo vazio, corrompido ou pequeno |
| `MODEL` | reconhecimento | release ausente, incompatível ou corrompida |
| `PROC` | processamento | filtro indisponível |
| `SEG` | segmentação | método indisponível |
| `DATA` | dataset | classe ou lote inválido |
| `CAM` | câmera | frame vazio ou grande |
| `CFG` | configuração | configuração inválida |
| `GUIDE` | descarte | orientação ausente |
| `IO` | arquivos | caminho ou permissão inválida |
| `APP` | aplicação | falha inesperada |

A interface não deve exibir stack trace, token, caminho privado ou registro pessoal. Logs precisam seguir a mesma regra e ser persistidos fora do filesystem efêmero na operação pública.
