import subprocess
from pyKomorebi import utils


def find_line_index(lines: list[str], search: str, lower_case: bool = False) -> int | None:
    for idx, line in enumerate(lines):
        line = line.lower() if lower_case else line
        if search not in line:
            continue
        return idx
    return None


def run_command(*command: str) -> list[str]:
    output = subprocess.check_output(["komorebic.exe", *command])
    return output.decode("utf-8").split("\n")


def run_help_command(*command: str) -> list[str]:
    command = command + ("--help",)
    return run_command(*command)


def get_lines(lines: list[str], search: str | None) -> list[str]:
    if search is None:
        return lines
    start_index = find_line_index(lines, search)
    start_index = start_index if start_index is not None else 0
    return utils.clean_blank(*lines[start_index + 1 :])


def komorebic_commands(search: str = "Commands:") -> list[str]:
    output = run_help_command()
    return get_lines(output, search)
