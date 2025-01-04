import re
from pathlib import Path
from typing import Iterable, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator import code as code_utils
from pyKomorebi.creator.code import ACodeCreator, FormatterArgs
from pyKomorebi.creator.lisp import package as pkg
from pyKomorebi.creator.lisp.code import LispCodeFormatter, LispCommandCreator, LispPackageHandler
from pyKomorebi.creator.lisp.helper.list import ListHelper
from pyKomorebi.model import ApiCommand

CLEANUP_PATTERN = [
    re.compile(r"(\(without.*?\))"),
]


class LispCreator(ACodeCreator):
    autoload_line = ";;;###autoload"

    def __init__(self, export_path: Path, manager: TranslationManager, max_length: int = 80):
        super().__init__(extension=export_path.suffix)
        self.max_length = max_length
        self.manager = manager
        self.formatter = LispCodeFormatter(
            module_name=export_path.with_suffix("").name,
            max_length=max_length,
        )
        self.var_hanlder = LispPackageHandler(self.formatter, manager)

    def _ensure_autoload_line_indent(self, lines: list[str]) -> list[str]:
        for idx, line in enumerate(lines):
            if self.autoload_line in line:
                lines[idx] = line.lstrip()
        return lines

    def setup_package_handler(self, commands: Iterable[ApiCommand]) -> None:
        self.var_hanlder = LispPackageHandler(self.formatter, self.manager)
        for command in commands:
            for arg in command.arguments:
                self.var_hanlder.add(arg)
            for opt in command.options:
                self.var_hanlder.add(opt)

    def variable_doc_string(self, arg_name: str, **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["is_code"] = False
        arg_name = self.formatter.remove_module(arg_name)
        doc_str = f"\"List of possible values for `{arg_name}'.\""
        doc_str = utils.ensure_ends_with(doc_str, end_str=")")
        kw = code_utils.with_level(kw)
        return [self.formatter.indent(doc_str, level=kw.get("level", 1))]

    def variables(self) -> list[str]:
        lines = []
        variables = sorted(self.var_hanlder.items(), key=lambda x: x[0])
        helper = ListHelper[str](formatter=self.formatter)
        kwargs = {"level": 0, "separator": " ", "is_code": True}
        for name, values in variables:
            var_name = f"(defvar {name}"
            values = [f'"{value}"' for value in values]
            with helper.with_context(previous_code=var_name, items=values, **kwargs) as ctx:
                if ctx.found_solution():
                    ctx.create()
            lines.extend(helper.as_list())
            lines.extend(self.variable_doc_string(name, **kwargs))
            lines.extend(self.formatter.empty_line(count=1))
        return lines

    def command(self, command: ApiCommand) -> list[str]:
        command.remove_help_option()
        creator = LispCommandCreator(command=command, variables=self.var_hanlder)
        lines = []
        lines.append(creator.signature(level=0))
        lines.append(
            creator.docstring(
                separator=" ",
                level=1,
                suffix_args=":",
            )
        )
        lines.append(creator.code(level=1, separator=" "))
        return self._ensure_autoload_line_indent(lines)

    def generate(self, commands: Iterable[ApiCommand]) -> list[str]:
        package_info = pkg.PackageInfo(
            name=self.formatter.module_name,
            version="0.0.2",
            repository="https://github.com/eraschle/pyKomorebi",
            user_name="Erich Raschle",
            user_email="erichraschle@gmail.com",
            emacs_version="28.1",
            formatter=self.formatter,
        )
        self.var_hanlder = LispPackageHandler(self.formatter, self.manager)
        self.setup_package_handler(commands)
        lines = pkg.pre_generator(package_info)
        lines.extend(self.variables())
        for command in commands:
            lines.extend(self.formatter.empty_line(count=2))
            lines.extend(self.command(command=command))
        lines.extend(self.formatter.empty_line(count=2))
        lines.extend(pkg.post_generator(package_info))
        return lines
