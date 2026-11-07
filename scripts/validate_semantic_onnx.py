"""Evaluate frozen local images before human confirmation; never select a threshold."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ecoscan.config import load_config
from ecoscan.services.evaluation_manifest import read_development_hashes
from ecoscan.services.field_evaluation import evaluate_field_manifest, report_paths, write_field_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'manifest', 'source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cases', type=Path, help='Optional subset of frozen test records: path,expected_class')
    parser.add_argument('--require-groups', action='store_true', help='Retained for compatibility; groups are now always required')
    parser.add_argument('--development-hashes', type=Path)
    args = parser.parse_args(argv)
    try:
        if any(p.exists() for p in report_paths(args.output).values()):
            raise ValueError('Use new report paths')
        report = evaluate_field_manifest(load_config(), args.model, args.manifest, args.source,
                                          development_hashes=read_development_hashes(args.development_hashes),
                                          cases_path=args.cases)
        write_field_report(report, args.output)
    except OSError:
        parser.error('Local file access failed; check inputs and output permissions')
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Report created ({report['source_kind']}); independent_test=false. No promotion authorized.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
