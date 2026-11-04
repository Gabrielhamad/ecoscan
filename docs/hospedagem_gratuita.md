# Hospedagem no Streamlit Cloud

## Arquivos necessários

- `streamlit_app.py`;
- `requirements.txt` e `runtime.txt`;
- `.streamlit/config.toml`;
- `config/`, `assets/` e `src/`;
- `models/semantic-v1/`, incluindo licença e hashes.

O dataset bruto, Secrets, logs e fotos privadas não pertencem ao Git.

## Publicação

1. Conecte `Gabrielhamad/ecoscan` no Streamlit Community Cloud.
2. Selecione `main` e `streamlit_app.py`.
3. Cadastre Secrets conforme `.streamlit/secrets.example.toml`.
4. Aguarde a CI do mesmo hash.
5. Teste visitante, participante e gestão no URL público.

O modo de câmera ao vivo usa um servidor separado. No deploy gratuito, use a captura estática do Streamlit ou upload.

O encoder aumenta o tempo de clone e build. A migração para storage versionado está no [roadmap](roadmap_entrega.md), condicionada a checksum, cache e rollback validados.
