"""Offline validation-only candidate selection and a locked single final test. No publishing."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ecoscan.config import load_config
from ecoscan.training.offline_experiment import final_test, fit_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('fit', 'test'))
    for name in ('manifest', 'audit', 'policy', 'source'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--run', required=True, help='Opaque local name under models/candidates/')
    args = parser.parse_args(argv)
    try:
        function = fit_experiment if args.phase == 'fit' else final_test
        result = function(load_config(), args.manifest, args.audit, args.policy, args.source, args.run)
    except FileExistsError:
        parser.error('Run or final-test reservation already exists; never overwrite or reset a consumed holdout')
    except OSError:
        parser.error('Local file access failed; check audited inputs and permissions')
    except (ValueError, KeyError, TypeError) as exc:
        parser.error('Offline gate failed: ' + str(exc))
    print(result['decision'] + '; active model unchanged; independent_test=false')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
