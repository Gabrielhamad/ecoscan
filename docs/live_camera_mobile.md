# EcoScan Live: câmera traseira e tracking

O modo `EcoScan Live` atende ao uso com celular e reconhecimento em tempo quase real.

## Execução

```powershell
python scripts\ecoscan_access.py --restart
```

A página usa `getUserMedia` com prioridade real para a câmera traseira do celular. A abertura segue esta ordem:

1. câmera traseira obrigatória com `facingMode: { exact: "environment" }`;
2. câmera traseira preferencial com `facingMode: { ideal: "environment" }`;
3. câmera traseira encontrada pelo nome do dispositivo, quando o navegador informa os rótulos;
4. câmera disponível como fallback, caso o navegador ou aparelho não confirme a traseira.

O botão `Alternar câmera` permite trocar para a câmera frontal quando necessário. A interface também informa quando a câmera ativa não pôde ser confirmada como traseira.

## Interface mobile

A interface foi organizada para uso em dispositivo:

- vídeo em área principal;
- painel inferior responsivo;
- anel de score;
- barras com as classes mais prováveis;
- status de câmera e quantidade de elementos rastreados;
- mensagens de erro com código e ação recomendada.

## Fluxo

```text
câmera do navegador
-> frame JPEG
-> backend local
-> filtro e segmentação
-> reconhecimento da classe do frame
-> probabilidades por classe
-> componentes segmentados
-> tracking por centroide
-> overlay com caixas e IDs
```

## Segurança do navegador

Em celulares, a câmera normalmente só é liberada em contexto seguro. Funciona diretamente em `localhost`; para acessar pelo celular usando o IP do computador, pode ser necessário HTTPS, túnel seguro ou certificado local informado com `--cert-file` e `--key-file`.

Para ver o IP correto da maquina e os links atuais, rode:

```powershell
python scripts\ecoscan_access.py --check-only
```

## Limite técnico atual

O modo ao vivo não substitui YOLO. Ele classifica o frame/resíduo principal e usa segmentação para rastrear componentes visuais. Para detectar várias classes diferentes na mesma cena, será necessário dataset anotado com caixas ou máscaras.
