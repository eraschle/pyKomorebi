from dataclasses import dataclass
from datetime import datetime


from pyKomorebi import utils
from pyKomorebi.creator.code import ICodeFormatter


@dataclass(frozen=True)
class FunctionNames:
    executable_custom_var: str = "executable"
    execute_func_name: str = "execute"
    ensure_string_func_name: str = "ensure-string"
    args_func_name: str = "args-get"

    def executable_var(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.executable_custom_var)

    def execute_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.execute_func_name, private=True)

    def ensure_string_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.ensure_string_func_name, private=True)

    def args_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.args_func_name, private=True)


@dataclass
class PackageInfo:
    name: str
    version: str
    repository: str
    user_name: str
    user_email: str
    emacs_version: str
    formatter: ICodeFormatter

    @property
    def user_and_email(self) -> str:
        return f"{self.user_name} <{self.user_email}>"

    @property
    def modified(self) -> str:
        return datetime.now().strftime("%B %d, %Y")

    @property
    def year(self) -> str:
        return datetime.now().strftime("%Y")

    def comment(self, *values: str, chars: str = ";;") -> list[str]:
        return self.formatter.comment(*values, chars=chars)

    def region(self, name: str) -> list[str]:
        return self.formatter.region_comment(name)

    def empty_line(self, count: int = 1) -> list[str]:
        return self.formatter.empty_line(count=count)

    def indent(self, line: str, level: int = 0) -> str:
        return self.formatter.indent(line, level)

    def prefix(self, line: str, prefix: int) -> str:
        column = self.formatter.column_prefix(prefix)
        return utils.as_string(column, line, separator=" ")


def _package_descriptions(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=0)
    lines.extend(info.comment(f"{info.name}.el --- Description -*- lexical-binding: t; -*-", chars=";;;"))
    lines.extend(info.comment())
    lines.extend(info.comment(f"Copyright (C) {info.year} {info.user_name}"))
    lines.extend(info.comment())
    lines.extend(info.comment(f"Author: {info.user_and_email}"))
    lines.extend(info.comment(f"Maintainer: {info.user_and_email}"))
    lines.extend(info.comment("Created: Oktober 07, 2024"))
    lines.extend(info.comment(f"Modified: {info.modified}"))
    lines.extend(info.comment(f"Version: {info.version}"))
    lines.extend(info.comment("Keywords: docs emulations extensions help languages lisp local processes"))
    lines.extend(info.comment(f"Homepage: {info.repository}"))
    lines.extend(info.comment(f'Package-Requires: ((emacs "{info.emacs_version}"))'))
    lines.extend(info.comment())
    lines.extend(info.comment("This file is not part of GNU Emacs."))
    lines.extend(info.comment())
    lines.extend(info.comment("Commentary:", chars=";;;"))
    lines.extend(info.comment())
    lines.extend(info.comment("Description", chars=";;;"))
    lines.extend(info.comment())
    lines.extend(info.comment("Code:", chars=";;;"))
    lines.extend(info.formatter.empty_line(count=2))
    return lines


def _require(package: str, info: PackageInfo) -> str:
    return info.indent(f"(require '{package})", level=0)


def _require_packages(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=1)
    lines.append(_require("komorebi-path", info))
    return lines


