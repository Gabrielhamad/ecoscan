"""Reject upward domain imports and cycles in eager, internal imports (stdlib only)."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Existing lazy runtime -> published_model import is intentional; eager cycles
# are checked across every module. Domain/image engines never depend on the UI.
FORBIDDEN = {
    'image_processing': {'ui', 'services', 'app'},
    'segmentation': {'ui', 'services', 'app'},
    'classification': {'ui'},
    'disposal': {'ui'},
    'services': {'ui'},
    'app': {'ui'},
}


def _imports(tree: ast.AST, *, eager: bool) -> list[ast.Import | ast.ImportFrom]:
    if eager and isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        # Class bodies execute on import, methods do not.
        if not isinstance(tree, ast.ClassDef):
            return []
    if isinstance(tree, ast.If) and ast.unparse(tree.test) in {'TYPE_CHECKING', 'typing.TYPE_CHECKING'}:
        return []
    result = [tree] if isinstance(tree, (ast.Import, ast.ImportFrom)) else []
    for child in ast.iter_child_nodes(tree):
        result.extend(_imports(child, eager=eager))
    return result


def _targets(node: ast.Import | ast.ImportFrom, module: str, is_package: bool) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    base = node.module or ''
    if node.level:
        package = module if is_package else module.rpartition('.')[0]
        base = importlib.util.resolve_name('.' * node.level + base, package)
    return {base, *(base + '.' + alias.name for alias in node.names)}


def check_architecture(source: Path) -> dict:
    modules = {}
    for path in sorted((source / 'ecoscan').rglob('*.py')):
        parts = path.relative_to(source).with_suffix('').parts
        name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
        modules[name] = path
    if not modules:
        raise ValueError('No ecoscan source modules found')
    graph = {name: set() for name in modules}
    violations = []
    for module, path in modules.items():
        tree = ast.parse(path.read_text(encoding='utf-8'))
        layer = module.split('.')[1] if '.' in module else ''
        for node in _imports(tree, eager=False):
            for target in _targets(node, module, path.name == '__init__.py'):
                if target.startswith('ecoscan.') and target.split('.')[1] in FORBIDDEN.get(layer, set()):
                    violations.append(f'{module}:{node.lineno} -> {target}')
        for node in _imports(tree, eager=True):
            graph[module].update(target for target in _targets(node, module, path.name == '__init__.py')
                                 if target in modules and target != module)
    active, visited, cycles = [], set(), []

    def visit(module: str) -> None:
        if module in active:
            cycles.append(active[active.index(module):] + [module])
            return
        if module in visited:
            return
        active.append(module)
        for target in sorted(graph[module]):
            visit(target)
        active.pop()
        visited.add(module)

    for module in sorted(graph):
        visit(module)
    return {'modules': len(modules), 'violations': sorted(set(violations)), 'eager_cycles': cycles,
            'scope': 'static internal imports; lazy runtime integrations are not proof of an acyclic runtime graph'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'src')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = check_architecture(args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return int(bool(result['violations'] or result['eager_cycles']))


if __name__ == '__main__':
    raise SystemExit(main())
