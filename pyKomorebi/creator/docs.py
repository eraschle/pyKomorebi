from abc import ABC
from typing import Unpack

from pyKomorebi import utils
from pyKomorebi.creator.code import ArgDoc, FormatterArgs, ICodeFormatter, IDocCreator


class ADocCreator(ABC, IDocCreator):
    def __init__(self, formatter: ICodeFormatter):
        self.formatter = formatter

    def has_sentence(self, *value: str) -> bool:
        return utils.has_sentence(*value)

    def get_first_sentence_and_rest(self, lines: list[str]) -> tuple[str | None, list[str]]:
        sentences = utils.get_sentences(*lines)
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

    def _add_possible_value_title(self, arg: ArgDoc, lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        default = arg.default if arg.has_default() else ""
        if arg.has_description():
            prefix = self.formatter.column_prefix(kw.get("columns", 0))
            pos_values = self.formatter.concat_values(prefix, "Possible values:", default, **kw)
            lines.extend(pos_values)
        else:
            kw["separator"] = " "
            last_line = lines.pop(-1)
            lines.extend(self.formatter.concat_values(last_line, "Possible values:", default, **kw))
        return lines

    def _can_append_to_title(self, doc_lines: list[str], doc: ArgDoc, **kw: Unpack[FormatterArgs]) -> bool:
        if doc.has_default() or len(doc_lines) > 1:
            return False
        values_str = kw["separator"].join([cst.name for cst in doc.possible_values])
        return self.formatter.is_valid_line(doc_lines[-1], values_str, **kw)

    def _get_possible_values(self, arg_doc: ArgDoc, doc_lines: list[str], **kw: Unpack[FormatterArgs]) -> list[str]:
        kw = kw.copy()
        doc_lines = self._add_possible_value_title(arg_doc, doc_lines, **kw)
        kw["prefix"] = kw.get("columns", 0) + 1  # +1 for the space
        if arg_doc.has_possible_values_descriptions():
            enum_column = max([len(arg_doc.get_name(const)) for const in arg_doc.possible_values])
            kw["columns"] = enum_column + kw.get("columns", 0) + 1  # +1 for the space
            for constant in arg_doc.possible_values:
                name = arg_doc.get_name(constant)
                if constant.has_description():
                    values = self.formatter.concat_values(name, *constant.description, **kw)
                else:
                    values = self.formatter.concat_values(name, **kw)
                doc_lines.extend(values)
        else:
            kw["separator"] = ", "
            values = [value.name for value in arg_doc.possible_values]
            if self._can_append_to_title(doc_lines, arg_doc, **kw):
                values_str = kw["separator"].join(values)
                doc_lines[-1] = utils.as_string(doc_lines[-1], values_str, separator=" ")
            else:
                doc_lines.extend(self.formatter.concat_values(*values, **kw))
        return doc_lines

    def _command_arg_doc(self, arg_doc: ArgDoc, **kw: Unpack[FormatterArgs]) -> list[str]:
        name = utils.ensure_ends_with(arg_doc.name, kw.get("suffix", None))
        name = self.formatter.fill_column(name, kw.get("columns", 0))
        doc_lines = self.formatter.concat_values(name, *arg_doc.description, **kw)
        if arg_doc.has_description() and len(doc_lines) == 1:
            doc_lines[0] = utils.ensure_ends_with(doc_lines[0], end_str=".")
        elif arg_doc.has_description() and len(doc_lines) > 1:
            doc_lines[-1] = utils.ensure_ends_with(doc_lines[-1], end_str=".")
        if arg_doc.has_possible_values():
            doc_lines = self._get_possible_values(arg_doc, doc_lines, **kw)
        elif arg_doc.has_default():
            column_prefix = self.formatter.column_prefix(kw.get("columns", 0))
            default_lines = self.formatter.concat_values(column_prefix, arg_doc.default, **kw)
            doc_lines.extend(default_lines)
        return doc_lines

    def _get_max_length(self, docs: list[ArgDoc], suffix: str) -> int:
        if suffix is None or len(suffix) == 0:
            return 0
        arg_names = [utils.ensure_ends_with(arg.name, suffix) for arg in docs]
        if len(arg_names) == 0:
            return 0
        return max([len(name) for name in arg_names])
