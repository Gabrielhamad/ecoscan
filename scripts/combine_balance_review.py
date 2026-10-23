"""Assemble explicit glass decisions with the already reviewed paper batch."""
import hashlib
import json
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parents[1]
    paper = root / 'reports/taco_balance_reviewed_20261023'
    glass = root / 'reports/trashnet_glass_review_20261023'
    output = root / 'reports/balance_reviewed_20261023'
    output.mkdir(exist_ok=False)
    rows = json.loads((paper / 'manifest.json').read_text())
    decisions = json.loads((glass / 'decisions.json').read_text())
    for row in rows:
        target = output / row['path']
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(paper / row['path'], target)
    for row in json.loads((glass / 'index.json').read_text()):
        item = decisions['approved'].get(row['review_id'])
        if item is None:
            continue
        path = glass / row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Glass source changed since review')
        relative = 'glass/' + path.name
        (output / 'glass').mkdir(exist_ok=True)
        shutil.copy2(path, output / relative)
        rows.append({**row, 'path': relative, 'item_id': item,
                     'review_method': 'assistant_visual_review', 'eligible_for_fit': True})
    (output / 'manifest.json').write_text(json.dumps(rows, indent=2))
    print(f'{len(rows)} reviewed examples assembled')


if __name__ == '__main__':
    main()
