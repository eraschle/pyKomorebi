import re
from abc import abstractmethod
from typing import Iterable, TypeGuard, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator import code as code_utils
from pyKomorebi.creator.code import (
    ACodeFormatter,
    ArgDoc,
    FormatterArgs,
    IArgCreator,
    ICommandCreator,
    TArg,
)
from pyKomorebi.creator.docs import ADocCreator
from pyKomorebi.creator.lisp import package as pkg
from pyKomorebi.creator.lisp.helper.list import ListHelper
from pyKomorebi.model import (
    ApiCommand,
    CommandArgs,
    CommandArgument,
    CommandOption,
)


class LispCodeFormatter(ACodeFormatter):
    pattern = re.compile(r'[^a-zA-Z0-9"]+')
    separator = "-"

    def __init__(self, module_name: str, max_length: int) -> None:
        super().__init__(indent="  ", max_length=max_length, module_name=module_name)

    def _clean_name(self, name: str) -> str:
        name = self.pattern.sub(self.separator, name)
        return name.removeprefix(self.separator).removesuffix(self.separator)

    def _new_line_indent(self, indent: str) -> str:
        columns = len(indent) - (len(self.indent_str) // 2)
        if columns <= 0:
            return indent
        return self.column_prefix(columns)

    def name_to_code(self, name: str) -> str:
        if not (name.startswith("(") and name.endswith(")")):
            name = self._clean_name(name)
        return name.lower()

    def name_to_doc(self, name: str, suffix: str | None = None) -> str:
        name = self._clean_name(name)
        return utils.ensure_ends_with(name, suffix)

    def concat_args(self, *args: str) -> str:
        arg_names = [self.name_to_code(arg) for arg in args]
        return " ".join(arg_names)

    def function_name(self, *name: str, private: bool = False) -> str:
        names = [self.separator] if private else []
        names.extend([self.name_to_code(n) for n in name])
        module_name = self.name_to_code(self.module_name)
        return self.separator.join([module_name, *names])

    def find_prefix_in_code(self, line: str, **kw: Unpack[FormatterArgs]) -> int:
        if not kw.get("is_code", False):
            return kw.get("prefix", 0)
        last_space = utils.last_space_index(line)
        if last_space > 0:
            return last_space
        last_bracket = line.rfind("(")
        next_space = line.find(" ", last_bracket)
        if next_space > 0:
            return next_space
        if last_bracket > 0:
            return last_bracket
        raise ValueError(f"Could not find prefix in line: {line}")


def valid_values_of(values: list[str] | None) -> TypeGuard[list[str]]:
    if values is None:
        return False
    return len(values) > 0


class ALispArgCreator(IArgCreator[TArg]):
    def __init__(self, elements: list[TArg], formatter: LispCodeFormatter) -> None:
        self.elements = elements
        self.formatter = formatter

    def valid_description(self, arg: TArg, strip_char: str | None = None) -> list[str]:
        return utils.clean_blank(*arg.description, strip_chars=strip_char)

    def default_value(self, arg: CommandArgs, format_str: str | None = None) -> str:
        return self.formatter.default_value(arg.default, format_str=format_str)

    def to_doc_name(self, arg: CommandArgs, suffix: str | None) -> str:
        doc_name = self.formatter.name_to_doc(arg.name, suffix=suffix)
        if not doc_name.isupper():
            doc_name = doc_name.upper()
        return doc_name

    def apply_doc_names_to(self, line: str) -> str:
        if len(self.elements) == 0:
            return line
        for elem in self.elements:
            search = elem.name
            replace = self.to_doc_name(elem, suffix=None)
            line = line.replace(search, replace)
        return line

    def to_arg(self, arg: CommandArgs) -> str:
        arg_name = self.formatter.name_to_code(arg.name)
        return f"{arg_name}"

    def docstring(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]:
        return [self.arg_docstring(option, **kw) for option in self.elements]

    @abstractmethod
    def can_arg_be_interactive(self, arg: TArg) -> bool:
        pass

    def can_be_interactive(self) -> bool:
        if len(self.elements) == 0:
            return True
        return all([self.can_arg_be_interactive(arg) for arg in self.elements])

    def interactive_value_of(self, arg: TArg, handler: "LispVariableHandler") -> list[str]:
        default = arg.default if arg.has_default() else "nil"
        prompt = f"\"Enter value for {arg.name}: \""
        return [
            f"(completing-read {prompt}",
            handler.get(arg, as_symbol=False),
            f"nil t {default})",
        ]

    def interactive_values(self, handler: "LispVariableHandler") -> list[list[str]]:
        args = [arg for arg in self.elements if self.can_arg_be_interactive(arg)]
        return [self.interactive_value_of(arg, handler) for arg in args]


class OptionCreator(ALispArgCreator[CommandOption]):
    def __init__(
        self, elements: list[CommandOption], formatter: LispCodeFormatter, interactive_names: list[str]
    ) -> None:
        super().__init__(elements, formatter)
        self.interactive_names = interactive_names

    def to_args(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.elements]

    def option_args(self) -> list[CommandOption]:
        return self.elements

    def arg_docstring(self, arg: CommandOption, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, kw.get("suffix", None)),
            default=self.default_value(arg, kw.get("default_format", None)),
            possible_values=arg.possible_values,
            description=self.valid_description(arg, strip_char=None),
        )

    def can_arg_be_interactive(self, arg: CommandOption) -> bool:
        if arg.has_possible_values():
            return True
        if len(self.interactive_names) == 0:
            return False
        return arg.name in self.interactive_names


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
            possible_values=arg.possible_values,
            description=self.valid_description(arg, strip_char=None),
        )

    def can_arg_be_interactive(self, arg: CommandArgument) -> bool:
        return arg.has_default() or arg.has_possible_values()


