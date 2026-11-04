"""Public recognition scope and safe disposal shortcuts."""


def render_scope(st):
    with st.expander("Quais itens posso testar?"):
        st.write("Piloto com seis categorias. As respostas são sugestões e precisam de confirmação.")
        st.write("Latas de bebida e conserva vazias; garrafas PET; frascos e potes plásticos rígidos vazios; caixas de papelão; folhas de papel e jornal; garrafas e potes de vidro inteiros; pilhas AA/AAA; celular, mouse e carregador de celular.")
        st.caption("Alimentos e resíduos orgânicos não são reconhecidos. Lâmpadas, remédios, óleo, aerossóis e embalagens químicas ficam fora da identificação automática desta etapa. Uma foto não confirma o conteúdo de uma embalagem.")
        st.write("Eletrônicos prioritários: celular, mouse e carregador de celular. Outros aparelhos precisam de orientação específica e não têm reconhecimento validado neste piloto.")
        st.caption("Amassados e papelão dobrado fazem parte dos testes previstos. Informe o estado ao reportar uma foto. Cacos soltos, baterias de outros formatos e fragmentos sem identificação ficam fora do reconhecimento automático inicial. Fotografe um objeto principal por vez.")
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
