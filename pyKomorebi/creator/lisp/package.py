from dataclasses import dataclass
from datetime import datetime

from pyKomorebi.creator.lisp.code import LispCodeFormatter


@dataclass(frozen=True)
class FunctionNames:
    executable_custom_var: str = "executable"
    execute_func_name: str = "execute"
    args_func_name: str = "args-get"

    def executable_var(self, formatter: LispCodeFormatter) -> str:
        return formatter.function_name(self.executable_custom_var)

    def execute_func(self, formatter: LispCodeFormatter) -> str:
        return formatter.function_name(self.execute_func_name)

    def args_func(self, formatter: LispCodeFormatter) -> str:
        return formatter.function_name(self.args_func_name, private=True)


@dataclass
class PackageInfo:
    name: str
    version: str
    repository: str
    user_name: str
    user_email: str
    emacs_version: str
    formatter: LispCodeFormatter

    @property
    def user_and_email(self) -> str:
        return f"{self.user_name} <{self.user_email}>"

    @property
    def modified(self) -> str:
        return datetime.now().strftime("%B %d, %Y")

    @property
    def year(self) -> str:
        return datetime.now().strftime("%Y")

    def indent(self, line: str, level: int = 0) -> str:
        return self.formatter.indent(line, level)


def _package_descriptions(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.append(info.indent(f";;; {info.name}.el --- Description -*- lexical-binding: t; -*-"))
    lines.append(info.indent(";;"))
    lines.append(info.indent(f";; Copyright (C) {info.year} {info.user_name}"))
    lines.append(info.indent(";;"))
    lines.append(info.indent(f";; Author: {info.user_and_email}"))
    lines.append(info.indent(f";; Maintainer: {info.user_and_email}"))
    lines.append(info.indent(";; Created: Oktober 07, 2024"))
    lines.append(info.indent(f";; Modified: {info.modified}"))
    lines.append(info.indent(f";; Version: {info.version}"))
    lines.append(info.indent(";; Keywords: docs emulations extensions help languages lisp local processes"))
    lines.append(info.indent(f";; Homepage: {info.repository}"))
    lines.append(info.indent(f';; Package-Requires: ((emacs "{info.emacs_version}"))'))
    lines.append(info.indent(";;"))
    lines.append(info.indent(";; This file is not part of GNU Emacs."))
    lines.append(info.indent(";;"))
    lines.append(info.indent(";;; Commentary:"))
    lines.append(info.indent(";;"))
    lines.append(info.indent(";;  Description"))
    lines.append(info.indent(";;"))
    lines.append(info.indent(";;; Code:"))
    lines.extend(info.formatter.empty_line())
    return lines


def require_packages(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=1)
    lines.append(info.indent("(require 'cl-lib)"))
    return lines


def _executable_var(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.executable_var(info.formatter)


def _custom_executable(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=1)
    lines.append(info.indent(f"(defcustom {_executable_var(info)} \"\"", level=0))
    lines.append(info.indent("\"The path to the komorebi executable.\"", level=1))
    lines.append(info.indent(":type 'string", level=1))
    lines.append(info.indent(f":group '{info.name})", level=1))
    return lines


def _args_func(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.args_func(info.formatter)


def _get_args_function(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=1)
    lines.append(info.indent(f"(defun {_args_func(info)} (args)", level=0))
    lines.append(info.indent("\"Return string of ARGS.\"", level=1))
    lines.append(info.indent("(string-join", level=1))
    lines.append(info.indent("(seq-filter (lambda (arg) (not (or (null arg) (string-empty-p arg)))) args)", level=2))
    lines.append(info.indent('" "))', level=2))
    return lines


def execute_func_name(formatter: LispCodeFormatter) -> str:
    func_names = FunctionNames()
    return func_names.execute_func(formatter)


def execute_func(info: PackageInfo) -> str:
    return execute_func_name(info.formatter)


def _execute_command(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.append(info.indent(f"(defun {_args_func(info)} (args)", level=0))
    lines.append(info.indent(f"(defun {execute_func(info)} (command &rest args)", level=0))
    lines.append(info.indent("\"Execute komorebi COMMAND with ARGS in shell.\"", level=1))
    lines.append(info.indent("(let ((shell-cmd (format \"%s %s %s\"", level=1))
    lines.append(info.indent(f"      (shell-quote-argument {_executable_var(info)})", level=2))
    lines.append(info.indent("      command", level=2))
    lines.append(info.indent(f"      ({_args_func(info)} args))))", level=2))
    lines.append(info.indent("(let ((result (shell-command-to-string shell-cmd)))", level=1))
    lines.append(info.indent("(message \"Result %S of Command: %S\" shell-cmd result)", level=2))
    lines.append(info.indent("result)))", level=1))
    return lines


def pre_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.extend(_package_descriptions(info))
    lines.append(";; Code generated by pyKomorebi.py")
    lines.extend(require_packages(info))
    lines.extend(_custom_executable(info))
    lines.extend(_get_args_function(info))
    lines.extend(_execute_command(info))
    lines.extend(info.formatter.empty_line(count=2))
    return lines


def post_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.append(info.indent(f"(provide '{info.name})"))
    lines.append(info.indent(f";;; {info.name}.el ends here"))
    return lines
