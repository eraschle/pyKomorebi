from pathlib import Path
from typing import Iterable, TypedDict, Unpack

from pyKomorebi import creator, factory
from pyKomorebi.model import ApiCommand


class GeneratorArgs(TypedDict):
    language: str
    import_path: Path
    extension: str
    export_path: Path
    exclude_names: list[str]


def _is_excluded(path: Path, exclude_names: list[str]) -> bool:
    file_name = path.name.lower()
    return any(exclude in file_name for exclude in exclude_names)


def _is_import_file(path: Path, exclude_names: list[str]) -> bool:
    if path.is_dir():
        return False
    return not _is_excluded(path, exclude_names)


def _get_import_files(**kwargs: Unpack[GeneratorArgs]) -> list[Path]:
    exclude = [exclude.lower() for exclude in kwargs["exclude_names"]]
    import_path = kwargs["import_path"]
    file_paths = import_path.rglob(f"*{kwargs['extension']}")
    file_paths = [path for path in file_paths if _is_import_file(path, exclude)]
    return sorted(file_paths, key=lambda p: p.name)


def _import_commands(**kwargs: Unpack[GeneratorArgs]) -> Iterable[ApiCommand]:
    factory_impl = factory.get(kwargs["extension"])
    for doc_path in _get_import_files(**kwargs):
        command = factory_impl(doc_path)
        yield command


def generate_from_path(**kwargs: Unpack[GeneratorArgs]) -> None:
    code = creator.get(**kwargs)
    commands = _import_commands(**kwargs)
    lines = code.generate(commands)
    with open(kwargs["export_path"], "w") as export_file:
        content = "\n".join(lines)
        export_file.write(content)
