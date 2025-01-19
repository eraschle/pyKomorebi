import re
from abc import abstractmethod
from typing import Callable, Iterable, TypeGuard, Unpack

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

    def comment(self, *comments: str, chars: str | None = None) -> list[str]:
        chars = chars or ";;"
        if len(comments) == 0:
            return [chars]
        lines = []
        for comment in comments:
            lines.append(f"{chars} {comment}".rstrip())
        return lines

    def region_comment(self, region: str) -> list[str]:
        return [";;", *self.comment(region, chars=";;;")]

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
        names = [self.name_to_code(n) for n in name]
        module_name = self.name_to_code(self.module_name)
        if private:
            module_name = f"{module_name}{self.separator}"
        return self.separator.join([module_name, *names])

    def _get_prefix(self, prefix: int, line: str) -> int:
        if prefix == self.prefix_of(line):
            return prefix + 1
        return prefix

    def find_prefix_in_code(self, line: str, **kw: Unpack[FormatterArgs]) -> int:
        if not kw.get("is_code", False) or len(line) == 0:
            return kw.get("prefix", 0)
        last_space = utils.last_space_index(line)
        if last_space > 0:
            return self._get_prefix(last_space, line)
        last_bracket = line.rfind("(")
        next_space = line.find(" ", last_bracket)
        if next_space > 0:
            return self._get_prefix(next_space, line)
        if last_bracket > 0:
            return self._get_prefix(last_space, line)
        raise ValueError(f"Could not find prefix in line: {line}")


def valid_values_of(values: list[str] | None) -> TypeGuard[list[str]]:
    if values is None:
        return False
    return len(values) > 0


class LispPackageHandler:
    def __init__(self, formatter: LispCodeFormatter, translation: TranslationManager) -> None:
        self.formatter = formatter
        self.translation = translation
        self._variables = {}

    def _get_names(self, arg: CommandArgs) -> tuple[str, ...]:
        return tuple([value.name for value in arg.constants])

    def add(self, arg: CommandArgs):
        if not arg.has_constants():
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
        if not arg.has_constants():
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


