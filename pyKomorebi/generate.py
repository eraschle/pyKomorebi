from pathlib import Path
from typing import Iterable, TypedDict, Unpack

from pyKomorebi import creator, factory
from pyKomorebi.model import ApiCommand


class Options(TypedDict):
    language: str
    import_path: Path
    extension: str
    export_path: Path
    exclude_names: list[str]
    translated: creator.TranslationManager


def _generate_code(commands: Iterable[ApiCommand | None], **kwargs: Unpack[Options]) -> None:
    code = creator.get(**kwargs)
    commands = [cmd for cmd in commands if cmd is not None]
    lines = code.generate(sorted(commands, key=lambda x: x.name))
    with open(kwargs["export_path"], "w") as export_file:
        content = "\n".join(lines)
        export_file.write(content)


def generate_code(**kwargs: Unpack[Options]) -> None:
    import_factory = factory.get(kwargs["extension"])
    commands = import_factory(kwargs)
    _generate_code(commands, **kwargs)
