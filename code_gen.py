import argparse
import logging
import sys
from pathlib import Path

from pyKomorebi import generate as gen
from pyKomorebi.creator import TranslationManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pyKomorebi code generator",
        description="Generates code from source files for code language.",
        epilog="Have fun coding!",
    )
    parser.add_argument(
        "-i",
        "--import-path",
        help="Path to import source files. Only need when import file on hardisk.",
        required=False,
        type=Path,
    )
    parser.add_argument(
        "-x",
        "--extension",
        help="File extension of import source files. Only needed if import files on hardisk.",
        required=False,
        type=str,
    )
    parser.add_argument(
        "-l",
        "--language",
        help="Implemented Language to generate code.",
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


def configure_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger()
    # logger.addHandler(app.get_tk_log_handler())
    logger.info("Logger configured")


def generate():
    configure_logger()
    args = parse_arguments()
    translated = TranslationManager(
        option_map={
            "await": "await-configuration",
            "tcp": "tcp-port",
        },
        argument_map={},
        variable_map={
            "system": "komorebi-api-style-border",
            "komorebi": "komorebi-api-style-mouse-follows",
            "linear": "komorebi-api-style-animation",
        },
    )
    options = gen.Options(
        language=args.language,
        import_path=args.import_path,
        extension=args.extension,
        export_path=args.export_path,
        exclude_names=["pipe", "socket", "tcp"],
        translated=translated,
    )
    logger = logging.getLogger()
    logger.info(f"Generate {args.language}:")
    logger.info(f"From: {args.extension}")
    logger.info(f"To: {args.export_path}")
    gen.generate_code(**options)
    logger.info("Finished generating code")


if __name__ == '__main__':
    print(f"Started with: {sys.argv}")
    if sys.argv[-1] == "--emacs":
        first = sys.argv.pop(0)
        print(f"Removed: {first}")
        first = sys.argv.pop(-1)

    generate()
