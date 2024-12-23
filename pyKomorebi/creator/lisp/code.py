import re
from typing import TypeGuard, Unpack


from pyKomorebi import utils
from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator.code import (
    ACodeFormatter,
    FormatterArgs,
    ArgDoc,
    IArgCreator,
    ICommandCreator,
    TArg,
)
from pyKomorebi.creator.docs import ADocCreator
from pyKomorebi.model import (
    ApiCommand,
    CommandArgument,
    CommandOption,
)
from pyKomorebi.creator.lisp import package as pkg


class LispCodeFormatter(ACodeFormatter):
    pattern = re.compile(r"[^a-zA-Z0-9]+")
    separator = "-"

    def __init__(self, module_name: str, max_length: int) -> None:
        super().__init__(indent="  ", max_length=max_length, module_name=module_name)

    def _clean_name(self, name: str) -> str:
        name = self.pattern.sub(self.separator, name)
        return name.removeprefix(self.separator).removesuffix(self.separator)

    def name_to_code(self, name: str) -> str:
        if not (name.startswith("(") and name.endswith(")")):
            name = self._clean_name(name)
        return name.lower()

    def name_to_doc(self, name: str, suffix: str | None = None) -> str:
        name = self._clean_name(name)
        return self.apply_suffix(name, suffix)

    def concat_args(self, *args: str, quote: bool = False) -> str:
        arg_names = [self.name_to_code(arg) for arg in args]
        if quote:
            arg_names = [f"\"{arg}\"" for arg in arg_names]
        return " ".join(arg_names)

    def function_name(self, name: str, private: bool = False) -> str:
        name = self.name_to_code(name)
        name = f"-{name}" if private else name
        return "-".join([self.name_to_code(self.module_name), name])


def valid_values_of(values: list[str] | None) -> TypeGuard[list[str]]:
    if values is None:
        return False
    return len(values) > 0


class ALispArgCreator(IArgCreator[TArg]):
    def __init__(self, elements: list[TArg], formatter: LispCodeFormatter) -> None:
        self.elements = elements
        self.formatter = formatter

    def valid_description(self, arg: TArg, strip_char: str | None = None) -> list[str]:
        return utils.list_without_none_or_empty(*arg.description, strip_chars=strip_char)

    def valid_possible_values(self, arg: TArg, strip_char: str | None) -> list[tuple[str, str | None]]:
        values = []
        for value in arg.possible_values:
            values.append(utils.split_enum(value, pattern=utils.ENUM_PATTERN, strip_char=strip_char))
        return values

    def default_value(self, arg: TArg, format_str: str | None = None) -> str:
        return self.formatter.default_value(arg.default, format_str=format_str)

    def to_doc_name(self, arg: TArg, suffix: str | None) -> str:
        doc_name = self.formatter.name_to_doc(arg.get_name(), suffix=suffix)
        if not doc_name.isupper():
            doc_name = doc_name.upper()
        return doc_name

    def apply_doc_names_to(self, line: str) -> str:
        if len(self.elements) == 0:
            return line
        for elem in self.elements:
            search = elem.get_name()
            replace = self.to_doc_name(elem, suffix=None)
            line = line.replace(search, replace)
        return line

    def to_arg(self, arg: TArg) -> str:
        arg_name = self.formatter.name_to_code(arg.get_name())
        return f"{arg_name}"

    def docstring(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]:
        return [self.arg_docstring(option, **kw) for option in self.elements]


class OptionCreator(ALispArgCreator[CommandOption]):
    def to_args(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.elements]

    def option_args(self) -> list[CommandOption]:
        return self.elements

    def arg_docstring(self, arg: CommandOption, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, kw.get("suffix", None)),
            default=self.default_value(arg, kw.get("default_format", None)),
            possible_values=self.valid_possible_values(arg, strip_char=None),
            description=self.valid_description(arg, strip_char=None),
        )


class ArgumentCreator(ALispArgCreator[CommandArgument]):
    def to_args(self, with_optional: bool = True) -> list[str]:
        elements = self.elements
        if not with_optional:
            elements = [arg for arg in elements if arg.optional]
        return [self.to_arg(arg) for arg in elements]

    def required_args(self) -> list[CommandArgument]:
        return [arg for arg in self.elements if not arg.optional]

    def required_arg_names(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.required_args()]

    def optional_args(self) -> list[CommandArgument]:
        return [arg for arg in self.elements if arg.optional]

    def optional_arg_names(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.optional_args()]

    def arg_docstring(self, arg: CommandArgument, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, kw.get("suffix", None)),
            default=self.default_value(arg, kw.get("default_format", None)),
            possible_values=self.valid_possible_values(arg, strip_char=None),
            description=self.valid_description(arg, strip_char=None),
        )


