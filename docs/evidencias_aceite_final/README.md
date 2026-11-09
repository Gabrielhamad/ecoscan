# Reprodução da auditoria final

Fonte do app: `89622ec714b815c216a9215ab9ba69999b39c6b8`. O PR desta pasta tem
somente documentos/sondas. Executar na raiz do repositório com Python 3.12 e
dependências declaradas instaladas. As versões usadas estão em `checks.json`;
main ainda não integra o lock do PR #27. Instalação nova no PC de apresentação
permanece pendente, mesmo que esta reprodução funcione em outro computador.

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python -m ruff check --ignore E402 docs/evidencias_aceite_final
python docs/evidencias_aceite_final/reproduzir.py --output reports/final-audit --onnx
```

`E402` é ignorado apenas para as sondas documentais: o wrapper adiciona `src/`
antes de importar o app, como os CLIs existentes. Os gates de `src scripts tests`
não são relaxados. A sonda recusa alterações nos arquivos versionados do app,
configuração e modelo em relação à fonte; não basta o nome da branch.

**Resultado observado: retorno 2, NO-GO**, 21 PASS / 5 FAIL / 6 BLOCKED. O retorno
nunca deve ser transformado em sucesso para aprovar release. `--onnx` executa o
encoder CPU real; sem essa opção sua linha fica BLOCKED. O runtime pode reunir
os shards no cache local `models/semantic-v1/encoder.onnx`, verificando SHA-256.
Não modifica os shards ou a cabeça. Remover esse cache apenas se tiver sido
criado por esta reprodução e não estiver em uso; não apagar arquivos do grupo.

A sonda usa apenas arrays/arquivos técnicos criados temporariamente e stubs para
identidade, erro do banco, relógio/cache e scores. Limpa variáveis `ECOSCAN_` do
próprio processo, desliga stores opcionais e substitui Streamlit Secrets por
dicionário vazio. Não lê credenciais nem acessa contas reais. O teste ONNX bloqueia
`socket.socket.connect` Python; **rede de bibliotecas nativas/SO não foi monitorada**.
Isso não prova operação totalmente offline do dispositivo ou de mapas externos.

`technical_processing.zip` contém somente a fixture artificial e a execução
associada: validação técnica, **nunca foto real de sustentabilidade ou avaliação
de acurácia**. ZIPs podem diferir por timestamps/tempos; compare shape, dtype,
hashes dos arrays, parâmetros e PNGs. Os outputs ficam em `reports/` ignorado.

## Browser local opcional

Playwright 1.64.1 e Chromium 156.0.8078.79 estavam disponíveis no ambiente de QA;
não foram adicionados ao runtime web. Em outro ambiente, instalar ferramentas de
teste separadamente e fornecer o executável por `--chromium`. Não dirigir a sonda
à URL publicada: o script aceita somente servidor HTTP local. O SHA da árvore
de trabalho é conferido; isso não é atestação remota do SHA servido pelo browser.
Iniciar exatamente o app desta árvore, em terminal dedicado, sem Secrets reais:

```bash
python - <<'PY'
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from streamlit.web.cli import main

for key in tuple(os.environ):
    if key.startswith("ECOSCAN_"):
        del os.environ[key]
os.environ.update(
    ECOSCAN_COMMUNITY_ENABLED="false",
    ECOSCAN_OPERATIONS_ENABLED="false",
    ECOSCAN_REMOTE_MODELS="false",
)
with TemporaryDirectory(prefix="ecoscan-audit-local-") as directory:
    empty = Path(directory) / "empty.toml"
    empty.write_text("# Audit: deliberately empty.\n", encoding="utf-8")
    sys.argv = [
        "streamlit", "run", "streamlit_app.py",
        "--server.address=127.0.0.1", "--server.port=8519",
        "--server.headless=true", "--browser.gatherUsageStats=false",
        f"--secrets.files={empty}",
    ]
    main()
