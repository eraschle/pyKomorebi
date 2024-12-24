import re
from subprocess import CalledProcessError
from typing import Iterable, TypeGuard

from pyKomorebi import console
from pyKomorebi.generate import Options
from pyKomorebi.model import ApiCommand
from pyKomorebi.factory import api_factory


def _get_command_help(command: str) -> list[str]:
    lines = console.run_help_command(command)
    return console.get_lines(lines, search=None)


def create(command: str) -> ApiCommand | None:
    try:
        lines = _get_command_help(command)
    except CalledProcessError:
        return None
    return api_factory.create_api_command(command, lines)


def _is_command(match: re.Match[str] | None) -> TypeGuard[re.Match[str]]:
    if match is None:
        return False
    prefix = match.group("prefix")
    if len(prefix) == 0 or len(prefix) > 5:
        return False
    name = match.group("name").strip()
    return not any(hlp in name for hlp in ["--help", "-h", "help", "Commands", "Options", "-V"])


def _get_command_names() -> Iterable[str]:
    pattern = re.compile(r"(?P<prefix>\s*)(?P<name>[a-zA-Z-_]+)")
    for command in console.komorebic_commands():
        match = pattern.match(command)
        if not _is_command(match):
            continue
        yield match.group("name")


def import_api(_: Options) -> Iterable[ApiCommand | None]:
    for cmd_name in _get_command_names():
        yield create(cmd_name)
