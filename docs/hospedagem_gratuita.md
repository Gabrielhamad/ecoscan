# Hospedagem gratuita do EcoScan

Este guia descreve o caminho recomendado para publicar o EcoScan sem custo para testes do grupo e uso demonstrativo.

## Decisão recomendada

Use o Streamlit Community Cloud para a primeira publicação gratuita.

Motivos:

- o projeto já é uma aplicação Streamlit;
- a publicação gera URL HTTPS no domínio `streamlit.app`;
- HTTPS ajuda no uso pelo celular e nas permissões de câmera do navegador;
- a atualização acontece a partir do GitHub;
- é suficiente para demonstração, testes em grupo, coleta de feedback e apresentação da APS.

## Arquivos preparados

- `streamlit_app.py`: entrada raiz para deploy.
- `requirements.txt`: dependências Python para servidor sem tela.
- `runtime.txt`: Python 3.12.
- `.streamlit/config.toml`: configuração Streamlit.
- `models/vision_classifier.npz`: modelo visual leve para reconhecimento inicial.
- `models/baseline_classifier.json`: modelo reserva.

Não suba o dataset inteiro para o GitHub. As pastas `data/raw`, `data/curated`, `data/processed`, `data/train`, `data/validation` e `data/test` devem continuar fora do repositório público.

## Passo a passo

1. Criar um repositório no GitHub para o EcoScan.
2. Subir o código do projeto para esse repositório.
3. Conferir se `streamlit_app.py`, `requirements.txt`, `runtime.txt`, `.streamlit/config.toml` e os modelos leves foram enviados.
4. Entrar em `https://share.streamlit.io`.
5. Criar um novo app.
6. Selecionar o repositório, a branch principal e o arquivo `streamlit_app.py`.
7. Configurar login e administradores conforme `docs/autenticacao.md`, usando o painel Secrets. Sem essa configuração, o app oferece apenas acesso público.
8. Compartilhar a URL `https://NOME-DO-APP.streamlit.app` com o grupo.

## Como o grupo deve testar

- Abrir a URL no celular ou PC.
- Usar o perfil de usuário para enviar imagem ou tirar foto.
- Registrar quando o reconhecimento errar.
- Testar materiais prioritários: plástico, metal, vidro, papel/papelão, pilha, eletrônico, lâmpada, óleo, aerosol, remédio e embalagem química.
- No admin, acompanhar a qualidade do reconhecimento, testes de campo e governança do modelo final.

## Limitações do gratuito

- O modo principal com foto/upload funciona melhor para a publicação gratuita.
- O EcoScan Live em tempo real usa outro servidor na porta `8765`; ele continua adequado para rede local, mas não deve ser tratado como disponível automaticamente no Streamlit Cloud.
- Registros gravados em `reports` na nuvem podem ser temporários. Para uso sério, exporte os dados ou conecte uma base externa.
- A preparação dos arquivos não comprova implantação concluída: validar login, permissões e persistência na URL publicada.
- O reconhecimento atual continua orientativo até o dataset final ser curado e o modelo definitivo passar por avaliação comparativa.

## Comando local de checagem

```powershell
python scripts\check_deployment_ready.py
```

O relatório será gerado em:

```text
reports/deployment_readiness/hospedagem_gratuita.md
```
