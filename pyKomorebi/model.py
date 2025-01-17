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
class CommandBase(ABC):
    description: list[str] = field(compare=False, repr=False)
    name: str = field(compare=True, repr=True, init=False)

    def __post_init__(self):
        self.description = utils.strip_and_clean_blank(*self.description, strip_chars=" ")
        self.name = self._get_name()

    @abstractmethod
    def _get_name(self) -> str:
        pass

    def has_description(self) -> bool:
        return len(self.description) > 0


@dataclass
class CommandConstant(CommandBase):
    constant: str = field(compare=True, repr=True)

    def __post_init__(self):
        super().__post_init__()

    def _get_name(self) -> str:
        return self.constant

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CommandConstant):
            return NotImplemented
        return self.constant == other.constant

    def __hash__(self) -> int:
        return hash(self.constant)


@dataclass
class CommandArgs(CommandBase):
    description: list[str]
    default: str | None
    constants: list[CommandConstant]

    def __post_init__(self):
        super().__post_init__()
        self.default = _value(self.default)
        self.constants = [value for value in self.constants if value.name is not None]

    def has_constants(self) -> bool:
        return len(self.constants) > 0

    def has_default(self) -> bool:
        return self.default is not None

    @abstractmethod
    def is_optional(self) -> bool:
        return self.default is not None


@dataclass
class CommandOption(CommandArgs):
    short: str | None
    long: str | None
    value: str | None

    def __post_init__(self):
        super().__post_init__()
        self.short = _value(self.short)
        self.long = _value(self.long)
        self.value = _value(self.value)

    def has_value(self) -> bool:
        return self.value is not None

    def is_help(self) -> bool:
        return self.long == "--help" or self.short == "-h"

    def is_optional(self) -> bool:
        return True

    @property
    def command_name(self) -> str:
        if self.long is not None:
            return self.long
        if self.short is not None:
            return self.short
        raise Exception("Option has neither short nor long name")

    @property
    def short_name(self) -> str | None:
        if self.short is None:
            return None
        return self.short.removeprefix("-")

    @property
    def long_name(self) -> str | None:
        if self.long is None:
            return None
        return self.long.removeprefix("--")

    def _get_name(self) -> str:
        if self.long_name is not None:
            return self.long_name
        if self.short_name is not None:
            return self.short_name
        raise Exception("Option has neither short nor long name")


@dataclass
class CommandArgument(CommandArgs):
    argument: str
    optional: bool

    def __post_init__(self):
        super().__post_init__()

    def _get_name(self) -> str:
        return self.argument

    def is_optional(self) -> bool:
        return self.optional


@dataclass(repr=True, order=True)
class ApiCommand:
    name: str = field(compare=True, repr=True)
    description: list[str] = field(compare=False, repr=False)
    usage: str | None = field(compare=False, repr=False)
    arguments: list[CommandArgument] = field(compare=False, repr=False)
    options: list[CommandOption] = field(compare=False, repr=False)

    def __post_init__(self):
        self.description = utils.strip_and_clean_blank(*self.description)
        self.usage = _value(self.usage)

    def remove_help_option(self):
        options = [opt for opt in self.options if not opt.is_help()]
        self.options = options
