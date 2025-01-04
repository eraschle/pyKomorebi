import re
import itertools

from pyKomorebi import utils
from pyKomorebi.model import ApiCommand, CommandConstant, CommandOption, CommandArgument


USAGE_LINE = "Usage:"

ARGUMENT_LINE = "Arguments:"
ARGS_PATTERN = re.compile(r"\s*(?P<name><[a-zA-Z-_]+>)(?P<rest>.*)?")
ARGS_OPT_PATTERN = re.compile(r"\s*(?P<name>\[[A-Z-_]+\])(?P<optional>[\.]*)?(?P<rest>.*)?")

OPTION_LINE = "Options:"
OPTION_PATTERN = re.compile(
    r"\s*(?P<short>-\w+)?(?:[,\s]*(?P<name>--[\w-]+))?\s*(?P<arg><.*>)?(?P<description>.*)"
)

DEFAULT_PATTERN = re.compile(r".*(?P<complete>\[default:\s*(?P<default>\w*)\])", re.DOTALL)
CONSTANTS_PATTERN = re.compile(
    r".*(?P<complete>\[possible\s*values:\s*(?P<values>.*)\].*)", re.DOTALL
)

CLEANUP_PATTERN = [
    re.compile(r"(\s*\(without.*?\))", re.DOTALL),
]


def find_line(lines: list[str], search: str, lower_case: bool = False) -> tuple[int, str | None]:
    for idx, line in enumerate(lines):
        if line is None:
            continue
        search_value = line.lower() if lower_case else line
        if search not in search_value:
            continue
        return idx, line
    return -1, None


def _create_usage(lines: list[str]) -> str | None:
    idx, line = find_line(lines, USAGE_LINE)
    if idx < 0 or line is None:
        return None
    return line.replace(USAGE_LINE, "").strip()


def _create_function_doc(lines: list[str]) -> list[str]:
    idx, line = find_line(lines, ARGUMENT_LINE)
    if idx < 0 or line is None:
        idx, line = find_line(lines, OPTION_LINE)
    if idx > 0:
        lines = lines[:idx]
    idx, line = find_line(lines, USAGE_LINE)
    if idx > 0 and line is not None:
        lines.pop(idx)
    return lines


def _get_lines(doc_lines: list[str], current: str, other: str) -> list[str]:
    idx, line = find_line(doc_lines, current)
    if idx < 0 or line is None:
        return []
    lines = doc_lines[idx:]
    arg_idx, _ = find_line(lines, other)
    if arg_idx > 0:
        lines = lines[:arg_idx]
    return lines


def _match_pattern(line: str, patterns: list[re.Pattern]) -> re.Match | None:
    for pattern in patterns:
        matched = pattern.match(line)
        if matched is None:
            continue
        return matched
    return None


def _match_any_value(matched: re.Match | None, *group_name: str) -> bool:
    if matched is None:
        return False
    for name, value in matched.groupdict().items():
        if len(group_name) > 0 and name not in group_name:
            continue
        if value is None or len(value.strip()) == 0:
            continue
        return True
    return False


def _get_indexes(lines: list[str], regexes: list[re.Pattern], *group: str) -> list[int]:
    indexes = []
    for idx, line in enumerate(lines):
        match = _match_pattern(line, regexes)
        if not _match_any_value(match, *group):
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


ENUM_PATTERN = re.compile(r"(?P<name>\s*-\s?[-\w\s]*:)")


def split_constant_string(text: str, strip_char: str = " ") -> tuple[str, list[str]]:
    if ENUM_PATTERN.match(text) is None:
        return utils.strip_value(text, strip_chars=strip_char), []
    values = ENUM_PATTERN.split(text, maxsplit=1)
    values = utils.strip_and_clean_blank(*values, strip_chars=strip_char)
    if len(values) == 0:
        return utils.strip_value(text, strip_chars=strip_char), []
    name = values.pop(0).removeprefix("-").removesuffix(":").strip()
    return name, utils.strip_and_clean_blank(*values, strip_chars=strip_char)


def constant_from_lines(lines: list[str]) -> list[CommandConstant]:
    constants = []
    for value in lines:
        name, desc = split_constant_string(value)
        constants.append(CommandConstant(constant=name.strip(), description=desc))
    return constants


def _get_constants_regex(doc_string: str) -> tuple[str, list[CommandConstant]]:
    matched = CONSTANTS_PATTERN.match(doc_string)
    if matched is None:
        return doc_string, []
    complete = matched.group("complete")
    doc_string = doc_string.replace(complete, "").strip()
    matched_values = matched.group("values").split(",")
    matched_values = utils.strip_lines(*matched_values, strip_chars=" ")
    return doc_string, constant_from_lines(matched_values)


