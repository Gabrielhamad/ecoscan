# Recicla SP · EcoScan

[![Qualidade](https://github.com/Gabrielhamad/ecoscan/actions/workflows/quality.yml/badge.svg)](https://github.com/Gabrielhamad/ecoscan/actions/workflows/quality.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg)](runtime.txt)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.66%2B-FF4B4B.svg)](https://ecoscan-gabrielhamad.streamlit.app)

Aplicação de educação ambiental que analisa uma foto, sugere o material e orienta o descarte. O produto combina processamento de imagens, reconhecimento assistido, mapa de coleta, conteúdo educativo, missões e uma área de gestão.

**Aplicação:** https://ecoscan-gabrielhamad.streamlit.app

**Autoria acadêmica:** identificada pelos nomes completos dos integrantes na capa
e nos elementos pré-textuais da APS. O identificador da conta GitHub é apenas o
endereço técnico do repositório; não substitui nomes de autores nem deve ser
tratado como referência autoral de conceitos científicos. Consulte
[Registro de autoria e contribuições](docs/autoria_aps.md).

## Estado da entrega

O fluxo web, a autenticação, o processamento de imagens e o reconhecedor ONNX estão implementados e cobertos por testes automatizados. A interface exibe o material sugerido e a cor do coletor padronizada; a pessoa confirma a classe para obter instruções completas. Percentuais da classificação permanecem restritos à avaliação técnica.

| Área | Estado | Observação |
| --- | --- | --- |
| Interface pública | Pronta para piloto | Câmera, upload, mapa, descarte e educação |
| Gestão | Pronta para piloto controlado | Revisões, campanhas, protocolos e indicadores |
| Reconhecimento | Assistido | Uma única release ONNX; confirmação obrigatória |
| Persistência | Condicional | Requer Supabase e migrações configuradas |
| Operação pública | Piloto validado | Jornada pública e contas verificadas em 04/11; continuidade operacional ainda em validação |

**Parecer de 07/11/2026:** candidato técnico à entrega acadêmica; a aprovação formal depende de aceite do SHA publicado, pacote de autoria/APS e release versionada. A última CI do commit `04c1a34` passou com 496 testes e 108 subtestes. [Parecer de prontidão](docs/parecer_prontidao_2026-11-07.md) · [Roadmap por marcos](docs/roadmap_entrega.md) · [Plano de gestão](docs/gestao_projeto.md).

## Escopo do reconhecimento

O modelo trabalha com seis materiais:

- plástico, com prioridade para garrafas PET e recipientes rígidos;
- metal, com prioridade para latas de bebida e conserva;
- vidro, com prioridade para garrafas e potes;
- papel e papelão;
- pilhas domésticas;
- pequenos eletrônicos.

Metal, plástico e vidro são as classes prioritárias do piloto. Alimentos, orgânicos, medicamentos e óleo não são identificados automaticamente.

## Arquitetura atual

```mermaid
flowchart LR
    UI[Streamlit] --> AS[Serviço de análise]
    AS --> PP[Pipeline RGB]
    PP --> CV[Filtros e segmentação]
    PP --> RT[Runtime ONNX]
    RT --> SAFE[Confirmação humana]
    SAFE --> GUIDE[Orientação de descarte]
    UI --> DB[Supabase opcional]
```

O runtime aceita somente `semantic_onnx_assisted`. A configuração aponta para `models/semantic-v1/semantic.json`; releases remotas precisam usar o mesmo encoder, classes, contrato de preparação e hashes. Os classificadores históricos e seus fallbacks foram removidos do produto atual.

Detalhes: [Arquitetura](docs/arquitetura_atual.md) e [Modelo de reconhecimento](docs/modelo_reconhecimento.md).

## Execução local

Requer Python 3.12.

Para a apresentação e o pacote com versões/hashes, siga o
[guia curto de execução](README_EXECUCAO.md) e o
[roteiro de empacotamento da APS](docs/pacote_execucao_aps.md).

```bash
git clone https://github.com/Gabrielhamad/ecoscan.git
cd ecoscan
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
streamlit run streamlit_app.py
```

A aplicação abre em `http://localhost:8501`.

## Configuração de serviços

Copie `.streamlit/secrets.example.toml` para `.streamlit/secrets.toml` e preencha somente no ambiente local ou no painel do Streamlit Cloud. Nunca publique chaves, tokens, fotos privadas ou dados de participantes.

O modo sem banco continua útil para demonstração pública. Cadastro, protocolos persistentes, campanhas compartilhadas e treinamento revisado exigem Supabase configurado conforme [Banco](docs/banco_gratuito.md) e [Autenticação](docs/autenticacao.md).

## Qualidade

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python scripts/run_acceptance_checks.py --diagnostic
```

A CI executa testes, lint crítico, verificação de dependências, diagnóstico e validação das migrações PostgreSQL.

## Estrutura

```text
config/             configuração funcional e conteúdo ambiental
models/semantic-v1 release ativa, licença e hashes
src/ecoscan/        aplicação, domínio, processamento e serviços
scripts/            operação, dataset e diagnóstico atuais
tests/              regressões automatizadas
migrations/         banco compartilhado e políticas de acesso
docs/               documentação atual da entrega
```

## Documentação

- [Índice da documentação](docs/README.md)
- [Autoria da APS](docs/autoria_aps.md)
- [Arquitetura atual](docs/arquitetura_atual.md)
- [Arquitetura modular da interface](docs/arquitetura_interface.md)
- [Modelo de reconhecimento](docs/modelo_reconhecimento.md)
- [Operação da gestão](docs/operacao_secretaria.md)
- [Roadmap de entrega e marcos](docs/roadmap_entrega.md)
- [Plano de validação técnica da APS em quatro dias](docs/plano_validacao_aps_4_dias.md)
- [Parecer de prontidão (07/11/2026)](docs/parecer_prontidao_2026-11-07.md)
- [Gestão do projeto: papéis, RACI, backlog, riscos e DoD](docs/gestao_projeto.md)
- [Avaliação técnica](docs/avaliacao_tecnica.md)
- [Como contribuir](CONTRIBUTING.md)
- [Catálogo de scripts](scripts/README.md)

O histórico de experimentos e métodos substituídos continua disponível no Git. O branch principal documenta apenas o produto atual.
