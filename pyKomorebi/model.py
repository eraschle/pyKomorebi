from abc import ABC, abstractmethod
from typing import TypeGuard
from dataclasses import dataclass, field

from pyKomorebi import utils


def _is_value(value: str | None) -> TypeGuard[str]:
    if value is None:
        return False
    return len(value.strip()) > 0


def _value(value: str | None) -> str | None:
    if not _is_value(value):
        return None
    return value.strip()


@dataclass
class CommandArgs(ABC):
    description: list[str]
    default: str | None
    possible_values: list[str]

    def __post_init__(self):
        self.default = _value(self.default)
        self.description = utils.list_without_none_or_empty(*self.description)
        self.possible_values = utils.list_without_none_or_empty(*self.possible_values)

    @abstractmethod
    def get_name(self) -> str:
        pass

    def has_default(self) -> bool:
        return self.default is not None

    def has_possible_values(self) -> bool:
        return len(self.possible_values) > 0


@dataclass
class CommandOption(CommandArgs):
    short: str | None
    name: str | None
    value: str | None

    def __post_init__(self):
        super().__post_init__()
        self.value = _value(self.value)
        self._short_name = None if self.short is None else self.short.removeprefix("-")
        self._long_name = None if self.name is None else self.name.removeprefix("--")

    def has_value(self) -> bool:
        return self.value is not None

    def is_help(self) -> bool:
        return self.name == "--help" or self.short == "-h"

    @property
    def command_name(self) -> str:
        if self.name is not None:
            return self.name
        if self.short is not None:
            return self.short
        raise Exception("Option has neither short nor long name")

    @property
    def short_name(self) -> str | None:
        return self._short_name

    @property
    def long_name(self) -> str | None:
        return self._long_name

    def get_name(self) -> str:
        name = self.long_name or self.short_name
        if name is None:
            raise Exception("Option has neither short nor long name")
        return name


@dataclass
class CommandArgument(CommandArgs):
    name: str
    optional: bool

    def __post_init__(self):
        super().__post_init__()

    def get_name(self) -> str:
        return self.name


@dataclass(repr=True, order=True)
class ApiCommand:
    name: str = field(compare=True, repr=True)
    description: list[str] = field(compare=False, repr=False)
    usage: str | None = field(compare=False, repr=False)
    arguments: list[CommandArgument] = field(compare=False, repr=False)
    options: list[CommandOption] = field(compare=False, repr=False)

    def __post_init__(self):
        self.description = utils.list_without_none_or_empty(*self.description)
        self.usage = _value(self.usage)

    def remove_help_option(self):
        options = [opt for opt in self.options if not opt.is_help()]
        self.options = options

    def has_required_arguments(self) -> bool:
        return len(self.required_arguments) > 0

    @property
    def required_arguments(self) -> list[CommandArgument]:
        return [arg for arg in self.arguments if not arg.optional]

    def has_optional_arguments(self) -> bool:
        return len(self.optional_arguments) > 0

    @property
    def optional_arguments(self) -> list[CommandArgs]:
        optional: list[CommandArgs] = [arg for arg in self.arguments if arg.optional]
        optional += sorted(self.options, key=lambda x: x.get_name())
        return optional

    def has_options(self) -> bool:
        return len(self.options) > 0

    def __len__(self):
        return len(self.arguments) + len(self.options)