def _get_constants_startswith(doc_string: str) -> tuple[str, list[CommandConstant]]:
    doc_lines = utils.strip_and_clean_blank(*doc_string.splitlines(keepends=False), strip_chars=" ")
    idx, line = find_line(doc_lines, search="possible values:", lower_case=True)
    if idx < 0 or line is None:
        return doc_string, []
    doc_string = "\n".join(doc_lines[:idx])
    values = []
    for value in doc_lines[idx + 1 :]:
        if not value.strip().startswith("-"):
            continue
        values.append(value)
    values = utils.strip_lines(*values)
    return doc_string, constant_from_lines(values)


def _get_constants(doc_string: str) -> tuple[str, list[CommandConstant]]:
    doc_string, values = _get_constants_regex(doc_string)
    if len(values) == 0:
        doc_string, values = _get_constants_startswith(doc_string)
    return doc_string, values


def _docs_default_and_constants(
    doc_lines: list[str], strip_char: str
) -> tuple[list[str], str | None, list[CommandConstant]]:
    doc_string = "\n".join(utils.clean_blank(*doc_lines, strip_chars=None))
    doc_string, default = _get_default_value(doc_string)
    doc_string, constants = _get_constants(doc_string)
    lines = utils.strip_and_clean_blank(
        *doc_string.splitlines(keepends=False), strip_chars=strip_char
    )
    return lines, default, constants


def _get_option_short_and_name(line: str) -> tuple[str | None, str | None, str | None, str]:
    option = OPTION_PATTERN.match(line)
    if option is None:
        raise Exception(f"No Option found in line {line}")
    return option.group("short"), option.group("name"), option.group("arg"), option.group("description")


def _create_options(doc_lines: list[str], strip_char: str) -> list[CommandOption]:
    option_lines = _get_lines(doc_lines, current=OPTION_LINE, other=ARGUMENT_LINE)
    option_indexes = _get_indexes(option_lines, [OPTION_PATTERN], "short", "name")
    options = []
    for start_idx, next_idx in itertools.pairwise(option_indexes):
        short, long, arg_value, desc = _get_option_short_and_name(option_lines[start_idx])
        doc_lines = option_lines[start_idx + 1 : next_idx]
        if utils.is_not_blank(desc):
            doc_lines = [desc] + doc_lines
        doc_lines, default, constants = _docs_default_and_constants(doc_lines, strip_char=strip_char)
        options.append(
            CommandOption(
                short=utils.strip_value(short, strip_chars=strip_char),
                long=utils.strip_value(long, strip_chars=strip_char),
                value=utils.strip_value(arg_value, strip_chars=strip_char),
                description=utils.strip_and_clean_blank(*doc_lines, strip_chars=strip_char),
                default=utils.strip_value(default, strip_chars=strip_char),
                constants=constants,
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


def _create_arguments(doc_lines: list[str], strip_char: str) -> list[CommandArgument]:
    args_lines = _get_lines(doc_lines, current=ARGUMENT_LINE, other=OPTION_LINE)
    args_indexes = _get_indexes(args_lines, [ARGS_PATTERN, ARGS_OPT_PATTERN], "name")
    args = []
    for start_idx, next_idx in itertools.pairwise(args_indexes):
        name, optional, rest = _get_argument_name(args_lines[start_idx])
        doc_lines = args_lines[start_idx + 1 : next_idx]
        if utils.is_not_blank(rest):
            doc_lines = [rest] + doc_lines
        doc_lines, default, constants = _docs_default_and_constants(doc_lines, strip_char=strip_char)
        args.append(
            CommandArgument(
                argument=utils.strip_value(name, strip_chars=strip_char),
                description=utils.strip_and_clean_blank(*doc_lines, strip_chars=strip_char),
                default=utils.strip_value(default, strip_chars=strip_char),
                constants=constants,
                optional=optional,
            )
        )
    return args


def create_api_command(command_name: str, lines: list[str]) -> ApiCommand:
    api_name = command_name
    lines = utils.clean_pattern_in(lines, CLEANUP_PATTERN)
    doc_string = _create_function_doc(lines)
    usage = _create_usage(lines)
    options = _create_options(lines, strip_char=" ")
    arguments = _create_arguments(lines, strip_char=" ")
    return ApiCommand(
        name=api_name,
        description=doc_string,
        usage=usage,
        arguments=arguments,
        options=options,
    )
