# Teste remoto do EcoScan pelo grupo

Este guia define como colegas podem testar o EcoScan em celular ou PC e como transformar erros de reconhecimento em dados úteis para melhorar o modelo.

## 1. Quando todos estão na mesma rede

Use o launcher local:

```powershell
python scripts\ecoscan_access.py --restart
```

Compartilhe o link exibido em "Celular ou outro PC na mesma rede Wi-Fi":

```text
http://SEU-IP:8501/?profile=usuario_demo
```

Esse link só funciona para aparelhos conectados ao mesmo Wi-Fi do computador que está rodando o sistema.

## 2. Quando cada pessoa está em um lugar diferente

O IP local, como `192.168.x.x`, não abre fora da sua rede. Para colegas em outras casas, faculdade ou trabalho, existem duas opções.

### Opção A: túnel HTTPS temporário

Use quando quiser testar rápido e manter os registros no seu computador.

1. Rode o EcoScan:

```powershell
python scripts\ecoscan_access.py --restart
```

2. Abra um túnel HTTPS apontando para a porta `8501`, por exemplo com Cloudflare Tunnel ou ngrok:

```powershell
cloudflared tunnel --url http://localhost:8501
```

ou:

```powershell
ngrok http 8501
```

3. Compartilhe a URL `https://...` gerada pelo túnel.

Essa opção costuma funcionar melhor para câmera no celular porque navegadores móveis exigem HTTPS para liberar câmera.

Para o EcoScan Live, crie outro túnel para a porta `8765` e configure:

```powershell
$env:ECOSCAN_LIVE_URL="https://URL-DO-LIVE/"
python scripts\ecoscan_access.py --restart
```

### Opção B: publicação web HTTPS

Use quando quiser um link mais estável para várias pessoas.

O projeto já possui arquivos de deploy:

- `Procfile`;
- `runtime.txt`;
- `Dockerfile`;
- `.streamlit/config.toml`.

Pode publicar em uma plataforma HTTPS compatível com Streamlit ou Docker. Atenção: em muitas plataformas gratuitas, arquivos gerados em `reports/` podem ser apagados quando o serviço reinicia. Para coletar feedback de forma segura, prefira túnel no seu computador ou configure armazenamento persistente.

## 3. Como cada colega deve testar

Peça para cada pessoa:

1. Abrir o link de usuário.
2. Tirar ou enviar uma foto real do resíduo.
3. Observar a classe prevista, confiança, filtro, segmentação e mapa de detecção.
4. Se estiver errado, abrir "O reconhecimento errou? Enviar correção para melhorar o modelo".
5. Informar a classe correta e uma observação simples.

Exemplo de observação:

```text
Era uma lata de refrigerante em cima da mesa, luz baixa. O app indicou vidro.
```

## 4. Onde os erros ficam salvos

As correções ficam em:

```text
reports/recognition_feedback/feedback.csv
reports/recognition_feedback/images/
```

Esse material deve ser revisado antes de ir para o dataset final. Imagens corrigidas podem ser copiadas para `data/raw/<classe>` ou para a fila de curadoria.

## 5. Regra de qualidade dos testes

Para melhorar o reconhecimento, o grupo deve buscar variação real:

- celular diferente;
- luz forte, luz fraca e sombra;
- fundo claro e fundo escuro;
- objeto perto e longe;
- objeto em pé, deitado e parcialmente amassado;
- resíduos limpos e usados;
- mais de uma marca e cor por tipo de resíduo.

O objetivo não é só acertar exemplos fáceis. O melhor teste é encontrar onde o sistema erra, registrar a classe correta e usar isso na próxima rodada de curadoria e treino.
