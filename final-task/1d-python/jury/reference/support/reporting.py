from pathlib import Path


def fresh_output(path):
    if path and Path(path).exists():
        raise ValueError(f"Результат уже существует: {path}; выберите новый путь для прогона")
