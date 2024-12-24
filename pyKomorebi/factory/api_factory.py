import re
import itertools

from pyKomorebi import utils
from pyKomorebi.model import ApiCommand, CommandOption, CommandArgument


USAGE_LINE = "Usage:"

ARGUMENT_LINE = "Arguments:"
ARGS_PATTERN = re.compile(r"\s*(?P<name><[a-zA-Z-_]+>)(?P<rest>.*)?")
ARGS_OPT_PATTERN = re.compile(r"\s*(?P<name>\[[A-Z-_]+\])(?P<optional>[\.]*)?(?P<rest>.*)?")

OPTION_LINE = "Options:"
OPTION_PATTERN = re.compile(r"\s*(?P<short>-\w+)?(?:[,\s]*(?P<name>--[\w-]+))?\s*(?P<arg><.*>)?(?P<description>.*)")

DEFAULT_PATTERN = re.compile(r".*(?P<complete>\[default:\s*(?P<default>\w*)\])", re.DOTALL)
POSSIBLE_PATTERN = re.compile(r".*(?P<complete>\[possible values:\s*(?P<values>.*)\])", re.DOTALL)


def find_line(doc_lines: list[str], search: str, lower_case: bool = False) -> tuple[int, str | None]:
    for idx, line in enumerate(doc_lines):
        line = line.lower() if lower_case else line
        if search not in line:
            continue
        return idx, line
    return -1, None


def _create_usage(doc_lines: list[str]) -> str | None:
    idx, line = find_line(doc_lines, USAGE_LINE)
    if idx < 0 or line is None:
        return None
    return line.replace(USAGE_LINE, "").strip()


def _create_function_doc(doc_lines: list[str]) -> list[str]:
    lines = list(doc_lines)
    idx, line = find_line(lines, ARGUMENT_LINE)
    if idx < 0 or line is None:
        idx, line = find_line(lines, OPTION_LINE)
    if idx > 0:
        lines = lines[:idx]
    idx, line = find_line(lines, USAGE_LINE)
    if idx > 0 and line is not None:
        lines.pop(idx)
    lines = utils.clean_none_or_empty(lines)
    return utils.strip_lines(lines)


def _get_lines(doc_lines: list[str], current: str, other: str) -> list[str]:
    idx, line = find_line(doc_lines, current)
    if idx < 0 or line is None:
        return []
    lines = doc_lines[idx + 1 :]
    arg_idx, _ = find_line(lines, other)
    if arg_idx > 0:
        lines = lines[:arg_idx]
    return utils.clean_none_or_empty(lines, strip_chars=None)


def _match_pattern(line: str, patterns: list[re.Pattern]) -> re.Match | None:
    for pattern in patterns:
        match = pattern.match(line)
        if match is None:
            continue
        return match
    return None


def _match_any_value(match: re.Match | None, *group_name: str) -> bool:
    if match is None:
        return False
    for name, value in match.groupdict().items():
        if len(group_name) > 0 and name not in group_name:
            continue
        if value is None or len(value.strip()) == 0:
            continue
        return True
    return False


def _get_indexes(lines: list[str], regexes: list[re.Pattern], *group_names: str) -> list[int]:
    indexes = []
    for idx, line in enumerate(lines):
        match = _match_pattern(line, regexes)
        if not _match_any_value(match, *group_names):
            continue
        indexes.append(idx)
    indexes.append(len(lines))
    return indexes


def _get_default_value(doc_string: str) -> tuple[str, str | None]:
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
    doc_lines = doc_string.splitlines(keepends=False)
    idx, line = find_line(doc_lines, search="possible values:", lower_case=True)
    if idx < 0 or line is None:
        return doc_string, []
    doc_string = "\n".join(doc_lines[:idx])
    values = []
    for value in doc_lines[idx + 1 :]:
        if not value.strip().startswith("-"):
            continue
        values.append(value)
    return doc_string, utils.strip_lines(values)


def _get_possible_values(doc_string: str) -> tuple[str, list[str]]:
    doc_string, values = _get_possible_values_regex(doc_string)
    if len(values) == 0:
        doc_string, values = _get_possible_values_startswith(doc_string)
    return doc_string, values


def _docs_default_and_values(doc_lines: list[str]) -> tuple[list[str], str | None, list[str]]:
    doc_string = "\n".join(utils.clean_none_or_empty(doc_lines, strip_chars=None))
    doc_string, default = _get_default_value(doc_string)
    doc_string, possible_values = _get_possible_values(doc_string)
    return doc_string.splitlines(keepends=False), default, possible_values


def _get_option_short_and_name(line: str) -> tuple[str | None, str | None, str | None, str]:
    option = OPTION_PATTERN.match(line)
    if option is None:
        raise Exception(f"No Option found in line {line}")
    return option.group("short"), option.group("name"), option.group("arg"), option.group("description")


def _create_options(doc_lines: list[str]) -> list[CommandOption]:
    option_lines = _get_lines(doc_lines, current=OPTION_LINE, other=ARGUMENT_LINE)
    option_indexes = _get_indexes(option_lines, [OPTION_PATTERN], "short", "name")
    options = []
    for start_idx, next_idx in itertools.pairwise(option_indexes):
        short, name, arg_value, desc = _get_option_short_and_name(option_lines[start_idx])
        doc_lines = option_lines[start_idx + 1 : next_idx]
        if desc is not None and len(desc.strip()) > 0:
            doc_lines = [desc] + doc_lines
        doc_lines, default, possible_values = _docs_default_and_values(doc_lines)
        options.append(
            CommandOption(
                short=utils.strip_value(short),
                name=utils.strip_value(name),
                value=utils.strip_value(arg_value),
                description=utils.strip_lines(doc_lines),
                default=utils.strip_value(default),
                possible_values=utils.strip_lines(possible_values),
            )
        )
    return options


def _get_argument_name(line: str) -> tuple[str, bool, str | None]:
    argument = ARGS_PATTERN.match(line)
    optional = False
    if argument is None:
        argument = ARGS_OPT_PATTERN.match(line)
        optional = True
    if argument is None:
        raise Exception(f"No ARGUMENT name found in line {line}")
    if optional and argument.group("optional") is not None:
        opt_value = argument.group("optional")
        optional = not opt_value.startswith("...")
    return argument.group("name"), optional, argument.group("rest")


def _create_arguments(doc_lines: list[str]) -> list[CommandArgument]:
    args_lines = _get_lines(doc_lines, current=ARGUMENT_LINE, other=OPTION_LINE)
    args_indexes = _get_indexes(args_lines, regexes=[ARGS_PATTERN, ARGS_OPT_PATTERN])
    args = []
    for start_idx, next_idx in itertools.pairwise(args_indexes):
        name, optional, rest = _get_argument_name(args_lines[start_idx])
        doc_lines = args_lines[start_idx + 1 : next_idx]
        if rest is not None and len(rest.strip()) > 0:
            doc_lines = [rest] + doc_lines
        doc_lines, default, possible_values = _docs_default_and_values(doc_lines)
        args.append(
            CommandArgument(
                name=utils.strip_value(name),
                description=utils.strip_lines(doc_lines),
                default=utils.strip_value(default),
                possible_values=utils.strip_lines(possible_values),
                optional=optional,
            )
        )
    return args


def create_api_command(command_name: str, lines: list[str]) -> ApiCommand:
    api_name = command_name
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
