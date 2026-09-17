from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessLink:
    label: str
    audience: str
    url: str
    note: str


@dataclass(frozen=True)
class ServiceStatus:
    label: str
    url: str
    ok: bool
    note: str


@dataclass(frozen=True)
class AccessPlan:
    lan_ip: str
    streamlit_port: int
    live_port: int
    local_links: tuple[AccessLink, ...]
    network_links: tuple[AccessLink, ...]
    notes: tuple[str, ...]
    test_steps: tuple[str, ...]


def detect_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = str(sock.getsockname()[0])
            if address and not address.startswith("127."):
                return address
    except OSError:
        pass

    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            if address and not address.startswith("127."):
                return str(address)
    except OSError:
        pass
    return "127.0.0.1"


def build_access_plan(
    *,
    lan_ip: str | None = None,
    streamlit_port: int = 8501,
    live_port: int = 8765,
) -> AccessPlan:
    resolved_lan_ip = lan_ip or detect_lan_ip()
    local_base = f"http://localhost:{streamlit_port}"
    network_base = f"http://{resolved_lan_ip}:{streamlit_port}"
    local_live = f"http://localhost:{live_port}/"
    network_live = f"http://{resolved_lan_ip}:{live_port}/"
    return AccessPlan(
        lan_ip=resolved_lan_ip,
        streamlit_port=streamlit_port,
        live_port=live_port,
        local_links=(
            AccessLink("Usuário neste PC", "demonstração local", f"{local_base}/?profile=usuario_demo", "Fluxo cidadão completo."),
            AccessLink("Admin neste PC", "secretaria", f"{local_base}/?profile=admin_secretaria", "Gestão, qualidade e relatórios."),
            AccessLink("Câmera ao vivo neste PC", "teste técnico", local_live, "Rastreamento em tempo real."),
        ),
        network_links=(
            AccessLink("Usuário no celular", "grupo na mesma rede", f"{network_base}/?profile=usuario_demo", "Use no Wi-Fi do mesmo roteador."),
            AccessLink("Admin na rede", "gestão em outro PC", f"{network_base}/?profile=admin_secretaria", "Painel administrativo em rede local."),
            AccessLink("Câmera ao vivo na rede", "teste mobile", network_live, "Pode exigir HTTPS no navegador do celular."),
        ),
        notes=(
            "Todos os aparelhos precisam estar na mesma rede Wi-Fi para usar o endereço local da rede.",
            "Upload de foto funciona em HTTP; câmera ao vivo no navegador do celular geralmente exige HTTPS.",
            "Para testar fora da rede da casa/faculdade, publique em HTTPS ou use um túnel HTTPS controlado.",
            "Cada erro de reconhecimento deve ser corrigido no app para virar evidência de melhoria do modelo.",
        ),
        test_steps=(
            "Abrir o link de usuário no celular ou PC.",
            "Testar pelo menos uma foto por classe prioritária: plástico, metal, vidro, papel, pilha/bateria, eletrônico, óleo e lâmpada.",
            "Registrar quando o app acertou, errou ou ficou inconclusivo.",
            "Quando errar, enviar correção pela área de feedback do reconhecimento.",
            "A secretaria deve revisar a aba Gestão para ver confusões críticas e classes para reforçar.",
        ),
    )


def probe_access_services(
    *,
    streamlit_port: int = 8501,
    live_port: int = 8765,
    timeout_seconds: float = 2.0,
) -> tuple[ServiceStatus, ...]:
    return (
        _probe("App principal", f"http://localhost:{streamlit_port}/", "Interface Streamlit do EcoScan.", timeout_seconds),
        _probe("Câmera ao vivo", f"http://localhost:{live_port}/health", "Servidor de rastreamento em tempo real.", timeout_seconds),
    )


def access_link_rows(plan: AccessPlan) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for link in (*plan.local_links, *plan.network_links):
        rows.append(
            {
                "link": link.label,
                "uso": link.audience,
                "url": link.url,
                "observação": link.note,
            }
        )
    return rows


def shareable_access_text(plan: AccessPlan) -> str:
    lines = [
        "EcoScan - links para teste",
        "",
        "Usuário:",
        plan.network_links[0].url,
        "",
        "Admin:",
        plan.network_links[1].url,
        "",
        "Observações:",
    ]
    lines.extend(f"- {note}" for note in plan.notes)
    return "\n".join(lines)


def _probe(label: str, url: str, note: str, timeout_seconds: float) -> ServiceStatus:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "EcoScanAccessPanel/1.0"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            ok = 200 <= int(response.status) < 500
    except (OSError, TimeoutError, urllib.error.URLError):
        ok = False
    return ServiceStatus(label=label, url=url, ok=ok, note=note)