class LispCommandDocCreator(ADocCreator):
    def quote_doc_start(self, lines: list[str], level: int) -> list[str]:
        if not lines[0].lstrip().startswith("\""):
            first_line = lines[0].lstrip()
            first_line = f"\"{first_line}"
            lines[0] = self.formatter.indent(first_line, level=level)
        return lines

    def quote_doc_end(self, lines: list[str]) -> list[str]:
        if not lines[-1].endswith("\""):
            lines[-1] = f"{lines[-1]}\""
        return lines

    def function_doc(self, lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        first, other_sentences = self.get_first_sentence_and_rest(lines)
        if first is None:
            return lines
        doc_lines = []
        if self.formatter.is_valid_line(first, **kw):
            doc_lines.append(self.formatter.ensure_ends_with_point(first))
        else:
            other_sentences.insert(0, first)
        other_sentences = self.ensure_sentences_has_valid_length(other_sentences, **kw)
        doc_lines.extend(self.formatter.concat_values(*other_sentences, **kw))
        return doc_lines

    def args_doc(self, docs: list[ArgDoc], **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["columns"] = self._get_max_length(docs, suffix=kw.get("suffix", ":"))
        doc_lines = []
        for arg in docs:
            doc_lines.extend(self._command_arg_doc(arg, **kw))
        return doc_lines


class LispCommandCreator(ICommandCreator):
    def __init__(self, command: ApiCommand, formatter: LispCodeFormatter, manager: TranslationManager) -> None:
        self.command = command
        self.formatter = formatter
        self.manager = manager
        self.opt = OptionCreator(command.options, formatter)
        self.arg = ArgumentCreator(command.arguments, formatter)
        self.doc = LispCommandDocCreator(formatter=formatter)

    def is_interactive(self) -> bool:
        return len(self.command) == 0

    def command_args(self) -> list[str]:
        return self.arg.to_args() + self.opt.to_args()

    def function_args(self) -> str:
        if self.is_interactive():
            return ""
        arguments = self.arg.required_arg_names()
        args_str = self.formatter.concat_args(*arguments)
        optional = self.arg.optional_arg_names() + self.opt.to_args()
        optional_str = self.formatter.concat_args(*optional)
        if len(optional_str.strip()) == 0:
            return args_str.strip()
        return f"{args_str} &optional {optional_str}".strip()

    def function_name(self) -> str:
        return self.formatter.function_name(self.command.name)

    def autoload_line(self) -> str:
        return self.formatter.indent(";;;###autoload", level=0)

    def _get_signature(self, level: int) -> str:
        func_kind = "defun"
        func_name = self.function_name()
        func_args = self.function_args()
        signature = f'({func_kind} {func_name} ({func_args})'
        return self.formatter.indent(signature, level=level)

    def signature(self, level: int) -> str:
        if not self.is_interactive():
            return self._get_signature(level)
        return utils.lines_as_str(
            self.autoload_line(),
            self._get_signature(level),
        )

    def _apply_changes(self, line: str) -> str:
        line = self.arg.apply_doc_names_to(line)
        line = self.opt.apply_doc_names_to(line)
        return line

    def _function_docs(self) -> list[str]:
        return [self._apply_changes(line) for line in self.command.description]

    def _arg_docs(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]:
        return self.arg.docstring(**kw) + self.opt.docstring(**kw)

    def _ensure_indent(self, line: str) -> str:
        if line.startswith(" "):
            return line
        lines = line.splitlines(keepends=False)
        first_line = lines[0]
        first_line = f"\"{first_line}"
        lines[0] = self.formatter.indent(first_line, level=1)
        return utils.lines_as_str(*lines)

    def docstring(self, level: int, separator: str = " ", columns: int = 0, suffix_args: str = ":") -> str:
        kw = {"separator": separator, "columns": columns, "level": level, "suffix": ""}
        doc_lines = self.doc.function_doc(lines=self._function_docs(), **kw)
        kw.update({"default_format": "(default {0})", "suffix": suffix_args})
        doc_lines.extend(self.doc.args_doc(docs=self._arg_docs(**kw), **kw))
        doc_lines = self.doc.quote_doc_end(doc_lines)
        doc_lines = self.doc.quote_doc_start(doc_lines, level=level)
        return utils.lines_as_str(*doc_lines)

    def code(self, **kw: Unpack[FormatterArgs]) -> str:
        lines = []
        lines.extend(self._function_body_interactive(**kw))
        lines.extend(self._function_body_check_possible_values(**kw))
        lines.extend(self._function_body_convert_args(**kw))
        args = self.command_args()
        lines.extend(self._function_body_call_komorebi(self.command.name, args, **kw))
        return utils.lines_as_str(*lines)

    def _function_body_interactive(self, **kw: Unpack[FormatterArgs]) -> list[str]:
        if not self.is_interactive():
            return []
        return [self.formatter.indent("(interactive)", level=kw.get("level", 1))]

    def _get_check_value_code_line(self, argument: CommandArgument, level: int) -> tuple[str, list[str]]:
        arg_name = self.arg.to_arg(argument)
        valid_values = [enum for enum, _ in self.arg.valid_possible_values(argument, strip_char="- :")]
        valid_values = [f"\"{value}\"" for value in valid_values]
        concat_values = self.formatter.concat_args(*valid_values, quote=True)
        code = self.formatter.indent(f"(unless (member {arg_name} (list {concat_values}))", level=level)
        if len(code) < (self.formatter.max_length * 1.2):
            return code, []
        code = self.formatter.indent(f"(unless (member {arg_name} (list {valid_values[0]}", level=level)
        return code, valid_values[1:]

    def _check_possible_values_code(self, argument: CommandArgument, **kw: Unpack[FormatterArgs]) -> list[str]:
        arg_name = self.arg.to_arg(argument)
        level = kw.get("level", 1)
        first_line, possible_values = self._get_check_value_code_line(argument, level=level)
        lines = [first_line]
        if len(possible_values) > 0:
            search = "(list"
            prefix = first_line.rfind(search) + len(search)
            for pos_value in possible_values:
                lines.append(utils.as_string(self.formatter.column_prefix(prefix), pos_value, separator=" ").rstrip())
            lines[-1] = lines[-1].rstrip() + "))"
        message = f"(error \"Invalid value for '{arg_name}' %S\" {arg_name}))"
        lines.append(self.formatter.indent(message, level=level + 1))
        return lines

    def _function_body_check_possible_values(self, **kw: Unpack[FormatterArgs]) -> list[str]:
        lines = []
        for argument in self.command.arguments:
            if not argument.has_possible_values():
                continue
            lines.extend(self._check_possible_values_code(argument, **kw))
        return lines

    def _get_option_plist(self, command: ApiCommand) -> str:
        values = []
        for option in command.options:
            arg_name = self.opt.to_arg(option)
            values.append(f":{arg_name} {arg_name}")
        return f"'({utils.lines_as_str(*values)})"

    def _expression(self, expression: str, **kw: Unpack[FormatterArgs]) -> str:
        return self.formatter.indent(f"({expression}", level=kw.get("level", 1))

    def _setq_line(self, arg_name: str, value: str, increase_level: bool = False, **kw: Unpack[FormatterArgs]) -> str:
        level = kw.get("level", 1) + 1
        if increase_level:
            level += 1
        return self.formatter.indent(f"(setq {arg_name} {value})", level=level)

    def _format_string(self, real_name: str, value: str) -> str:
        return f"(format \"{real_name} %s\" {value})"

    def _real_option_name(self, option: CommandOption) -> str:
        name = option.name if option.name is not None else option.short
        if name is None:
            raise ValueError(f"Option {option} has no name or short")
        return self.manager.option_name(name)

    def _get_option_value(self, option: CommandOption) -> str:
        real_name = self._real_option_name(option)
        if option.has_value():
            arg_name = self.opt.to_arg(option)
            return self._format_string(real_name, arg_name)
        return f"\"{real_name}\""

    def _set_option_line(self, option: CommandOption, **kw: Unpack[FormatterArgs]) -> list[str]:
        arg_name = self.opt.to_arg(option)
        lines = [self._expression(f"when {arg_name}", **kw)]
        value = self._get_option_value(option)
        lines.append(self._setq_line(arg_name, value, **kw))
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _set_argument_value(self, argument: CommandArgument, **kw: Unpack[FormatterArgs]) -> list[str]:
        if not argument.has_default():
            return []
        arg_name = self.arg.to_arg(argument)
        lines = [self._expression(f"(unless {arg_name}", **kw)]
        lines.append(self._setq_line(arg_name, f"\"{argument.default}\"", **kw))
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _function_body_convert_args(self, **kw: Unpack[FormatterArgs]) -> list[str]:
        lines = []
        for argument in self.arg.optional_args():
            lines.extend(self._set_argument_value(argument, **kw))
        for option in self.opt.option_args():
            lines.extend(self._set_option_line(option, **kw))
        return lines

    def _function_body_call_komorebi(self, cmd_name: str, args: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        args_str = f"{self.formatter.concat_args(*args)}" if len(args) > 0 else ""
        cmd = f"({pkg.execute_func_name(self.formatter)} \"{cmd_name}\" {args_str}"
        return [self.formatter.indent(cmd, kw.get("level", 1)).rstrip() + "))"]
