"""Material education, source references and formative assessment."""
from pathlib import Path

from ecoscan.services.engagement import CATALOG, LESSONS, award_quiz


def render_education(st, project_root, profile=None, ledger_path=None):
    st.subheader("Aprender para transformar")
    st.write("Reduza o que consome, reutilize quando for seguro e encaminhe cada resíduo à rota correta.")
    key = st.selectbox("Material", list(LESSONS), format_func=lambda k: LESSONS[k]["title"], key="education_material")
    lesson = LESSONS[key]
    st.image(str(Path(project_root) / "assets" / "disposal_targets" / lesson["asset"]), width=120)
    st.markdown("### " + lesson["title"])
    st.write(lesson["examples"])
    if not lesson["recognition"]:
        st.caption("Orientação educativa. Este material não está no reconhecimento automático.")
    impact, action, challenge = st.tabs(["Impacto", "Descarte", "Desafio"])
    with impact:
        st.markdown("#### Quando vai para o lugar errado")
        st.write(lesson["harm"])
        st.markdown("#### O que muda com o destino correto")
        st.write(lesson["benefit"])
        st.markdown("#### A próxima vida do material")
        st.write(lesson["cycle"])
    with action:
        for index, step in enumerate(lesson["steps"], 1):
            st.write(f"{index}. {step}")
        st.warning(lesson["avoid"])
    with challenge:
        st.caption("10 pontos por material, uma vez por conta.")
        answer = st.radio(lesson["question"], range(len(lesson["options"])),
                          format_func=lambda i: lesson["options"][i], index=None, key=f"quiz_{key}")
        if st.button("Conferir resposta", key=f"quiz_check_{key}", disabled=answer is None, icon=":material/check:"):
            if answer != lesson["answer"]:
                st.warning("Ainda não. " + lesson["explanation"])
            else:
                st.success(lesson["explanation"])
                if profile is None or profile.id.startswith("visitor_") or ledger_path is None:
                    st.info("Entre em sua conta para registrar os 10 pontos. Visitantes podem praticar sem salvar.")
                else:
                    try:
                        award_quiz(ledger_path, user_id=profile.id, material=key, answer=answer)
                        st.success("+10 pontos educativos registrados no seu perfil.")
                    except (ValueError, OSError) as exc:
                        st.info(str(exc))
        st.caption("Uma pontuação por material e conta. Repetir a leitura e o desafio continua disponível.")
    with st.expander("Fontes e critérios"):
        for label, url in lesson["sources"]:
            st.link_button(label, url)
        st.caption("Revisão: " + CATALOG["reviewed_at"] + ". Aceitação e tratamento dependem do operador.")
        st.write("Pontos reconhecem participação educativa; não medem massa reciclada, emissões evitadas ou entrega física. Esses resultados exigem comprovantes e acompanhamento com os operadores.")
