from typing import Iterable, Unpack

from pyKomorebi.creator.code import ACodeCreator, ACodeFormatter
from pyKomorebi.generate import GeneratorArgs
from pyKomorebi.model import ApiCommand, CommandArgument, CommandOption


class AHKCodeFormatter(ACodeFormatter):
    def __init__(self):
        super().__init__(indent="  ", max_length=80)

    def function_name(self, name: str, private: bool = False) -> str:
        raise NotImplementedError

    def concat_args(self, args: list[str]) -> str:
        raise NotImplementedError

    def name_to_doc(self, name: str, **kw) -> str:
        raise NotImplementedError

    def name_to_code(self, name: str) -> str:
        raise NotImplementedError


class AutoHotKeyCreator(ACodeCreator):
    name_replacement = [" ", "-"]

    def __init__(self):
        super().__init__(extension="ahk")
        self.formatter = AHKCodeFormatter()

    def _ahk_name(self, name: str, separator: str, capitalize: bool) -> str:
        names = name.split("-")
        if capitalize:
            names = [name.capitalize() for name in names]
        else:
            names = [name.lower() for name in names]
        return separator.join(names)

    def _function_name(self, command: ApiCommand) -> str:
        names = ["Komorebi", self._ahk_name(command.name, separator="", capitalize=True)]
        return "".join(names)

    def _opt_name(self, arg: CommandOption, with_dash: bool, **kwargs: Unpack[GeneratorArgs]) -> str:
        name = arg.get_name(kwargs["with_default"])
        if arg.name is not None:
            name = arg.name
        name = self._ahk_name(name.removeprefix("--"), separator="_", capitalize=False)
        if with_dash:
            return f"--{name}"
        return name

    def _option_names(self, command: ApiCommand, with_dash: bool) -> list[str]:
        if len(command.options) == 0:
            return []
        options = [self._opt_name(opt, with_dash) for opt in command.options]
        help_name = "--help" if with_dash else "help"
        options = [opt for opt in options if opt != help_name]
        return options

    def _arg_name(self, arg: CommandArgument) -> str:
        name = arg.get_name(with_default=False)
        return self._ahk_name(name, separator="_", capitalize=False)

    def _arguments_names(self, command: ApiCommand) -> list[str]:
        if len(command.arguments) == 0:
            return []
        return [self._arg_name(arg) for arg in command.arguments]

    def _arguments(self, command: ApiCommand) -> str:
        values = self._arguments_names(command)
        values.extend(self._option_names(command, with_dash=False))
        return ", ".join(values)

    def _command_call(self, command: ApiCommand) -> str:
        args = ' " " '.join(self._arguments_names(command))
        args = f" {args}" if len(args) > 0 else ""
        options = ' " " '.join(self._option_names(command, with_dash=True))
        options = f" {options}" if len(options) > 0 else ""
        cmd = command.name if len(command.arguments) == 0 else f"{command.name} "
        return f'RunWait("komorebic.exe {cmd}"{args}{options}, , "Hide")'

    def pre_generator(self) -> list[str]:
        lines = ["#Requires AutoHotkey v2.0.2", ""]
        lines.extend(self.formatter.empty_line())
        return lines

    def _generate_command(self, command: ApiCommand) -> list[str]:
        lines = []
        func_args = self._arguments(command)
        func_name = self._function_name(command)
        lines.append(self.formatter.indent(f'{func_name}({func_args})' + " {", level=0))
        lines.append(self.formatter.indent(self._command_call(command), level=1))
        lines.append(self.formatter.indent("}", level=0))
        lines.extend(self.formatter.empty_line())
        return lines

    def post_generator(self) -> list[str]:
        return []

    def generate(self, commands: Iterable[ApiCommand]) -> list[str]:
        lines = []
        for command in commands:
            lines.extend(self.pre_generator())
            lines.extend(self._generate_command(command))
            lines.extend(self.post_generator())
        return lines
