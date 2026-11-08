"""Scan tracked text files with pinned Gitleaks; emit only counts, never findings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def scan(directory: Path, executable: str) -> tuple[int, int]:
    with tempfile.TemporaryDirectory(prefix='ecoscan-secret-report-') as temporary:
        report = Path(temporary) / 'findings.json'
        completed = subprocess.run([executable, 'dir', str(directory), '--no-banner', '--redact=100',
                                    '--log-level', 'error', '--report-format', 'json', '--report-path', str(report)],
                                   capture_output=True, timeout=120)
        if completed.returncode not in (0, 1) or not report.exists():
            raise RuntimeError('Secret scanner failed; no success inferred')
        findings = json.loads(report.read_text())
        return completed.returncode, len(findings)


def check_tracked(root: Path, executable: str) -> dict:
    entries = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True, capture_output=True).stdout
    count = 0
    with tempfile.TemporaryDirectory(prefix='ecoscan-tracked-text-') as temporary:
        snapshot = Path(temporary)
        for name in entries.decode().split('\0'):
            if not name:
                continue
            source = root / name
            if source.is_symlink():
                raise ValueError('Tracked symlink must be reviewed before scanning')
            if not source.is_file():
                continue
            with source.open('rb') as stream:
                if b'\0' in stream.read(8192):
                    continue  # text scanner, never decode/collect private binary content
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            count += 1
        status, findings = scan(snapshot, executable)
    if status != 0 or findings:
        raise ValueError(f'SECRET-001: {findings} finding(s); inspect privately with Gitleaks, never publish values')
    # Prove the configured executable detects a generated, invalid GitHub-token canary.
    with tempfile.TemporaryDirectory(prefix='ecoscan-secret-canary-') as temporary:
        canary = Path(temporary)
        token = 'ghp_' + 'Ab3De6Gh9Jk2Mn5Pq8St1Vw4Yz7Cd0Fg3Hi6'
        (canary / 'canary.txt').write_text('access_token = "' + token + '"\n')
        status, findings = scan(canary, executable)
        if status != 1 or findings < 1:
            raise RuntimeError('SECRET-002: scanner failed its generated canary')
    return {'tracked_text_files': count, 'findings': 0, 'canary_detected': True,
            'scope': 'current tracked text snapshot; binary files, ignored local files and git history are outside this gate'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gitleaks', default='gitleaks')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = check_tracked(ROOT, args.gitleaks)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'SECRET gate failed ({type(exc).__name__}); inspect locally with redaction')
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
