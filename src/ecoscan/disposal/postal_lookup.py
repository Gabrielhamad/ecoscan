"""Address lookup only: a postcode never implies a truck timetable."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


COLLECTION_PORTALS = {
    "Loga · coleta comum e seletiva": "https://sgo3.loga.com.br/consultav2/",
    "Ecourbis · coleta comum e seletiva": "https://www.ecourbis.com.br/coleta/index.html",
    "Cata-bagulho · Prefeitura": "https://coleta.prefeitura.sp.gov.br/",
}
OFFICIAL_MAP = "https://www.google.com/maps/d/embed?ehbc=2E312F&mid=1Kok7L5JyjXN758y3vy3kMsKYdJylrQE"
OFFICIAL_POINTS = "https://prefeitura.sp.gov.br/web/subprefeituras/w/ecoponto-esta%C3%A7%C3%A3o-de-entrega-volunt%C3%A1ria-de-inserv%C3%ADveis"


@dataclass(frozen=True)
class PostalAddress:
    cep: str
    street: str
    neighborhood: str

    @property
    def full_address(self) -> str:
        return ", ".join(p for p in (self.street, self.neighborhood, "São Paulo - SP", self.cep) if p)


def normalize_cep(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[0-9]{5}-?[0-9]{3}", value):
        raise ValueError("Informe um CEP com 8 números, como 01001-000.")
    return value.replace("-", "")


def lookup_capital_cep(value: str) -> PostalAddress:
    cep = normalize_cep(value)
    request = Request(f"https://viacep.com.br/ws/{cep}/json/", headers={"User-Agent": "EcoScan/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(16385)
        if len(payload) > 16384:
            raise ValueError("Resposta excessiva")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Formato inesperado")
    except (URLError, OSError, ValueError):
        raise OSError("Consulta de CEP indisponível. Tente novamente ou use os portais oficiais abaixo.") from None
    if data.get("erro"):
        raise ValueError("CEP não encontrado. Confira os números.")
    if data.get("ibge") != "3550308" or data.get("uf") != "SP":
        raise ValueError("Esta consulta atende somente o município de São Paulo, não toda a Grande SP.")
    fields = [data.get(key, "") for key in ("logradouro", "bairro")]
    if any(not isinstance(field, str) or len(field) > 300 for field in fields):
        raise OSError("Endereço inválido na resposta do serviço. Consulte pelo portal oficial.")
    return PostalAddress(cep[:5] + "-" + cep[5:], *fields)
