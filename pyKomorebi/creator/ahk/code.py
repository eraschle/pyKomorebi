import re
from abc import ABC, abstractmethod
from typing import TypeGuard, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator.code import (
    ACodeFormatter,
    ArgDoc,
    FormatterArgs,
    IArgCreator,
    ICommandCreator,
    TArg,
)
from pyKomorebi.creator.docs import ADocCreator
from pyKomorebi.model import ApiCommand, CommandArgument, CommandOption


class AHKCodeFormatter(ACodeFormatter):
    pattern = re.compile(r"[^a-zA-Z0-9]+")
    separator = "-"

    def __init__(self, module_name: str, max_length: int) -> None:
        super().__init__(indent="  ", max_length=max_length, module_name=module_name)

    def _new_line_indent(self, indent: str) -> str:
        return indent

    def _clean_name(self, name: str) -> list[str]:
        name = self.pattern.sub(self.separator, name)
        names = [name.capitalize() for name in name.split(self.separator)]
        return utils.clean_blank(*names)

    def _concat_names(self, *names: str) -> str:
        return utils.as_string(*names, separator="")

    def name_to_code(self, name: str) -> str:
        names = self._clean_name(name)
        names[0] = names[0].lower()
        return self._concat_names(*names)

    def name_to_doc(self, name: str, suffix: str | None = None) -> str:
        name = utils.as_string(*self._clean_name(name), separator="")
        return utils.ensure_ends_with(name, end_str=suffix)

    def concat_args(self, *args: str, quote: bool = False) -> str:
        arg_names = utils.clean_blank(*args)
        if quote:
            arg_names = [f"\"{arg}\"" for arg in args]
        return ", ".join(arg_names)

    def concat_cli_args(self, *args: str) -> str:
        arg_names = utils.clean_blank(*args)
        return " \" \" ".join(arg_names)

    def function_name(self, *name: str, private: bool = False) -> str:
        names = [self.module_name.capitalize()]
        for func_name in name:
            names += self._clean_name(func_name)
        if private:
            names[0] = f"_{names[0]}"
        return self._concat_names(*names)

    def cli_name(self, name: str) -> str:
        names = [name.lower() for name in self._clean_name(name)]
        return utils.as_string(*names, separator="-")

    def find_prefix_in_code(self, line: str, **kw: Unpack[FormatterArgs]) -> int:
        if " " not in line:
            return -1
        return kw.get("prefix", 0)


def valid_values_of(values: list[str] | None) -> TypeGuard[list[str]]:
    if values is None:
        return False
    return len(values) > 0


class AAutohotKeyCreator(ABC, IArgCreator[TArg]):
    def __init__(self, elements: list[TArg], formatter: AHKCodeFormatter) -> None:
        self.elements = elements
        self.formatter = formatter

    def to_arg(self, arg: TArg) -> str:
        return self.formatter.name_to_code(arg.name)

    def to_doc_name(self, arg: TArg, suffix: str | None) -> str:
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

    def default_value(self, arg: TArg, format_str: str | None = None) -> str:
        return self.formatter.default_value(arg.default, format_str=format_str)

    def docstring(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]:
        return [self.arg_docstring(arg, **kw) for arg in self.elements]

    def valid_description(self, arg: TArg) -> list[str]:
        return utils.clean_blank(*arg.description)

    @abstractmethod
    def to_arg_with_default(self, elem: TArg) -> str:
        pass

    def to_args_with_default(self) -> list[str]:
        return [self.to_arg_with_default(elem) for elem in self.elements]

    @abstractmethod
    def if_has_value(self, elem: TArg, manager: TranslationManager, level: int) -> list[str]:
        pass

    def check_if_has_value(self, manager: TranslationManager, level: int) -> list[str]:
        lines = []
        for elem in self.elements:
            lines.extend(self.if_has_value(elem, manager, level=level))
        return lines


