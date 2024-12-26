from typing import Generic, TypeGuard, TypeVar, Unpack

from pyKomorebi import utils
from pyKomorebi.creator import code as code_utils

from pyKomorebi.creator.code import FormatterArgs, ICodeFormatter

TItem = TypeVar("TItem", str, list[str])


class ListHelper(Generic[TItem]):
    start_str = "(list"
    close_str = ")"

    def __init__(self, formatter: ICodeFormatter):
        self.formatter = formatter
        self.prev_code = ""
        self.args: FormatterArgs = FormatterArgs(separator=" ")
        self.items: list[TItem] = []
        self._values: list[str] = []

    def _previous_code(self) -> list[str]:
        return [self.formatter.indent(self.prev_code, level=self.args.get("level", 0))]

    def _get_line(self, values: list[str], **kw: Unpack[FormatterArgs]) -> str:
        prefix = self.formatter.column_prefix(kw.get("prefix", 0))
        if len(prefix) > len(self.formatter.indent_for(kw.get("level", 0))):
            values = [prefix] + values
        lines = self.formatter.concat_values(*values, **kw)
        return self.formatter.indent(utils.lines_as_str(*lines), level=kw.get("level", 0))

    def _last_valid_index(self, values: list[str], **kw: Unpack[FormatterArgs]) -> int:
        for idx in range(len(values), -1, -1):
            line = self._get_line(list(values[:idx]), **kw)
            if self.formatter.is_not_max_length(line):
                return idx
        return -1

    def create_list_str(self, *list_item: TItem, **kw: Unpack[FormatterArgs]) -> list[str]:
        items = []
        for idx, item in enumerate(list_item):
            values = []
            if kw.get("level") == self.args.get("level") and len(items) == 0:
                values = self._previous_code()
            if len(items) == 0:
                values.append(self.start_str)
            values.extend([item] if isinstance(item, str) else list(item))
            if not isinstance(item, list):
                line = utils.as_string(*values, separator=" ")
                items.append(self.formatter.indent(line, level=kw.get("level", 0)))
                continue
            if idx > 0:
                list_idx = items[0].find(self.start_str)
                kw["prefix"] = items[0].find(" ", list_idx) - 2
            index = self._last_valid_index(values, **kw)
            items.append(self._get_line(values[:index], **kw))
            kw["prefix"] = self.formatter.find_prefix_in_code(items[-1], **kw)
            items.extend(self.formatter.concat_values(*values[index:], **kw))
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
        self._values.extend(self.create_list_str(*items, **kw))  # type: ignore
        self._values.extend(self._append_other_items(all_items, **kw))

    def _append_other_items(self, all_items: bool, **kw: Unpack[FormatterArgs]) -> list[str]:
        if all_items:
            return []
        kw["prefix"] = self.formatter.find_prefix_in_code(self._values[0], **kw)
        values = []
        for item in self.items[1:]:
            if isinstance(item, list):
                values.extend(self.formatter.concat_values(*item, **kw))
            else:
                values.extend(self.formatter.concat_values(item, **kw))
        return values

    def _get_list_lines(self) -> list[str]:
        for idx, line in enumerate(self._values):
            if self.start_str not in line:
                continue
            return self._values[idx:]
        raise ValueError("List lines not found")

    def _list_lines_are_valid(self) -> bool:
        return all(self.formatter.is_not_max_length(line) for line in self._get_list_lines())

    def create(self) -> None:
        pass

    def can_create_all_on(self, second_line: bool) -> bool:
        self._values = []
        kwargs = code_utils.copy_args(self.args, separator=" ")
        if second_line:
            kwargs = code_utils.with_level(self.args)
        self._create_list(all_items=True, **kwargs)
        return self._list_lines_are_valid()

    def can_create_with_first_on(self, second_line: bool) -> bool:
        self._values = []
        kwargs = code_utils.copy_args(self.args, separator=" ")
        if second_line:
            kwargs = code_utils.with_level(self.args)
        self._create_list(all_items=False, **kwargs)
        return self._list_lines_are_valid()

    def found_solution(self) -> bool:
        if self.can_create_all_on(second_line=False) or self.can_create_with_first_on(second_line=False):
            return True
        if self.can_create_all_on(second_line=True) or self.can_create_with_first_on(second_line=True):
            return True
        return False

    def close_list(self) -> None:
        self._values[-1] = f"{self._values[-1]})"

    def as_str(self) -> str:
        value = utils.lines_as_str(*self._values)
        self.reset()
        return value

    def as_list(self) -> list[str]:
        values = list(self._values)
        self.reset()
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