class LispCommandDocCreator(ADocCreator):
    def quote_doc_start(self, lines: list[str], level: int) -> list[str]:
        if not lines[0].lstrip().startswith("\""):
            first_line = lines[0].lstrip()
            first_line = f"\"{first_line}"
            lines[0] = self.formatter.indent(first_line, level=level)
        return lines

    def quote_doc_end(self, lines: list[str]) -> list[str]:
        lines[-1] = utils.ensure_ends_with(lines[-1], end_str='"')
        return lines

    def function_doc(self, lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        first, other_sentences = self.get_first_sentence_and_rest(lines)
        if first is None:
            return lines
        doc_lines = []
        if self.formatter.is_valid_line(first, **kw):
            doc_lines.append(utils.ensure_ends_with(first, end_str="."))
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


class LispVariableHandler:
    def __init__(self) -> None:
        self._manager: TranslationManager | None = None
        self._formatter: LispCodeFormatter | None = None
        self._variables = {}

    @property
    def formatter(self) -> LispCodeFormatter:
        if self._formatter is None:
            raise ValueError("Formatter not set")
        return self._formatter

    @formatter.setter
    def formatter(self, formatter: LispCodeFormatter) -> None:
        self._formatter = formatter

    @property
    def translation(self) -> TranslationManager:
        if self._manager is None:
            raise ValueError("Translation not set")
        return self._manager

    @translation.setter
    def translation(self, manager: TranslationManager) -> None:
        self._manager = manager

    def _get_names(self, arg: CommandArgs) -> tuple[str, ...]:
        return tuple([value.name for value in arg.possible_values])

    def add(self, arg: CommandArgs):
        if not arg.has_possible_values():
            return
        value_tuple = self._get_names(arg)
        if value_tuple in self._variables:
            return
        name = self.formatter.function_name(arg.name)
        self._variables[value_tuple] = name

    def items(self) -> Iterable[tuple[str, tuple[str, ...]]]:
        for value in self._variables:
            name = self._variables[value]
            if self.translation.has_variable(value):
                name = self.translation.variable_name(value)
            yield name, value

    def exists(self, arg: CommandArgs) -> bool:
        if not arg.has_possible_values():
            return False
        return self._get_names(arg) in self._variables

    def get(self, arg: CommandArgs, as_symbol: bool) -> str:
        values = self._get_names(arg)
        if values not in self._variables:
            raise ValueError(f"No name found for values: {values}")
        var_name = self._variables[values]
        if self.translation.has_variable(values):
            var_name = self.translation.variable_name(values)
        if as_symbol:
            return f"'{var_name}"
        return var_name


class LispCommandCreator(ICommandCreator):
    variables = LispVariableHandler()

    @classmethod
    def add(cls, arg: CommandArgs):
        cls.variables.add(arg)

    @classmethod
    def has_variable_name(cls, arg: CommandArgs) -> bool:
        return cls.variables.exists(arg)

    @classmethod
    def variable_name(cls, arg: CommandArgs, as_symbol: bool = True) -> str:
        return cls.variables.get(arg, as_symbol=as_symbol)

    @classmethod
    def set_formatter(cls, formatter: LispCodeFormatter) -> None:
        cls.variables.formatter = formatter

    @classmethod
    def set_translation(cls, manager: TranslationManager) -> None:
        cls.variables.translation = manager

    def __init__(self, command: ApiCommand, formatter: LispCodeFormatter, manager: TranslationManager) -> None:
        self.command = command
        self.formatter = formatter
        self.manager = manager
        self.opt = OptionCreator(command.options, formatter, interactive_names=[])
        self.arg = ArgumentCreator(command.arguments, formatter)
        self.doc = LispCommandDocCreator(formatter=formatter)

    def is_interactive(self) -> bool:
        return self.arg.can_be_interactive() and self.opt.can_be_interactive()

    def command_args(self) -> list[str]:
        return self.arg.to_args() + self.opt.to_args()

    def function_args(self) -> str:
        arguments = self.arg.required_arg_names()
        args_str = self.formatter.concat_args(*arguments).strip()
        optional = self.arg.optional_arg_names() + self.opt.to_args()
        optional_str = self.formatter.concat_args(*optional).strip()
        if len(args_str) == 0 and len(optional_str) == 0:
            return ""
        if len(optional_str.strip()) == 0:
            return args_str.strip()
        return f"{args_str} &optional {optional_str}".strip()

    def function_name(self, *name: str) -> str:
        return self.formatter.function_name(self.command.name, *name)

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
        kw = {"separator": separator, "columns": columns, "level": level, "suffix": "", "is_code": False}
        doc_lines = self.doc.function_doc(lines=self._function_docs(), **kw)
        kw.update({"default_format": "(default {0})", "suffix": suffix_args})
        doc_lines.extend(self.doc.args_doc(docs=self._arg_docs(**kw), **kw))
        doc_lines = self.doc.quote_doc_end(doc_lines)
        doc_lines = self.doc.quote_doc_start(doc_lines, level=level)
        return utils.lines_as_str(*doc_lines)

    def code(self, **kw: Unpack[FormatterArgs]) -> str:
        kw["is_code"] = True
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
        kw = code_utils.copy_args(kw, level=1, separator=kw["separator"])
        values = self.arg.interactive_values(self.variables) + self.opt.interactive_values(self.variables)
        if len(values) == 0:
            return [self.formatter.indent("(interactive)", level=kw.get("level", 1))]
        helper = ListHelper[list[str]](self.formatter)
        with helper.with_context(
            previous_code="(interactive",
            items=values,
            **kw,
        ) as ctx:
            if not ctx.found_solution():
                print(f"Could not find solution for interactive in {self.command.name}")
            ctx.create()
        lines = helper.as_list()
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _get_check_value_code_line(self, argument: CommandArgument, level: int) -> str:
        arg_name = self.arg.to_arg(argument)
        var_name = self.variable_name(argument, as_symbol=False)
        code_line = f"(unless (member {arg_name} {var_name})"
        return self.formatter.indent(code_line, level=level)

    def _check_possible_values_code(self, argument: CommandArgument, **kw: Unpack[FormatterArgs]) -> list[str]:
        arg_name = self.arg.to_arg(argument)
        level = kw.get("level", 1)
        code_line = self._get_check_value_code_line(argument, level=level)
        lines = [code_line]
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

    def _expression(self, expression: str, **kw: Unpack[FormatterArgs]) -> str:
        return self.formatter.indent(f"({expression}", level=kw.get("level", 1))

    def _setq_line(self, arg_name: str, value: str, **kw: Unpack[FormatterArgs]) -> str:
        level = code_utils.with_level(kw).get("level", 0)
        return self.formatter.indent(f"(setq {arg_name} {value})", level=level)

    def _format_string(self, real_name: str, value: str) -> str:
        return f"(format \"{real_name} %s\" {value})"

    def _real_option_name(self, option: CommandOption) -> str:
        name = option.long if option.long is not None else option.short
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
        if self.has_variable_name(option):
            var_name = self.variable_name(option, as_symbol=False)
            lines = [self._expression(f"when (member {arg_name} {var_name})", **kw)]
        else:
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
