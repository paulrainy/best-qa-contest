"""Сценарии JMeter задания 1г из исходников на Python.

Запуск: python build_jmx.py ../1g-load-review [--tree NN]
Исходники — jury/source/scripts/NN_<операция>.py. В каждом FILE = 'NN-<операция>' и plan(fixed) -> jmx.El.
Пишет participant/scripts/<FILE>.jmx (plan(False), с дефектами) и jury/fixed/scripts/<FILE>.jmx (plan(True)).
--tree NN печатает все пути плана с классом элемента — по ним пишется место в ключе.
"""
import importlib.util
import sys
from pathlib import Path

import jmx


def load_sources(task: Path) -> dict:
    sources = {}
    for path in sorted((task / 'jury' / 'source' / 'scripts').glob('[0-9][0-9]_*.py')):
        spec = importlib.util.spec_from_file_location(f'scenario_{path.stem}', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        unit = path.name[:2]
        if unit in sources:
            sys.exit(f'два исходника сценария {unit}')
        sources[unit] = module
    return sources


def outputs(task: Path, module) -> dict:
    return {False: task / 'participant' / 'scripts' / f'{module.FILE}.jmx',
            True: task / 'jury' / 'fixed' / 'scripts' / f'{module.FILE}.jmx'}


def build(task: Path) -> None:
    for module in load_sources(task).values():
        for fixed, path in outputs(task, module).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(jmx.render(module.plan(fixed)), encoding='utf-8')


def stale(task: Path) -> list:
    """Единицы, у которых файл участника или исправленный не совпадает с исходником."""
    found = []
    for unit, module in load_sources(task).items():
        for fixed, path in outputs(task, module).items():
            if not path.exists() or path.read_text(encoding='utf-8') != jmx.render(module.plan(fixed)):
                found.append(unit)
                break
    return found


def tree(task: Path, unit: str, fixed: bool = False) -> str:
    module = load_sources(task)[unit]
    lines = []
    for path, element in jmx.paths(module.plan(fixed)).items():
        off = '' if element.enabled else '  (выключен)'
        lines.append(f'{path}  [{element.test_class}]{off}')
    return '\n'.join(lines)


if __name__ == '__main__':
    if '--help' in sys.argv or len(sys.argv) < 2:
        sys.exit(__doc__)
    target = Path(sys.argv[1]).resolve()
    if '--tree' in sys.argv:
        print(tree(target, sys.argv[sys.argv.index('--tree') + 1]))
    else:
        build(target)
        print(f'Готово: {len(load_sources(target))} сценариев')
