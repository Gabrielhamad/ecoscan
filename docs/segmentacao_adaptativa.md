# Segmentação adaptativa

## Objetivo

A segmentação não fica mais fixa em um único método para todas as imagens. O EcoScan usa o modo `auto` como padrão e escolhe a melhor alternativa disponível para cada imagem analisada.

## Métodos candidatos

- `otsu`: limiar global em tons de cinza, adequado quando há bom contraste entre resíduo e fundo.
- `hsv_color`: máscara por saturação e brilho, útil para resíduos coloridos ou objetos com cor destacada. Possui fallback em NumPy quando OpenCV não está instalado.
- `grabcut`: segmentação por primeiro plano/fundo a partir de uma região central. É usada quando OpenCV está disponível.

## Critérios usados na escolha

O seletor adaptativo avalia a máscara gerada por cada método candidato. A pontuação considera:

- proporção de primeiro plano;
- contato da máscara com as bordas;
- quantidade de componentes visuais relevantes;
- tamanho do maior componente;
- saturação média da imagem;
- densidade de bordas;
- contraste e foco depois do filtro.

## Saída auditável

O pipeline registra a decisão em `metadata["segmentation"]["decision"]`, incluindo:

- método solicitado;
- método selecionado;
- motivo da seleção;
- perfil de qualidade da imagem;
- pontuação dos candidatos;
- métodos ignorados por dependência indisponível.

Isso permite explicar por que uma foto usou Otsu, HSV ou GrabCut, em vez de aplicar a mesma segmentação de forma cega para todos os casos.

## Limitação atual

A segmentação adaptativa melhora o preparo da imagem, mas não substitui o treinamento do modelo final. A precisão de reconhecimento ainda depende da ampliação e curadoria do dataset.
