"""Factory module for creating ApiCommand objects from files."""


def get(extension: str):
    if not extension.startswith("."):
        raise ValueError(f"Extension '{extension}' must start with a period")
    if extension.endswith(".cmd"):
        from pyKomorebi.factory import console

        return console.import_api
    if extension.endswith(".md"):
        from pyKomorebi.factory import markdown

        return markdown.import_api
    raise ValueError(f"Unsupported extension '{extension}' for factory")
