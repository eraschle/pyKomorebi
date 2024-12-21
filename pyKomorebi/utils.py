import re
from typing import Any


def strip_value(value):
    if value is None:
        return ""
    return value.strip()


def strip_lines(lines: list[str]) -> list[str]:
    values = [strip_value(line) for line in lines]
    return [value for value in values if len(value) > 0]


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


def replace_double_quotes(lines: list[str]) -> list[str]:
    changed = []
    for line in lines:
        if '"' in line and not line.startswith('"') and not line.endswith('"'):
            line = line.replace('"', "'")
        changed.append(line)
    return changed


def _clean_pattern_in(line: str, patterns: list[re.Pattern]) -> str:
    for pattern in patterns:
        match = pattern.findall(line)
        if match is None:
            continue
        for replace in match:
            line = line.replace(replace, "")
    return line


def clean_pattern_in(lines: list[str], patterns: list[re.Pattern]) -> list[str]:
    changed = []
    for line in lines:
        changed.append(_clean_pattern_in(line, patterns))
    return changed


def as_string(*values: str, separator: str) -> str:
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return values[0]
    return separator.join([value for value in values if len(value) > 0])


def lines_as_str(*values: str) -> str:
    if len(values) == 0:
        return ""
    return as_string(*values, separator="\n")