PY
```

Em outro terminal com o mesmo ambiente Python:

```bash
python docs/evidencias_aceite_final/smoke_browser.py \
  --url http://127.0.0.1:8519 --chromium /usr/bin/chromium \
  --output reports/final-audit-browser.json
```

Resultado observado: **retorno 2**, 9 PASS / 2 FAIL. Os dois FAIL são ausência de
escolha manual após upload inválido, em Escanear e Descarte. O navegador usa
contextos novos, fixtures próprias, nenhum login e bloqueia requests externos.
O argumento Chromium `--no-sandbox` atende o container isolado de QA; não é mudança
no app/deploy. Encerrar somente esse servidor com Ctrl+C após a execução.

O arquivo de configuração oficial tem `remote_models_enabled=true`; a variável
`ECOSCAN_REMOTE_MODELS=false` sozinha não sobrepõe esse booleano em main. Nesta
execução isolada o Secrets vazio impede disponibilidade do store remoto. Não
interpretar o teste como prova dos pesos usados pela aplicação publicada.

## Exportador oficial e avaliação

Para reproduzir a fixture técnica usada no exportador, sem foto ou rótulo real:

```bash
python - <<'PY'
from pathlib import Path
import numpy as np
from PIL import Image

folder = Path("reports/final-audit-input")
folder.mkdir(parents=True, exist_ok=True)
y, x = np.indices((96, 128))
rgb = np.stack((180 + x // 4, 180 + y // 3, 190 + x // 8), axis=-1).astype(np.uint8)
rgb[20:80, 35:95] = (45, 105, 70)
rgb[40:46, 60:66] = 240
Image.fromarray(rgb).save(folder / "technical.png")
PY
python scripts/export_processing_evidence.py \
  --image reports/final-audit-input/technical.png --output reports/final-audit-pdi
python scripts/evaluate_bundled_model.py --output reports/final-audit-historical.json
```

O exportador retorna 0: 22 artefatos e mais `reproduction.json`. O JSON técnico
versionado elimina `image_path` do relatório de pipeline; revisar os arquivos
brutos antes de compartilhar. `evaluate_bundled_model` retorna 0 e reutiliza
features históricas; não comprova independência ou ganho em fotos novas.

A CLI `scripts/validate_semantic_onnx.py` **não foi executada em corpus real novo**:
não há imagens locais elegíveis fornecidas com consentimento/proveniência/grupos.
Não usar crops de treino, rasters do pacote ou a fixture geométrica para preencher
essa lacuna. O [protocolo existente](../avaliacao_campo.md) fornece o comando com
manifesto, raiz externa ao Git, `--require-groups` e hashes de desenvolvimento.
Definir treino/validação/teste antes de inferir; manter `independent_test=false`
até auditoria externa real. A autorização de assertividade por classe segue
bloqueada, mesmo que os testes técnicos passem.

O aceite estrito executado nesta etapa, sob isolamento de stores/Secrets, equivale
ao CLI abaixo **sem `--diagnostic`** e retornou 2 (12 ok / 4 attention / 5 pending):

```bash
python scripts/run_acceptance_checks.py \
  --sample-image reports/final-audit-input/technical.png --output reports/final-audit-acceptance
```

Para repetir sem ler configuração privada, executar somente no checkout/ambiente
limpo e sem Secrets/contas locais, com stores opcionais desativados. Esse comando
grava logs/relatórios locais: não publicar os brutos. `prepare_delivery_pack.py`
em main retorna 0 ao produzir sete relatórios de inventário; ADV-17 demonstra
que esse inventário não é aceite independente nem pacote de release aprovado.

As sondas registram esta baseline e não recebem atestados manuais futuros.
Depois de corrigir o app, revisar os mesmos casos e a referência de fonte em
nova auditoria; a recusa do guard ao encontrar código diferente é intencional.

CI PostgreSQL usa banco descartável/fixtures, nunca produção. Casos físicos,
contas autorizadas, recuperação em cópia isolada, fotos reais e os três ensaios
continuam `manual_pending`; o relatório final lista o menor caminho de correção.
