from typing import Optional
from dataclasses import dataclass


@dataclass
class CommandArgs:
    description: list[str]
    default: Optional[str]
    possible_values: list[str]

    def get_name(self) -> str:
        raise NotImplementedError

    def get_default(self) -> str:
        if self.default is None:
            return ""
        return f"Default: {self.default}"


@dataclass
class CommandOption(CommandArgs):
    short: Optional[str]
    name: Optional[str]
    arg_value: Optional[str]

    def __post_init__(self):
        self._short_name = None if self.short is None else self.short.removeprefix("-")
        self._long_name = None if self.name is None else self.name.removeprefix("--")

    @property
    def has_value(self) -> bool:
        return self.arg_value is not None

    @property
    def is_help(self) -> bool:
        return self.name == "--help" or self.short == "-h"

    @property
    def short_name(self) -> Optional[str]:
        return self._short_name

    @property
    def long_name(self) -> Optional[str]:
        return self._long_name

    def get_name(self) -> str:
        name = self.long_name or self.short_name
        if name is None:
            raise Exception("Option has neither short nor long name")
        return name


@dataclass
class CommandArgument(CommandArgs):
    name: str

    def get_name(self) -> str:
        return self.name


@dataclass
class ApiCommand:
    name: str
    description: list[str]
    usage: Optional[str]
    arguments: list[CommandArgument]
    options: list[CommandOption]

    def remove_help_option(self):
        options = [opt for opt in self.options if not opt.is_help]
        self.options = options

    def __len__(self):
        return len(self.arguments) + len(self.options)
