from dataclasses import dataclass
from typing import Iterable, Protocol

from pyKomorebi.model import ApiCommand


@dataclass
class TranslationManager:
    option_map: dict[str, str]
    argument_map: dict[str, str]

    def option_name(self, name: str) -> str:
        prefix = "--" if name.startswith("--") else "-"
        opt_name = name.removeprefix(prefix)
        if opt_name not in self.option_map:
            return name
        opt_name = self.option_map[opt_name]
        return f"{prefix}{opt_name}"

    def argument_name(self, name: str) -> str:
        if name not in self.argument_map:
            return name
        return self.argument_map[name]


class ICodeCreator(Protocol):
    @property
    def extension(self) -> str: ...

    def generate(self, commands: Iterable[ApiCommand]) -> list[str]: ...


def get(**kwargs) -> ICodeCreator:
    if kwargs["language"] == "ahk":
        from pyKomorebi.creator import ahk

        return ahk.AutoHotKeyCreator()
    if kwargs["language"] == "lisp":
        from pyKomorebi.creator import lisp

        return lisp.LispCreator(kwargs["export_path"], kwargs["translated"])
    raise ValueError(f"Language {kwargs['language']} is not supported.")
