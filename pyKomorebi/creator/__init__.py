from typing import Iterable, Protocol

from pyKomorebi.model import ApiCommand


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

        return lisp.LispCreator(kwargs["export_path"])
    raise ValueError(f"Language {kwargs['language']} is not supported.")
