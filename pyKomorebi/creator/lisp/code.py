import re
from typing import Iterable, Optional, TypeGuard, Unpack

from pyKomorebi import utils
from pyKomorebi.creator.code import (
    ACodeFormatter,
    CreatorArgs,
    ArgDoc,
    FormatterArgs,
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

    def __init__(self, lisp_module: str) -> None:
        super().__init__(indent="  ", max_length=80)
        self.lisp_module = lisp_module

    def _clean_name(self, name: str) -> str:
        name = self.pattern.sub(self.separator, name)
        return name.removeprefix(self.separator).removesuffix(self.separator)

    def name_to_code(self, name: str) -> str:
        name = self._clean_name(name)
        return name.lower()

    def name_to_doc(self, name: str, **kw: Unpack[FormatterArgs]) -> str:
        name = self._clean_name(name)
        return self.apply_suffix(name, kw.get("suffix", None))

    def concat_args(self, args: Iterable[str]) -> str:
        args = [self.name_to_code(arg) for arg in args]
        return " ".join(args)

    def function_name(self, name: str, private: bool = False) -> str:
        name = self.name_to_code(name)
        name = f"-{name}" if private else name
        return "-".join([self.name_to_code(self.lisp_module), name])


def valid_values_of(values: Optional[list[str]]) -> TypeGuard[list[str]]:
    if values is None:
        return False
    return len(values) > 0


class ALispArgCreator(IArgCreator[TArg]):
    def __init__(self, elements: list[TArg], formatter: LispCodeFormatter) -> None:
        self.elements = elements
        self.formatter = formatter

    def valid_possible_values(self, arg: TArg, **kw: Unpack[CreatorArgs]) -> list[str]:
        if not valid_values_of(arg.possible_values):
            return []
        return arg.possible_values

    def default_value(self, arg: TArg, **kw: Unpack[CreatorArgs]) -> str:
        return self.formatter.default_value(arg.default, kw.get("default_format", ""))

    def to_doc_name(self, arg: TArg, **kw: Unpack[FormatterArgs]) -> str:
        return self.formatter.name_to_doc(arg.get_name(), **kw)

    def apply_doc_names_to(self, line: str) -> str:
        if len(self.elements) == 0:
            return line
        for elem in self.elements:
            search = elem.get_name()
            replace = self.to_doc_name(elem, suffix="")
            line = line.replace(search, replace)
        return line

    def to_arg(self, arg: TArg) -> str:
        return self.formatter.name_to_code(arg.get_name())

    def to_args(self) -> Iterable[str]:
        return [self.to_arg(arg) for arg in self.elements]

    def validate_values(self) -> list[str]:
        return [self.validate_code(arg) for arg in self.elements]

    def to_call_args(self) -> Iterable[str]:
        return [self.as_call_arg(arg) for arg in self.elements]

    def docstring(self, **kw: Unpack[CreatorArgs]) -> Iterable[ArgDoc]:
        for option in self.elements:
            yield self.arg_docstring(option, **kw)


class OptionCreator(ALispArgCreator[CommandOption]):
    def arg_docstring(self, arg: CommandOption, **kw: Unpack[CreatorArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, **kw),
            default=self.default_value(arg, **kw),
            possible_values=self.valid_possible_values(arg, **kw),
            description=[desc for desc in arg.description if len(desc) > 0],
        )

    def validate_code(self, arg: CommandOption) -> str:
        if not arg.has_value:
            return ""
        return ""

    def as_call_arg(self, arg: CommandOption) -> str:
        if arg.arg_value is None:
            return self.to_arg(arg)
        return self.to_arg(arg)


class ArgumentCreator(ALispArgCreator[CommandArgument]):
    def arg_docstring(self, arg: CommandArgument, **kw: Unpack[CreatorArgs]) -> ArgDoc:
        return ArgDoc(
            name=self.to_doc_name(arg, **kw),
            default=self.default_value(arg, **kw),
            possible_values=self.valid_possible_values(arg, **kw),
            description=[desc for desc in arg.description if len(desc) > 0],
        )

    def validate_code(self, arg: CommandArgument) -> str:
        return ""

    def as_call_arg(self, arg: CommandArgument) -> str:
        return self.to_arg(arg)


class LispCommandDocCreator(ADocCreator):
    def quote_doc_start(self, line: str) -> str:
        return self.formatter.indent(f"\"{line}", level=1)

    def quote_doc_end(self, line: str) -> str:
        if line.endswith("\""):
            return line
        return f"{line}\""

    def function_doc(self, lines: Iterable[str], **kw: Unpack[CreatorArgs]) -> str:
        doc_lines = []
        for _, line in enumerate(lines):
            if self.formatter.is_valid_length(line):
                if len(doc_lines) == 0:
                    line = self.quote_doc_start(line)
                else:
                    line.rstrip()
                doc_lines.append(line)
        utils.clean_none_or_empty(doc_lines, strip=False)
        return utils.lines_as_str(*doc_lines)

    def args_doc(self, docs: Iterable[ArgDoc], **kw: Unpack[CreatorArgs]) -> str:
        kw["columns"] = self._get_max_length(docs, kw.get("suffix", ":"))
        doc_lines = []
        for arg in docs:
            line = self._command_arg_doc(arg, **kw)
            doc_lines.append(line)
        return utils.lines_as_str(*doc_lines)


class LispCommandCreator(ICommandCreator):
    def __init__(self, command: ApiCommand, formatter: LispCodeFormatter, max_length: int = 80):
        self.command = command
        self.formatter = formatter
        self.opt = OptionCreator(command.options, formatter)
        self.arg = ArgumentCreator(command.arguments, formatter)
        self.doc = LispCommandDocCreator(max_length=max_length, formatter=formatter)

    def is_interactive(self) -> bool:
        return len(self.command) == 0

    def command_args(self) -> Iterable[str]:
        for arg in self.arg.to_args():
            yield arg
        for option in self.opt.to_args():
            yield option

    def function_args(self) -> str:
        if self.is_interactive():
            return ""
        args = self.command_args()
        args_str = self.formatter.concat_args(args)
        return f"&key {args_str}"

    def function_name(self) -> str:
        return self.formatter.function_name(self.command.name)

    def autoload_line(self) -> list[str]:
        if not self.is_interactive():
            return []
        return [self.formatter.indent(";;;###autoload", level=0)]

    def _get_signature(self, level: int) -> str:
        func_kind = "defun" if self.is_interactive() else "cl-defun"
        func_name = self.function_name()
        func_args = self.function_args()
        signature = f'({func_kind} {func_name} ({func_args})'
        return self.formatter.indent(signature, level=level)

    def signature(self, level: int) -> str:
        lines = []
        lines.extend(self.autoload_line())
        lines.append(self._get_signature(level))
        return utils.lines_as_str(*lines)

    def _apply_changes(self, line: str) -> str:
        line = self.arg.apply_doc_names_to(line)
        line = self.opt.apply_doc_names_to(line)
        return line

    def _function_docs(self) -> Iterable[str]:
        for line in self.command.description:
            line = self._apply_changes(line)
            yield line

    def _arg_docs(self, **kw: Unpack[CreatorArgs]) -> list[ArgDoc]:
        docs = []
        docs.extend(self.arg.docstring(**kw))
        docs.extend(self.opt.docstring(**kw))
        return docs

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
        func_doc = self.doc.function_doc(lines=self._function_docs(), **kw)
        kw.update({"default_format": "(default {0})", "suffix": suffix_args})
        arg_doc = self.doc.args_doc(
            docs=self._arg_docs(**kw),
            **kw,
        )
        if len(func_doc.strip()) == 0 and len(arg_doc.strip()) == 0:
            doc_string = ""
        elif len(func_doc.strip()) == 0:
            doc_string = arg_doc
        elif len(arg_doc.strip()) == 0:
            doc_string = func_doc
        else:
            doc_string = utils.lines_as_str(func_doc, arg_doc)
        doc_string = self.doc.quote_doc_end(doc_string)
        return self._ensure_indent(doc_string)

    def _command_call(self, command: ApiCommand) -> str:
        args = self.arg.to_args()
        func_name = pkg.execute_func_name(self.formatter)
        cmd_string = f"({func_name} \"{command.name}\")"
        if len(list(args)) > 0:
            args_str = self.formatter.concat_args(args)
            cmd_string = f"{cmd_string[:-1]} {args_str})"
        cmd_string += ")"
        return self.formatter.indent(cmd_string, level=1)

    def code(self, **kw: Unpack[CreatorArgs]) -> str:
        lines = []
        if self.is_interactive():
            lines.append(self.formatter.indent("(interactive)", level=kw.get("level", 1)))
        lines.append(self._command_call(self.command))
        return utils.lines_as_str(*lines)