class AHKOptionCreator(AAutohotKeyCreator[CommandOption]):
    def to_args(self) -> list[str]:
        return [self.to_arg(arg) for arg in self.elements]

    def to_arg_with_default(self, elem: CommandOption) -> str:
        name = self.to_arg(elem)
        if elem.has_value() or elem.has_default():
            return f"{name} := \"\""
        # if elem.has_default():
        #     return f"{name} := \"{elem.default}\""
        return f"{name} := false"

    def arg_docstring(self, arg: CommandOption, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=arg.name,
            default=self.default_value(arg, format_str=kw.get("default_format", None)),
            description=self.valid_description(arg),
            possible_values=arg.possible_values,
        )

    def _if_expression(self, opt: CommandOption, level: int) -> str:
        arg_name = self.to_arg(opt)
        if opt.has_value():
            value = f'{arg_name} == ""'
        elif opt.has_default():
            value = f'{arg_name} == "{opt.default}"'
        else:
            value = f'{arg_name}'
        line = f"if (not {value})" + " {"
        return self.formatter.indent(line, level=level)

    def _else_code_line(self, opt: CommandOption, level: int) -> list[str]:
        arg_name = self.to_arg(opt)
        return [
            self.formatter.indent(f'{arg_name} := ""', level=level),
        ]

    def _if_code_line(self, opt: CommandOption, manager: TranslationManager, level: int) -> list[str]:
        opt_name = opt.long if opt.long is not None else opt.short
        if opt_name is None:
            raise ValueError("Option must have a name or a short name")
        real_name = manager.option_name(opt_name)
        arg_name = self.to_arg(opt)
        if opt.has_value() or opt.has_default():
            value = self.to_arg(opt)
            assign = f'{arg_name} := "{real_name} " {value}'
        else:
            assign = f'{arg_name} := "{real_name}"'
        return [
            self.formatter.indent(assign, level=level),
        ]

    def if_has_value(self, elem: CommandOption, manager: TranslationManager, level: int) -> list[str]:
        lines = []
        lines.append(self._if_expression(elem, level=level))
        lines.extend(self._if_code_line(elem, manager, level=level + 1))
        # lines.append(self.formatter.indent("} else {", level=level))
        # lines.extend(self._else_code_line(elem, level=level + 1))
        lines.append(self.formatter.indent("}", level=level))
        return lines


class AHKArgumentCreator(AAutohotKeyCreator[CommandArgument]):
    def to_args(self, with_optional: bool = True) -> list[str]:
        elements = self.elements
        if not with_optional:
            elements = [arg for arg in elements if arg.optional]
        return [self.to_arg(arg) for arg in elements]

    def to_arg_with_default(self, elem: CommandArgument) -> str:
        name = self.to_arg(elem)
        if not elem.has_default() and not elem.optional:
            return name
        return f"{name} := \"\""
        # return f"{name} := \"{elem.default}\""

    def arg_docstring(self, arg: CommandArgument, **kw: Unpack[FormatterArgs]) -> ArgDoc:
        return ArgDoc(
            name=arg.name,
            default=self.default_value(arg, format_str=kw.get("default_format", None)),
            description=self.valid_description(arg),
            possible_values=arg.possible_values,
        )

    def _if_expression(self, arg: CommandArgument, level: int) -> str:
        arg_name = self.to_arg(arg)
        if arg.has_default():
            # value = f'{arg_name} == "{arg.default}"'
            value = f'{arg_name} == ""'
        else:
            value = f'{arg_name}'
        line = f"if (not {value})" + " {"
        return self.formatter.indent(line, level=level)

    def _else_code_line(self, arg: CommandArgument, level: int) -> list[str]:
        arg_name = self.to_arg(arg)
        return [
            self.formatter.indent(f'{arg_name} := ""', level=level),
        ]

    def _if_code_line(self, arg: CommandArgument, manager: TranslationManager, level: int) -> list[str]:
        opt_name = arg.argument if arg.argument is not None else arg.short
        if opt_name is None:
            raise ValueError("Option must have a name or a short name")
        real_name = manager.option_name(opt_name)
        arg_name = self.to_arg(arg)
        if arg.has_default():
            value = self.to_arg(arg)
            assign = f'{arg_name} := "{real_name} " {value}'
        else:
            assign = f'{arg_name} := {real_name}'
        return [
            self.formatter.indent(assign, level=level),
        ]

    def if_has_value(self, elem: CommandArgument, manager: TranslationManager, level: int) -> list[str]:
        lines = []
        lines.append(self._if_expression(elem, level=level))
        lines.extend(self._if_code_line(elem, manager, level=level + 1))
        # lines.append(self.formatter.indent("} else {", level=level))
        # lines.extend(self._else_code_line(elem, level=level + 1))
        lines.append(self.formatter.indent("}", level=level))
        return lines

    def check_if_has_value(self, manager: TranslationManager, level: int) -> list[str]:
        lines = []
        # for elem in self.elements:
        # if not elem.optional:
        #     continue
        # lines.extend(self.if_has_value(elem, manager, level=level))
        return lines


