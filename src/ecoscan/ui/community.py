"""Citizen protocols and secretariat publishing, without local persistence."""
from __future__ import annotations

import copy
import json
from uuid import uuid4

from ecoscan.services.community_store import community_enabled, community_store

DECISIONS = {"encaminhar": "Encaminhamento registrado",
             "arquivar": "Arquivado", "solicitar_nova_foto": "Nova foto solicitada"}


def credentials(st):
    try:
        access = dict(st.secrets.get("access", {}))
    except FileNotFoundError:
        access = {}
    return {"token": st.session_state.get("auth_access_token"), "access": access}


def render_reports(st, *, admin=False, key="citizen_reports"):
    st.subheader("Triagem de relatos" if admin else "Meus relatos de descarte")
    if not community_enabled():
        st.info("O recebimento compartilhado de relatos está em preparação. Nenhum relato novo é gravado em arquivos temporários.")
        return
    st.button("Atualizar relatos", key=key + "_refresh")
    try:
        store = community_store()
        auth = credentials(st)
        rows = store.reports(**auth, own_only=not admin, limit=100)
    except (ValueError, PermissionError, OSError) as exc:
        st.error(str(exc))
        return
    st.caption("Últimos 100 protocolos. Fotos privadas; acesso restrito ao autor e aos analistas autorizados.")
    if not rows:
        st.info("Nenhum relato encontrado para esta consulta.")
        return
    for row in rows:
        latest = row["reviews"][-1] if row["reviews"] else None
        status = DECISIONS[latest["decision"]] if latest else "Aguardando análise"
        with st.expander(f"{row['record']['location_note']} · {status}"):
            st.code(row["id"], language=None)
            st.write(row["record"]["description"])
            st.caption("Recebido em " + row["created_at"][:19].replace("T", " ") + " UTC")
            if admin:
                record = row["record"]
                st.caption(f"Triagem: {record.get('verification_status', 'não informada')} · "
                           f"Filtro: {record.get('filter_decision', '')} · "
                           f"Segmentação: {record.get('segmentation_decision', '')}")
            if latest:
                st.write("**Resposta da equipe:** " + latest["note"])
            if st.button("Ver foto", key=f"{key}_photo_{row['id']}"):
                try:
                    st.image(store.evidence(row["id"], **auth), caption="Evidência enviada", width="stretch")
                except (ValueError, PermissionError, OSError) as exc:
                    st.error(str(exc))
            # Do not export internal actor IDs or private contacts in a receipt.
            receipt = {"protocolo": row["id"], "recebido_em": row["created_at"],
                       "local": row["record"]["location_note"], "status": status,
                       "resposta": latest["note"] if latest else "Aguardando análise"}
            st.download_button("Baixar protocolo", json.dumps(receipt, ensure_ascii=False, indent=2),
                               file_name=f"ecoscan-relato-{row['id']}.json", mime="application/json",
                               key=f"{key}_receipt_{row['id']}")
    if not admin:
        return
    selected = st.selectbox("Protocolo para revisar", rows, format_func=lambda r:
                           f"{r['id'][:8]} · {r['record']['location_note']}", key=key + "_selected")
    # Keep the revision displayed when the analyst began editing, not the latest
    # revision fetched by Streamlit on form submission.
    draft_key = key + "_draft"
    if st.session_state.get(draft_key, {}).get("id") != selected["id"]:
        st.session_state[draft_key] = copy.deepcopy(selected)
    if st.button("Carregar revisão mais recente", key=key + "_reload"):
        st.session_state[draft_key] = copy.deepcopy(selected)
    draft = st.session_state[draft_key]
    st.caption(f"Revisão em edição: {draft['revision']}. A resposta ficará visível para o autor.")
    with st.form(key + "_review_" + draft["id"] + "_" + str(draft["revision"])):
        decision = st.selectbox("Decisão da equipe", list(DECISIONS), format_func=DECISIONS.get)
        note = st.text_area("Resposta ao participante", max_chars=2000)
        sent = st.form_submit_button("Registrar resposta")
    if sent:
        try:
            store.review(draft["id"], expected_revision=draft["revision"],
                         decision=decision, note=note, **auth)
        except (ValueError, PermissionError, OSError) as exc:
            st.error(str(exc))
        else:
            st.session_state.pop(draft_key, None)
            st.success("Resposta salva no banco. O autor poderá consultá-la no perfil.")


def render_campaign_editor(st, config):
    st.subheader("Publicar campanha e missões")
    if not community_enabled():
        st.info("A edição compartilhada será liberada após a ativação do banco. A campanha atual é a configuração de referência do projeto.")
        return
    try:
        store = community_store()
        snapshot = store.campaign()
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    key = "community_campaign_draft"
    reload = st.button("Recarregar campanha publicada", key="community_campaign_reload")
    if key not in st.session_state or reload:
        initial = snapshot or {"revision": None, "record": json.loads(
            (config.project_root / "config" / "campaigns.json").read_text(encoding="utf-8"))}
        st.session_state[key] = {**copy.deepcopy(initial), "form_id": uuid4().hex}
    draft = st.session_state[key]
    payload = copy.deepcopy(draft["record"])
    st.caption("Revisão " + str(draft["revision"]) if draft["revision"] is not None else "Primeira publicação: revise a campanha de referência.")
    with st.form("community_campaign_" + draft["form_id"]):
        payload["title"] = st.text_input("Nome da campanha", payload["title"], max_chars=120)
        payload["public_message"] = st.text_area("Mensagem para a comunidade", payload["public_message"], max_chars=2000)
        for index, mission in enumerate(payload["missions"]):
            with st.expander(mission["title"]):
                mission["title"] = st.text_input("Título da missão", mission["title"], max_chars=120, key=f"{draft['form_id']}_title_{index}")
                mission["description"] = st.text_area("Objetivo", mission["description"], max_chars=1000, key=f"{draft['form_id']}_desc_{index}")
                mission["proof_hint"] = st.text_area("Orientação da evidência", mission["proof_hint"], max_chars=1000, key=f"{draft['form_id']}_proof_{index}")
                mission["points"] = st.number_input("Pontos educativos", min_value=0, max_value=10000,
                    value=mission["points"], step=1, key=f"{draft['form_id']}_points_{index}")
        publish = st.form_submit_button("Publicar para todos")
    if publish:
        try:
            store.publish_campaign(payload, expected_revision=draft["revision"], **credentials(st))
        except (ValueError, PermissionError, OSError) as exc:
            st.error(str(exc))
        else:
            st.session_state.pop(key, None)
            st.success("Campanha publicada. Participantes verão a atualização ao recarregar o app. Pontos já concedidos não são alterados.")
