"""Non-consumable digital achievements, no implied municipal entitlement."""
import html


def render_rewards(st, campaign, points, profile):
    st.caption("Pontos educativos, sem valor monetário. Selos não comprovam reciclagem nem concedem benefícios públicos. Não é necessário comprar ou gerar resíduos.")
    for reward in sorted(campaign.rewards, key=lambda r: r.points_required):
        st.markdown("#### " + reward.title)
        st.write(reward.description)
        if reward.kind != "digital_badge":
            st.info("Planejado, sem resgate disponível. Depende de parceiro, autorização, estoque e regulamento.")
            continue
        unlocked = not profile.id.startswith("visitor_") and points >= reward.points_required
        st.progress(min(1.0, max(0, points) / max(1, reward.points_required)),
                    text="Conquistado" if unlocked else f"{max(0, reward.points_required - points)} pontos para conquistar")
        if unlocked:
            name, title = html.escape(profile.display_name), html.escape(reward.title)
            content = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>EcoScan · {title}</title>
<style>body{{font:18px/1.7 system-ui,sans-serif;max-width:640px;margin:48px auto;padding:24px;color:#183c31;background:#f2f7f5}}h1{{color:#176b4f}}small{{display:block;color:#46574f}}</style>
<main><p>ECOSCAN · EDUCAÇÃO AMBIENTAL</p><h1>{title}</h1><h2>{name}</h2>
<p>Reconhecimento digital por participação educativa: {points} pontos no momento da emissão.</p>
<small>Sem valor monetário ou certificação profissional. Não comprova entrega de resíduos, vínculo governamental ou benefício municipal.</small></main></html>'''
            st.download_button("Baixar selo digital", content, file_name="ecoscan-selo.html",
                               mime="text/html", key=f"badge_{reward.id}", icon=":material/download:")
    with st.expander("Incentivos materiais: proposta para parceiros"):
        st.write("Oficinas de reparo e reutilização, visitas educativas a cooperativas e kits duráveis podem compor futuras campanhas. Mudas só com orientação de espécie, local e cuidado. Não há convênios ou resgates materiais ativos.")
        st.write("Antes de ofertar: responsável, parceiro confirmado, validade, estoque, regra inclusiva de acesso, comprovante de entrega e registro de resgate. Benefícios não devem incentivar compras, coleta arriscada nem competição por peso de lixo.")
