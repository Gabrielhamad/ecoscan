import io
import json
from unittest.mock import patch

import pytest

from ecoscan.disposal.postal_lookup import lookup_capital_cep, normalize_cep
from ecoscan.disposal.collection_points import filter_collection_points, load_collection_points, rank_collection_points
from ecoscan.config import PROJECT_ROOT


@pytest.mark.parametrize("value", ["123", "abcdefgh", "01001000/evil", "０１００１０００", "https://evil"])
def test_rejects_invalid_cep_without_network(value):
    with patch("ecoscan.disposal.postal_lookup.urlopen") as client:
        with pytest.raises(ValueError):
            lookup_capital_cep(value)
        client.assert_not_called()


def test_address_never_infers_schedule():
    data = {"ibge": "3550308", "uf": "SP", "logradouro": "Praça da Sé", "bairro": "Sé"}
    with patch("ecoscan.disposal.postal_lookup.urlopen", return_value=io.BytesIO(json.dumps(data).encode())) as client:
        result = lookup_capital_cep("01001-000")
    assert result.cep == "01001-000"
    assert "São Paulo" in result.full_address
    assert not hasattr(result, "schedule")
    assert client.call_args.kwargs['timeout'] == 8
    assert client.call_args.args[0].full_url == "https://viacep.com.br/ws/01001000/json/"


@pytest.mark.parametrize("payload, error", [
    ({"erro": True}, ValueError), ({"uf": "SP", "ibge": "3543402"}, ValueError),
    ([], OSError), ({"uf": "SP", "ibge": "3550308", "bairro": []}, OSError),
])
def test_handles_missing_outside_capital_and_bad_responses(payload, error):
    with patch("ecoscan.disposal.postal_lookup.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
        with pytest.raises(error):
            lookup_capital_cep("01001000")


def test_timeout_is_actionable():
    with patch("ecoscan.disposal.postal_lookup.urlopen", side_effect=TimeoutError):
        with pytest.raises(OSError, match="indisponível"):
            lookup_capital_cep("01001000")


def test_directory_accepts_unaccented_name_and_postcode():
    points = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")
    assert filter_collection_points(points, city_query="Freguesia do O")
    assert filter_collection_points(points, city_query="01001") == []
    assert filter_collection_points(points, city_query="02029000")[0].name == "Ecoponto Santana"


def test_zero_distance_sorts_first():
    from dataclasses import replace
    point = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")[0]
    zero = replace(point, name="Zero", latitude=-23.5, longitude=-46.6)
    other = replace(point, name="Other", latitude=-23.6, longitude=-46.6)
    assert rank_collection_points([other, zero], user_latitude=-23.5, user_longitude=-46.6)[0].point.name == "Zero"
