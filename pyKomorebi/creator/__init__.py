from dataclasses import dataclass
from typing import Iterable, Protocol

from pyKomorebi.model import ApiCommand


@dataclass
class TranslationManager:
    option_map: dict[str, str]
    argument_map: dict[str, str]
    # by now the first value is the key...
    variable_map: dict[str, str]

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

    def has_variable(self, values: tuple[str, ...]) -> bool:
        return values[0] in self.variable_map

    def variable_name(self, values: tuple[str, ...]) -> str:
        if values[0] not in self.variable_map:
            raise ValueError(f"Variable {values[0]} not found.")
        return self.variable_map[values[0]]


class ICodeCreator(Protocol):
    @property
    def extension(self) -> str: ...

    def generate(self, commands: Iterable[ApiCommand]) -> list[str]: ...


def get(**kwargs) -> ICodeCreator:
    if kwargs["language"] == "ahk":
        from pyKomorebi.creator import ahk

        return ahk.AutoHotKeyCreator(kwargs["translated"])
    if kwargs["language"] == "lisp":
        from pyKomorebi.creator import lisp

        return lisp.LispCreator(kwargs["export_path"], kwargs["translated"])
    raise ValueError(f"Language {kwargs['language']} is not supported.")
