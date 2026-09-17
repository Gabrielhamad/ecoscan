from __future__ import annotations

import hashlib

from ecoscan.services.learning_contributions import (
    contribution_image, contribution_package, list_contributions,
    review_contribution, submit_contribution,
)
from ecoscan.services.recognition_scope import ITEMS


def render_scope(st):
    with st.expander("Quais itens posso testar?"):
        st.write("Piloto com seis categorias. As respostas são sugestões e precisam de confirmação.")
        st.write("Latas de bebida/conserva; garrafas PET e potes plásticos; caixas e folhas de papel; garrafas e potes de vidro; pilhas/baterias; pequenos eletrônicos.")
        st.caption("Alimentos e resíduos orgânicos não são reconhecidos. Lâmpadas, remédios, óleo, aerossóis e embalagens químicas ficam fora da identificação automática desta etapa. Uma foto não confirma o conteúdo de uma embalagem.")


def render_contribution(st, config, result, profile):
    pixels = result.pipeline.loaded.array
    signature = hashlib.sha256(str(pixels.shape).encode() + pixels.tobytes()).hexdigest()[:16]
    receipt_key = f"contribution_receipt_{signature}"
    with st.expander("O resultado está errado? Contribuir com uma correção", expanded=not result.accepted):
        st.caption("Sua foto pode ajudar o grupo a corrigir erros como confundir lata com vidro. Cada envio passa por revisão; o modelo não aprende imediatamente.")
        with st.form(f"contribution_form_{signature}"):
            item = st.selectbox("O que aparece na foto?", list(ITEMS), index=None,
                                placeholder="Escolha o item real", format_func=lambda key: ITEMS[key][0])
            note = st.text_area("Observação opcional", max_chars=600,
                                placeholder="Ex.: lata amassada, foto com reflexo. Não informe dados pessoais.")
            consent = st.checkbox("Autorizo o grupo EcoScan a guardar esta foto e usá-la na revisão e no treinamento. A foto é minha e não contém pessoas ou dados pessoais.")
            sent = st.form_submit_button("Enviar correção")
        if sent:
            try:
                record = submit_contribution(config, result, item_id=item, reporter_id=profile.id,
                                             consent=consent, note=note)
                st.session_state[receipt_key] = (record["id"], contribution_package(config, [record]))
            except (ValueError, OSError) as exc:
                st.error(str(exc) if isinstance(exc, ValueError) else "Não foi possível guardar a contribuição. Tente novamente.")
        receipt = st.session_state.get(receipt_key)
        if receipt:
            st.success(f"Contribuição recebida para revisão. Protocolo: {receipt[0][:8]}")
            st.warning("A hospedagem atual usa armazenamento temporário. Baixe sua contribuição e envie ao responsável do grupo para preservá-la.")
            st.download_button("Baixar minha contribuição", receipt[1],
                               file_name=f"ecoscan-contribuicao-{receipt[0]}.zip", mime="application/zip",
                               key=f"download_{signature}")


def render_review(st, config, profile):
    if not profile.is_admin:
        return
    st.subheader("Revisão das contribuições")
    records = list_contributions(config)
    st.caption("Confira foto e rótulo. A aprovação prepara o próximo treino; não altera o modelo em uso.")
    if not records:
        st.info("Nenhuma contribuição recebida nesta instância.")
        return
    selected = st.selectbox("Contribuição", records,
                            format_func=lambda row: f"{row['status']} · {ITEMS.get(row['item_id'], (row['item_id'],))[0]} · {row['id'][:8]}")
    try:
        st.image(str(contribution_image(config, selected)), width=300)
        st.write(f"Modelo sugeriu: {selected['feedback']['predicted_class'] or selected['feedback']['top_class'] or 'inconclusivo'}")
        st.write(selected["feedback"]["note"])
        with st.form("review_contribution"):
            decision = st.selectbox("Decisão", ["approved", "rejected"], index=None,
                                    format_func=lambda value: "Aprovar rótulo e foto" if value == "approved" else "Rejeitar")
            if st.form_submit_button("Salvar revisão"):
                review_contribution(config, selected["id"], decision=decision, reviewer=profile)
                st.session_state.pop("review_packages", None)
                st.rerun()
        if st.button("Preparar pacotes de contribuições"):
            st.session_state["review_packages"] = (
                contribution_package(config, records),
                contribution_package(config, records, approved_only=True),
            )
        packages = st.session_state.get("review_packages")
        if packages:
            st.download_button("Baixar fila para revisão offline", packages[0], "ecoscan-fila.zip", "application/zip")
            st.download_button("Baixar somente aprovadas", packages[1], "ecoscan-aprovadas.zip", "application/zip")
        st.caption("Exporte antes de reiniciar a hospedagem. Fotos aprovadas ainda precisam de divisão entre treino, validação e teste.")
    except (ValueError, OSError) as exc:
        st.error(str(exc))
