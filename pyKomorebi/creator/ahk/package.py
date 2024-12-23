from dataclasses import dataclass
from datetime import datetime

from pyKomorebi.creator.ahk.code import AHKCodeFormatter


@dataclass
class PackageInfo:
    name: str
    version: str
    repository: str
    user_name: str
    user_email: str
    formatter: AHKCodeFormatter

    @property
    def user_and_email(self) -> str:
        return f"{self.user_name} <{self.user_email}>"

    @property
    def modified(self) -> str:
        return datetime.now().strftime("%B %d, %Y")

    @property
    def year(self) -> str:
        return datetime.now().strftime("%Y")

    def indent(self, line: str, level: int = 0) -> str:
        return self.formatter.indent(line, level)


def pre_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.extend([f"; Generated by {info.user_and_email} on {info.modified}"])
    lines.extend(info.formatter.empty_line(count=1))
    lines.extend(["#Requires AutoHotkey v2.0.2", ""])
    return lines


def post_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    return lines
