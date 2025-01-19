from abc import ABC
from dataclasses import dataclass
from typing import NotRequired, Protocol, TypedDict, TypeVar, Unpack

from pyKomorebi import utils
from pyKomorebi.model import CommandArgs, CommandConstant


class FormatterArgs(TypedDict):
    level: NotRequired[int]
    columns: NotRequired[int]
    suffix: NotRequired[str]
    default_format: NotRequired[str]
    separator: str
    is_code: NotRequired[bool]
    prefix: NotRequired[int]


def copy_args(args: FormatterArgs, **kwargs: Unpack[FormatterArgs]) -> FormatterArgs:
    copy_args = args.copy()
    copy_args.update(kwargs)
    return copy_args


def with_level(args: FormatterArgs, level: int | None = None) -> FormatterArgs:
    if level is None:
        level = args.get("level", 0) + 1
    return copy_args(args, level=level, separator=args["separator"])


class ICodeFormatter(Protocol):
    module_name: str
    separator: str
    max_length: int

    def empty_line(self, count: int = 1) -> list[str]: ...

    def comment(self, *comments: str, chars: str | None = None) -> list[str]: ...

    def region_comment(self, region: str) -> list[str]: ...

    def prefix_of(self, line: str) -> int: ...

    def indent_for(self, level: int, prefix: int = -1) -> str: ...

    def indent(self, line: str, level: int, prefix: int = -1) -> str: ...

    def concat_args(self, *args: str) -> str: ...

    def function_name(self, *name: str, private: bool = False) -> str: ...

    def remove_module_prefix(self, name: str) -> str: ...

    def fill_column(self, value: str, columns: int) -> str: ...

    def column_prefix(self, columns: int) -> str: ...

    def is_not_max_length(self, line: str | None) -> bool: ...

    def is_valid_line(self, *text: str | None, **kw: Unpack[FormatterArgs]) -> bool: ...

    def valid_lines_for(self, *text: str | None, **kw: Unpack[FormatterArgs]) -> list[str]: ...

    def concat_values(self, *values: str, **kw: Unpack[FormatterArgs]) -> list[str]: ...

    def find_prefix_in_code(self, line: str, **kw: Unpack[FormatterArgs]) -> int: ...


