import re
import itertools
from pathlib import Path
from typing import Optional, Any


from pyKomorebi import utils
from pyKomorebi.model import ApiCommand, CommandOption, CommandArgument


CLEANUP_LINES = ["```"]

USAGE_LINE = "Usage:"

ARGUMENT_LINE = "Arguments:"
ARGS_PATTERN = re.compile(r"\s*(?P<name><\w+>)")

OPTION_LINE = "Options:"
OPTION_PATTERN = re.compile(r"\s*(?P<short>-\w+)?(?:[,\s]*(?P<name>--\w+))?\s*(?P<arg><.*>)?")

DEFAULT_PATTERN = re.compile(r".*(?P<complete>\[default:\s*(?P<default>\w*)\])", re.DOTALL)
POSSIBLE_PATTERN = re.compile(r".*(?P<complete>\[possible values:\s*(?P<values>.*)\])", re.DOTALL)


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


def _split_usage_line(line: str, cli_name: Optional[str] = None) -> dict[str, Any]:
    if cli_name is None:
        cli_name = "komorebic.exe"
    command = line.split(" ")
    if cli_name not in command:
        raise Exception(f"{cli_name} not found in line {line}")
    cmd_index = command.index(cli_name)
    command = command[cmd_index + 1 :]
    return {"name": command[0], "arguments": command[1:]}


def _find_line(doc_lines: list[str], search: str) -> tuple[int, Optional[str]]:
    for idx, line in enumerate(doc_lines):
        if search not in line:
            continue
        return idx, search
    return -1, None


def _get_cmd_name(path: Path, doc_lines: list[str]) -> str:
    if doc_lines[0].startswith("#"):
        line = doc_lines.pop(0)
        return line.removeprefix("#").strip()
    _, line = _find_line(doc_lines, search="Usage:")
    file_name = path.with_suffix("").name
    if line is None:
        return file_name
    cmd_dict = _split_usage_line(line)
    return cmd_dict.get("name", file_name)


def _create_usage(doc_lines: list[str]) -> Optional[str]:
    idx, line = _find_line(doc_lines, USAGE_LINE)
    if idx < 0 or line is None:
        return None
    return line.replace(USAGE_LINE, "").strip()


def _create_function_doc(doc_lines: list[str]) -> list[str]:
    lines = list(doc_lines)
    idx, line = _find_line(lines, ARGUMENT_LINE)
    if idx < 0 or line is None:
        idx, line = _find_line(lines, OPTION_LINE)
    if idx > 0:
        lines = lines[:idx]
    idx, line = _find_line(lines, USAGE_LINE)
    if idx > 0 and line is not None:
        lines.pop(idx)
    lines = utils.clean_none_or_empty(lines)
    return [line.strip() for line in lines]


def _get_lines(doc_lines: list[str], current: str, other: str) -> list[str]:
    idx, line = _find_line(doc_lines, current)
    if idx < 0 or line is None:
        return []
    lines = doc_lines[idx + 1 :]
    arg_idx, _ = _find_line(lines, other)
    if arg_idx > 0:
        lines = lines[:arg_idx]
    return utils.clean_none_or_empty(lines, strip=True)


def _get_indexes(lines: list[str], startswith: str) -> list[int]:
    indexes = []
    for idx, line in enumerate(lines):
        if not line.strip().startswith(startswith):
            continue
        indexes.append(idx)
    indexes.append(len(lines))
    return indexes


def _get_default_value(doc_string: str) -> tuple[str, Optional[str]]:
    matched = DEFAULT_PATTERN.match(doc_string)
    if matched is None:
        return doc_string, None
    default = matched.group("default")
    doc_string = doc_string.replace(matched.group("complete"), "").strip()
    return doc_string, default


def _get_possible_values_regex(doc_string: str) -> tuple[str, list[str]]:
    matched = POSSIBLE_PATTERN.match(doc_string)
    if matched is None:
        return doc_string, []
    complete = matched.group("complete")
    doc_string = doc_string.replace(complete, "").strip()
    possible_values = utils.strip_lines(matched.group("values").split(","))
    return doc_string, possible_values


def _get_possible_values_startswith(doc_string: str) -> tuple[str, list[str]]:
    if not doc_string.lower().startswith("possible values:"):
        return doc_string, []
    possible_values = doc_string.splitlines(keepends=False)
    values = []
    for value in possible_values[1:]:
        if not value.strip().startswith("-"):
            continue
        values.append(value.strip())
    return doc_string, values


def _get_possible_values(doc_string: str) -> tuple[str, list[str]]:
    doc_string, values = _get_possible_values_regex(doc_string)
    if len(values) == 0:
        doc_string, values = _get_possible_values_startswith(doc_string)
    return doc_string, values


def _docs_default_and_values(doc_lines: list[str]) -> tuple[list[str], Optional[str], list[str]]:
    doc_string = "\n".join(utils.clean_none_or_empty(doc_lines, strip=True))
    doc_string, default = _get_default_value(doc_string)
    doc_string, possible_values = _get_possible_values(doc_string)
    doc_lines = [line.strip() for line in doc_string.split("\n")]
    doc_lines = [line for line in doc_lines if len(line) > 0]
    return doc_lines, default, possible_values


def _get_option_short_and_name(line: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    option = OPTION_PATTERN.match(line)
    if option is None:
        raise Exception(f"No Option found in line {line}")
    return option.group("short"), option.group("name"), option.group("arg")


def _create_options(doc_lines: list[str]) -> list[CommandOption]:
    option_lines = _get_lines(doc_lines, current=OPTION_LINE, other=ARGUMENT_LINE)
    option_indexes = _get_indexes(option_lines, startswith="-")
    options = []
    for start_idx, next_idx in itertools.pairwise(option_indexes):
        short, name, arg_value = _get_option_short_and_name(option_lines[start_idx])
        doc_lines = option_lines[start_idx + 1 : next_idx]
        doc_lines, default, possible_values = _docs_default_and_values(doc_lines)
        options.append(
            CommandOption(
                short=utils.strip_value(short),
                name=utils.strip_value(name),
                arg_value=utils.strip_value(arg_value),
                description=utils.strip_lines(doc_lines),
                default=utils.strip_value(default),
                possible_values=utils.strip_lines(possible_values),
            )
        )
    return options


def _get_argument_name(line: str) -> str:
    argument = ARGS_PATTERN.match(line)
    if argument is None:
        raise Exception(f"No ARGUMENT name found in line {line}")
    return argument.group("name")


def _create_arguments(doc_lines: list[str]) -> list[CommandArgument]:
    args_lines = _get_lines(doc_lines, current=ARGUMENT_LINE, other=OPTION_LINE)
    args_indexes = _get_indexes(args_lines, startswith="<")
    args = []
    for start_idx, next_idx in itertools.pairwise(args_indexes):
        name = _get_argument_name(args_lines[start_idx])
        doc_lines = args_lines[start_idx + 1 : next_idx]
        doc_lines, default, possible_values = _docs_default_and_values(doc_lines)
        args.append(
            CommandArgument(
                name=utils.strip_value(name),
                description=utils.strip_lines(doc_lines),
                default=utils.strip_value(default),
                possible_values=utils.strip_lines(possible_values),
            )
        )
    return args


def create(path: Path) -> ApiCommand:
    lines = _read_docs(path)
    api_name = _get_cmd_name(path, lines)
    doc_string = _create_function_doc(lines)
    usage = _create_usage(lines)
    options = _create_options(lines)
    arguments = _create_arguments(lines)
    return ApiCommand(
        name=api_name,
        description=doc_string,
        usage=usage,
        arguments=arguments,
        options=options,
    )
