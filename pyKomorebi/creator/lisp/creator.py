import re
from pathlib import Path
from typing import Iterable

from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator.code import ACodeCreator
from pyKomorebi.creator.lisp import package as pkg
from pyKomorebi.creator.lisp.code import LispCodeFormatter, LispCommandCreator
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
            name="komorebi",
            version="0.0.2",
            repository="https://github.com/eraschle/pyKomorebi",
            user_name="Erich Raschle",
            user_email="erichraschle@gmail.com",
            emacs_version="28.1",
            formatter=self.formatter,
        )
        lines = pkg.pre_generator(package_info)
        for command in commands:
            lines.extend(self.formatter.empty_line(count=2))
            lines.extend(self.command(command=command))
        lines.extend(self.formatter.empty_line(count=2))
        lines.extend(pkg.post_generator(package_info))
        return lines
