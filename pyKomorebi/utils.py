import re
from typing import Any, TypeGuard


def strip_value(value, strip_chars: str | None = None) -> str:
    if value is None:
        return ""
    return str(value).strip(strip_chars)


def strip_lines(*line: str | None, strip_chars: str | None = None) -> list[str]:
    if strip_chars is None:
        return [line for line in line if is_not_blank(line)]
    return [strip_value(val, strip_chars) for val in line]


def is_not_blank(line: Any, strip_chars: str | None = None) -> TypeGuard[str]:
    if line is None:
        return False
    if not isinstance(line, str):
        line = str(line)
    if strip_chars is not None:
        line = line.strip(strip_chars)
    return len(line) > 0


def strip_and_clean_blank(*text: str | None, strip_chars: str | None = None) -> list[str]:
    values = strip_lines(*text, strip_chars=strip_chars)
    return [val for val in values if is_not_blank(val, strip_chars=strip_chars)]


def clean_blank(*text: str | None, strip_chars: str | None = None) -> list[str]:
    return [val for val in text if is_not_blank(val, strip_chars=strip_chars)]


def ensure_ends_with(line: str, end_str: str | None) -> str:
    if end_str is None or line.rstrip().endswith(end_str):
        return line
    return f"{line.rstrip()}{end_str}"


def quote(value: str, quote_str: str = "\"") -> str:
    return f"{quote_str}{value}{quote_str}"


def replace_double_quotes(lines: list[str]) -> list[str]:
    changed = []
    for line in lines:
        if '"' in line and not line.startswith('"') and not line.endswith('"'):
            line = line.replace('"', "'")
        changed.append(line)
    return changed


def _clean_pattern_in(line: str, patterns: list[re.Pattern]) -> str:
    for pattern in patterns:
        matched = pattern.findall(line)
        if matched is None:
            continue
        for match_string in matched:
            replace = ""
            if match_string.startswith(" ") or match_string.endswith(" "):
                replace = " "
            line = line.replace(match_string, replace)
    return line


def clean_pattern_in(lines: list[str], patterns: list[re.Pattern]) -> list[str]:
    text = lines_as_str(*lines)
    changed = _clean_pattern_in(text, patterns)
    return changed.split("\n")


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


LAST_SPACE_REGEX = re.compile(r'\s+(?=(?:[^"\']*["\'][^"\']*["\'])*[^"\']*$)')


def last_space_index(text: str) -> int:
    # Regulärer Ausdruck, um das letzte Leerzeichen außerhalb von Anführungszeichen zu finden
    matched = re.search(LAST_SPACE_REGEX, text[::-1])
    if matched is not None:
        split_index = len(text) - matched.start()
        return split_index
    return -1


SENTENCE_SPLIT = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s")


def has_sentence(*text: str) -> bool:
    line = as_string(*text, separator=" ")
    return SENTENCE_SPLIT.search(line) is not None


def get_sentences(*text: str) -> list[str]:
    line = as_string(*text, separator=" ")
    return SENTENCE_SPLIT.split(line)
