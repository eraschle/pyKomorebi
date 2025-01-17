import re
from typing import Generic, TypeGuard, TypeVar, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import code as code_utils

from pyKomorebi.creator.code import FormatterArgs, ICodeFormatter

TItem = TypeVar("TItem", str, list[str])


class ListHelper(Generic[TItem]):
    start_str = "(list"
    close_str = ")"
    pair_pattern = re.compile(r"\((.*?)\)")

    def __init__(self, formatter: ICodeFormatter):
        self.formatter = formatter
        self.prev_code = ""
        self.args: FormatterArgs = FormatterArgs(separator=" ")
        self.items: list[TItem] = []
        self._values: list[str] = []
        self._valid_list = False

    def _previous_code(self) -> list[str]:
        return [self.formatter.indent(self.prev_code, level=self.args.get("level", 0))]

    def _get_line(self, values: list[str], **kw: Unpack[FormatterArgs]) -> str:
        lines = self.formatter.concat_values(*values, **kw)
        as_str = utils.lines_as_str(*lines)
        if as_str.startswith("  "):
            return as_str
        return self.formatter.indent(as_str, level=kw.get("level", 0), prefix=kw.get("prefix", 0))

    def _last_valid_index(self, values: list[str], **kw: Unpack[FormatterArgs]) -> int:
        if len(values) == 0:
            return -1
        for idx in range(len(values), -1, -1):
            line = self._get_line(list(values[:idx]), **kw)
            if self.formatter.is_not_max_length(line):
                return idx
        return -1

    def _list_line_exists(self, lines: list[str]) -> bool:
        for line in lines:
            if self.start_str not in line:
                continue
            return line.strip() == self.start_str
        return False

    def _min_or_prefix(self, lines: list[str], prefix: int) -> int:
        level_one_prefix = len(self.formatter.indent_for(level=1))
        if len(lines) == 0:
            return level_one_prefix
        first_line = lines[0].rstrip()
        if len(lines) == 1 and first_line.endswith(self.prev_code):
            return level_one_prefix + 1
        idx, line = self._get_start_list_line(lines)
        if line is None:
            if not lines[-1].endswith(self.close_str):
                open_idx = lines[-1].rfind("(")
                return max(prefix, open_idx)
            return max(prefix, level_one_prefix + 1)
        start_idx = line.find(self.start_str)
        if line.endswith(self.start_str):
            return max(prefix, start_idx + 1)
        if idx < len(lines) - 1:
            bracket_idxs = [line.find("(") for line in lines[idx:]]
            bracket_idxs = [idx for idx in bracket_idxs if idx > start_idx]
            if len(bracket_idxs) == 0:
                bracket_idxs = [start_idx + 1]
            arg_prefix = min(bracket_idxs)
            return max(prefix, arg_prefix)
        arg_prefix = line.find("(", start_idx + 1)
        return max(prefix, arg_prefix)

    def _get_start_list_line(self, lines: list[str]) -> tuple[int, str | None]:
        for idx, line in enumerate(lines):
            if self.start_str not in line:
                continue
            return idx, line
        return -1, None

    def _get_list_prefix(self, lines: list[str], current_prefix: int | None = None) -> int:
        _, line = self._get_start_list_line(lines)
        if line is None:
            if current_prefix is not None:
                prefix = current_prefix
            else:
                prefix = self.formatter.prefix_of(lines[-1])
            return self._min_or_prefix(lines, prefix)
        list_idx = line.find(self.start_str)
        if line.endswith(self.start_str):
            return self._min_or_prefix(lines, list_idx)
        prefix = line.find("(", list_idx + 1)
        if prefix > 0:
            return self._min_or_prefix(lines, prefix)
        else:
            return self._min_or_prefix(lines, list_idx)

    def _open_bracket_count(self, lines: list[str]) -> int:
        return sum([line.count("(") for line in lines])

    def _close_bracket_count(self, lines: list[str]) -> int:
        return sum([line.count(")") for line in lines])

    def _has_closed_command(self, lines: list[str]) -> bool:
        open_brackets = self._open_bracket_count(lines)
        close_brackets = self._close_bracket_count(lines)
        if close_brackets == 0:
            return False
        return (open_brackets - close_brackets) == 2

    def _get_opening_line(self, lines: list[str]) -> str | None:
        if len(lines) == 0:
            return None
        for idx in range(len(lines), -1, -1):
            if idx < 0 or idx >= len(lines):
                continue
            if lines[idx].endswith("))"):
                continue
            if lines[idx].rfind("(") < 0:
                continue
            return lines[idx]
        if ")" in lines[-1] and "(" in lines[-1]:
            return lines[-1]
        return None

    def _get_prefix(self, lines: list[str], current_prefix: int | None = None, **kw: Unpack[FormatterArgs]) -> int:
        if lines[-1].endswith(self.start_str):
            prefix = self._get_list_prefix(lines, current_prefix)
            return prefix
        if self._has_closed_command(lines):
            return self._get_list_prefix(lines, current_prefix)
        line = self._get_opening_line(lines)
        if line is None:
            return self._get_list_prefix(lines, current_prefix)
        prefix = self.formatter.find_prefix_in_code(line, **kw)
        prefix = self._min_or_prefix(lines, prefix=prefix)
        return max(prefix, self._get_list_prefix(lines, current_prefix))

    def _exists(self, value: str, values: list[str] | None = None) -> bool:
        for line in values or self._values:
            if value not in line:
                continue
            return True
        return False

    def create_list_str(self, *list_item: TItem, **kw: Unpack[FormatterArgs]) -> list[str]:
        items = list(self._values)
        last_expr = (-1, -1)
        for item in list_item:
            values = []
            if kw.get("level") == self.args.get("level") and not self._exists(self.prev_code, items):
                values = self._previous_code()
            if not self._exists(self.start_str, items):
                values.append(self.start_str)
            values.extend([item] if isinstance(item, str) else list(item))
            if not isinstance(item, list):
                line = utils.as_string(*values, separator=" ")
                items.append(self.formatter.indent(line, level=kw.get("level", 0)))
                continue
            index = self._last_valid_index(values, **kw)
            if index > 0:
                if self._has_closed_command(items):
                    kw["prefix"] = self._get_prefix(items, **kw)
                elif len(items) > 0 and items[-1].endswith(self.start_str):
                    kw["prefix"] = self._min_or_prefix(items, kw.get("prefix", 0))
                last_row = len(items)
                items.append(self._get_line(values[:index], **kw))
                last_col = items[last_row].find(item[0]) - 2
                last_expr = (last_row, last_col)
                kw["prefix"] = self._get_prefix(items, **kw)
                values = values[index:]
            if len(values) == 0:
                kw["prefix"] = self._min_or_prefix(items, last_expr[1])
                continue
            if self.formatter.is_valid_line(*values, **kw) or len(values) == 1:
                last_row = len(items)
                items.extend(self.formatter.concat_values(*values, **kw))
                last_col = items[last_row].find(item[0]) - 2
                last_expr = (last_row, last_col)
            elif len(values) > 1:
                kw["prefix"] = self._get_prefix(items, **kw)
                last_row = len(items)
                items.extend(self.formatter.concat_values(values[0], **kw))
                last_col = items[last_row].find(item[0]) - 2
                last_expr = (last_row, last_col)
                kw["prefix"] = self._get_prefix(items, **kw)
                items.extend(self.formatter.concat_values(*values[1:], **kw))
        return items

    def _is_list_of_strings(self, values: list[TItem]) -> TypeGuard[list[str]]:
        return all(isinstance(value, str) for value in values)

    def _create_list(self, all_items: bool, **kw: Unpack[FormatterArgs]) -> None:
        if all_items:
            if self._is_list_of_strings(self.items):
                items = [self.formatter.concat_args(*self.items)]
            else:
                items = list(self.items)
        else:
            items = [self.items[0]]
        kw["prefix"] = self._min_or_prefix(self._values, prefix=0)
        if len(self._values) == 0:
            self._values.extend(self.create_list_str(*items, **kw.copy()))  # type: ignore
        else:
            self._values = self.create_list_str(*items, **kw.copy())  # type: ignore
        self._values.extend(self._append_other_items(all_items, **kw))

    def _append_other_items(self, all_items: bool, **kw: Unpack[FormatterArgs]) -> list[str]:
        if all_items:
            return []
        if self._list_line_exists(self._values) or self._values[-1].endswith(self.close_str):
            kw["prefix"] = self._get_list_prefix(self._values, kw.get("prefix", None))
        elif self._values[-1].endswith(self.close_str):
            kw["prefix"] = self._get_prefix(self._values, kw.get("prefix", None), **kw)
        else:
            kw["prefix"] = self.formatter.find_prefix_in_code(self._values[-1], **kw)
        values = []
        for item in self.items[1:]:
            if isinstance(item, list):
                if len(item) == 0:
                    continue
                if len(item) == 1:
                    values.extend(self.formatter.concat_values(*item, **kw))
                else:
                    values.extend(self.formatter.concat_values(item[0], **kw))
                    kw["prefix"] = self._get_prefix(values, **kw)
                    values.extend(self.formatter.concat_values(*item[1:], **kw))
            elif isinstance(item, str):
                prefix = kw.get("prefix", 0)
                level = kw.get("level", 0)
                item_str = self.formatter.indent(item, level=level, prefix=prefix)
                values.append(item_str)
        return values

    def _get_list_lines(self) -> list[str]:
        for idx, line in enumerate(self._values):
            if self.start_str not in line:
                continue
            return self._values[idx:]
        raise ValueError("List lines not found")

    def _list_lines_are_valid(self) -> bool:
        return all(self.formatter.is_not_max_length(line) for line in self._get_list_lines())

    def is_valid_list(self) -> bool:
        return self._valid_list

    def create(self) -> None:
        self._values = [val for val in self._values if utils.is_not_blank(val, strip_chars=" ")]
        self._valid_list = True

    def can_create_all_on(self, second_line: bool) -> bool:
        self._values = self._previous_code() if second_line else []
        kwargs = code_utils.copy_args(self.args, separator=" ")
        if second_line:
            # kwargs = code_utils.with_level(self.args)
            prefix = self._min_or_prefix(self._values, prefix=0)
            kwargs["prefix"] = prefix
        self._create_list(all_items=True, **kwargs)
        return self._list_lines_are_valid()

    def can_create_with_first_on(self, second_line: bool) -> bool:
        self._values = self._previous_code() if second_line else []
        kwargs = code_utils.copy_args(self.args, separator=" ")
        if second_line:
            # kwargs = code_utils.with_level(self.args)
            prefix = self._min_or_prefix(self._values, prefix=0)
            kwargs["prefix"] = prefix
        self._create_list(all_items=False, **kwargs)
        return self._list_lines_are_valid()

    def create_with_list_on_second_line(self) -> bool:
        self._values = self._previous_code()
        prefix = self._min_or_prefix(self._values, prefix=0)
        self._values.append(
            self.formatter.indent(
                self.start_str,
                level=self.args.get("level", 0),
                prefix=prefix,
            )
        )
        kwargs = code_utils.copy_args(self.args, separator=" ")
        prefix = self._min_or_prefix(self._values, prefix=0)
        kwargs["prefix"] = prefix
        self._create_list(all_items=False, **kwargs)
        return True

    def found_solution(self) -> bool:
        if self.can_create_all_on(second_line=False):
            return True
        if self.can_create_with_first_on(second_line=False):
            return True
        if self.can_create_all_on(second_line=True):
            return True
        if self.can_create_with_first_on(second_line=True):
            return True
        return self.create_with_list_on_second_line()

    def close_list(self) -> None:
        self._values[-1] = f"{self._values[-1]})"

    def as_str(self) -> str:
        value = utils.lines_as_str(*self._values)
        return value

    def as_list(self) -> list[str]:
        values = list(self._values)
        return values

    def reset(self) -> None:
        self.prev_code = ""
        self.items = []
        self.args = FormatterArgs(separator=" ")
        self._values = []

    def with_context(self, previous_code: str, items: list[TItem], **kw: Unpack[FormatterArgs]):
        self.reset()
        self.prev_code = previous_code
        self.items = items
        self.args = kw
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any(exc for exc in (exc_type, exc_val, exc_tb)):
            raise exc_type(exc_val)
        self.close_list()
