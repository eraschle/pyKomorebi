from dataclasses import dataclass
from datetime import datetime


from pyKomorebi import utils
from pyKomorebi.creator.code import ICodeFormatter


@dataclass(frozen=True)
class FunctionNames:
    executable_custom_var: str = "executable"
    execute_func_name: str = "execute"
    args_func_name: str = "args-get"
    get_path_func_name: str = "path-get"
    config_home_func_name: str = "config-home"

    def executable_var(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.executable_custom_var)

    def execute_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.execute_func_name, private=True)

    def args_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.args_func_name, private=True)

    def config_home_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.config_home_func_name, private=True)

    def get_path_func(self, formatter: ICodeFormatter) -> str:
        return formatter.function_name(self.get_path_func_name, private=True)


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

    def indent(self, line: str, level: int = 0) -> str:
        return self.formatter.indent(line, level)

    def prefix(self, line: str, prefix: int) -> str:
        column = self.formatter.column_prefix(prefix)
        return utils.as_string(column, line, separator=" ")


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
    lines = info.formatter.empty_line(count=2)
    lines.append(info.indent(f"(defcustom {_executable_var(info)} \"\"", level=0))
    lines.append(info.indent("\"The path to the komorebi executable.\"", level=1))
    lines.append(info.indent(":type 'string", level=1))
    lines.append(info.indent(f":group '{info.name})", level=1))
    return lines


def _args_func(info: PackageInfo) -> str:
    func_names = FunctionNames()
    return func_names.args_func(info.formatter)


def _get_args_function(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=2)
    lines.append(info.indent(f"(defun {_args_func(info)} (args)", level=0))
    lines.append(info.indent("\"Return string of ARGS.\"", level=1))
    lines.append(info.indent("(string-join", level=1))
    lines.append(info.indent("(seq-filter (lambda (arg) (not (or (null arg) (string-empty-p arg)))) args)", level=2))
    lines.append(info.indent('" "))', level=2))
    return lines


def execute_func_name(formatter: ICodeFormatter) -> str:
    func_names = FunctionNames()
    return func_names.execute_func(formatter)


def execute_func(info: PackageInfo) -> str:
    return execute_func_name(info.formatter)


def _execute_command(info: PackageInfo) -> list[str]:
    exe_path = _executable_var(info)
    lines = info.formatter.empty_line(count=2)
    lines.append(info.indent(f"(defun {execute_func(info)} (command &rest args)", level=0))
    lines.append(info.indent("\"Execute komorebi COMMAND with ARGS in shell.\"", level=1))
    lines.append(info.indent("(let ((shell-cmd (format \"%s %s %s\"", level=1))
    prefix = lines[-1].find("\"%s %s %s\"") - 1
    lines.append(info.prefix(f"(shell-quote-argument {exe_path})", prefix=prefix))
    lines.append(info.prefix("command", prefix=prefix))
    lines.append(info.prefix(f"({_args_func(info)} args))))", prefix=prefix))
    lines.append(info.indent("(let ((result (string-trim (shell-command-to-string shell-cmd))))", level=2))
    lines.append(info.indent("(if (string-empty-p result)", level=3))
    lines.append(info.indent("(message \"Command: %S executed\" command)", level=5))
    lines.append(info.indent("(message \"Command %S executed > %s\" command result))", level=4))
    lines.append(info.indent("result)))", level=3))
    return lines


def get_path_func(formatter: ICodeFormatter) -> str:
    func_names = FunctionNames()
    return func_names.get_path_func(formatter)


def _get_path_function(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=2)
    lines.append(info.indent(f"(defun {get_path_func(info.formatter)} (current-path)", level=0))
    lines.append(info.indent("\"Return the CURRENT-PATH with slashes instead of backslashes.\"", level=1))
    lines.append(info.indent("(let ((path (string-replace \"\\\\\" \"/\" current-path)))", level=1))
    lines.append(info.indent("(unless (string-suffix-p \"/\" path)", level=2))
    lines.append(info.indent("(setq path (concat path \"/\")))", level=3))
    lines.append(info.indent("path))", level=2))
    return lines


def config_home_func(formatter: ICodeFormatter) -> str:
    func_names = FunctionNames()
    return func_names.config_home_func(formatter)


def _config_home_function(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=2)
    lines.append(info.indent(f"(defun {config_home_func(info.formatter)} ()", level=0))
    lines.append(info.indent("\"Return the path to the komorebi configuration folder or nil.\"", level=1))
    lines.append(info.indent("(let ((config-path (getenv \"KOMOREBI_CONFIG_HOME\"))", level=1))
    prefix = lines[-1].find("(config-path") - 1
    lines.append(info.prefix("(user-profile (getenv \"USERPROFILE\")))", prefix=prefix))
    lines.append(info.indent("(if (and config-path (file-directory-p config-path))", level=2))
    func_name = get_path_func(info.formatter)
    lines.append(info.indent(f"({func_name} config-path)", level=4))
    lines.append(
        info.indent("(setq config-path (concat user-profile \".config\" \".komorebi\"))", level=3)
    )
    lines.append(info.indent("(if (file-directory-p config-path)", level=3))
    lines.append(info.indent(f"({func_name} config-path)", level=5))
    lines.append(info.indent("nil))))", level=4))
    return lines


def pre_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.extend(_package_descriptions(info))
    lines.append(";; Code generated by pyKomorebi.py")
    lines.extend(_custom_executable(info))
    lines.extend(_get_args_function(info))
    lines.extend(_execute_command(info))
    lines.extend(_get_path_function(info))
    lines.extend(_config_home_function(info))
    lines.extend(info.formatter.empty_line(count=2))
    lines.append(";;")
    lines.append(";;; Generated CLI Commands")
    return lines


def post_generator(info: PackageInfo) -> list[str]:
    lines = info.formatter.empty_line(count=0)
    lines.append(info.indent(f"(provide '{info.name})"))
    lines.append(info.indent(f";;; {info.name}.el ends here"))
    return lines
