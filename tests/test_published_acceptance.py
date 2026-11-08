"""Technical fixtures never attest to production accounts or independent accuracy."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest

from ecoscan.services import published_acceptance as module
from ecoscan.services.acceptance_checks import _external_acceptance_checks
from scripts import audit_published_deployment as cli

SHA = 'a' * 40
URL = 'https://example.streamlit.app'
MODEL = {'scope': 'local_candidate_only_not_deployment',
         'configured_artifact': 'models/semantic-v1/semantic.json',
         **{key: 'b' * 64 for key in module.FINGERPRINT_KEYS},
         'threshold': .8, 'shards_verified': 3, 'remote_override_enabled': True,
         'confirmation_required': True}


def report():
    return module.new_report(SHA, URL, deepcopy(MODEL))


def metadata(**overrides):
    return {'at': datetime.now(timezone.utc).isoformat(), 'observed_sha': SHA,
            'browser': 'Chrome', 'browser_version': '156.0.0.1', 'evidence_ref': 'EVID-101', **overrides}


def test_required_devices_and_actors_start_pending_and_no_execution_is_invented():
    result = report()
    module.validate_report(result)
    assert len(result['cases']) == 31
    assert {row['status'] for row in result['cases']} == {'manual_pending'}
    assert {'PC', 'Android', 'iPhone'} <= {row['device'] for row in result['cases']}
    assert {'visitor', 'controlled_A_B', 'controlled_analyst'} <= {row['role'] for row in result['cases']}
    assert all(row['executed_at_utc'] is None for row in result['cases'])
    assert result['external_qa'] == {key: 'manual_pending' for key in module.EXTERNAL_QA}


@pytest.mark.parametrize('url', ['https://user:password@example.org', 'https://example.org?token=private',
                                'https://example.org/#access_token=private', 'https://example.org/recovery/secret',
                                'http://example.org', 'https://example.org:8443'])
def test_credential_or_non_origin_urls_are_rejected(url):
    with pytest.raises(ValueError):
        module.deployment_url(url)


def test_manual_record_requires_time_browser_evidence_and_candidate_match():
    with pytest.raises(ValueError):
        module.record_case(report(), 'pc_visitor', 'passed')
    with pytest.raises(ValueError, match='different SHA'):
        module.record_case(report(), 'pc_visitor', 'passed', **metadata(observed_sha='c' * 40))
    with pytest.raises(ValueError):
        module.record_case(report(), 'pc_visitor', 'passed', **metadata(evidence_ref='protocol-private'))
    with pytest.raises(ValueError):
        module.record_case(report(), 'pc_visitor', 'passed', **metadata(browser_version='citizen@example.org'))
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError):
        module.record_case(report(), 'pc_visitor', 'passed', **metadata(at=future))


def test_accounts_require_explicit_authorization_and_never_promote_qa():
    with pytest.raises(ValueError, match='authorization'):
        module.record_case(report(), 'pc_accounts', 'passed', **metadata())
    result = module.record_case(report(), 'pc_accounts', 'passed', authorization_confirmed=True, **metadata())
    module.validate_report(result)
    assert result['external_qa']['QA-18'] == 'manual_pending'
    assert result['formal_acceptance'] == 'manual_review_required'
    assert all(check.status == 'pending' for check in _external_acceptance_checks())


def test_runtime_model_requires_observed_hashes_and_keeps_qa09_pending():
    with pytest.raises(ValueError):
        module.record_case(report(), 'published_model', 'passed', **metadata())
    result = module.record_case(report(), 'published_model', 'passed', **metadata(),
                                runtime_fingerprint={key: MODEL[key] for key in module.FINGERPRINT_KEYS})
    module.validate_report(result)
    assert result['external_qa']['QA-09'] == 'manual_pending'


@pytest.mark.parametrize('case', ['extra_root', 'extra_case', 'private_model', 'wrong_gate', 'private_browser'])
def test_serialization_refuses_private_fields_or_inferred_approval(tmp_path, case):
    result = report()
    if case == 'extra_root':
        result['token'] = 'secret'
    elif case == 'extra_case':
        result['cases'][0]['protocol'] = 'private'
    elif case == 'private_model':
        result['local_model']['note'] = 'person@example.org'
    elif case == 'wrong_gate':
        result['external_qa']['QA-18'] = 'passed'
    else:
        result['cases'][0]['browser'] = 'private/person@example.org'
    with pytest.raises(ValueError):
        module.save_report(result, tmp_path / 'export')
    assert not (tmp_path / 'export').exists()


@pytest.mark.parametrize('http_status,expected', [(200, 'passed'), (303, 'manual_pending'),
                                                (403, 'manual_pending'), (503, 'failed')])
def test_http_status_does_not_attest_to_code_model_devices_or_accounts(http_status, expected, tmp_path):
    client = MagicMock()
    client.__enter__.return_value.get.return_value.__enter__.return_value.status_code = http_status
    with patch.object(cli.requests, 'Session', return_value=client):
        result = cli.http_observation(report())
    assert next(row for row in result['cases'] if row['id'] == 'http')['status'] == expected
    assert all(row['status'] == 'manual_pending' for row in result['cases'] if row['id'] != 'http')
    assert all(row['observed_sha'] is None for row in result['cases'])
    module.save_report(result, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {'acceptance.json', 'acceptance.md', 'acceptance.csv'}
    assert 'não comprovado' in (tmp_path / 'acceptance.md').read_text()
    assert b'\r' not in (tmp_path / 'acceptance.csv').read_bytes()


def test_network_error_never_echoes_signed_link_or_private_data(tmp_path):
    private = 'https://example.org?token=secret citizen@example.org /private/photo.png'
    with patch.object(cli.requests, 'Session', side_effect=OSError(private)):
        result = cli.http_observation(report())
    assert next(row for row in result['cases'] if row['id'] == 'http')['reason'] == 'network_unavailable'
    module.save_report(result, tmp_path)
    assert all(private not in path.read_text() for path in tmp_path.iterdir())


def test_existing_encoder_assembler_checks_parts_and_combined_hash(tmp_path):
    content = b'not a real encoder; integrity fixture only'
    (tmp_path / 'encoder_00.part').write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    model = {'encoder_file': 'encoder.onnx', 'encoder_sha256': digest,
             'parts': [{'name': 'encoder_00.part', 'sha256': digest}]}
    assert module.verified_encoder_hash(tmp_path, model) == digest
    assert not (tmp_path / 'encoder.onnx').exists()
    (tmp_path / 'encoder_00.part').write_bytes(b'changed')
    with pytest.raises(ValueError):
        module.verified_encoder_hash(tmp_path, model)
    model['parts'][0]['name'] = '../private'
    with pytest.raises(ValueError):
        module.verified_encoder_hash(tmp_path, model)


def test_cli_init_record_and_strict_check_remain_incomplete(tmp_path, capsys):
    output = tmp_path / 'smoke'
    with (patch.object(cli, 'inspect_candidate_model', return_value=deepcopy(MODEL)),
          patch.object(cli, 'error_privacy_observation', side_effect=lambda data: data)):
        assert cli.main(['init', '--candidate-sha', SHA, '--url', URL, '--output', str(output)]) == 0
    path = output / 'acceptance.json'
    assert cli.main(['check', '--report', str(path)]) == 2
    assert cli.main(['record', '--report', str(path), '--case', 'pc_visitor', '--status', 'passed',
                     '--at', module.utc_now(), '--observed-sha', SHA,
                     '--browser', 'Chrome', '--browser-version', '156.0.0.1', '--evidence', 'EVID-006']) == 0
    result = json.loads(path.read_text())
    assert next(row for row in result['cases'] if row['id'] == 'pc_visitor')['status'] == 'passed'
    assert result['external_qa']['QA-20'] == 'manual_pending'
    assert cli.main(['record', '--report', str(path), '--case', 'pc_accounts', '--status', 'passed']) == 1
    assert 'External QA gates are not approved' in capsys.readouterr().out


def test_all_manually_attested_cases_still_do_not_approve_formal_external_qa(tmp_path):
    result = report()
    for index, case in enumerate(module.CATALOG.values(), start=101):
        result = module.record_case(result, case.id, 'passed', **metadata(evidence_ref=f'EVID-{index}'),
                                    authorization_confirmed=True,
                                    runtime_fingerprint={key: MODEL[key] for key in module.FINGERPRINT_KEYS}
                                    if case.id == 'published_model' else None)
    module.save_report(result, tmp_path)
    assert all(row['status'] == 'passed' for row in result['cases'])
    assert cli.main(['check', '--report', str(tmp_path / 'acceptance.json')]) == 2
    assert result['external_qa']['QA-09'] == 'manual_pending'


def test_tls_browser_error_is_pending_with_no_raw_content_or_tls_bypass():
    from types import SimpleNamespace
    class BrowserError(Exception):
        pass
    manager = MagicMock()
    launch = manager.__enter__.return_value.chromium.launch
    browser = launch.return_value
    browser.version = '156.0.8078.79'
    private = 'ERR_CERT_AUTHORITY_INVALID token=secret /private/photo.png citizen@example.org'
    browser.new_page.return_value.goto.side_effect = BrowserError(private)
    stub = SimpleNamespace(sync_playwright=lambda: manager, Error=BrowserError, TimeoutError=BrowserError)
    with patch.dict('sys.modules', {'playwright': SimpleNamespace(), 'playwright.sync_api': stub}):
        result = cli.browser_observation(report())
    row = next(row for row in result['cases'] if row['id'] == 'browser')
    assert row['status'] == 'manual_pending' and row['reason'] == 'browser_tls_error'
    assert private not in json.dumps(result)
    assert 'ignore_https_errors' not in str(launch.call_args)
    browser.close.assert_called_once()


@pytest.mark.parametrize('exposes', [True, False])
def test_privacy_probe_detects_raw_detail_without_publishing_the_marker(exposes):
    def boundary(st, exc, *, context):
        if exposes:
            st.code(str(exc))
        else:
            st.error('APP-001')
    with patch('ecoscan.ui.common_views._render_user_error', side_effect=boundary):
        result = cli.error_privacy_observation(report())
    row = next(row for row in result['cases'] if row['id'] == 'local_error_privacy')
    assert row['status'] == ('failed' if exposes else 'passed')
    assert 'ECO_SCAN_SYNTHETIC_DETAIL_ONLY' not in json.dumps(result)
