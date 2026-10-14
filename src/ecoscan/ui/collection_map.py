"""Capital-only collection directory and official schedule consultation."""
from ecoscan.disposal.collection_points import (
    build_collection_point_directions_url, filter_collection_points,
)
from ecoscan.disposal.postal_lookup import (
    COLLECTION_PORTALS, OFFICIAL_MAP, OFFICIAL_POINTS, lookup_capital_cep,
)


def render_collection_map(st, points, guidance):
    st.subheader("Descarte em São Paulo")
    mode = st.segmented_control("Consulta", ["Pontos de entrega", "Coleta na minha rua"],
                                default="Pontos de entrega", key="collection_mode")
    with st.form("collection_postcode"):
        cep = st.text_input("Seu CEP", max_chars=9, placeholder="01001-000")
        st.caption("Ao consultar, somente o CEP é enviado ao ViaCEP. O endereço não é salvo no perfil.")
        submitted = st.form_submit_button("Consultar CEP", icon=":material/search:")
    if submitted:
        st.session_state.pop("collection_address", None)
        try:
            with st.spinner("Consultando endereço..."):
                st.session_state["collection_address"] = lookup_capital_cep(cep)
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    address = st.session_state.get("collection_address")
    if address:
        st.success(address.full_address)
        if not address.street:
            st.info("Este CEP não identifica uma rua. Informe também rua e número no portal de coleta.")
    if mode == "Coleta na minha rua":
        st.markdown("### Dias e períodos do caminhão")
        st.info("Horário ainda não consultado. O CEP identifica o endereço; a programação depende da rua e do trecho. Consulte o serviço oficial com o número do imóvel.")
        st.write("Loga: Centro, Norte, Oeste e parte da Leste. Ecourbis: Sul e parte da Leste. A divisão é por área de atendimento, não apenas pelo nome da zona.")
        if address:
            st.code(address.full_address, language=None)
        for label, url in COLLECTION_PORTALS.items():
            st.link_button(label, url, icon=":material/open_in_new:", width="stretch")
        st.caption("Coleta comum, seletiva e cata-bagulho são serviços diferentes. Confirme o serviço, dia e período; não há rastreamento de caminhões neste app.")
        st.link_button("SP Regula · orientação e concessionárias", "https://prefeitura.sp.gov.br/spregula/w/residuos_solidos/residuos_solidos/domiciliar/4636")
        return
    points = [p for p in points if p.city == "São Paulo" and p.state == "SP"]
    regions = ["Todas", "Centro", "Norte", "Sul", "Leste", "Oeste"]
    region = st.selectbox("Região", regions, key="collection_region")
    material = st.selectbox("Material", ["all", "plastic", "metal", "paper_cardboard", "glass", "battery", "electronic", "oil", "medicine"],
                            format_func=lambda key: {"all": "Todos os recicláveis secos", "oil": "Óleo de cozinha", "medicine": "Medicamentos"}.get(key, guidance[key].display_name if key in guidance else key), key="collection_material")
    query = st.text_input("Bairro, rua, nome ou CEP do ponto", key="collection_search")
    candidates = [p for p in points if region == "Todas" or p.region == region]
    candidates = filter_collection_points(candidates, class_id=None if material == "all" else material, city_query=query)
    st.caption(f"{len(candidates)} unidades na seleção · lista parcial · endereços conferidos em 14/10/2026. Ordem alfabética, não por proximidade.")
    if st.toggle("Exibir mapa da Prefeitura", key="collection_show_map"):
        import streamlit.components.v1 as components
        st.caption("Mapa externo Google My Maps, publicado pela Prefeitura; possui filtros próprios e não acompanha a lista abaixo. Ao abrir, sua conexão é compartilhada com o provedor.")
        components.iframe(OFFICIAL_MAP, height=420, scrolling=True)
    st.link_button("Rede completa e situação das unidades", OFFICIAL_POINTS, icon=":material/map:", width="stretch")
    if not candidates:
        st.info("Nenhuma unidade compatível nesta seleção. Ecopontos não são destino universal de resíduos especiais.")
        urls = {
            "battery": "https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/pilhas-e-baterias/",
            "electronic": "https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/eletroeletronicos/",
            "oil": "https://www.sabesp.com.br/o-que-fazemos/obras-programas/reciclagem-oleo",
            "medicine": "https://www.cofen.gov.br/medicamentos-nao-devem-ser-descartados-em-lixos-comuns/",
        }
        if material in urls:
            st.link_button("Consultar orientação da rede especializada", urls[material], width="stretch")
        return
    for point in sorted(candidates, key=lambda p: p.name):
        with st.expander(f"{point.name} · {point.region}"):
            st.write(point.full_address)
            st.write(point.hours)
            st.write("Recebe: " + ", ".join(point.accepted_materials))
            st.caption(point.limit_note + " " + point.notes)
            st.link_button("Traçar rota", build_collection_point_directions_url(point, origin=address.full_address if address else None), icon=":material/directions:", width="stretch")
            st.link_button("Conferir na fonte oficial", point.source_url)
