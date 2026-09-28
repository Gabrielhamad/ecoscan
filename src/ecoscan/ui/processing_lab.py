"""Teaching views for the image-processing stages, independent of model predictions."""
from __future__ import annotations

import numpy as np

from ecoscan.image_processing.preprocessing import to_grayscale
from ecoscan.segmentation.morphology import OPERATIONS


def select_morphology_parameters(st, defaults=None):
    defaults = defaults or {}
    operation = st.selectbox("Morfologia da máscara", list(OPERATIONS),
                             format_func=OPERATIONS.get, key="morphology_operation",
                             index=list(OPERATIONS).index(defaults.get("default", "open_close")))
    if operation == "none":
        st.caption("Controle: preserva a máscara. Ative uma operação para comparar seus efeitos.")
        return operation, {}
    shape = st.selectbox("Elemento estruturante", ["square", "cross", "disk"],
                         format_func={"square": "Quadrado", "cross": "Cruz", "disk": "Disco"}.get,
                         key="morphology_shape",
                         index=["square", "cross", "disk"].index(defaults.get("kernel_shape", "square")))
    size = st.select_slider("Tamanho do elemento (pixels)", options=[1, 3, 5, 7, 9, 11, 13, 15],
                            value=defaults.get("kernel_size", 3), key="morphology_size")
    iterations = st.slider("Iterações por primitiva", 1, 5, defaults.get("iterations", 1), key="morphology_iterations")
    st.caption("Aplicada após a segmentação. Elementos grandes podem apagar detalhes ou unir objetos.")
    return operation, {"kernel_size": size, "kernel_shape": shape, "iterations": iterations}


def render_processing_lab(st, pipeline):
    morphology = getattr(pipeline, "morphology_result", None)
    raw = getattr(pipeline, "raw_segmentation_result", None)
    if morphology is None or raw is None:
        st.info("Refaça a análise para visualizar as etapas morfológicas desta versão.")
        return
    st.subheader("Preparação e morfologia matemática")
    st.caption("Aquisição → RGB e tamanho → filtro → segmentação → morfologia → regiões → reconhecimento.")
    columns = st.columns(3)
    gray = to_grayscale(pipeline.preprocessing.resized)
    filtered_gray = to_grayscale(pipeline.filter_result.image)
    columns[0].image(pipeline.preprocessing.resized, caption="Preparada em RGB", width="stretch")
    columns[1].image(gray, caption="Tons de cinza: representação de intensidade", width="stretch")
    columns[2].image(filtered_gray, caption="Intensidade após o filtro", width="stretch")
    st.caption("Otsu usa tons de cinza; HSV usa cor e GrabCut usa o RGB. A imagem colorida é preservada.")
    st.line_chart({
        "Antes do filtro": np.bincount(gray.ravel(), minlength=256),
        "Após o filtro": np.bincount(filtered_gray.ravel(), minlength=256),
    }, x_label="Intensidade (0–255)", y_label="Quantidade de pixels")
    st.caption("Histograma mostra a distribuição de intensidades, não a precisão do reconhecimento.")
    prepared = pipeline.preprocessing
    st.write(f"Normalização de referência: {prepared.normalized.dtype}, "
             f"intervalo [{prepared.normalized.min():.3f}, {prepared.normalized.max():.3f}], "
             f"tensor {tuple(prepared.model_input.shape)}.")
    st.caption("Redimensionamento bicúbico para o tamanho configurado; mantém o contrato do modelo "
               "atual e pode alterar proporções. Cada classificador aplica sua própria preparação final.")
    columns = st.columns(3)
    columns[0].image(raw.mask, caption="Máscara antes da morfologia (branco = primeiro plano)", width="stretch")
    columns[1].image(morphology.mask, caption="Máscara após a morfologia", width="stretch")
    columns[2].image(morphology.gradient, caption="Gradiente morfológico: contorno, só para inspeção", width="stretch")
    metadata = morphology.metadata
    st.write(OPERATIONS[metadata["operation"]] + ": " + metadata["explanation"])
    columns = st.columns(3)
    columns[0].metric("Pixels de primeiro plano antes", metadata["foreground_pixels_before"])
    columns[1].metric("Pixels de primeiro plano depois", metadata["foreground_pixels_after"])
    columns[2].metric("Pixels alterados", metadata["changed_pixels"])
    st.caption("Mais pixels ou menos componentes não significam uma segmentação melhor. "
               "Compare com o objeto visível e, em avaliação, com uma máscara de referência.")
    with st.expander("Elemento estruturante e sequência executada"):
        st.dataframe(morphology.kernel, hide_index=True)
        st.caption("1 = posição ativa; âncora no centro. Fora da imagem é fundo zero, inclusive na erosão.")
        st.write("Ordem: " + (" → ".join(metadata["sequence"]) or "sem alteração"))
        st.write(f"Iterações por primitiva: {metadata['iterations']}.")
        for index, (name, stage) in enumerate(morphology.stages, start=1):
            st.image(stage, caption=f"{index}. {OPERATIONS[name]}", width=250)
    if metadata["operation"] != "none" and metadata["foreground_ratio_after"] in (0.0, 1.0):
        st.warning("A máscara final está vazia ou ocupa toda a imagem. Revise a segmentação e o elemento estruturante.")


def render_applied_processing(st, pipeline):
    from ecoscan.services.processing_evidence import processing_evidence, processing_evidence_zip

    stages = processing_evidence(pipeline)
    if not stages:
        st.info("Refaça a análise para gerar o antes e depois das operações.")
        return
    st.subheader("Processamento aplicado: antes e depois")
    st.caption("Evidência desta foto: preparação → filtro → segmentação → morfologia → classificação.")
    columns = st.columns(2)
    columns[0].image(pipeline.loaded.array, caption="Antes: imagem original em RGB", width="stretch")
    columns[1].image(pipeline.segmentation_result.image,
                     caption="Depois: imagem entregue ao classificador", width="stretch")
    st.caption("O classificador recebe a imagem da direita e aplica sua própria extração de características. "
               "As comparações abaixo mostram os resultados reais das operações, inclusive quando não há alteração.")
    for tab, stage in zip(st.tabs([stage.label for stage in stages]), stages):
        with tab:
            st.write(stage.status)
            columns = st.columns(3)
            columns[0].image(stage.before, caption="Antes da operação", width="stretch")
            columns[1].image(stage.after, caption="Depois da operação", width="stretch")
            difference = stage.difference
            if difference is not None:
                columns[2].image(difference, caption="Diferença absoluta, sem amplificação (0–255)", width="stretch")
                st.caption("Preto = sem mudança. Na máscara binária, branco = pixel alterado. "
                           "No RGB, a intensidade indica a maior diferença entre os canais.")
            else:
                columns[2].info("Dimensões ou representações diferentes: diferença pixel a pixel não se aplica.")
            st.json(stage.parameters)
    st.caption("Abertura = erosão → dilatação. Fechamento = dilatação → erosão. "
               "Cada aba morfológica mostra a entrada e a saída daquela primitiva. "
               "Alteração de pixels comprova o efeito, mas não comprova melhora na precisão.")
    st.download_button("Baixar evidências do processamento (ZIP)",
                       processing_evidence_zip(pipeline), "ecoscan_antes_depois.zip",
                       "application/zip", key="processing_evidence_download")