class ACodeFormatter(ABC, ICodeFormatter):
    _empty_line = [""]

    def __init__(self, indent: str, max_length: int, module_name: str):
        self.indent_str = indent
        self.max_length = max_length
        self.module_name = module_name

    def remove_module_prefix(self, name: str) -> str:
        return name.removeprefix(self.module_name).removeprefix(self.separator)

    def is_not_max_length(self, line: str | None) -> bool:
        if line is None:
            return False
        return len(line) <= self.max_length

    def empty_line(self, count: int = 1) -> list[str]:
        if count <= 0:
            return []
        return self._empty_line * count

    def prefix_of(self, line: str) -> int:
        return len(line) - len(line.lstrip())

    def indent_for(self, level: int, prefix: int = -1) -> str:
        if level <= 0 and prefix <= 0:
            return ""
        indent = self.indent_str * level
        if len(indent) > prefix:
            return indent
        return self.column_prefix(prefix)

    def indent(self, line: str, level: int = 0, prefix: int = -1) -> str:
        indent = self.indent_for(level, prefix)
        return f"{indent}{line}"

    def default_value(self, value: str | None, format_str: str | None = None) -> str:
        if value is None or len(value.strip()) == 0:
            return ""
        value = value.upper()
        if format_str is None:
            return value
        return format_str.format(value)

    def fill_column(self, value: str, columns: int) -> str:
        if 0 > len(value) >= columns:
            return value
        return value.ljust(columns)

    def column_prefix(self, columns: int) -> str:
        if columns <= 0:
            return ""
        return "".ljust(columns)

    def prepend_prefix(self, value: str, column: int) -> str:
        prefix = self.column_prefix(column)
        return utils.as_string(prefix, value, separator="")

    def is_valid_line(self, *text: str | None, **kw: Unpack[FormatterArgs]) -> bool:
        values = utils.clean_blank(*text)
        if len(values) == 0:
            return False
        level_col = self.indent_for(level=kw.get("level", 0))
        as_str = utils.as_string(*values, separator=kw["separator"])
        line_length = len(as_str.rstrip()) + max(len(level_col), kw.get("columns", 0))
        return line_length <= self.max_length

    def _get_words(self, value: str, split_char: str | None = None) -> list[str]:
        if split_char is None:
            split_char = " "
        return value.split(split_char)

    def into_words(self, *text: str | None) -> list[str]:
        values = utils.clean_blank(*text)
        if len(text) == 0:
            return []
        if len(values) == 1:
            return self._get_words(values[0])
        words = [values[0]]
        for value in values[1:]:
            words.extend(self._get_words(value))
        return words

    def valid_lines_for(self, *text: str | None, **kw: Unpack[FormatterArgs]) -> list[str]:
        if text is None or len(text) == 0:
            return []
        if self.is_valid_line(*text, **kw):
            return utils.clean_blank(*text)
        words = self.into_words(*text)
        return self.concat_values(*words, **kw)

    def _concat_to_long_value(self, *value: str, **kw: Unpack[FormatterArgs]) -> tuple[str, str]:
        kwargs = kw.copy()
        kwargs["separator"] = " "
        value_lines = self.valid_lines_for(*value, **kwargs)
        if kw.get("is_code", False):
            prefix = self.find_prefix_in_code(value_lines[-2], **kw)
            kw["prefix"] = prefix
        return utils.lines_as_str(*value_lines[:-1]), value_lines[-1].lstrip()

    def _must_fill_column_in(self, value: str, columns: int) -> bool:
        if columns <= 0:
            return False
        return len(value) != columns

    def concat_values(self, *values: str, **kw: Unpack[FormatterArgs]) -> list[str]:
        if len(values) == 0:
            return []
        concat_lines = []
        current = self.prepend_prefix(values[0].strip(), kw.get("prefix", 0))
        if self._must_fill_column_in(current, kw.get("columns", 0)):
            current = self.fill_column(current, kw.get("columns", 0))
        for value in values[1:]:
            value = value.strip()
            if len(value) == 0:
                continue
            concat = utils.as_string(current, value, separator=kw["separator"])
            if self.is_not_max_length(concat):
                current = concat
                continue
            elif not self.is_valid_line(value, **kw):
                current, value = self._concat_to_long_value(current, value, **kw)
            if len(kw["separator"].strip()) > 0:
                current = f"{current}{kw['separator']}".rstrip()
            concat_lines.append(current)
            prefix = 0
            if kw.get("columns", 0) > 0:
                prefix = max(kw.get("prefix", 0), kw.get("columns", 0) + 1)
            current = self.prepend_prefix(value, prefix)
        concat_lines.append(current)
        return concat_lines


@dataclass
class ArgDoc:
    name: str
    default: str
    description: list[str]
    constants: list[CommandConstant]

    def has_default(self) -> bool:
        return len(self.default) > 0

    def has_description(self) -> bool:
        return len(self.description) > 0

    def has_constants(self) -> bool:
        return len(self.constants) > 0

    def has_constants_descriptions(self) -> bool:
        return any(value.has_description() for value in self.constants)

    def get_name(self, constant: CommandConstant) -> str:
        return f"- {constant.name.upper()}:"


TArg = TypeVar("TArg", bound=CommandArgs, contravariant=True)


class IArgCreator(Protocol[TArg]):
    def to_arg(self, arg: TArg) -> str: ...

    def to_doc_name(self, arg: TArg, suffix: str | None) -> str: ...

    def to_args(self) -> list[str]: ...

    def arg_docstring(self, arg: TArg, **kw: Unpack[FormatterArgs]) -> ArgDoc: ...

    def docstring(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]: ...

    def apply_doc_names_to(self, line: str) -> str: ...


class IDocCreator(Protocol):
    def function_doc(self, lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]: ...

    def args_doc(self, docs: list[ArgDoc], **kw: Unpack[FormatterArgs]) -> list[str]: ...


class ICommandCreator(Protocol):
    def signature(self, level: int) -> str: ...

    def docstring(self, level: int, separator: str = " ", columns: int = 0) -> str: ...

    def code(self, **kw: Unpack[FormatterArgs]) -> str: ...


class ACodeCreator(ABC):
    def __init__(self, extension: str):
        self._extension = extension

    @property
    def extension(self) -> str:
        if not self._extension.startswith("."):
            return f".{self._extension}"
        return self._extension
