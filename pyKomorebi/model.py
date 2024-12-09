from typing import Optional
from dataclasses import dataclass


@dataclass
class CommandArgs:
    doc_string: list[str]
    default: Optional[str]
    possible_values: list[str]

    def _get_name_with_default(self, name: str) -> str:
        if self.default is not None:
            return f"{name} ({self.default})"
        return name

    def full_name(self, with_default: bool) -> str:
        raise NotImplementedError

    def description(self, with_default: bool) -> str:
        if len(self.doc_string) == 0 and (self.default is None or not with_default):
            return ""
        if len(self.doc_string) == 0 and with_default:
            return f"Default: {self.default}"
        if not with_default:
            return "\n".join(self.doc_string)
        lines = [f"{self.doc_string[0]} (Default: {self.default})"]
        lines.extend(self.doc_string[1:])
        return "\n".join(lines)


@dataclass
class CommandOption(CommandArgs):
    short: Optional[str]
    name: Optional[str]

    def full_name(self, with_default: bool) -> str:
        name = None
        if self.short is not None:
            name = self.short
        if self.name is not None:
            if name is None:
                name = ""
            if len(name) > 0:
                name += ", "
            name += self.name
        if name is None:
            raise ValueError("No option name")
        if with_default:
            return self._get_name_with_default(name)
        return name


@dataclass
class CommandArgument(CommandArgs):
    name: str

    def full_name(self, with_default: bool) -> str:
        if with_default and self.default is not None:
            return self._get_name_with_default(self.name)
        return self.name


@dataclass
class ApiCommand:
    name: str
    description: list[str]
    arguments: list[CommandArgument]
    options: list[CommandOption]
