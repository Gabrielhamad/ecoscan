from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ecoscan.services.learning_contributions import (
    contribution_image, contribution_package, list_contributions,
    review_contribution, submit_contribution, citizen_contributions,
)
from ecoscan.services.recognition_scope import ITEMS, ITEM_CONDITIONS
from ecoscan.services.contribution_store import persistent_enabled
from ecoscan.services.secretariat_training import candidate_runs, train_candidate, training_dir


STATUS_LABELS = {"pending": "Recebido pela secretaria", "approved": "Aprovado pelo analista",
                 "rejected": "Não aproveitado", "queued": "Na fila de treino",
                 "awaiting_validation": "Candidato treinado; aguardando validação", "excluded": "Fora do treino"}


def render_citizen_protocols(st, config, profile):
    st.subheader("Minhas contribuições à secretaria")
    if profile.id.startswith("visitor_"):
        st.info("Entre em uma conta verificada para enviar e acompanhar contribuições. No modo visitante, nada é salvo no perfil.")
        return
    st.button("Atualizar protocolos", key="refresh_contributions")
    try:
        records = citizen_contributions(config, profile.id)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return
    if persistent_enabled():
        st.caption("Consulta ao banco concluída. As contribuições enviadas ficam disponíveis para revisão da secretaria.")
    else:
        st.warning("Armazenamento temporário: baixe seus comprovantes e pacotes.")
    st.caption("Protocolos vinculados à sua conta. Use a mesma conta em outro dispositivo para acompanhá-los.")
    if not records:
        st.caption("Quando você reportar uma análise, o protocolo e a resposta da equipe aparecerão aqui.")
        return
    pending = sum(row["status"] == "pending" for row in records)
    st.caption(f"{len(records)} contribuição(ões) · {pending} aguardando revisão")
    for row in records:
        item = ITEMS.get(row["item_id"], (row["item_id"],))[0]
        status = STATUS_LABELS.get(row["status"], row["status"])
        with st.expander(f"{item} · {status}"):
            st.code(row["id"], language=None)
            st.write("**Resposta da secretaria:** " + (row["response"] or "Aguardando análise da equipe."))
            st.caption(STATUS_LABELS.get(row["training_status"], "Ainda não utilizado no treinamento"))
            st.download_button("Baixar protocolo", json.dumps(row, ensure_ascii=False, indent=2),
                               file_name=f"ecoscan-protocolo-{row['id']}.json", mime="application/json",
                               key=f"protocol_download_{row['id']}")


def render_scope(st):
    with st.expander("Quais itens posso testar?"):
        st.write("Piloto com seis categorias. As respostas são sugestões e precisam de confirmação.")
        st.write("Latas de bebida/conserva; garrafas PET e potes plásticos; caixas e folhas de papel; garrafas e potes de vidro; pilhas/baterias; pequenos eletrônicos.")
        st.caption("Alimentos e resíduos orgânicos não são reconhecidos. Lâmpadas, remédios, óleo, aerossóis e embalagens químicas ficam fora da identificação automática desta etapa. Uma foto não confirma o conteúdo de uma embalagem.")
        st.write("Eletrônicos prioritários: celular, mouse e carregador de celular. Outros aparelhos precisam de orientação específica e não têm reconhecimento validado neste piloto.")
        st.caption("Amassados, papelão dobrado e cacos são casos de avaliação, não capacidades já comprovadas. Informe o estado ao reportar uma foto. Cacos não permitem confirmar pela aparência que se trata de vidro de embalagem, e não cerâmica ou outro material.")
    with st.expander("Óleo de cozinha usado: consultar descarte"):
        st.write("Esta orientação é para óleo de cozinha que você já identificou; o sistema não confirma líquidos pela foto.")
        st.write("Deixe esfriar, armazene em garrafa PET bem fechada e entregue em um ponto que aceite óleo de cozinha. Não despeje na pia, no vaso sanitário ou no solo. Não misture com óleo de motor ou outros produtos.")
        st.link_button("Consultar campanha e pontos em São Paulo", "https://prefeitura.sp.gov.br/web/sesana/w/doe-seu-oleo-usado")
        st.caption("Confirme endereço, horário e condições de recebimento com o ponto antes de sair. A garrafa com óleo não deve receber a orientação de uma embalagem plástica vazia.")
    with st.expander("Medicamentos vencidos ou sem uso: consultar descarte"):
        st.write("Para medicamentos domiciliares de uso humano e suas embalagens. A orientação depende da sua confirmação: não identificamos remédios, validade ou conteúdo pela foto.")
        st.write("Leve a um ponto de recebimento de medicamentos em farmácia ou drogaria participante. Não descarte na pia, no vaso sanitário, no lixo comum ou na coleta seletiva de embalagens.")
        st.write("Mantenha os produtos nas embalagens, quando disponíveis, sem abrir ou misturar conteúdos. Confirme com o ponto como entregar líquidos e embalagens vazias.")
        st.warning("Agulhas, seringas e outros perfurocortantes exigem orientação específica do serviço de saúde; não os coloque no coletor de medicamentos sem confirmar a aceitação.")
        st.link_button("Buscar pontos de descarte de medicamentos", "https://logmed.org.br/")
        st.link_button("Consultar orientação oficial do SINIR", "https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/medicamentos-seus-residuos-e-embalagens/")
        st.caption("Confirme endereço, horário e materiais aceitos antes de sair. Não envie receitas, nomes de pacientes ou outros dados de saúde. Este serviço orienta o descarte, não o uso ou a suspensão de tratamentos.")


