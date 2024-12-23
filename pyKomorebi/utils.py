import re
from typing import Any


def strip_value(value, strip_chars: str | None = None) -> str:
    if value is None:
        return ""
    return str(value).strip(strip_chars)


def strip_lines(lines: list[str], strip_chars: str | None = None) -> list[str]:
    values = [strip_value(line, strip_chars) for line in lines]
    return [value for value in values if len(value) > 0]


def is_none_or_empty(line: Any, strip_chars: str | None = None) -> bool:
    if line is None:
        return True
    if not isinstance(line, str):
        line = str(line)
    line = strip_value(line, strip_chars)
    return len(line) == 0


def list_without_none_or_empty(*text: str | None, strip_chars: str | None = None) -> list[str]:
    values = [value for value in text if value is not None]
    if strip_chars is not None:
        values = strip_lines(values, strip_chars)
    return [val for val in values if not is_none_or_empty(val, strip_chars)]


def _clean_none_or_empty(lines: list[str], index: int, strip_chars: str | None = None) -> list[str]:
    while len(lines) > 0 and is_none_or_empty(lines[index], strip_chars):
        lines.pop(index)
    return lines


def clean_none_or_empty(lines: list[str], strip_chars: str | None = None) -> list[str]:
    lines = strip_lines(lines, strip_chars)
    lines = _clean_none_or_empty(lines, index=0, strip_chars=strip_chars)
    lines = _clean_none_or_empty(lines, index=-1, strip_chars=strip_chars)
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


ENUM_PATTERN = re.compile(r"(?P<name>\s*-\s?[-\w\s]*:)")


def split_enum(text: str, pattern: re.Pattern, strip_char: str | None) -> tuple[str, str | None]:
    if not pattern.match(text):
        return strip_value(text, strip_chars=strip_char), None
    values = pattern.split(text, maxsplit=1)
    values = list_without_none_or_empty(*values, strip_chars=strip_char)
    if len(values) == 0:
        return strip_value(text, strip_chars=strip_char), None
    return values[0], values[1]
