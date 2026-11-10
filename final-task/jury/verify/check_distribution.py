#!/usr/bin/env python3
"""Проверка четырёх выдач по SHA-256, runtime и составу архива; без записи."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import zipfile

DIRECTIONS = ('1a-java', '1b-manual', '1c-load', '1d-python')
FORBIDDEN = {'jury', 'starters', 'stand-src', '.m2', 'target', '.venv', '__pycache__', '.pytest_cache', 'test-data'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_distribution(root):
    root = Path(root)
    final = root / 'final-task'
    errors, hashes = [], {}
    manifest = final / 'jury/stand-manifest.md'
    if not manifest.is_file():
        return [f'{manifest}: манифест отсутствует']
    for sha, name in re.findall(r'^\| ([a-f0-9]{64}) \| ([^|]+?) \|$', manifest.read_text(encoding='utf-8'), re.M):
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not name.startswith('final-task/'):
            errors.append(f'{name}: небезопасный путь в манифесте'); continue
        if name in hashes:
            errors.append(f'{name}: повторная строка манифеста')
        hashes[name] = sha
        path = root / name
        if not path.is_file() or path.is_symlink():
            errors.append(f'{name}: файл отсутствует или является ссылкой')
        elif digest(path) != sha:
            errors.append(f'{name}: SHA-256 отличается от сборки')
    canonical = final / 'jury/source/spec.md'
    first = None
    for direction in DIRECTIONS:
        participant = final / direction / 'participant'
        stand = participant / 'stand'
        for name in ('README.md', 'spec.md', 'stand/run.sh', 'stand/run.cmd', 'stand/stand.properties', 'stand/transfer-stand.jar'):
            if not (participant / name).is_file(): errors.append(f'{participant / name}: отсутствует')
        if canonical.is_file() and (participant / 'spec.md').is_file() and canonical.read_bytes() != (participant / 'spec.md').read_bytes():
            errors.append(f'{participant / "spec.md"}: отличается от канонического ТЗ')
        libs = list((stand / 'lib').glob('*.jar'))
        if not libs: errors.append(f'{stand / "lib"}: нет runtime JAR')
        if not list((stand / 'lib').glob('*dojo*.zip')): errors.append(f'{stand / "lib"}: нет ZIP консоли Dojo')
        runtime = {}
        for path in sorted(participant.rglob('*')):
            if path.is_symlink(): errors.append(f'{path}: ссылка вместо физической копии')
            if not path.is_file(): continue
            relative = path.relative_to(participant)
            if relative.parts[:2] == ('stand', 'test-data') or relative.parts[0] == 'stand' and path.suffix in ('.log', '.lck'):
                continue
            if FORBIDDEN.intersection(relative.parts): errors.append(f'{path}: запрещённый материал в выдаче')
            key = path.relative_to(root).as_posix()
            if key not in hashes: errors.append(f'{key}: файл не учтён в манифесте')
            if path.suffix in ('.jar', '.zip'):
                if path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1'):
                    errors.append(f'{path}: LFS pointer вместо бинарника')
                elif not zipfile.is_zipfile(path): errors.append(f'{path}: повреждённый архив')
                else:
                    with zipfile.ZipFile(path) as archive:
                        if archive.testzip(): errors.append(f'{path}: повреждённая запись ZIP')
                        if path.name == 'transfer-stand.jar':
                            try:
                                mf = archive.read('META-INF/MANIFEST.MF').decode().replace('\r\n', '\n').replace('\n ', '')
                                cp = re.search(r'^Class-Path: (.+)$', mf, re.M)
                                if not cp: errors.append(f'{path}: Class-Path отсутствует')
                                else:
                                    for lib in cp.group(1).split():
                                        if not (stand / lib).is_file(): errors.append(f'{path}: нет зависимости {lib}')
                            except KeyError: errors.append(f'{path}: нет manifest')
            if relative.parts[0] == 'stand': runtime[relative.as_posix()] = digest(path)
        if first is None: first = runtime
        elif runtime != first: errors.append(f'{stand}: runtime отличается от первого направления')
    return errors


def check_archive(path, participant):
    expected = {p.relative_to(participant).as_posix(): p for p in Path(participant).rglob('*') if p.is_file() and p.suffix not in ('.log', '.lck') and not FORBIDDEN.intersection(p.relative_to(participant).parts)}
    errors, seen = [], set()
    try:
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if entry.is_dir(): continue
                name = entry.filename.removeprefix('participant/')
                parts = PurePosixPath(name)
                if parts.is_absolute() or '..' in parts.parts or FORBIDDEN.intersection(parts.parts) or name not in expected:
                    errors.append(f'{entry.filename}: лишний или запрещённый файл'); continue
                if name in seen: errors.append(f'{name}: дубликат')
                seen.add(name)
                if archive.read(entry) != expected[name].read_bytes(): errors.append(f'{name}: содержимое отличается')
        for name in expected.keys() - seen: errors.append(f'{name}: отсутствует в архиве')
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--direction', choices=DIRECTIONS, default='1a-java')
    args = parser.parse_args()
    errors = check_distribution(args.root)
    if args.archive: errors += check_archive(args.archive, args.root / 'final-task' / args.direction / 'participant')
    print('\n'.join(errors) if errors else 'Четыре выдачи: состав, бинарники и SHA-256 корректны')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