def render_contribution(st, config, result, profile):
    if profile.id.startswith("visitor_"):
        st.info("Para reportar esta análise à secretaria, entre em uma conta verificada. A foto do visitante não será guardada como contribuição.")
        return
    pixels = result.pipeline.loaded.array
    signature = hashlib.sha256(str(pixels.shape).encode() + pixels.tobytes()).hexdigest()[:16]
    receipt_key = f"contribution_receipt_{signature}"
    with st.expander("O resultado está errado? Contribuir com uma correção", expanded=not result.accepted):
        st.caption("Sua correção entra na fila dos analistas da secretaria. Acompanhe a resposta em Perfil. Fotos aprovadas podem alimentar um modelo candidato, validado antes da publicação.")
        with st.form(f"contribution_form_{signature}"):
            item = st.selectbox("O que aparece na foto?", list(ITEMS), index=None,
                                placeholder="Escolha o item real", format_func=lambda key: ITEMS[key][0])
            condition = st.selectbox("Estado do objeto", list(ITEM_CONDITIONS),
                                     format_func=lambda key: ITEM_CONDITIONS[key])
            note = st.text_area("Observação opcional", max_chars=600,
                                placeholder="Ex.: lata amassada, foto com reflexo. Não informe dados pessoais.")
            consent = st.checkbox("Autorizo o grupo EcoScan a guardar esta foto e usá-la na revisão e no treinamento. A foto é minha e não contém pessoas ou dados pessoais.")
            sent = st.form_submit_button("Enviar correção")
        if sent:
            try:
                record = submit_contribution(config, result, item_id=item, reporter_id=profile.id,
                                             consent=consent, note=note, condition=condition)
                st.session_state[receipt_key] = {
                    "record": record, "persistent": bool(record.get("storage_key")),
                    "received_at": datetime.now(timezone.utc).isoformat(), "package": None,
                }
            except (ValueError, OSError) as exc:
                st.error(str(exc) if isinstance(exc, ValueError) else
                         "Não foi possível confirmar o envio. Consulte Perfil → Atualizar protocolos antes de reenviar.")
        receipt = st.session_state.get(receipt_key)
        # Sessions opened before this release may still contain the old tuple.
        if receipt and not isinstance(receipt, dict):
            st.session_state.pop(receipt_key, None)
            receipt = None
        if receipt:
            identifier = receipt["record"]["id"]
            st.success(f"Contribuição recebida para revisão. Protocolo: {identifier[:8]}")
            if receipt["persistent"]:
                st.caption("Protocolo salvo no banco e foto em armazenamento privado. O pacote abaixo é uma cópia para você.")
            else:
                st.warning("Banco ainda não ativado. Baixe sua contribuição e envie ao responsável do grupo para preservá-la.")
            st.download_button("Baixar comprovante do envio", json.dumps({
                "protocol": identifier, "received_at": receipt["received_at"],
                "persistent": receipt["persistent"], "item_id": receipt["record"].get("item_id"),
                "status_at_submission": receipt["record"]["status"],
            }, ensure_ascii=False, indent=2), file_name=f"ecoscan-protocolo-{identifier}.json",
                mime="application/json", key=f"receipt_download_{signature}")
            if st.button("Preparar cópia com foto", key=f"prepare_receipt_{signature}"):
                try:
                    receipt["package"] = contribution_package(config, [receipt["record"]])
                except (ValueError, OSError):
                    st.warning("Seu envio já foi confirmado. Não foi possível preparar a cópia agora; tente novamente sem reenviar a contribuição.")
            if receipt["package"] is not None:
                st.download_button("Baixar minha contribuição", receipt["package"],
                                   file_name=f"ecoscan-contribuicao-{identifier}.zip", mime="application/zip",
                                   key=f"download_{signature}")


