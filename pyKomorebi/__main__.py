import argparse
from pathlib import Path

from pyKomorebi.generate import generate_from_path
from pyKomorebi.generator import Options


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pyKomorebi code generator",
        description="Generates code from source files for code language.",
        epilog="Have fun coding!",
    )
    parser.add_argument(
        "-i",
        "--import-path",
        help="Path to import source files.",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-x",
        "--extension",
        help="File extension of import source files.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-l",
        "--language",
        help="Language of generated code.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-e",
        "--export-path",
        help="Path to export generated code.",
        required=False,
        type=Path,
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    options = Options(
        import_path=args.import_path,
        import_extension=args.extension,
        export_path=args.export_path,
    )
    generate_from_path(args.language, options)
