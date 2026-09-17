from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class DeploymentCheck:
    item: str
    status: str
    evidence: str
    detail: str
    next_step: str


@dataclass(frozen=True)
class FreeHostingPlan:
    recommended_platform: str
    entrypoint: str
    expected_url: str
    can_use_camera_photo: bool
    live_mode_available: bool
    summary: str
    checks: tuple[DeploymentCheck, ...]
    steps: tuple[str, ...]
    limitations: tuple[str, ...]


def build_free_hosting_plan(config: AppConfig) -> FreeHostingPlan:
    root = Path(config.project_root)
    checks = (
        _file_check(
            root / "streamlit_app.py",
            "Entrada Streamlit na raiz",
            "O Streamlit Cloud deve apontar para este arquivo.",
            "Criar wrapper na raiz chamando ecoscan.ui.streamlit_app.main().",
        ),
        _requirements_check(root / "requirements.txt"),
        _file_check(
            root / "runtime.txt",
            "Versão de Python declarada",
            "Fixa o runtime recomendado para reduzir surpresa na nuvem.",
            "Manter Python 3.12 enquanto o projeto usa dependências científicas leves.",
        ),
        _file_check(
            root / ".streamlit" / "config.toml",
            "Configuração Streamlit",
            "Define execução headless e configurações base do servidor.",
            "Manter configuração simples para Community Cloud.",
        ),
        _model_check(root / "models" / "vision_classifier.npz", "Modelo visual leve"),
        _model_check(root / "models" / "baseline_classifier.json", "Modelo baseline reserva"),
        _gitignore_model_check(root / ".gitignore"),
        DeploymentCheck(
            item="Login e autorização da secretaria",
            status="attention",
            evidence="docs/autenticacao.md; .streamlit/secrets.example.toml",
            detail="A gestão exige identidade OIDC e e-mail verificado autorizado. Configuração no provedor e teste de login ainda precisam ser confirmados no ambiente publicado.",
            next_step="Configurar Secrets, cadastrar contas da secretaria e testar acesso autorizado e negado.",
        ),
        DeploymentCheck(
            item="Persistência dos dados do grupo",
            status="attention",
            evidence="reports; config/campaigns.json",
            detail="Dados operacionais ainda usam arquivos locais. A existência dos arquivos não garante persistência após uma nova implantação.",
            next_step="Conectar armazenamento persistente e validar restauração antes de uso institucional.",
        ),
        DeploymentCheck(
            item="Modo câmera ao vivo separado",
            status="attention",
            evidence="src/ecoscan/live_camera/server.py; porta 8765",
            detail="A hospedagem gratuita do Streamlit publica o app principal; o servidor Live separado não deve ser tratado como disponível na mesma URL.",
            next_step="No deploy grátis, usar upload/câmera do Streamlit. Manter EcoScan Live para rede local ou backend HTTPS dedicado.",
        ),
    )
    ready = all(check.status == "ok" for check in checks if check.item != "Modo câmera ao vivo separado")
    summary = (
        "Projeto pronto para publicar no Streamlit Community Cloud como app gratuito, com uso por link HTTPS."
        if ready
        else "Projeto quase pronto; revise os itens em atenção antes de publicar."
    )
    return FreeHostingPlan(
        recommended_platform="Streamlit Community Cloud",
        entrypoint="streamlit_app.py",
        expected_url="https://NOME-DO-APP.streamlit.app",
        can_use_camera_photo=True,
        live_mode_available=False,
        summary=summary,
        checks=checks,
        steps=(
            "Criar ou usar uma conta no GitHub.",
            "Subir a pasta do projeto para um repositório GitHub.",
            "Confirmar que requirements.txt, runtime.txt, .streamlit/config.toml, streamlit_app.py e os modelos leves foram enviados.",
            "Entrar em https://share.streamlit.io e criar um novo app.",
            "Selecionar repositório, branch principal e arquivo streamlit_app.py.",
            "Configurar login OIDC e lista de administradores em Secrets, conforme docs/autenticacao.md.",
            "Publicar e compartilhar a URL HTTPS gerada com o grupo.",
            "No celular, testar primeiro upload/câmera do app; registrar erros na aba Perfil para reforçar o reconhecimento.",
        ),
        limitations=(
            "Não subir data/raw completo para o GitHub; usar apenas modelos leves e configurações.",
            "O reconhecimento ainda é orientativo até o dataset final ser curado e o modelo definitivo passar pela governança.",
            "O EcoScan Live em tempo real usa outro servidor local; em hospedagem gratuita, priorize foto/câmera do Streamlit.",
            "Arquivos gerados em reports/logs na nuvem podem ser temporários; registros oficiais devem ser exportados periodicamente.",
        ),
    )


