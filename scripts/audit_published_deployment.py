"""Prepare/update anonymized smoke evidence; never log in or mutate the deployment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecoscan.services.published_acceptance import (
    BROWSERS, CATALOG, REASONS, inspect_candidate_model, new_report, record_case,
    save_report, technical_observation, utc_now, validate_report,
)


def http_observation(report: dict) -> dict:
    at = utc_now()
    try:
        # A new anonymous cookie jar handles the hosting redirects, then is discarded.
        with requests.Session() as client:
            with client.get(report['deployment_url'], timeout=20, stream=True) as response:
                status = response.status_code
    except (OSError, requests.RequestException):
        return technical_observation(report, 'http', status='manual_pending', reason='network_unavailable',
                                     at=at, browser='HTTP', browser_version=platform.python_version(), evidence_ref='EVID-001')
    state = 'passed' if status == 200 else 'failed' if status >= 500 else 'manual_pending'
    reason = None if state == 'passed' else 'observed_failure' if state == 'failed' else 'application_not_rendered'
    return technical_observation(report, 'http', status=state, reason=reason, at=at,
                                 browser='HTTP', browser_version=platform.python_version(),
                                 evidence_ref='EVID-001', http_status=status)


def browser_observation(report: dict, executable: str | None = None, *, container_browser: bool = False) -> dict:
    at = utc_now()
    # Optional test tooling only; never a runtime dependency and no TLS bypass.
    try:
        from playwright.sync_api import sync_playwright, Error, TimeoutError
    except ImportError:
        return technical_observation(report, 'browser', status='manual_pending', reason='browser_unavailable',
                                     at=at, browser='Chromium', browser_version=None, evidence_ref='EVID-002')
    with sync_playwright() as playwright:
        options = {'headless': True}
        if container_browser:
            options['args'] = ['--no-sandbox']  # isolated test container only; TLS stays enabled
        if executable:
            options['executable_path'] = executable
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        if proxy:
            options['proxy'] = {'server': proxy}
        try:
            browser = playwright.chromium.launch(**options)
        except Error:
            return technical_observation(report, 'browser', status='manual_pending', reason='browser_unavailable',
                                         at=at, browser='Chromium', browser_version=None, evidence_ref='EVID-002')
        version = browser.version
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(report['deployment_url'], wait_until='domcontentloaded', timeout=30000)
            page.get_by_role('tab', name='Escanear', exact=True).wait_for(timeout=30000)
            # Store only the revision prefix, never HTML, screenshots, cookies or account text.
            if page.locator('[data-testid=stException]').count():
                return technical_observation(report, 'browser', status='failed', reason='observed_failure',
                                             at=at, browser='Chromium', browser_version=version, evidence_ref='EVID-002')
            text = page.locator('body').inner_text()
            prefixes = re.findall(r'Revisão\s+([a-f0-9]{7,40})', text)
            prefix = prefixes[0] if len(set(prefixes)) == 1 else None
            result = technical_observation(report, 'browser', status='passed', reason=None,
                                           at=at, browser='Chromium', browser_version=version,
                                           evidence_ref='EVID-002', revision_prefix=prefix)
            if prefix and not report['candidate_sha'].startswith(prefix):
                next(row for row in result['cases'] if row['id'] == 'published_sha').update(reason='revision_mismatch')
            return result
        except (Error, TimeoutError) as exc:
            reason = 'browser_tls_error' if 'ERR_CERT_' in str(exc) else 'application_not_rendered'
            return technical_observation(report, 'browser', status='manual_pending', reason=reason,
                                         at=at, browser='Chromium', browser_version=version, evidence_ref='EVID-002')
        finally:
            browser.close()


def error_privacy_observation(report: dict) -> dict:
    from unittest.mock import MagicMock, patch
    from ecoscan.ui import common_views
    marker = 'ECO_SCAN_SYNTHETIC_DETAIL_ONLY'
    view = MagicMock()
    with patch.object(common_views, 'LOGGER') as logger:
        common_views._render_user_error(view, RuntimeError(marker), context='audit_fixture')
        exposed = marker in str(logger.mock_calls) or marker in str(view.mock_calls)
    return technical_observation(report, 'local_error_privacy', status='failed' if exposed else 'passed',
                                 reason='raw_exception_exposed' if exposed else None,
                                 at=utc_now(), browser='Python', browser_version=platform.python_version(),
                                 evidence_ref='EVID-005')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('init')
    create.add_argument('--candidate-sha', required=True)
    create.add_argument('--url', required=True, help='Public HTTPS origin; no query, token or credentials')
    create.add_argument('--output', type=Path, required=True, help='New directory, usually ignored reports/')
    for command in ('probe', 'record', 'check'):
        sub = commands.add_parser(command)
        sub.add_argument('--report', type=Path, required=True)
        if command == 'probe':
            sub.add_argument('--browser', action='store_true')
            sub.add_argument('--container-browser', action='store_true', help='Chromium test-container compatibility; TLS is still validated')
            sub.add_argument('--chromium', help='Optional local executable, never included in reports')
        elif command == 'record':
            sub.add_argument('--case', choices=list(CATALOG), required=True)
            sub.add_argument('--status', choices=['passed', 'failed', 'manual_pending'], required=True)
            sub.add_argument('--at')
            sub.add_argument('--observed-sha')
            sub.add_argument('--browser', choices=sorted(BROWSERS))
            sub.add_argument('--browser-version')
            sub.add_argument('--evidence', help='Anonymized alias such as EVID-003; never a protocol or URL')
            sub.add_argument('--reason', choices=sorted(REASONS), default='not_executed')
            sub.add_argument('--authorization-confirmed', action='store_true')
            sub.add_argument('--runtime-fingerprint', type=Path, help='JSON with only metadata/head/encoder/processing SHA-256')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            if args.output.exists():
                raise ValueError('Choose a new report directory')
            model = inspect_candidate_model(ROOT, args.candidate_sha)
            report = new_report(args.candidate_sha, args.url, model)
            report = technical_observation(report, 'local_model', status='passed', reason=None,
                                           at=utc_now(), browser='Python', browser_version=platform.python_version(),
                                           evidence_ref='EVID-003')
            report = error_privacy_observation(report)
            save_report(report, args.output)
        else:
            report = json.loads(args.report.read_text())
            validate_report(report)
            if args.command == 'probe':
                report = http_observation(report)
                if args.browser:
                    report = browser_observation(report, args.chromium, container_browser=args.container_browser)
            elif args.command == 'record':
                report = record_case(report, args.case, args.status, at=args.at, observed_sha=args.observed_sha,
                                     browser=args.browser, browser_version=args.browser_version,
                                     evidence_ref=args.evidence, reason=args.reason,
                                     authorization_confirmed=args.authorization_confirmed,
                                     runtime_fingerprint=json.loads(args.runtime_fingerprint.read_text()) if args.runtime_fingerprint else None)
            save_report(report, args.report.parent)
        pending = sum(row['status'] == 'manual_pending' for row in report['cases'])
        failed = sum(row['status'] == 'failed' for row in report['cases'])
        print(f'Smoke record: {pending} manual_pending, {failed} failed. External QA gates are not approved.')
        # Formal external QA remains pending even if every recorded smoke case passes.
        return (1 if failed else 2) if args.command == 'check' else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        # Never echo arbitrary exception/file/URL content, including signed links.
        print(f'Audit rejected ({type(exc).__name__}); review non-sensitive inputs and the documented schema.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
