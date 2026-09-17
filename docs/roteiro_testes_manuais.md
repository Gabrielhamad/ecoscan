# Roteiro de testes manuais

## Câmera

1. Abrir a aplicação com `python scripts\run_streamlit_app.py`.
2. Acessar a aba `Análise`.
3. Selecionar `Câmera`.
4. Permitir acesso à câmera no navegador.
5. Capturar uma foto com um resíduo principal centralizado.
6. Verificar se o sistema mostra classe, score, categoria ambiental e orientação.
7. Abrir `Processamento` e conferir filtro, máscara, elementos visuais e metadata.

Teste alternativo com OpenCV instalado:

```powershell
python scripts\capture_webcam.py --camera-index 0
```

O script deve salvar captura e evidências em `reports/camera_detection`.

Teste ao vivo no celular:

```powershell
python scripts\run_live_camera_app.py --host 0.0.0.0 --port 8765
```

1. Abrir a URL indicada pelo terminal no celular.
2. Tocar em `Iniciar`.
3. Confirmar se a câmera traseira foi priorizada.
4. Apontar para um resíduo centralizado.
5. Conferir se aparecem classe, score, latência, filtro, segmentação e caixas com IDs.
6. Usar `Alternar` se o navegador escolher a câmera frontal.

Se o celular bloquear a câmera, repetir o teste por HTTPS ou túnel seguro, pois navegadores móveis normalmente exigem contexto seguro para `getUserMedia`.

Use este roteiro nas próximas fases da APS.

## Imagens válidas

- imagem clara com fundo simples;
- imagem escura;
- fundo complexo;
- objeto pequeno na imagem;
- objeto parcialmente cortado;
- objeto centralizado;
- objeto fora do centro.

## Classes

- plástico;
- papel/papelão;
- metal;
- vidro;
- orgânico;
- pilha/bateria;
- eletrônico.

## Entradas problemáticas

- arquivo vazio;
- arquivo corrompido;
- formato não suportado;
- imagem muito pequena;
- imagem sem resíduo;
- imagem fora do domínio.

## Critérios esperados

- o sistema não deve quebrar com entrada inválida;
- mensagens de erro devem ser claras;
- baixa confiança não deve forçar classificação;
- a tela técnica deve mostrar as etapas do processamento;
- a orientação deve vir da base configurável, não do modelo.
