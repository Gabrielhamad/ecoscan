"""Evidence from the executed preprocessing, never a second illustrative pipeline."""
from __future__ import annotations

import numpy as np


def comparison_metrics(pipeline):
    before = pipeline.preprocessing.resized
    after = pipeline.filter_result.image
    if before.shape != after.shape:
        raise ValueError("A comparação exige imagens com as mesmas dimensões.")
    difference = np.abs(before.astype(np.float32) - after.astype(np.float32))
    return {
        "mean_absolute_change": float(difference.mean()),
        "changed_pixel_percent": float(np.mean(np.any(difference > 0, axis=-1)) * 100),
    }


def render_processing_comparison(st, pipeline):
    st.subheader("Antes do reconhecimento")
    columns = st.columns(2)
    columns[0].image(pipeline.preprocessing.resized,
                     caption="Antes: RGB no tamanho de processamento", width="stretch")
    columns[1].image(pipeline.filter_result.image,
                     caption="Depois: " + pipeline.filter_result.name, width="stretch")
    st.write(pipeline.filter_result.explanation)
    decision = pipeline.metadata.get("filter", {}).get("decision", {})
    if decision.get("reason"):
        st.caption(str(decision["reason"]))
    with st.expander("Parâmetros e medidas desta foto"):
        st.json({"filtro": pipeline.filter_result.name,
                 "parametros": pipeline.filter_result.parameters,
                 "sequencia": decision.get("selected_sequence", []),
                 "segmentacao": pipeline.segmentation_result.name,
                 "parametros_segmentacao": pipeline.segmentation_result.parameters})
        rows = []
        for label, attribute in (("Brilho médio (0–255)", "brightness_mean"),
                                 ("Contraste (desvio / 255)", "contrast"),
                                 ("Nitidez (variância do Laplaciano normalizada)", "sharpness"),
                                 ("Densidade de bordas", "edge_density")):
            before = getattr(pipeline.quality_original, attribute)
            after = getattr(pipeline.quality_filtered, attribute)
            rows.append({"Medida": label, "Antes": before, "Depois": after,
                         "Variação": after - before})
        st.dataframe(rows, hide_index=True, width="stretch")
        change = comparison_metrics(pipeline)
        st.caption(f"Pixels alterados pelo filtro: {change['changed_pixel_percent']:.2f}%. "
                   f"Diferença absoluta média por canal: {change['mean_absolute_change']:.2f}/255.")
        st.caption("As medidas descrevem a transformação, não a acurácia. Suavização pode reduzir "
                   "nitidez e ruído ao mesmo tempo; contraste maior também pode realçar ruído.")
    columns = st.columns(2)
    columns[0].image(pipeline.segmentation_result.mask,
                     caption="Segmentação: branco indica o primeiro plano selecionado", width="stretch")
    columns[1].image(pipeline.segmentation_result.image,
                     caption="Imagem entregue à etapa de classificação", width="stretch")
    st.caption("O classificador ainda aplica sua preparação específica. A máscara não confirma "
               "o material nem garante que todos os objetos foram separados.")
