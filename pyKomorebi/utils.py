from typing import Any


def strip_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines]


def is_none_or_empty(line: Any) -> bool:
    if line is None:
        return True
    if not isinstance(line, str):
        line = str(line)
    return len(line.strip()) == 0


def _clean_none_or_empty(lines: list[str], index: int) -> list[str]:
    while len(lines) > 0 and is_none_or_empty(lines[index]):
        lines.pop(index)
    return lines


def clean_none_or_empty(lines: list[str], strip: bool = False) -> list[str]:
    if strip:
        lines = strip_lines(lines)
    lines = _clean_none_or_empty(lines, index=0)
    lines = _clean_none_or_empty(lines, index=-1)
    return lines


def concat_values(values: list[str], max_length: int, separator: str) -> list[str]:
    concat_values = []
    current = ""
    for value in strip_lines(values):
        if len(value) == 0:
            continue
        if len(current) > 0:
            value = f"{separator}{value}"
        if len(current) + len(value) <= max_length:
            current += value
        else:
            concat_values.append(current)
            current = value.removeprefix(separator).strip()
    concat_values.append(current)
    return concat_values


def ensure_max_length(lines: list[str], max_length: int, split: str) -> list[str]:
    ensure_max_length = []
    for line in clean_none_or_empty(lines, strip=True):
        if len(line) <= max_length:
            ensure_max_length.append(line)
            continue
        split_lines = concat_values(line.split(split), max_length, split)
        ensure_max_length.extend(split_lines)
    return ensure_max_length
