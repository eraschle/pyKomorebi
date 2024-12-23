from typing import Iterable

from pyKomorebi.creator import TranslationManager
from pyKomorebi.creator.code import ACodeCreator
from pyKomorebi.creator.ahk.code import AHKCodeFormatter, AHKCommandCreator
from pyKomorebi.creator.ahk import package as pkg
from pyKomorebi.model import ApiCommand


class AutoHotKeyCreator(ACodeCreator):
    name_replacement = [" ", "-"]

    def __init__(self, manager: TranslationManager, max_length: int = 80):
        super().__init__(extension="ahk")
        self.manager = manager
        self.formatter = AHKCodeFormatter(max_length=max_length, module_name="Komorebi")

    def command(self, command: ApiCommand) -> list[str]:
        command.remove_help_option()
        creator = AHKCommandCreator(
            command=command,
            formatter=self.formatter,
            manager=self.manager,
        )
        lines = []
        lines.append(creator.signature(level=0))
        lines.append(creator.docstring(level=0))
        lines.append(creator.code(level=0, separator=" "))
        return lines

    def generate(self, commands: Iterable[ApiCommand]) -> list[str]:
        package_info = pkg.PackageInfo(
            name="komorebi",
            version="0.0.2",
            repository="https://github.com/eraschle/pyKomorebi",
            user_name="Erich Raschle",
            user_email="erichraschle@gmail.com",
            formatter=self.formatter,
        )
        lines = pkg.pre_generator(package_info)
        for command in commands:
            lines.extend(self.formatter.empty_line(count=1))
            lines.extend(self.command(command=command))
        # lines.extend(self.formatter.empty_line(count=2))
        # lines.extend(pkg.post_generator(package_info))
        return lines
