"""Сценарии JMeter задания 1г из исходников на Python.

Запуск: python build_jmx.py ../1g-load-review [--tree NN]
Исходники — jury/source/scripts/NN_<операция>.py. В каждом FILE = 'NN-<операция>' и plan(fixed) -> jmx.El.
Пишет participant/scripts/<FILE>.jmx (plan(False), с дефектами) и jury/fixed/scripts/<FILE>.jmx (plan(True)).
--tree NN печатает все пути плана с классом элемента — по ним пишется место в ключе.
--check загружает все собранные .jmx (участника и исправленные) в JMeter 5.6.3 через check_jmx.groovy.
Нужны JMETER_HOME и Java 17+ (JAVA или /opt/homebrew/opt/openjdk@21/bin/java).
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import jmx

HERE = Path(__file__).resolve().parent
JAVA = os.environ.get('JAVA', '/opt/homebrew/opt/openjdk@21/bin/java')


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


def check(files) -> tuple:
    """Загружает файлы в JMeter через check_jmx.groovy. Возвращает (код, вывод)."""
    home = os.environ.get('JMETER_HOME')
    if not home:
        sys.exit('нет JMETER_HOME — скачайте JMeter 5.6.3, см. README')
    classpath = f'{home}/lib/*:{home}/lib/ext/*'
    result = subprocess.run([JAVA, '-Djava.awt.headless=true', '-cp', classpath, 'groovy.ui.GroovyMain',
                             str(HERE / 'check_jmx.groovy'), *map(str, files)],
                            capture_output=True, text=True, encoding='utf-8')
    return result.returncode, result.stdout + result.stderr


def built_files(task: Path) -> list:
    return [path for module in load_sources(task).values() for path in outputs(task, module).values()]


if __name__ == '__main__':
    if '--help' in sys.argv or len(sys.argv) < 2:
        sys.exit(__doc__)
    target = Path(sys.argv[1]).resolve()
    if '--check' in sys.argv:
        code, output = check(built_files(target))
        print(output, end='')
        sys.exit(code)
    if '--tree' in sys.argv:
        print(tree(target, sys.argv[sys.argv.index('--tree') + 1]))
    else:
        build(target)
        print(f'Готово: {len(load_sources(target))} сценариев')
