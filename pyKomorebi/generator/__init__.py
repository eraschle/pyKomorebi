from functools import cache
from abc import ABC, abstractmethod
from typing import Protocol

from pyKomorebi.model import ApiCommand


class ICodeGenerator(Protocol):
    @property
    def extension(self) -> str: ...

    def create_content(self, code_lines: list[str]) -> list[str]: ...

    def generate(self, command: ApiCommand) -> list[str]: ...


class AGenerator(ABC, ICodeGenerator):
    def __init__(self, extension: str, indent: str):
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
def get(language: str) -> ICodeGenerator:
    if language == "ahk":
        from pyKomorebi.generator import ahk

        return ahk.AutoHotKeyGenerator()
    if language == "lisp":
        from pyKomorebi.generator import lisp

        return lisp.LispGenerator()
    raise ValueError("Unsupported language {}".format(language))