class AHKCommandDocCreator(ADocCreator):
    def apply_comment_char(self, lines: list[str]) -> list[str]:
        return [f"; {line}" for line in lines]

    def function_doc(self, lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        first, other_sentences = self.get_first_sentence_and_rest(lines)
        if first is None:
            return lines
        doc_lines = []
        if self.formatter.is_valid_line(first, **kw):
            doc_lines.append(first)
        else:
            other_sentences.insert(0, first)
        other_sentences = self.ensure_sentences_has_valid_length(other_sentences, **kw)
        doc_lines.extend(self.formatter.concat_values(*other_sentences, **kw))
        return doc_lines

    def usage_doc(self, line: str | None, **kw: Unpack[FormatterArgs]) -> list[str]:
        if line is None or len(line) == 0:
            return []
        doc_lines = [self.formatter.indent("Usage:", level=kw.get("level", 0))]
        doc_lines.append(self.formatter.indent(line, level=kw.get("level", 0) + 1))
        return doc_lines

    def args_doc(self, docs: list[ArgDoc], **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["columns"] = self._get_max_length(docs, suffix=kw.get("suffix", ":"))
        doc_lines = []
        for arg in docs:
            doc_lines.extend(self._command_arg_doc(arg, **kw))
        return doc_lines


class AHKCommandCreator(ICommandCreator):
    def __init__(self, command: ApiCommand, formatter: AHKCodeFormatter, manager: TranslationManager) -> None:
        self.command = command
        self.formatter = formatter
        self.manager = manager
        self.opt = AHKOptionCreator(command.options, formatter)
        self.arg = AHKArgumentCreator(command.arguments, formatter)
        self.doc = AHKCommandDocCreator(formatter)

    def command_arg_names(self) -> list[str]:
        return self.arg.to_args() + self.opt.to_args()

    def _signature_arguments(self) -> list[str]:
        return self.arg.to_args_with_default() + self.opt.to_args_with_default()

    def function_args(self) -> str:
        return self.formatter.concat_args(*self._signature_arguments())

    def function_name(self) -> str:
        return self.formatter.function_name(self.command.name)

    def _get_signature(self, level: int) -> str:
        func_name = self.function_name()
        func_args = self.function_args()
        signature = f'{func_name}({func_args})' + " {"
        return self.formatter.indent(signature, level=level)

    def signature(self, level: int) -> str:
        return utils.lines_as_str(self._get_signature(level))

    def _apply_changes(self, line: str) -> str:
        line = self.arg.apply_doc_names_to(line)
        line = self.opt.apply_doc_names_to(line)
        return line

    def _function_docs(self) -> list[str]:
        return [self._apply_changes(line) for line in self.command.description]

    def _usage_docs(self) -> str | None:
        if self.command.usage is None:
            return None
        return self._apply_changes(self.command.usage)

    def _arg_docs(self, **kw: Unpack[FormatterArgs]) -> list[ArgDoc]:
        return self.arg.docstring(**kw) + self.opt.docstring(**kw)

    def docstring(self, level: int, separator: str = " ", columns: int = 0, suffix_args: str = ":") -> str:
        kw = {"separator": separator, "columns": columns, "level": level, "suffix": ""}
        doc_lines = self.doc.function_doc(lines=self._function_docs(), **kw)
        doc_lines.extend(self.doc.usage_doc(line=self._usage_docs(), **kw))
        kw.update({"default_format": "(default {0})", "suffix": suffix_args})
        doc_lines.extend(self.doc.args_doc(docs=self._arg_docs(**kw), **kw))
        doc_lines = self.doc.apply_comment_char(doc_lines)
        return utils.lines_as_str(*doc_lines)

    def _command_line(self, level: int) -> str:
        cmd_name = self.formatter.cli_name(self.command.name)
        cli_args = self.command_arg_names()
        if len(cli_args) == 0:
            command = f'RunWait("komorebic.exe {cmd_name}", , "Hide")'
        else:
            cli_names = self.formatter.concat_cli_args(*cli_args)
            command = f'RunWait("komorebic.exe {cmd_name} " {cli_names}, , "Hide")'
        return self.formatter.indent(command, level=level)

    def code(self, **kw: Unpack[FormatterArgs]) -> str:
        level = kw.get("level", 0)
        lines = []
        lines.extend(self.opt.check_if_has_value(self.manager, level=level + 1))
        lines.extend(self.arg.check_if_has_value(self.manager, level=level + 1))
        lines.append(self._command_line(level=level + 1))
        lines.append(self.formatter.indent("}", level))
        return utils.lines_as_str(*lines)
