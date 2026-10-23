"""Combine original and expanded provenance before downloading another batch."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for path in args.manifest:
        for row in json.loads(path.read_text(encoding='utf-8')):
            rows.append({'path': row['path']})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(rows, file)
    print(f'{len(rows)} references excluded, including previous held-out scenes')


if __name__ == '__main__':
    main()