def _executable_var(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.executable_var(info.formatter)


def _custom_executable(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=2)
    lines.append(info.indent(f"(defcustom {_executable_var(info)} \"\"", level=0))
    lines.append(info.indent("\"The path to the komorebi executable.\"", level=1))
    lines.append(info.indent(":type 'string", level=1))
    lines.append(info.indent(f":group '{info.name})", level=1))
    return lines


def _ensure_string_func(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.ensure_string_func(info.formatter)


def _ensure_args_are_string(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=2)
    lines.append(info.indent(f"(defun {_ensure_string_func(info)} (args)", level=0))
    lines.append(info.indent("\"Ensure that ARGS are strings.\"", level=1))
    lines.append(info.indent("(seq-map (lambda (arg)", level=1))
    pre_lambda = lines[-1].find("(lambda (arg)") - 1
    lines.append(info.prefix("(cond ((numberp arg) (number-to-string arg))", prefix=pre_lambda + 2))
    pre_cond = lines[-1].find("((") - 1
    lines.append(info.prefix("((stringp arg) arg)", prefix=pre_cond))
    lines.append(info.prefix("(t (error (format \"Invalid argument: %S\" arg)))))", prefix=pre_cond))
    lines.append(info.prefix("args))", prefix=pre_lambda))
    return lines


def _args_func(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.args_func(info.formatter)


def _get_args_function(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=2)
    lines.append(info.indent(f"(defun {_args_func(info)} (args)", level=0))
    lines.append(info.indent("\"Return string of ARGS.\"", level=1))
    lines.append(info.indent("(string-join", level=1))
    pre_join = len(info.formatter.indent_for(level=1))
    lines.append(info.prefix(f"({_ensure_string_func(info)}", prefix=pre_join))
    pre_ensure = lines[-1].find(f"({_ensure_string_func(info)}")
    lines.append(info.prefix("(seq-filter", prefix=pre_ensure))
    pre_pred = pre_ensure + 1
    lines.append(info.prefix("(lambda (arg)", prefix=pre_pred))
    pre_filter = lines[-1].find("(lambda (arg)") - 1
    pre_lambda = pre_filter + 2
    lines.append(info.prefix("(unless (null arg)", prefix=pre_lambda))
    pre_unless = lines[-1].find("(unless") + 1
    lines.append(info.prefix("(or (numberp arg) (stringp arg)", prefix=pre_unless))
    pre_num = lines[-1].find("(numberp") - 1
    lines.append(info.prefix("(not (string-empty-p arg)))))", prefix=pre_num))
    lines.append(info.prefix("args))", prefix=pre_filter))
    lines.append(info.prefix('" "))', prefix=pre_join))
    return lines


def execute_func_name(formatter: ICodeFormatter) -> str:
    func_names = FunctionNames()
    return func_names.execute_func(formatter)


def execute_func(info: PackageInfo) -> str:
    return execute_func_name(info.formatter)


def _executable_is_set_check(info: PackageInfo, level: int) -> list[str]:
    lines = info.empty_line(count=0)
    exe_path = _executable_var(info)
    lines.append(info.indent(f"(unless (and {exe_path}", level=level))
    pre_empty = lines[-1].find(f"{exe_path}") - 1
    lines.append(info.prefix(f"(length> {exe_path} 0))", prefix=pre_empty))
    return lines


def _executable_is_set_message(info: PackageInfo, level: int) -> list[str]:
    lines = info.empty_line(count=0)
    exe_path = _executable_var(info)
    lines.append(info.indent("(error (string-join", level=level + 1))
    pre_message = lines[-1].find("(string-join")
    lines.append(info.prefix(f"(list \"`{exe_path}' variable not set.\"", prefix=pre_message))
    pre_exe = lines[-1].find(f" \"`{exe_path}'")
    message = "\"Please set it to the path of the komorebic executable.\")"
    lines.append(info.prefix(message, prefix=pre_exe))
    lines.append(info.prefix("\" \")))", prefix=pre_message))
    return lines


def _executable_exists_check(info: PackageInfo, level: int) -> list[str]:
    lines = info.empty_line(count=0)
    exe_path = _executable_var(info)
    message = f"(format \"%s does not exist.\" {exe_path})"
    lines.append(info.indent(f"(unless (file-exists-p {exe_path})", level=level))
    lines.append(info.indent(f"(error {message}))", level=level + 1))
    return lines


def _execute_command(info: PackageInfo) -> list[str]:
    exe_path = _executable_var(info)
    lines = info.empty_line(count=2)
    lines.append(info.indent(f"(defun {execute_func(info)} (command &rest args)", level=0))
    lines.append(info.indent("\"Execute komorebi COMMAND with ARGS in shell.\"", level=1))
    lines.extend(_executable_is_set_check(info, level=1))
    lines.extend(_executable_is_set_message(info, level=1))
    lines.extend(_executable_exists_check(info, level=1))
    lines.append(info.indent("(let* ((shell-cmd (format \"%s %s %s\"", level=1))
    pre_result = lines[-1].find("(shell-cmd") - 1
    pre_format = lines[-1].find("\"%s %s %s\"") - 1
    lines.append(info.prefix(f"(shell-quote-argument {exe_path})", prefix=pre_format))
    lines.append(info.prefix("command", prefix=pre_format))
    lines.append(info.prefix(f"({_args_func(info)} args)))", prefix=pre_format))
    lines.append(info.prefix("(result (string-trim", prefix=pre_result))
    pre_trim = lines[-1].find("(string-trim")
    lines.append(info.prefix("(shell-command-to-string shell-cmd))))", prefix=pre_trim))
    lines.append(info.indent("(if (string-empty-p result)", level=2))
    lines.append(info.indent("(message \"Command: %S executed\" command)", level=4))
    lines.append(info.indent("(message \"Command %S executed > %s\" command result))", level=3))
    lines.append(info.indent("result))", level=2))
    return lines


def pre_generator(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=0)
    lines.extend(_package_descriptions(info))
    lines.extend(info.region("Code generated by pyKomorebi.py"))
    lines.extend(_require_packages(info))
    lines.extend(_custom_executable(info))
    lines.extend(_ensure_args_are_string(info))
    lines.extend(_get_args_function(info))
    lines.extend(_execute_command(info))
    lines.extend(info.empty_line(count=2))
    lines.extend(info.region("Generated CLI Commands"))
    lines.extend(info.empty_line(count=2))
    return lines


def post_generator(info: PackageInfo) -> list[str]:
    lines = info.empty_line(count=0)
    lines.append(info.indent(f"(provide '{info.name})"))
    lines.extend(info.comment(f"{info.name}.el ends here", chars=";;;"))
    return lines
