"""Factory module for creating ApiCommand objects from files."""

from pathlib import Path
from typing import Callable

from pyKomorebi.model import ApiCommand

IFactory = Callable[[Path], ApiCommand]


def get(extension: str) -> IFactory:
    if extension.endswith("md"):
        from pyKomorebi.factory import markdown

        return markdown.create
    raise ValueError(f"Unsupported extension '{extension}' for factory")
