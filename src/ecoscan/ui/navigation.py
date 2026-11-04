"""Single source of truth for citizen and analyst navigation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationSpec:
    analysis: str
    campaign: str
    report: str
    collection: str
    account: str
    tabs: tuple[str, ...]


def navigation_for(*, admin: bool) -> NavigationSpec:
    if admin:
        return NavigationSpec(
            analysis="Análise",
            campaign="Campanha",
            report="Denúncia",
            collection="Pontos de coleta",
            account="Conta",
            tabs=(
                "Análise", "Gestão", "Conclusão", "Campanha", "Denúncia",
                "Pontos de coleta", "Conta", "Processamento", "Base de imagens",
                "Histórico", "Sistema", "Aprender",
            ),
        )
    return NavigationSpec(
        analysis="Escanear",
        campaign="Missões",
        report="Denunciar",
        collection="Mapa",
        account="Perfil",
        tabs=("Escanear", "Mapa", "Descarte", "Aprender", "Missões", "Denunciar", "Perfil"),
    )
