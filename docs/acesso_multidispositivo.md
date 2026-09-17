# Acesso multidispositivo do EcoScan

Este guia organiza o uso do EcoScan em PC, celular na mesma rede e publicacao web com HTTPS.

## 1. Uso mais simples no computador

```powershell
python scripts\ecoscan_access.py --restart
```

Ou execute:

```powershell
.\run_ecoscan_rede.ps1
```

O script inicia o app principal e o EcoScan Live, valida os servicos e imprime links de usuario, admin e camera.

## 2. Links no computador

```text
http://localhost:8501/?profile=usuario_demo
http://localhost:8501/?profile=admin_secretaria
http://localhost:8765/
```

## 3. Links no celular ou outro PC da mesma rede

O IP muda de acordo com a rede. Nao copie link antigo. Rode:

```powershell
python scripts\ecoscan_access.py --check-only
```

Use o IP exibido pelo script:

```text
http://SEU-IP:8501/?profile=usuario_demo
http://SEU-IP:8501/?profile=admin_secretaria
http://SEU-IP:8765/
```

Se nao abrir no celular:

- confirme que celular e computador estao no mesmo Wi-Fi;
- desative VPN no celular e no PC durante o teste local;
- permita Python/Streamlit no Firewall do Windows;
- rode o launcher com `--restart` para limpar processos antigos.

## 4. Camera no celular

Upload de imagem funciona em HTTP na rede local. Ja a camera ao vivo depende do navegador.

Navegadores moveis normalmente so liberam camera em contexto seguro:

- `localhost` no proprio aparelho;
- HTTPS publico;
- tunel HTTPS;
- certificado local confiavel.

Por isso, para demonstracao em sala sem HTTPS, use o fluxo de upload/foto rapida no app principal. Para uso real por todos, publique em HTTPS.

## 5. Publicacao web para todos

Para acesso independente de celular, PC e rede local, publique o app principal em uma plataforma HTTPS, como Render, Railway, Hugging Face Spaces, Streamlit Community Cloud ou um servidor Docker.

Arquivos ja preparados:

- `Procfile`
- `runtime.txt`
- `Dockerfile`
- `.streamlit/config.toml`

Com Docker:

```powershell
docker build -t ecoscan .
docker run --rm -p 8501:8501 ecoscan
```

Em plataformas com `PORT`, o `Procfile` usa a porta fornecida automaticamente.

## 6. URL externa da camera ao vivo

Se o EcoScan Live for publicado em outra URL HTTPS, configure:

```powershell
$env:ECOSCAN_LIVE_URL="https://sua-url-live.exemplo/"
python scripts\run_streamlit_app.py
```

Assim o botao de camera ao vivo dentro do app aponta para a URL publica correta.

## 7. Teste remoto com o grupo

Para organizar testes com colegas em lugares diferentes, use o roteiro em `docs/teste_remoto_grupo.md`.

O app também possui um formulário de correção após a análise. Quando o reconhecimento errar, o colega pode informar a classe correta; a imagem e os metadados ficam salvos em:

```text
reports/recognition_feedback/feedback.csv
reports/recognition_feedback/images/
```