class CompletingHandler:
    read_number = [
        ("zero-indexed",),
        ("number",),
        ("border",),
        ("pixel", "integer"),
        ("size", "offset"),
        ("size", "monitor"),
        ("red",),
        ("green",),
        ("blue",),
        ("duration",),
        ("delta", "pixel", "resizing"),
        ("alpha",),
        (
            "tcp",
            "server",
            "start",
        ),
    ]
    read_name = [
        ("string",),
        (
            "workspace",
            "name",
        ),
        (
            "display",
            "name",
        ),
        (
            "socket",
            "name",
        ),
        (
            "pipe",
            "name",
        ),
        ("exe",),
    ]
    read_path = [
        (
            "configuration",
            "static",
        ),
        (
            "yaml",
            "file",
        ),
        (
            "file",
            "resize",
        ),
    ]
    read_boolean = [
        ("whkd",),
        ("ahk",),
        ("autohotkey",),
        ("komorebi-bar",),
        ("masir",),
        (
            "wait",
            "komorebic",
            "complete-configuration",
        ),
        (
            "auto-apply",
            "dumped",
            "temp",
            "file",
        ),
    ]

    def __init__(self, handler: LispPackageHandler, creator: "ALispArgCreator"):
        self.handler = handler
        self.creator = creator
        self._factory = self._create_factory()

    def _create_factory(
        self,
    ) -> list[tuple[Callable[[CommandArgs], bool], Callable[[CommandArgs], list[str]]]]:
        return [
            (self.is_read_variable, self.completing_variable),
            (self.is_read_number, self.completing_number),
            (self.is_read_string, self.completing_string),
            (self.is_read_path, self.completing_path),
            (self.is_read_boolean, self.completing_boolean),
        ]

    def is_read_variable(self, arg: CommandArgs) -> bool:
        return self.handler.exists(arg)

    def completing_variable(self, arg: CommandArgs) -> list[str]:
        name = self.creator.to_doc_name(arg, suffix=None)
        prompt = f'"Enter value for {name}: "'
        variable = self.handler.get(arg, as_symbol=False)
        if arg.has_default():
            variable = f'{variable} nil t "{arg.default}")'
        else:
            variable = f"{variable} nil t)"
        return [f"(completing-read {prompt}", variable]

    def replace_argument_name(self, arg_name: str, description) -> str:
        # # Construct a regex pattern to match the argument name in any case
        # pattern = re.compile(re.escape(arg_name), re.IGNORECASE)
        # matched_text = match.group(0)

        # result = pattern.sub(arg_name, description)
        # return result
        return ""

    def _get_description(self, arg: CommandArgs, suffix: str) -> str:
        if utils.has_sentence(*arg.description):
            description = utils.get_sentences(*arg.description)[0]
        else:
            description = utils.as_string(*arg.description, separator=" ")
        description = description.rstrip().removesuffix(".")
        doc_name = self.creator.to_doc_name(arg, suffix=None)
        description = f"{doc_name}: {description}"
        return f"\"{description}{suffix}\""

    def _create_read(self, arg: CommandArgs, suffix: str) -> list[str]:
        if not arg.has_description():
            return []
        description = self._get_description(arg, suffix=":")
        return [f"(read-{suffix} {description})"]

    def _is_read(self, line: str, values: tuple[str, ...]) -> bool:
        line = line.lower()
        for value in values:
            if value in line:
                continue
            return False
        return True

    def _is_read_boolean(self, line: str) -> bool:
        return any(self._is_read(line, values) for values in self.read_boolean)

    def is_read_boolean(self, arg: CommandArgs) -> bool:
        if self.is_read_variable(arg):
            return False
        if not arg.has_description():
            return False
        return any(self._is_read_boolean(line) for line in arg.description)

    def completing_boolean(self, arg: CommandArgs) -> list[str]:
        description = self._get_description(arg, suffix="?")
        return [f"(y-or-n-p {description})"]

    def _is_read_number(self, line: str) -> bool:
        return any(self._is_read(line, values) for values in self.read_number)

    def is_read_number(self, arg: CommandArgs) -> bool:
        if self.is_read_variable(arg):
            return False
        if not arg.has_description():
            return False
        return any(self._is_read_number(line) for line in arg.description)

    def default_number(self, arg: CommandArgs) -> int | None:
        return -1 if arg.is_optional else None

    def _default_number_str(self, arg: CommandArgs) -> str:
        default = self.default_number(arg)
        if default is None:
            return ""
        return f" {default}"

    def completing_number(self, arg: CommandArgs) -> list[str]:
        if not arg.has_description():
            return []
        description = self._get_description(arg, suffix=":")
        default = self._default_number_str(arg)
        return [f"(read-number {description}{default})"]

    def _is_read_string(self, line: str) -> bool:
        return any(self._is_read(line, values) for values in self.read_name)

    def is_read_string(self, arg: CommandArgs) -> bool:
        if self.is_read_variable(arg):
            return False
        if not arg.has_description():
            return False
        return any(self._is_read_string(line) for line in arg.description)

    def completing_string(self, arg: CommandArgs) -> list[str]:
        if not arg.has_description():
            return []
        description = self._get_description(arg, suffix=":")
        if arg.is_optional():
            return [f"(read-string {description} nil nil \"-\")"]
        return [f"(read-string {description})"]

    def is_read_path(self, arg: CommandArgs) -> bool:
        for line in arg.description:
            if not any(self._is_read(line, values) for values in self.read_path):
                continue
            return True
        return False

    def completing_path(self, arg: CommandArgs) -> list[str]:
        if not self.is_read_path(arg):
            return []
        description = self._get_description(arg, suffix=":")
        last_line = f"({pkg.config_home_func(self.creator.formatter)})"
        if arg.is_optional():
            last_line += ")"
        else:
            last_line += " nil t)"
        return [f"(read-file-name {description}", last_line]

    def is_completing(self, arg: CommandArgs) -> bool:
        for is_read, _ in self._factory:
            if not is_read(arg):
                continue
            return True
        return False

    def completing(self, arg: CommandArgs, **kwargs) -> list[str]:
        for is_read, completing in self._factory:
            if not is_read(arg):
                continue
            return completing(arg, **kwargs)
        return []


class ALispArgCreator(IArgCreator[TArg]):
    def __init__(self, elements: list[TArg], handler: LispPackageHandler) -> None:
        self.elements = elements
        self.handler = handler
        self.completing = CompletingHandler(handler, self)

    @property
    def formatter(self) -> LispCodeFormatter:
        return self.handler.formatter

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

    def is_option_number(self, arg: TArg) -> bool:
        return self.completing.is_read_number(arg)

    def default_read_number(self, arg: TArg) -> int | None:
        return self.completing.default_number(arg)

    def interactive_value_of(self, arg: TArg) -> list[str]:
        return self.completing.completing(arg)

    def interactive_values(self) -> list[list[str]]:
        args = [arg for arg in self.elements if self.can_arg_be_interactive(arg)]
        return [self.interactive_value_of(arg) for arg in args]


