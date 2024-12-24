from pathlib import Path
from typing import Iterable

from pyKomorebi.generate import Options
from pyKomorebi.model import ApiCommand
from pyKomorebi.factory import api_factory


CLEANUP_LINES = ["```"]


def read_markdown(path: Path) -> list[str]:
    with open(path) as md:
        return md.readlines()


def _clean_doc_lines(lines: list[str]) -> list[str]:
    doc_lines = []
    for line in lines:
        if line.strip() in CLEANUP_LINES:
            continue
        doc_lines.append(line)
    return doc_lines


def _read_docs(path: Path) -> list[str]:
    lines = read_markdown(path)
    lines = _clean_doc_lines(lines)
    return lines


def _split_usage_line(line: str, cli_name: str | None = None) -> dict:
    if cli_name is None:
        cli_name = "komorebic.exe"
    command = line.split(" ")
    if cli_name not in command:
        raise Exception(f"{cli_name} not found in line {line}")
    cmd_index = command.index(cli_name)
    command = command[cmd_index + 1 :]
    return {"name": command[0], "arguments": command[1:]}


def _get_cmd_name(path: Path, doc_lines: list[str]) -> str:
    if doc_lines[0].startswith("#"):
        line = doc_lines.pop(0)
        return line.removeprefix("#").strip()
    _, line = api_factory.find_line(doc_lines, search="Usage:")
    file_name = path.with_suffix("").name
    if line is None:
        return file_name
    cmd_dict = _split_usage_line(line)
    return cmd_dict.get("name", file_name)


def create(path: Path) -> ApiCommand:
    lines = _read_docs(path)
    api_name = _get_cmd_name(path, lines)
    return api_factory.create_api_command(api_name, lines)


def _is_excluded(path: Path, exclude_names: list[str]) -> bool:
    file_name = path.name.lower()
    return any(exclude in file_name for exclude in exclude_names)


def _is_import_file(path: Path, exclude_names: list[str]) -> bool:
    if path.is_dir():
        return False
    return not _is_excluded(path, exclude_names)


def _get_import_files(args: Options) -> list[Path]:
    exclude = [exclude.lower() for exclude in args["exclude_names"]]
    import_path = args["import_path"]
    file_paths = import_path.rglob(f"*{args['extension']}")
    file_paths = [path for path in file_paths if _is_import_file(path, exclude)]
    return sorted(file_paths, key=lambda p: p.name)


def import_api(args: Options) -> Iterable[ApiCommand | None]:
    for doc_path in _get_import_files(args):
        command = create(doc_path)
        yield command