def deployment_check_rows(checks: Iterable[DeploymentCheck]) -> list[dict[str, str]]:
    return [
        {
            "item": check.item,
            "status": check.status,
            "evidência": check.evidence,
            "detalhe": check.detail,
            "próximo_passo": check.next_step,
        }
        for check in checks
    ]


def format_free_hosting_markdown(plan: FreeHostingPlan) -> str:
    lines = [
        "# Hospedagem gratuita - EcoScan",
        "",
        f"- Plataforma recomendada: {plan.recommended_platform}.",
        f"- Arquivo de entrada: `{plan.entrypoint}`.",
        f"- URL esperada: `{plan.expected_url}`.",
        f"- Câmera/foto no app principal: {'sim' if plan.can_use_camera_photo else 'não'}.",
        f"- EcoScan Live separado na hospedagem grátis: {'sim' if plan.live_mode_available else 'não'}.",
        "",
        "## Passos",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(plan.steps, start=1))
    lines.extend(["", "## Checklist", "", "| Item | Status | Evidência | Próximo passo |", "|---|---:|---|---|"])
    for check in plan.checks:
        lines.append(f"| {check.item} | {check.status} | `{check.evidence}` | {check.next_step} |")
    lines.extend(["", "## Limitações", ""])
    lines.extend(f"- {item}" for item in plan.limitations)
    lines.append("")
    return "\n".join(lines)


def _file_check(path: Path, item: str, ok_detail: str, next_step: str) -> DeploymentCheck:
    return DeploymentCheck(
        item=item,
        status="ok" if path.exists() else "attention",
        evidence=str(path),
        detail=ok_detail if path.exists() else "Arquivo não encontrado.",
        next_step="Nenhuma ação necessária." if path.exists() else next_step,
    )


def _requirements_check(path: Path) -> DeploymentCheck:
    if not path.exists():
        return DeploymentCheck(
            item="Dependências Python",
            status="attention",
            evidence=str(path),
            detail="requirements.txt não encontrado.",
            next_step="Criar requirements.txt com Streamlit e bibliotecas de processamento.",
        )
    text = path.read_text(encoding="utf-8").lower()
    has_streamlit = "streamlit" in text
    has_headless_cv = "opencv-python-headless" in text
    status = "ok" if has_streamlit and has_headless_cv else "attention"
    detail = (
        "Dependências incluem Streamlit e OpenCV headless, adequado para servidor sem interface gráfica."
        if status == "ok"
        else "Revise Streamlit e opencv-python-headless para reduzir falhas de build na nuvem."
    )
    return DeploymentCheck(
        item="Dependências Python",
        status=status,
        evidence=str(path),
        detail=detail,
        next_step="Nenhuma ação necessária." if status == "ok" else "Usar opencv-python-headless e manter Streamlit declarado.",
    )


def _model_check(path: Path, item: str) -> DeploymentCheck:
    return DeploymentCheck(
        item=item,
        status="ok" if path.exists() else "attention",
        evidence=str(path),
        detail="Modelo encontrado para deploy." if path.exists() else "Modelo não encontrado no workspace.",
        next_step=(
            "Confirmar que este arquivo será enviado ao GitHub."
            if path.exists()
            else "Gerar ou copiar um modelo leve antes de publicar."
        ),
    )


def _gitignore_model_check(path: Path) -> DeploymentCheck:
    if not path.exists():
        return DeploymentCheck(
            item="Modelos liberados no Git",
            status="attention",
            evidence=str(path),
            detail=".gitignore não encontrado.",
            next_step="Permitir os modelos leves e continuar ignorando datasets brutos.",
        )
    text = path.read_text(encoding="utf-8")
    required = {"!models/vision_classifier.npz", "!models/baseline_classifier.json"}
    missing = sorted(required - set(line.strip() for line in text.splitlines()))
    return DeploymentCheck(
        item="Modelos liberados no Git",
        status="ok" if not missing else "attention",
        evidence=str(path),
        detail="Modelos leves estão liberados para commit." if not missing else "Faltam exceções: " + ", ".join(missing),
        next_step="Nenhuma ação necessária." if not missing else "Adicionar exceções para os modelos leves.",
    )
