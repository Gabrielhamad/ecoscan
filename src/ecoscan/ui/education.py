"""Evidence-based citizen education, without claiming measured app impact."""
from pathlib import Path


LESSONS = {
    "plastic": ("Plástico e PET", "plastic_red_bin.png",
        "Separar por material e retirar restos de produto ajuda a recuperar plástico que seria rejeitado na triagem.",
        "Garrafas PET podem virar novas embalagens, fibras têxteis e peças. O destino depende da resina, da limpeza e do processo industrial; nem todo plástico segue o mesmo ciclo.",
        "Esvazie e retire o excesso de resíduos. Consulte a aceitação local. Garrafa com óleo ou produto químico não deve receber a orientação de uma embalagem vazia.",
        "ABIPET · revalorização", "https://abipet.org.br/revalorizacao/"),
    "metal": ("Latas e metais", "metal_yellow_bin.png",
        "Recuperar alumínio reduz a demanda de produção primária. A ABAL informa consumo de cerca de 5% da energia elétrica do processo primário na reciclagem de alumínio; isso não é uma economia medida pelo EcoScan.",
        "O metal recuperado volta como matéria-prima para novos produtos, incluindo embalagens. Latas de aço e de alumínio têm cadeias diferentes.",
        "Esvazie a embalagem e evite manusear bordas cortantes. Aerossóis e embalagens contaminadas exigem orientação específica.",
        "ABAL · reciclagem e energia", "https://abal.org.br/noticia/abal-assina-protocolo-para-elaboracao-de-plano-de-descarbonizacao-com-o-ministerio-do-meio-ambiente/"),
    "paper_cardboard": ("Papel e papelão", "paper_blue_bin.png",
        "Manter o papel seco e separado de alimentos preserva fibras aproveitáveis e reduz perdas na cadeia de triagem.",
        "As fibras recuperadas podem integrar novos papéis e embalagens. As fibras se degradam ao longo dos ciclos; por isso a reciclagem não é ilimitada e pode exigir fibras novas.",
        "Dobre caixas para reduzir volume. Não misture papel sanitário, engordurado ou contaminado com papel limpo.",
        "Ibá · economia circular", "https://iba.org/sustentabilidade/economia-circular/"),
    "glass": ("Garrafas e potes de vidro", "glass_green_bin.png",
        "A triagem adequada permite reaproveitar o vidro de embalagem como matéria-prima, evitando misturar materiais incompatíveis.",
        "Cacos de embalagens corretamente separados podem voltar à fabricação de garrafas e potes. Cerâmica, espelhos e outros tipos de vidro não devem ser tratados como equivalentes.",
        "Não quebre o vidro de propósito. Para cacos, consulte o ponto sobre acondicionamento seguro e sinalize o material cortante.",
        "Abividro · guia técnico", "https://abividro.org.br/sustentabilidade/"),
    "battery": ("Pilhas e baterias", "battery_orange_dropoff.png",
        "A logística reversa direciona o material a tratamento especializado e evita o descarte junto aos recicláveis comuns.",
        "Conforme a composição e a tecnologia de tratamento, podem ser recuperados metais e compostos como zinco, sais e óxidos metálicos. Há rejeitos que precisam de destinação adequada.",
        "Não abra nem desmonte. Procure um coletor que aceite o tipo de bateria. Material danificado ou com vazamento exige orientação do fabricante ou operador.",
        "SINIR · pilhas e baterias", "https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/pilhas-e-baterias/"),
    "electronic": ("Pequenos eletrônicos", "electronic_orange_dropoff.png",
        "O manejo inadequado pode contaminar água e solo, conforme a composição, e causar incêndios ou danos à saúde.",
        "A cadeia especializada pode encaminhar componentes para reutilização, reciclagem e recuperação de materiais; o que não é recuperável exige disposição adequada.",
        "Priorize conserto ou doação quando possível. Apague dados pessoais antes de entregar um celular. Não desmonte aparelhos para separar materiais em casa.",
        "SINIR · eletroeletrônicos", "https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/eletroeletronicos/"),
}


def render_education(st, project_root):
    st.subheader("Cada material tem um próximo destino")
    key = st.selectbox("O que você quer conhecer?", list(LESSONS),
                       format_func=lambda item: LESSONS[item][0], key="education_material")
    name, asset, why, becomes, action, source, url = LESSONS[key]
    st.image(str(Path(project_root) / "assets" / "disposal_targets" / asset), width=140)
    st.markdown("### " + name)
    st.markdown("**Por que separar**")
    st.write(why)
    st.markdown("**O que pode virar**")
    st.write(becomes)
    st.markdown("**Sua próxima ação**")
    st.write(action)
    st.link_button(source, url)
    st.caption("Fontes consultadas em 20/09/2026. O destino depende da composição e da aceitação pelo operador.")
    with st.expander("O que o EcoScan pode ajudar a melhorar"):
        st.write("Orientação por material, consulta de destinos e missões educativas podem ajudar a separar melhor os resíduos. Reportes revisados pela secretaria podem melhorar a base de avaliação do reconhecimento.")
        st.warning("Foto analisada, ponto consultado ou missão pontuada não comprova reciclagem. Ainda não medimos redução de emissões, massa reciclada ou renda gerada pelo app.")
        st.write("Para avaliar resultados, compare acertos antes e depois das orientações; acompanhe reportes resolvidos e, com parceiros e consentimento, entregas e massas efetivamente recebidas. Compare períodos ou grupos equivalentes e registre limitações.")
        st.link_button("Ipea · estudo de benefícios da reciclagem (2010)",
                       "https://repositorio.ipea.gov.br/bitstreams/51fe3ce8-2ad2-4313-b05f-16b4648abbe2/download")
        st.caption("O estudo do Ipea analisa benefícios econômicos e ambientais e serviços ambientais urbanos. Suas estimativas nacionais e históricas não são resultados atribuíveis ao EcoScan.")
    with st.expander("Óleo e medicamentos também precisam de cuidado"):
        st.write("Não estão no reconhecimento automático. Consulte Descarte para a orientação específica e pontos de logística reversa. Não despeje esses materiais na rede de esgoto.")