class OptionCreator(ALispArgCreator[CommandOption]):
    def to_args(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.elements]

    def option_args(self) -> list[CommandOption]:
        return self.elements

    def arg_docstring(self, arg: CommandOption, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, kw.get("suffix", None)),
            default=self.default_value(arg, kw.get("default_format", None)),
            constants=arg.constants,
            description=self.valid_description(arg, strip_char=None),
        )

    def can_arg_be_interactive(self, arg: CommandOption) -> bool:
        if arg.has_constants() or arg.has_default():
            return True
        return self.completing.is_completing(arg)


class ArgumentCreator(ALispArgCreator[CommandArgument]):
    def to_args(self, with_optional: bool = True) -> list[str]:
        elements = self.elements
        if not with_optional:
            elements = [arg for arg in elements if arg.is_optional()]
        return [self.to_arg(arg) for arg in elements]

    def required_args(self) -> list[CommandArgument]:
        return [arg for arg in self.elements if not arg.is_optional()]

    def required_arg_names(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.required_args()]

    def optional_args(self) -> list[CommandArgument]:
        return [arg for arg in self.elements if arg.is_optional()]

    def optional_arg_names(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.optional_args()]

    def arg_docstring(self, arg: CommandArgument, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, kw.get("suffix", None)),
            default=self.default_value(arg, kw.get("default_format", None)),
            constants=arg.constants,
            description=self.valid_description(arg, strip_char=None),
        )

    def can_arg_be_interactive(self, arg: CommandArgument) -> bool:
        return arg.has_default() or arg.has_constants() or self.completing.is_completing(arg)


