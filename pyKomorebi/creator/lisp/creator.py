import re
from pathlib import Path
from typing import Iterable, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator import code as code_utils
from pyKomorebi.creator.code import ACodeCreator, FormatterArgs
from pyKomorebi.creator.lisp import package as pkg
from pyKomorebi.creator.lisp.code import LispCodeFormatter, LispCommandCreator
from pyKomorebi.creator.lisp.helper.list import ListHelper
from pyKomorebi.model import ApiCommand

CLEANUP_PATTERN = [
    re.compile(r"(\(without.*?\))"),
]

SINGLE_QUOTE = re.compile(r"'([^']*)'")


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

    def _replace_single_quotes(self, lines: list[str]) -> list[str]:
        changed = []
        for line in lines:
            line = SINGLE_QUOTE.sub(r"/='\1/='", line)
            changed.append(line)
        return changed

    def _ensure_autoload_line_indent(self, lines: list[str]) -> list[str]:
        for idx, line in enumerate(lines):
            if self.autoload_line in line:
                lines[idx] = line.lstrip()
        return lines

    def _add_variable(self, command: ApiCommand):
        for arg in command.arguments:
            LispCommandCreator.add(arg)
        for opt in command.options:
            LispCommandCreator.add(opt)

    def setup_variable_handler(self, commands: Iterable[ApiCommand]) -> None:
        LispCommandCreator.set_formatter(self.formatter)
        LispCommandCreator.set_translation(self.manager)
        for command in commands:
            self._add_variable(command)

    def variable_doc_string(self, arg_name: str, **kw: Unpack[FormatterArgs]) -> list[str]:
        kw["is_code"] = False
        arg_name = self.formatter.remove_module_prefix(arg_name)
        doc_str = f"\"List of possible values for \\\\='{arg_name}\\\\='.\""
        doc_str = utils.ensure_ends_with(doc_str, end_str=")")
        kw = code_utils.with_level(kw)
        return [self.formatter.indent(doc_str, level=kw.get("level", 1))]

    def variables(self) -> list[str]:
        lines = []
        variables = sorted(LispCommandCreator.variables.items(), key=lambda x: x[0])
        helper = ListHelper[str](formatter=self.formatter)
        kwargs = {"level": 0, "separator": " ", "is_code": True}
        for name, values in variables:
            var_name = f"(defvar {name}"
            values = [f'"{value}"' for value in values]
            with helper.with_context(previous_code=var_name, items=values, **kwargs) as ctx:
                if not ctx.found_solution():
                    continue
                ctx.create()
            lines.extend(helper.as_list())
            lines.extend(self.variable_doc_string(name, **kwargs))
            lines.extend(self.formatter.empty_line(count=1))
        return lines

    def command(self, command: ApiCommand) -> list[str]:
        command.remove_help_option()
        creator = LispCommandCreator(
            command=command,
            formatter=self.formatter,
            manager=self.manager,
        )
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
        self._ensure_autoload_line_indent(lines)
        return lines

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
        self.setup_variable_handler(commands)
        lines = pkg.pre_generator(package_info)
        lines.extend(self.variables())
        for command in commands:
            lines.extend(self.formatter.empty_line(count=2))
            lines.extend(self.command(command=command))
        lines.extend(self.formatter.empty_line(count=2))
        lines.extend(pkg.post_generator(package_info))
        return lines
