import re
from abc import ABC
from typing import Iterable, Optional, Unpack

from pyKomorebi import utils
from pyKomorebi.creator.code import ArgDoc, ICodeFormatter, IDocCreator, CreatorArgs


class ADocCreator(ABC, IDocCreator):
    sentence_split = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s")
    enumeration = re.compile(r"(?P<name>\s*-\s?[\w\s]*:)")

    def __init__(self, max_length: int, formatter: ICodeFormatter):
        self.max_length = max_length
        self.formatter = formatter

    def is_valid_length(self, line: Optional[str], level: int = 0, columns: int = 0) -> bool:
        if line is None:
            return False
        level_col = self.formatter.indent_for(level=level)
        line_length = len(line) + max(len(level_col), columns)
        return line_length <= self.max_length

    def valid_lines_of(self, some_text: Optional[str], **kw: Unpack[CreatorArgs]) -> list[str]:
        if some_text is None or len(some_text.strip()) == 0:
            return []
        if self.is_valid_length(
            some_text,
            level=kw.get("level", 0),
            columns=kw.get("columns", 0) or 0,
        ):
            return [some_text]
        return self.concat_values(*some_text.split(kw["separator"]), **kw)

    def _get_enumeration(self, text: str, **kw: Unpack[CreatorArgs]) -> tuple[Optional[str], str]:
        if text is None or len(text.strip()) == 0:
            return None, text
        values = self.enumeration.split(text)
        if values is None or len(values) == 0:
            return None, text
        values = [value.strip("- :") for value in values]
        values = [value for value in values if len(value) > 0]
        if len(values) != 2:
            return None, text
        return self.formatter.fill_column(values[0], kw.get("columns", 0)), values[1]

    def _concat_enumeration(self, enum: str, rest: str, **kw: Unpack[CreatorArgs]) -> tuple[str, str]:
        lines = self.concat_values(enum, rest, **kw)
        return utils.lines_as_str(*lines[:-1]), lines[-1]

    def _concat_to_long_value(self, value: str, **kw: Unpack[CreatorArgs]) -> tuple[str, str]:
        separator = kw.get("separator", None)
        kw["separator"] = " "
        value_lines = self.valid_lines_of(value, **kw)
        kw["separator"] = separator
        return utils.lines_as_str(*value_lines[:-1]), value_lines[-1]

    def concat_values(self, *values: str, **kw: Unpack[CreatorArgs]) -> list[str]:
        concat_lines = []
        current = ""
        for value in values:
            concat = utils.as_string(current, value, separator=kw["separator"])
            kw_valid = {"level": kw.get("level", 0), "columns": 0}
            if self.is_valid_length(concat, **kw_valid):
                current = concat
                continue
            enum, rest = self._get_enumeration(value, **kw)
            if enum is not None:
                current, value = self._concat_enumeration(enum, rest, **kw)
            elif not self.is_valid_length(value, level=kw.get("level", 0)):
                current, value = self._concat_to_long_value(value, **kw)
            concat_lines.append(current)
            columns = self.formatter.fill_column("", kw.get("columns", 0))
            current = utils.as_string(columns, value, separator=kw["separator"])
        concat_lines.append(current)
        return concat_lines

    def _ensure_not_empty(self, lines: list[str]) -> list[str]:
        return [line for line in lines if len(line.strip()) > 0]

    def _command_arg_doc(self, arg_doc: ArgDoc, **kw: Unpack[CreatorArgs]) -> str:
        name = self.formatter.apply_suffix(arg_doc.name, kw.get("suffix", None))
        name = self.formatter.fill_column(name, kw.get("columns", 0))
        doc_lines = self.concat_values(name, *arg_doc.description, **kw)
        doc_string = utils.lines_as_str(*doc_lines)
        if len(arg_doc.possible_values) > 0:
            separator = kw.get("separator", None)
            kw["separator"] = ", "
            concat_values = self.concat_values(doc_string, *arg_doc.possible_values, **kw)
            doc_string = utils.lines_as_str(*concat_values)
            kw["separator"] = separator
        if len(arg_doc.default) > 0:
            default = self.formatter.fill_column(arg_doc.default, kw.get("columns", 0))
            doc_string = utils.lines_as_str(doc_string, default)
        return doc_string

    def _get_max_length(self, docs: Iterable[ArgDoc], suffix: str) -> Optional[int]:
        if suffix is None or len(suffix) == 0:
            return None
        arg_names = [self.formatter.apply_suffix(arg.name, suffix) for arg in docs]
        if len(arg_names) == 0:
            return None
        return max([len(name) for name in arg_names]) + 2
