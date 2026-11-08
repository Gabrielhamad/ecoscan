# EcoScan — executar a demonstração APS

Requer **Python 3.12** e navegador. O programa é Streamlit; não é necessário `.exe`.

Se recebeu o ZIP de revisão, compare `SHA256SUMS` com o checksum fornecido pelo
grupo, extraia em pasta gravável e siga seu `README_EXECUCAO.md`. O manifesto
identifica o SHA completo do programa, o empacotador, o lock e todos os arquivos.
Um pacote de revisão não comprova aceite nem teste em equipamento real.

Para um clone de desenvolvimento:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_delivery_demo.py verify
python -m pip check
python scripts/run_delivery_demo.py serve
```

No Windows, crie o ambiente com `py -3.12 -m venv .venv`, ative com
`.venv\Scripts\activate.bat` e use os mesmos comandos Python. Depois da instalação,
`run_ecoscan_rede.bat` ou `run_ecoscan_rede.ps1` também iniciam o app. O clone usa
os intervalos do `pyproject.toml`; o ZIP revisável exige lock exato com hashes.

Abra <http://localhost:8501>. Use `--port 8510` se a porta estiver ocupada.
`--lan` permite acesso pela rede da apresentação, somente quando autorizado.
Ctrl+C encerra esta instância; o launcher não mata outros processos nem inicia
o servidor Live separado. O encoder é reunido dos shards e verificado por SHA-256.

O perfil local ignora Secrets globais e variáveis `ECOSCAN_*` herdadas: demonstração
como visitante, sem banco nem substituição remota do modelo. Nenhuma credencial é
necessária. Confirme o material para consultar o destino; a foto não comprova
composição ou conteúdo. Mapas/CEP e a instalação inicial precisam de Internet.

Antes de apresentar, executar no **computador da apresentação**: abertura, upload
de foto autorizada, análise, confirmação/correção, orientação e reabertura sem rede.
Registrar data, SHA, Python, dispositivo, navegador, resultado e evidência sem PII.
Windows, câmera física e fotos reais não são aprovados por smoke Linux ou CI.

[Preparação, exclusões, exemplos autorizados e gates de release](docs/pacote_execucao_aps.md).
Rollback local: Ctrl+C e abrir o pacote anterior identificado por SHA; preservar
Secrets, imagens originais, evidências e banco.