def render_review(st, config, profile):
    if not profile.is_admin:
        return
    st.subheader("Central de análise da secretaria")
    try:
        records = list_contributions(config)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return
    columns = st.columns(3)
    columns[0].metric("Aguardando análise", sum(row["status"] == "pending" for row in records))
    columns[1].metric("Aprovadas", sum(row["status"] == "approved" for row in records))
    columns[2].metric("Na fila de treino", sum(row.get("training_status") == "queued" for row in records))
    render_training(st, config, profile)
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
        st.write("Estado informado: " + ITEM_CONDITIONS.get(selected.get("condition", "unspecified"), "Não informado"))
        with st.form(f"review_contribution_{selected['id']}_{selected.get('revision', 0)}"):
            item_id = st.selectbox("Item confirmado pelo analista", list(ITEMS),
                                   index=list(ITEMS).index(selected["item_id"]),
                                   format_func=lambda key: ITEMS[key][0])
            decision = st.selectbox("Decisão", ["approved", "rejected"], index=None,
                                    format_func=lambda value: "Aprovar rótulo e foto" if value == "approved" else "Rejeitar")
            response = st.text_area("Resposta ao cidadão", max_chars=600,
                                    value=selected.get("response", ""),
                                    placeholder="Ex.: Confirmamos uma lata metálica. Obrigado pela contribuição.")
            train_now = st.checkbox("Gerar candidato após aprovar", value=not persistent_enabled(), disabled=persistent_enabled())
            if st.form_submit_button("Salvar revisão"):
                review_contribution(config, selected["id"], decision=decision, reviewer=profile,
                                    item_id=item_id, response=response,
                                    expected_revision=selected.get("revision", 0))
                st.session_state.pop("review_packages", None)
                if decision == "approved" and train_now:
                    try:
                        with st.spinner("Treinando candidato com fotos aprovadas..."):
                            train_candidate(config, reviewer=profile)
                    except (ValueError, OSError) as exc:
                        st.session_state["training_notice"] = "Revisão salva; treino pendente. " + str(exc)
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
        st.caption("Fotos aprovadas ainda precisam de divisão entre treino, validação e teste. Mantenha cópias de segurança dos pacotes.")
    except (ValueError, OSError) as exc:
        st.error(str(exc))


def render_training(st, config, profile):
    if not profile.is_admin:
        return
    if persistent_enabled():
        st.info("Banco de contribuições ativo. Exporte as aprovadas para treino local; candidatos e publicação de modelos ainda não estão integrados ao banco.")
        return
    if st.session_state.get("training_notice"):
        st.warning(st.session_state.pop("training_notice"))
    with st.expander("Treinos supervisionados"):
        st.caption("Cada candidato reúne a base publicada e as fotos aprovadas. O modelo público só deve mudar após avaliação independente.")
        if st.button("Treinar candidato com aprovadas"):
            try:
                with st.spinner("Processando fotos e treinando candidato..."):
                    train_candidate(config, reviewer=profile)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        runs = candidate_runs(config)
        if runs:
            st.dataframe([{"Lote": run["id"][:8], "Estado": run["status"],
                           "Fotos novas": run["new_examples"]} for run in runs], hide_index=True)
            latest = next((run for run in runs if run["status"] == "awaiting_validation"), None)
            if latest:
                from uuid import UUID
                model = training_dir(config) / str(UUID(latest["id"])) / "candidate.npz"
                st.download_button("Baixar candidato para avaliação", model.read_bytes(),
                                   "ecoscan-candidate.npz", "application/octet-stream")
                st.caption(latest["validation"])
