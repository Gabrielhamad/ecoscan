"""Freeze a manifest from explicitly labelled local images; no upload or inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ecoscan.config import load_config
from ecoscan.services.evaluation_manifest import build_local_manifest, read_development_hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('csv', 'source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--development-hashes', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError('Use a new manifest path')
        records = build_local_manifest(args.csv, args.source, load_config(),
                                       read_development_hashes(args.development_hashes))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as file:
            json.dump(records, file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write('\n')
    except OSError:
        parser.error('Local file access failed; check inputs and output permissions')
    except ValueError as exc:
        parser.error(str(exc))
    print(f'Manifest created: {len(records)} records. independent_test=false; provenance requires external audit.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
