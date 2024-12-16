from dataclasses import dataclass
from pathlib import Path

from pyKomorebi import factory
from pyKomorebi.factory import IFactory
from pyKomorebi import generator
from pyKomorebi.generator import ICodeGenerator, Options
from pyKomorebi.model import ApiCommand


@dataclass
class GeneratorOptions:
    options: Options
    generator: ICodeGenerator
    factory: IFactory

    @property
    def import_extension(self) -> str:
        return self.options.import_extension

    @property
    def export_path(self) -> Path:
        if self.options.export_path is None:
            raise ValueError("export_path is not set")
        return self.options.export_path

    def doc_file_path(self) -> list[Path]:
        paths = list(self.options.import_path.rglob(f"*{self.options.import_extension}"))
        return sorted(paths, key=lambda p: p.name)

    def export_per_command(self) -> bool:
        if self.options.export_path is None:
            return False
        return len(self.options.export_path.suffix) == 0

    def export_one_file(self) -> bool:
        if self.options.export_path is None:
            return False
        return len(self.options.export_path.suffix) > 0

    def export_path_for(self, command: ApiCommand) -> Path:
        export_path = self.options.export_path
        if export_path is None:
            raise ValueError("export_path is not set")
        if not self.export_per_command():
            raise ValueError("export_path is not per command")
        if self.generator is None:
            raise ValueError("generator is not set")
        if not export_path.exists():
            export_path.mkdir(parents=True, exist_ok=True)
        file_name = f"{command.name}{self.generator.extension}"
        return export_path / file_name


def _generate(doc_path: Path, options: GeneratorOptions) -> list[str]:
    command = options.factory(doc_path)
    code_lines = options.generator.generate(command)

    if options.export_per_command():
        export_path = options.export_path_for(command)
        code_lines = options.generator.pre_generator(code_lines)
        with open(export_path, "w") as export_file:
            export_file.write("\n".join(code_lines))
    return code_lines


def _get_generator_options(language: str, options: Options) -> GeneratorOptions:
    return GeneratorOptions(
        options=options,
        generator=generator.get(language=language, options=options),
        factory=factory.get(options.import_extension),
    )


def generate_from_path(language: str, options: Options) -> list[str]:
    gen_options = _get_generator_options(language=language, options=options)
    empty_lines = ["", ""]
    commands = []
    for doc_path in gen_options.doc_file_path():
        code_lines = _generate(doc_path, gen_options)
        commands.extend(code_lines)
        commands.extend(empty_lines)
    if gen_options.export_one_file():
        commands = gen_options.generator.pre_generator(commands)
        commands = gen_options.generator.post_generator(commands)
        with open(gen_options.export_path, "w") as export_file:
            export_file.write("\n".join(commands))
    return commands
