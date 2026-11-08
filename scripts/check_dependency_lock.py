"""Check declared runtime requirements, hashed locks and installed versions."""
from __future__ import annotations

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import re
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def locked_requirements(path: Path) -> dict[str, Requirement]:
    result = {}
    for entry in path.read_text().replace('\\\n', ' ').splitlines():
        entry = entry.strip()
        if not entry or entry.startswith('#'):
            continue
        requirement = Requirement(entry.split(' --hash=')[0].strip())
        specs = list(requirement.specifier)
        if len(specs) != 1 or specs[0].operator != '==' or '*' in specs[0].version:
            raise ValueError('Every lock entry must pin an exact version')
        if not re.search(r'--hash=sha256:[0-9a-f]{64}(?:\s|$)', entry):
            raise ValueError('Every lock entry needs a SHA-256')
        name = canonicalize_name(requirement.name)
        if name in result:
            raise ValueError('Duplicate lock package')
        result[name] = requirement
    if not result:
        raise ValueError('Empty dependency lock')
    return result


def check(root: Path, *, installed: bool = False) -> dict:
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    declared = {canonicalize_name(r.name): r for r in map(Requirement, project['dependencies'])}
    inputs = {canonicalize_name(r.name): r for r in map(Requirement,
              [line for line in (root / 'requirements.in').read_text().splitlines()
               if line.strip() and not line.startswith('#')])}
    if {name: str(req) for name, req in inputs.items()} != {name: str(req) for name, req in declared.items()}:
        raise ValueError('requirements.in and pyproject.toml runtime declarations diverge')
    if (root / 'requirements.txt').read_text().strip() != '-r requirements.lock':
        raise ValueError('Deploy requirements must consume the hashed runtime lock')
    runtime = locked_requirements(root / 'requirements.lock')
    tooling = locked_requirements(root / 'requirements-dev.lock')
    for name, requirement in declared.items():
        if name not in runtime or next(iter(runtime[name].specifier)).version not in requirement.specifier:
            raise ValueError(f'Runtime lock does not satisfy declaration: {name}')
    for name in runtime.keys() & tooling.keys():
        if runtime[name].specifier != tooling[name].specifier:
            raise ValueError('Runtime and tooling locks disagree')
    for name, requirement in {**runtime, **tooling}.items():
        if installed and version(name) not in requirement.specifier:
            raise ValueError(f'Installed version differs from the lock: {name}')
    return {'runtime_packages': len(runtime), 'tooling_packages': len(tooling),
            'installed_checked': installed, 'declarations_aligned': True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args(argv)
    print(json.dumps(check(ROOT, installed=args.installed)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
