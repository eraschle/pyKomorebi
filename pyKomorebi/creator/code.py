from abc import ABC
from dataclasses import dataclass
from typing import Iterable, NotRequired, Optional, Protocol, TypeVar, TypedDict, Unpack

from pyKomorebi.model import CommandArgs


class FormatterArgs(TypedDict):
    level: NotRequired[int]
    columns: NotRequired[Optional[int]]
    suffix: NotRequired[str]
    default_format: NotRequired[str]


class ICodeFormatter(Protocol):
    def empty_line(self, count: int = 1) -> list[str]: ...

    def is_valid_length(self, line: Optional[str]) -> bool: ...

    def indent_for(self, level: int) -> str: ...

    def indent(self, line: str, level: int = 0) -> str: ...

    def name_to_doc(self, name: str, **kw: Unpack[FormatterArgs]) -> str: ...

    def name_to_code(self, name: str) -> str: ...

    def concat_args(self, args: list[str]) -> str: ...

    def function_name(self, name: str, private: bool = False) -> str: ...

    def fill_column(self, value: str, columns: Optional[int] = None) -> str: ...

    def apply_suffix(self, value: str, suffix: Optional[str]) -> str: ...


class ACodeFormatter(ABC, ICodeFormatter):
    _empty_line = [""]

    def __init__(self, indent: str, max_length: int):
        self.indent_str = indent
        self.max_length = max_length

    def is_valid_length(self, line: Optional[str]) -> bool:
        if line is None:
            return False
        return len(line) <= self.max_length

    def empty_line(self, count: int = 1) -> list[str]:
        if count <= 0:
            return []
        return self._empty_line * count

    def indent_for(self, level: int) -> str:
        if level <= 0:
            return ""
        return self.indent_str * level

    def indent(self, line: str, level: int = 0) -> str:
        indent = self.indent_for(level)
        return f"{indent}{line}"

    def default_value(self, value: Optional[str], format_str: Optional[str] = None) -> str:
        if value is None or len(value.strip()) == 0:
            return ""
        if format_str is None:
            return value
        return format_str.format(value)

    def apply_suffix(self, value: str, suffix: Optional[str]) -> str:
        if suffix is None or len(suffix) == 0 or value.strip().endswith(suffix):
            return value
        return f"{value}{suffix}"

    def fill_column(self, value: str, columns: Optional[int] = None) -> str:
        if columns is None or 0 > len(value) >= columns:
            return value
        return value.ljust(columns)


@dataclass
class ArgDoc:
    name: str
    default: str
    description: list[str]
    possible_values: list[str]


TArg = TypeVar("TArg", bound=CommandArgs, contravariant=True)


class CreatorArgs(FormatterArgs):
    separator: str


class IArgCreator(Protocol[TArg]):
    def to_arg(self, arg: TArg) -> str: ...

    def to_doc_name(self, arg: TArg, **kw: Unpack[FormatterArgs]) -> str: ...

    def to_args(self) -> Iterable[str]: ...

    def validate_code(self, arg: TArg) -> str: ...

    def validate_values(self) -> list[str]: ...

    def as_call_arg(self, arg: TArg) -> str: ...

    def to_call_args(self) -> Iterable[str]: ...

    def arg_docstring(self, arg: TArg, **kw: Unpack[CreatorArgs]) -> ArgDoc: ...

    def docstring(self, **kw: Unpack[CreatorArgs]) -> Iterable[ArgDoc]: ...

    def apply_doc_names_to(self, line: str) -> str: ...


class IDocCreator(Protocol):
    def is_valid_length(self, line: Optional[str], level: int = 0, columns: int = 0) -> bool: ...

    def function_doc(self, lines: Iterable[str], **kw: Unpack[CreatorArgs]) -> str: ...

    def args_doc(self, docs: Iterable[ArgDoc], **kw: Unpack[CreatorArgs]) -> str: ...


class ICommandCreator(Protocol):
    def signature(self, level: int) -> str: ...

    def docstring(self, level: int, separator: str = " ", columns: int = 0) -> str: ...

    def code(self, **kw: Unpack[CreatorArgs]) -> str: ...


class ACodeCreator(ABC):
    def __init__(self, extension: str):
        self._extension = extension

    @property
    def extension(self) -> str:
        if not self._extension.startswith("."):
            return f".{self._extension}"
        return self._extension
