"""Deployment smoke records: technical observations never approve external QA gates."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
from typing import Any, Literal

Status = Literal['passed', 'failed', 'manual_pending']
EXTERNAL_QA = ('QA-09', 'QA-18', 'QA-19', 'QA-20', 'QA-21')
REASONS = {'not_executed', 'no_device', 'no_authorized_account', 'no_real_photo',
           'revision_unverified', 'runtime_model_unverified', 'isolated_environment_required',
           'independent_evidence_required', 'network_unavailable', 'browser_tls_error',
           'browser_unavailable', 'application_not_rendered', 'revision_mismatch', 'observed_failure', 'raw_exception_exposed'}
BROWSERS = {'Chrome', 'Chromium', 'Edge', 'Firefox', 'Safari', 'HTTP', 'Python', 'PostgreSQL'}
FINGERPRINT_KEYS = {'metadata_sha256', 'head_sha256', 'encoder_sha256', 'processing_sha256'}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def revision(value: str) -> str:
    if not re.fullmatch('[a-f0-9]{40}', value):
        raise ValueError('Use a full 40-character Git SHA; never a URL or token')
    return value


def deployment_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ('', '/') or parsed.port):
        raise ValueError('Use the public HTTPS origin only, without credentials, path, query or fragment')
    if not re.fullmatch('[a-zA-Z0-9.-]+', parsed.hostname):
        raise ValueError('Invalid deployment hostname')
    return 'https://' + parsed.hostname.lower()


@dataclass(frozen=True)
class Scenario:
    id: str
    device: str
    role: str
    environment: str
    qa: str
    instruction: str
    reason: str


def scenarios() -> tuple[Scenario, ...]:
    result = [
        Scenario('http', 'Codex Linux', 'visitor', 'published', '', 'Verificar resposta HTTP; não comprova renderização ou SHA.', 'not_executed'),
        Scenario('browser', 'Codex Linux', 'visitor', 'published', 'QA-20', 'Abrir sessão anônima; verificar renderização, sem login nem dados reais.', 'not_executed'),
        Scenario('published_sha', 'PC', 'operator', 'published', '', 'Conferir SHA completo no provedor/runtime e comparar com candidato; prefixo ou CI não bastam.', 'revision_unverified'),
        Scenario('published_model', 'PC', 'operator', 'published', 'QA-09', 'Conferir hashes do modelo efetivamente carregado, inclusive override remoto e contrato.', 'runtime_model_unverified'),
        Scenario('local_model', 'Codex Linux', 'fixture', 'local_fixture', '', 'Verificar configuração, cabeça e montagem dos shards locais; não atesta deployment.', 'not_executed'),
        Scenario('local_error_privacy', 'Codex Linux', 'fixture', 'local_fixture', '', 'Usar marcador sintético para verificar se a fronteira de erro repassa detalhe bruto à UI/log; não é incidente observado em produção.', 'not_executed'),
        Scenario('local_rls', 'CI PostgreSQL 16', 'fixture', 'local_fixture', '', 'Executar fixtures/RLS/permissões em PostgreSQL 16 descartável, sem dados reais.', 'not_executed'),
    ]
    steps = (
        ('visitor', 'visitor', 'QA-20', 'Abrir como visitante; navegar sem gestão/conta alheia e sem enviar contribuição.', 'no_device'),
        ('capture', 'visitor', 'QA-20', 'Capturar/enviar foto real autorizada; conferir EXIF e alternativa após negar câmera.', 'no_real_photo'),
        ('analysis', 'visitor', 'QA-09', 'Analisar foto real; separar hipótese, rejeição, confirmação humana e limites do reconhecimento.', 'no_real_photo'),
        ('disposal', 'visitor', 'QA-20', 'Corrigir material; conferir lixeira/ponto e orientação especial de pilhas/eletrônicos.', 'no_device'),
        ('accounts', 'controlled_A_B', 'QA-18', 'Com autorização, entrar A/B em sessões separadas; B não acessa protocolos/fotos/respostas de A.', 'no_authorized_account'),
        ('analyst', 'controlled_analyst', 'QA-18', 'Com autorização, validar analista na allowlist e negar gestão a visitante/B.', 'no_authorized_account'),
        ('reopen', 'controlled_A_B', 'QA-19', 'Persistir evidência consentida de A; reabrir/login/recarregar, revisar e conferir isolamento em B.', 'no_authorized_account'),
    )
    for device in ('PC', 'Android', 'iPhone'):
        result.extend(Scenario(device.lower() + '_' + key, device, role, 'published', qa, action, reason)
                      for key, role, qa, action, reason in steps)
    result.extend([
        Scenario('database_outage', 'PC', 'controlled_A_B', 'isolated_copy', 'QA-19', 'Simular erro de banco somente em cópia isolada; nenhuma gravação incerta deve virar sucesso/reenvio automático.', 'isolated_environment_required'),
        Scenario('recovery', 'PC', 'operator', 'isolated_copy', 'QA-21', 'Ensaiar reabertura/rollback/restore somente em cópia descartável autorizada; nunca produção.', 'isolated_environment_required'),
        Scenario('independent_recognition', 'PC', 'operator', 'field_evaluation', 'QA-09', 'Exigir avaliação independente por classe e proveniência auditada; smoke, fixtures e CI não aprovam reconhecimento.', 'independent_evidence_required'),
    ])
    return tuple(result)


CATALOG = {case.id: case for case in scenarios()}


def new_report(candidate_sha: str, url: str, model: dict[str, Any]) -> dict[str, Any]:
    return {'schema_version': 1, 'created_at_utc': utc_now(), 'candidate_sha': revision(candidate_sha),
            'deployment_url': deployment_url(url), 'local_model': model,
            'formal_acceptance': 'manual_review_required',
            'external_qa': {code: 'manual_pending' for code in EXTERNAL_QA},
            'cases': [
                {'id': case.id, 'device': case.device, 'role': case.role, 'environment': case.environment,
                 'qa': case.qa, 'scenario': case.instruction, 'status': 'manual_pending', 'reason': case.reason,
                 'executed_at_utc': None, 'observed_sha': None, 'browser': None,
                 'browser_version': None, 'evidence_ref': None, 'evidence_kind': None,
                 'runtime_fingerprint': None, 'authorization_confirmed': False, 'attempted_at_utc': None, 'http_status': None, 'revision_prefix': None}
                for case in CATALOG.values()]}


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('Execution time must have a timezone and cannot be in the future')
    return parsed.astimezone(timezone.utc).isoformat(timespec='seconds')


def record_case(report: dict[str, Any], case_id: str, status: Status, *,
                at: str | None = None, observed_sha: str | None = None,
                browser: str | None = None, browser_version: str | None = None,
                evidence_ref: str | None = None, reason: str = 'not_executed',
                authorization_confirmed: bool = False,
                runtime_fingerprint: dict[str, str] | None = None) -> dict[str, Any]:
    case = CATALOG[case_id]
    if runtime_fingerprint is not None:
        if (case_id != 'published_model' or set(runtime_fingerprint) != FINGERPRINT_KEYS
                or any(not re.fullmatch('[a-f0-9]{64}', value) for value in runtime_fingerprint.values())):
            raise ValueError('Only the four non-sensitive runtime SHA-256 fields are accepted')
    if status not in {'passed', 'failed', 'manual_pending'} or reason not in REASONS:
        raise ValueError('Unsupported status/reason')
    if status != 'manual_pending':
        if not (at and observed_sha and browser and browser_version and evidence_ref):
            raise ValueError('Executed cases require time, full observed SHA, browser/version and anonymized evidence')
        at, observed_sha = _timestamp(at), revision(observed_sha)
        if browser not in BROWSERS or not re.fullmatch(r'\d+(?:\.\d+){0,3}', browser_version):
            raise ValueError('Use a browser family and numeric version only')
        if not re.fullmatch(r'EVID-\d{3,6}', evidence_ref):
            raise ValueError('Use only an anonymized EVID-001 style reference; no notes, URL or protocol')
        if status == 'passed' and observed_sha != report['candidate_sha']:
            raise ValueError('Evidence for a different SHA cannot pass this candidate')
        if case.role.startswith('controlled_') and not authorization_confirmed:
            raise ValueError('Explicit authorization for controlled accounts is required')
        if case_id == 'published_model' and status == 'passed':
            if runtime_fingerprint != {key: report['local_model'][key] for key in FINGERPRINT_KEYS}:
                raise ValueError('Runtime fingerprint must match the frozen candidate model')
    else:
        at = observed_sha = browser = browser_version = evidence_ref = runtime_fingerprint = None
    result = deepcopy(report)
    row = next(item for item in result['cases'] if item['id'] == case_id)
    row.update(status=status, reason=reason if status != 'passed' else None, executed_at_utc=at,
               observed_sha=observed_sha, browser=browser, browser_version=browser_version,
               evidence_ref=evidence_ref, evidence_kind='manual_attestation' if at else None,
               runtime_fingerprint=runtime_fingerprint, authorization_confirmed=bool(authorization_confirmed and at), attempted_at_utc=None, http_status=None, revision_prefix=None)
    # Deliberately no bridge to acceptance_checks or QA promotion.
    return result


def inspect_candidate_model(root: Path, candidate_sha: str) -> dict[str, Any]:
    """Read candidate files only; assemble with the existing resolver in a temporary folder."""
    from ecoscan.classification.semantic_onnx import file_digest
    from ecoscan.config import load_config
    from ecoscan.image_processing.contracts import processing_contract
    revision(candidate_sha)
    config = load_config(root / 'config/settings.json')
    relative = config.model['artifact_path']
    if relative != 'models/semantic-v1/semantic.json':
        raise ValueError('Unexpected configured candidate model')
    for name in ('config/settings.json', relative, 'src/ecoscan/ui/common_views.py'):
        frozen = subprocess.run(['git', 'show', candidate_sha + ':' + name], cwd=root,
                                capture_output=True, check=True, timeout=10).stdout
        if frozen != (root / name).read_bytes():
            raise ValueError('Local configuration/model metadata differs from the specified candidate')
    metadata_path = root / relative
    metadata = json.loads(metadata_path.read_text())
    if set(metadata['classes']) != set(config.classes) | {'unknown'}:
        raise ValueError('Configured class scope differs from model')
    if metadata['processing'] != processing_contract(config):
        raise ValueError('Processing contract mismatch')
    head = metadata_path.parent / 'head.npz'
    if file_digest(head) != metadata['head_sha256']:
        raise ValueError('Head checksum mismatch')
    assembled_hash = verified_encoder_hash(metadata_path.parent, metadata)
    return {'scope': 'local_candidate_only_not_deployment', 'configured_artifact': relative,
            'metadata_sha256': file_digest(metadata_path), 'head_sha256': file_digest(head),
            'encoder_sha256': assembled_hash, 'processing_sha256': metadata['processing']['sha256'],
            'threshold': metadata['threshold'], 'shards_verified': len(metadata['parts']),
            'remote_override_enabled': bool(config.model.get('remote_models_enabled')),
            'confirmation_required': bool(config.model.get('confirmation_required', True))}


def verified_encoder_hash(folder: Path, metadata: dict[str, Any]) -> str:
    from ecoscan.classification.semantic_onnx import file_digest, resolve_encoder
    with tempfile.TemporaryDirectory(prefix='ecoscan-published-audit-') as temporary:
        target = Path(temporary)
        parts = metadata.get('parts', [])
        if not 1 <= len(parts) <= 4:
            raise ValueError('Invalid part count')
        for index, part in enumerate(parts):
            if part['name'] != f'encoder_{index:02d}.part':
                raise ValueError('Invalid encoder part path')
            source = folder / part['name']
            if source.is_symlink():
                raise ValueError('Encoder part symlink refused')
            shutil.copyfile(source, target / part['name'])
        return file_digest(resolve_encoder(target, metadata))


def validate_report(report: dict[str, Any]) -> None:
    if report['schema_version'] != 1:
        raise ValueError('Unsupported report version')
    revision(report['candidate_sha'])
    deployment_url(report['deployment_url'])
    _timestamp(report['created_at_utc'])
    model = report['local_model']
    if set(model) != FINGERPRINT_KEYS | {'scope', 'configured_artifact', 'threshold', 'shards_verified', 'remote_override_enabled', 'confirmation_required'}:
        raise ValueError('Only the local model fingerprint is accepted; do not enter private notes')
    if (model['scope'] != 'local_candidate_only_not_deployment' or model['configured_artifact'] != 'models/semantic-v1/semantic.json'
            or any(not re.fullmatch('[a-f0-9]{64}', model[key]) for key in FINGERPRINT_KEYS)):
        raise ValueError('Invalid model fingerprint')
    if (type(model['threshold']) not in (float, int) or not 0 <= model['threshold'] <= 1
            or type(model['shards_verified']) is not int or not 1 <= model['shards_verified'] <= 4
            or type(model['remote_override_enabled']) is not bool or type(model['confirmation_required']) is not bool):
        raise ValueError('Invalid model inspection metadata')
    if set(report) != {'schema_version', 'created_at_utc', 'candidate_sha', 'deployment_url', 'local_model', 'formal_acceptance', 'external_qa', 'cases'}:
        raise ValueError('Unknown report field; private notes are not accepted')
    if report['external_qa'] != {code: 'manual_pending' for code in EXTERNAL_QA}:
        raise ValueError('This report cannot promote external QA gates')
    if report['formal_acceptance'] != 'manual_review_required':
        raise ValueError('Formal approval requires separate review')
    expected = set(new_report(report['candidate_sha'], report['deployment_url'], model)['cases'][0])
    if {row['id'] for row in report['cases']} != set(CATALOG) or len(report['cases']) != len(CATALOG):
        raise ValueError('Scenario catalog changed or duplicated')
    for row in report['cases']:
        if set(row) != expected or row['status'] not in {'passed', 'failed', 'manual_pending'}:
            raise ValueError('Unknown case field/status; do not put private notes in this report')
        case = CATALOG[row['id']]
        if any(row[key] != getattr(case, attr) for key, attr in (('device', 'device'), ('role', 'role'), ('environment', 'environment'), ('qa', 'qa'), ('scenario', 'instruction'))):
            raise ValueError('Scenario metadata must come from the fixed catalog')
        if row['reason'] is not None and row['reason'] not in REASONS:
            raise ValueError('Do not enter free-form private evidence')
        if type(row['authorization_confirmed']) is not bool:
            raise ValueError('Authorization must be an explicit boolean, never an identity or credential')
        if row['evidence_kind'] not in {None, 'manual_attestation', 'technical_http', 'technical_browser', 'technical_local'}:
            raise ValueError('Unsupported evidence kind')
        if row['evidence_kind'] is None and (row['status'] != 'manual_pending' or any(row[key] is not None for key in ('executed_at_utc', 'observed_sha', 'browser', 'browser_version', 'evidence_ref', 'runtime_fingerprint', 'attempted_at_utc', 'http_status', 'revision_prefix'))):
            raise ValueError('Pending, unexecuted scenarios cannot contain private or inferred evidence')
        if row['evidence_kind'] in {'technical_http', 'technical_browser', 'technical_local'}:
            if row['id'] not in {'http', 'browser', 'local_model', 'local_rls', 'local_error_privacy'}:
                raise ValueError('Technical probes cannot attest to manual scenarios')
            unknown_browser = row['status'] == 'manual_pending' and row['reason'] == 'browser_unavailable' and row['browser_version'] is None
            if row['browser'] not in BROWSERS or (not unknown_browser and not re.fullmatch(r'\d+(?:\.\d+){0,3}', row['browser_version'] or '')):
                raise ValueError('Invalid technical browser/version')
            _timestamp(row['attempted_at_utc'] or row['executed_at_utc'])
            if row['observed_sha'] is not None or row['runtime_fingerprint'] is not None:
                raise ValueError('Technical observations cannot imply a published revision or contain private payloads')
            if row['status'] == 'manual_pending':
                if row['executed_at_utc'] is not None:
                    raise ValueError('A pending scenario is not a completed execution')
            else:
                _timestamp(row['executed_at_utc'])
            if not re.fullmatch(r'EVID-\d{3,6}', row['evidence_ref'] or ''):
                raise ValueError('Invalid evidence reference')
            if row['revision_prefix'] is not None and not re.fullmatch('[a-f0-9]{7,40}', row['revision_prefix']):
                raise ValueError('Invalid observed revision prefix')
            if row['http_status'] is not None and (type(row['http_status']) is not int or not 100 <= row['http_status'] <= 599):
                raise ValueError('Invalid HTTP status')
        elif row['status'] != 'manual_pending':
            # Reuse metadata validation without requiring a repeated authorization assertion on reading.
            record_case(report, row['id'], row['status'], at=row['executed_at_utc'],
                        observed_sha=row['observed_sha'], browser=row['browser'],
                        browser_version=row['browser_version'], evidence_ref=row['evidence_ref'],
                        reason=row['reason'] or 'not_executed', authorization_confirmed=row['authorization_confirmed'],
                        runtime_fingerprint=row['runtime_fingerprint'])


def technical_observation(report: dict[str, Any], case_id: str, *, status: Status,
                          reason: str | None, at: str, browser: str, browser_version: str | None,
                          evidence_ref: str, http_status: int | None = None,
                          revision_prefix: str | None = None) -> dict[str, Any]:
    if case_id not in {'http', 'browser', 'local_model', 'local_rls', 'local_error_privacy'}:
        raise ValueError('Technical observations cannot approve a manual scenario')
    result = deepcopy(report)
    row = next(item for item in result['cases'] if item['id'] == case_id)
    row.update(status=status, reason=reason, browser=browser, browser_version=browser_version,
               evidence_ref=evidence_ref, attempted_at_utc=_timestamp(at),
               executed_at_utc=at if status != 'manual_pending' else None,
               evidence_kind={'http': 'technical_http', 'browser': 'technical_browser'}.get(case_id, 'technical_local'),
               http_status=http_status, revision_prefix=revision_prefix)
    validate_report(result)
    return result


def save_report(report: dict[str, Any], directory: Path) -> None:
    import csv
    import io
    validate_report(report)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'acceptance.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    fields = ['id', 'device', 'role', 'environment', 'qa', 'scenario', 'status', 'reason',
              'executed_at_utc', 'observed_sha', 'browser', 'browser_version', 'evidence_ref', 'evidence_kind']
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(report['cases'])
    (directory / 'acceptance.csv').write_text(buffer.getvalue(), encoding='utf-8')
    rows = ['# Smoke da versão publicada — evidências e pendências', '',
            'Data de preparação: ' + report['created_at_utc'], 'Candidato: `' + report['candidate_sha'] + '`.',
            'URL: ' + report['deployment_url'], '',
            '**Sem aprovação formal automática. QA-09 e QA-18..QA-21 continuam manual_pending neste relatório.**',
            'HTTP 200, fixtures, emulação e CI não comprovam o SHA publicado, contas, telefone real ou acurácia independente.', '',
            '| Caso | Dispositivo / papel | Ambiente | Cenário | Estado / motivo | Execução / SHA observado | Navegador | Evidência |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in report['cases']:
        rows.append(f"| {row['id']} | {row['device']} / {row['role']} | {row['environment']} | {row['scenario']} | "
                    f"{row['status']} / {row['reason'] or '—'} | {row['executed_at_utc'] or ('tentativa ' + row['attempted_at_utc'] if row['attempted_at_utc'] else 'não executado')} / "
                    f"{row['observed_sha'] or 'não comprovado'} | {row['browser'] or '—'} {row['browser_version'] or ''} | "
                    f"{row['evidence_ref'] or '—'} ({row['evidence_kind'] or 'pendente'}) |")
    rows += ['', '## Fingerprint local do candidato (não é leitura do deployment)', '', '```json',
             json.dumps(report['local_model'], indent=2, ensure_ascii=False), '```', '',
             'Referências EVID-001 são aliases para evidência anonimizada revisada pelo grupo. Não são protocolos, contas ou links assinados.',
             'Não executar indisponibilidade, migrations de fixture ou restore em produção. Contas A/B/analista exigem autorização explícita.']
    (directory / 'acceptance.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
