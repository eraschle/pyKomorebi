from functools import cache
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Optional
from pathlib import Path

from pyKomorebi.model import ApiCommand


@dataclass(frozen=True)
class Options:
    import_path: Path
    import_extension: str

    export_path: Optional[Path] = None


class ICodeGenerator(Protocol):
    @property
    def extension(self) -> str: ...

    def pre_generator(self, code_lines: list[str]) -> list[str]: ...

    def generate(self, command: ApiCommand) -> list[str]: ...

    def post_generator(self, code_lines: list[str]) -> list[str]: ...


class AGenerator(ABC, ICodeGenerator):
    def __init__(self, options: Options, extension: str, indent: str):
        self.options = options
        self._extension = extension
        self.indent = indent

    @property
    def extension(self) -> str:
        if not self._extension.startswith("."):
            return f".{self._extension}"
        return self._extension

    def _line(self, line: str, level: int) -> str:
        indent = self.indent * level if level > 0 else ""
        return f"{indent}{line}"

    @abstractmethod
    def generate(self, command: ApiCommand) -> list[str]:
        pass


@cache
def get(language: str, options: Options) -> ICodeGenerator:
    if language == "ahk":
        from pyKomorebi.generator import ahk

        return ahk.AutoHotKeyGenerator(options)
    if language == "lisp":
        from pyKomorebi.generator import lisp

        return lisp.LispGenerator(options)
    raise ValueError("Unsupported language {}".format(language))