SINGLE_QUOTE = re.compile(r"\s+'([^']*)'")


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

    def _replace_single_quotes(self, lines: list[str]) -> list[str]:
        for idx, line in enumerate(lines):
            lines[idx] = SINGLE_QUOTE.sub(r" `\1'", line)
        return lines

    def args_doc(self, docs: list[ArgDoc], **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["columns"] = self._get_max_length(docs, suffix=kw.get("suffix", ":"))
        doc_lines = []
        for arg in docs:
            lines = self._command_arg_doc(arg, **kw)
            lines = self._replace_single_quotes(lines)
            doc_lines.extend(lines)
        return doc_lines


class LispCommandCreator(ICommandCreator):
    def __init__(self, command: ApiCommand, variables: LispPackageHandler) -> None:
        self.command = command
        self.handler = variables
        self.opt = OptionCreator(command.options, variables)
        self.arg = ArgumentCreator(command.arguments, variables)
        self.doc = LispCommandDocCreator(formatter=variables.formatter)

    @property
    def formatter(self) -> LispCodeFormatter:
        return self.handler.formatter

    @property
    def manager(self) -> TranslationManager:
        return self.handler.translation

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

    def docstring(
        self, level: int, separator: str = " ", columns: int = 0, suffix_args: str = ":"
    ) -> str:
        kw = {
            "separator": separator,
            "columns": columns,
            "level": level,
            "suffix": "",
            "is_code": False,
        }
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
        lines.extend(self._function_body_check_constants(**kw))
        lines.extend(self._function_body_convert_args(kw.get("level", 1)))
        args = self.command_args()
        lines.extend(self._function_body_call_komorebi(self.command.name, args, **kw))
        return utils.lines_as_str(*lines)

    def _function_body_interactive(self, **kw: Unpack[FormatterArgs]) -> list[str]:
        if not self.is_interactive():
            return []
        kw = code_utils.copy_args(kw, level=1, separator=kw["separator"])
        values = self.arg.interactive_values() + self.opt.interactive_values()
        if len(values) == 0:
            return [self.formatter.indent("(interactive)", level=kw.get("level", 1))]
        helper = ListHelper[list[str]](self.formatter)
        with helper.with_context(previous_code="(interactive", items=values, **kw) as ctx:
            if ctx.can_create_all_on(second_line=False):
                ctx.create()
            elif ctx.can_create_with_first_on(second_line=False):
                ctx.create()
            else:
                ctx.create_with_list_on_second_line()
                ctx.create()
        lines = helper.as_list()
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _get_check_value_code_line(self, argument: CommandArgument, level: int) -> str:
        arg_name = self.arg.to_arg(argument)
        var_name = self.handler.get(argument, as_symbol=False)
        code_line = f"(unless (member {arg_name} {var_name})"
        return self.formatter.indent(code_line, level=level)

    def _check_constant_code(self, argument: CommandArgument, **kw: Unpack[FormatterArgs]) -> list[str]:
        arg_name = self.arg.to_arg(argument)
        level = kw.get("level", 1)
        code_line = self._get_check_value_code_line(argument, level=level)
        lines = [code_line]
        message = f"(error \"Invalid value for '{arg_name}' %S\" {arg_name}))"
        lines.append(self.formatter.indent(message, level=level + 1))
        return lines

    def _function_body_check_constants(self, **kw: Unpack[FormatterArgs]) -> list[str]:
        lines = []
        for argument in self.command.arguments:
            if not argument.has_constants():
                continue
            lines.extend(self._check_constant_code(argument, **kw))
        return lines

    def _expression(self, expression: str, level: int) -> str:
        return self.formatter.indent(f"({expression}", level=level)

    def _setq_line(self, arg_name: str, value: str, level: int) -> str:
        return self.formatter.indent(f"(setq {arg_name} {value})", level=level)

    def _format_string(self, real_name: str, value: str) -> str:
        return f"(format \"{real_name} %s\" {value})"

    def _real_option_name(self, option: CommandOption) -> str:
        name = option.long if option.long is not None else option.short
        if name is None:
            raise ValueError(f"Option {option} has no name or short")
        return self.manager.option_name(name)

    def _get_option_value(self, option: CommandOption, level: int) -> str:
        real_name = self._real_option_name(option)
        arg_name = self.opt.to_arg(option)
        if option.has_value():
            value = self._format_string(real_name, arg_name)
        else:
            value = f"\"{real_name}\""
        return self._setq_line(arg_name, value, level=level)

    def _get_option_numebr_value(self, option: CommandOption, level: int) -> list[str]:
        arg_name = self.opt.to_arg(option)
        default = self.opt.default_read_number(option)
        lines = [self._expression(f"if (= {arg_name} {default})", level=level)]
        lines.append(self._setq_line(arg_name, "nil", level=level + 2))
        lines.append(self._get_option_value(option, level=level + 1))
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _set_option_line(self, option: CommandOption, level: int) -> list[str]:
        arg_name = self.opt.to_arg(option)
        if self.handler.exists(option):
            var_name = self.handler.get(option, as_symbol=False)
            lines = [self._expression(f"when (member {arg_name} {var_name})", level=level)]
        else:
            lines = [self._expression(f"when {arg_name}", level=level)]
        if self.opt.is_option_number(option):
            lines.extend(self._get_option_numebr_value(option, level=level + 1))
        else:
            lines.append(self._get_option_value(option, level=level + 1))
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _set_argument_value(self, argument: CommandArgument, level: int) -> list[str]:
        if not argument.has_default():
            return []
        arg_name = self.arg.to_arg(argument)
        lines = [self._expression(f"unless {arg_name}", level=level)]
        lines.append(self._setq_line(arg_name, f"\"{argument.default}\"", level=level + 1))
        lines[-1] = lines[-1].rstrip() + ")"
        return lines

    def _function_body_convert_args(self, level: int) -> list[str]:
        lines = []
        for argument in self.arg.optional_args():
            lines.extend(self._set_argument_value(argument, level=level))
        for option in self.opt.option_args():
            lines.extend(self._set_option_line(option, level=level))
        return lines

    def _function_call_final_try(self, command: str, **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["prefix"] = len(self.formatter.indent_for(level=kw.get("level", 1)))
        cmd_values = utils.strip_and_clean_blank(*command.split(" "), strip_chars=" ")
        cmd_lines = self.formatter.concat_values(*cmd_values, **kw)
        kw["prefix"] = cmd_lines[0].find(cmd_values[1]) - 1
        cmd_lines.extend(self.formatter.concat_values(*cmd_lines.pop(-1).split(" "), **kw))
        return cmd_lines

    def _function_call_many_lines(self, command: str, **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["prefix"] = len(self.formatter.indent_for(level=kw.get("level", 1)))
        function, *args = utils.strip_and_clean_blank(*command.split(" "), strip_chars=" ")
        cmd_lines = self.formatter.concat_values(function, **kw)
        kw["prefix"] += 1
        cmd_lines.extend(self.formatter.concat_values(*args, **kw))
        return cmd_lines

    def _function_body_call_komorebi(self, cmd_name: str, args: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        args_str = f"{self.formatter.concat_args(*args)}" if len(args) > 0 else ""
        command_str = f"({pkg.execute_func_name(self.formatter)} \"{cmd_name}\" {args_str}"
        command_str = self.formatter.indent(command_str, kw.get("level", 1)).rstrip() + "))"
        if self.formatter.is_valid_line(command_str, **kw):
            return [command_str]
        cmd_lines = self._function_call_many_lines(command_str, **kw)
        if len(cmd_lines) == 2:
            return cmd_lines
        print(f"command {cmd_name} with {args} needs final try!!!!")
        return self._function_call_final_try(command_str, **kw)
