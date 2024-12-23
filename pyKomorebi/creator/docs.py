import re
from abc import ABC
from typing import Unpack

from pyKomorebi import utils
from pyKomorebi.creator.code import ArgDoc, FormatterArgs, ICodeFormatter, IDocCreator


class ADocCreator(ABC, IDocCreator):
    sentence_split = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s")

    def __init__(self, formatter: ICodeFormatter):
        self.formatter = formatter

    def has_sentence(self, value: str | list[str]) -> bool:
        if isinstance(value, str):
            value = [value]
        return any(self.sentence_split.match(line) is not None for line in value)

    def get_first_sentence_and_rest(self, lines: list[str]) -> tuple[str | None, list[str]]:
        text = utils.as_string(*lines, separator=" ")
        sentences = self.sentence_split.split(text)
        if len(sentences) == 0:
            return None, lines
        if len(sentences) == 1:
            return sentences[0], []
        return sentences[0], sentences[1:]

    def ensure_sentences_has_valid_length(self, sentences: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        if len(sentences) == 0:
            return []
        valid_sentences = []
        for sentence in sentences:
            valid_lines = self.formatter.valid_lines_for(sentence, **kw)
            valid_sentences.extend(valid_lines)
        return valid_sentences

    def _add_possible_value_title(
        self, arg_doc: ArgDoc, doc_lines: list[str], **kw: Unpack[FormatterArgs]
    ) -> list[str]:
        if arg_doc.has_description():
            prefix = self.formatter.column_prefix(kw.get("columns", 0))
            pos_values = self.formatter.concat_values(prefix, "Possible values:", **kw)
            doc_lines.extend(pos_values)
        else:
            kw["separator"] = " "
            last_line = doc_lines.pop(-1)
            doc_lines.extend(self.formatter.concat_values(last_line, "Possible values:", **kw))
        return doc_lines

    def _prepare_enum_possible_values(self, arg_doc: ArgDoc) -> list[tuple[str, str | None]]:
        enum_values = []
        for enum, value in arg_doc.possible_values:
            if enum is None:
                raise ValueError("Enum value is None")
            enum_values.append((enum.upper(), value))
        return enum_values

    def _get_possible_values(self, arg_doc: ArgDoc, doc_lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        kw = kw.copy()
        doc_lines = self._add_possible_value_title(arg_doc, doc_lines, **kw)
        kw["prefix"] = kw.get("columns", 0) + 1
        if arg_doc.are_enums_possible_values():
            enum_possible_values = self._prepare_enum_possible_values(arg_doc)
            enum_column = max([len(enum) for enum, _ in enum_possible_values]) + 1
            kw["columns"] = enum_column + kw.get("columns", 0)
            for enum, value in enum_possible_values:
                if value is None:
                    values = self.formatter.concat_values(enum, **kw)
                else:
                    values = self.formatter.concat_values(enum, value, **kw)
                doc_lines.extend(values)
        else:
            kw["separator"] = ", "
            possible_values = [enum for enum, _ in arg_doc.possible_values]
            doc_lines.extend(self.formatter.concat_values(*possible_values, **kw))
        return doc_lines

    def _command_arg_doc(self, arg_doc: ArgDoc, **kw: Unpack[FormatterArgs]) -> list[str]:
        name = self.formatter.apply_suffix(arg_doc.name, kw.get("suffix", None))
        name = self.formatter.fill_column(name, kw.get("columns", 0))
        doc_lines = self.formatter.concat_values(name, *arg_doc.description, **kw)
        if arg_doc.has_description() and len(doc_lines) == 1:
            doc_lines[0] = self.formatter.ensure_ends_with_point(doc_lines[0])
        if arg_doc.has_possible_values():
            doc_lines = self._get_possible_values(arg_doc, doc_lines, **kw)
        if arg_doc.has_default():
            column_prefix = self.formatter.column_prefix(kw.get("columns", 0))
            default_lines = self.formatter.concat_values(column_prefix, arg_doc.default, **kw)
            doc_lines.extend(default_lines)
        return doc_lines

    def _get_max_length(self, docs: list[ArgDoc], suffix: str) -> int:
        if suffix is None or len(suffix) == 0:
            return 0
        arg_names = [self.formatter.apply_suffix(arg.name, suffix) for arg in docs]
        if len(arg_names) == 0:
            return 0
        return max([len(name) for name in arg_names])
