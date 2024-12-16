from datetime import datetime
from pyKomorebi.generator import AGenerator, Options
from pyKomorebi.model import ApiCommand, CommandArgs
from pyKomorebi import utils


class LispGenerator(AGenerator):
    name_replacement = [" ", "_"]

    def __init__(self, options: Options):
        super().__init__(options=options, extension=".el", indent="  ")
        self.lisp_module = ""
        if self.options.export_path is not None:
            self.lisp_module = self.options.export_path.with_suffix("").name

    def _lisp_name(self, name: str) -> str:
        for char in self.name_replacement:
            name = name.replace(char, "-")
        return name

    def is_interactive(self, command: ApiCommand) -> bool:
        return len(command.arguments) == 0

    def _function_name(self, name: str, private: bool = False) -> str:
        names = [self.lisp_module]
        if private:
            name = f"-{name}"
        names.append(name)
        return "-".join(names)

    def _arguments_names(self, command: ApiCommand) -> str:
        if len(command.arguments) == 0:
            return ""
        args = [self._lisp_name(arg.name.lower()) for arg in command.arguments]
        return " ".join(args)

    def _arguments(self, command: ApiCommand) -> str:
        if len(command.arguments) == 0:
            return ""
        arg_str = self._arguments_names(command)
        return f"&key {arg_str}"

    def _name_and_description(self, args: CommandArgs, max_length: int) -> list[str]:
        with_default = len(args.full_name(with_default=True)) <= max_length
        values = [args.full_name(with_default)]
        values.append(args.description(not with_default))
        return utils.concat_values(values, max_length, separator=" ")

    def _possible_values(self, args: CommandArgs, max_length: int) -> list[str]:
        if len(args.possible_values) == 0:
            return []
        values = utils.concat_values(args.possible_values, max_length, separator=",")
        if len(values) == 1:
            line = f"Possible values: {values[0]}"
            if len(line) <= max_length:
                return [line]
        values = ["Possible values:"] + values
        return utils.concat_values(values, max_length, separator=",")

    def _options_docstring(self, command: ApiCommand, max_length: int) -> list[str]:
        doc_lines = []
        for opt in command.options:
            values = self._name_and_description(opt, max_length)
            values = utils.replace_double_quotes(values)
            values.extend(self._possible_values(opt, max_length))
            doc_lines.append(self._line("\n".join(values), level=0))
        return utils.clean_none_or_empty(doc_lines, strip=True)

    def _argument_docstring(self, command: ApiCommand, max_length: int) -> list[str]:
        doc_lines = []
        for arg in command.arguments:
            values = self._name_and_description(arg, max_length)
            values = utils.replace_double_quotes(values)
            values.extend(self._possible_values(arg, max_length))
            doc_lines.append(self._line("\n".join(values), level=0))
        return utils.clean_none_or_empty(doc_lines, strip=True)

    def _command_docstring(self, command: ApiCommand, max_length: int) -> list[str]:
        doc_lines = []
        command_doc_lines = utils.ensure_max_length(command.description, max_length, split=" ")
        command_doc_lines = utils.replace_double_quotes(command_doc_lines)
        for idx, line in enumerate(command_doc_lines):
            if idx == 0:
                doc_lines.append(self._line(f'"{line}', level=1))
            elif len(line) == 0:
                continue
            else:
                doc_lines.append(self._line(line, level=0))
        return doc_lines

    def _docstring(self, command: ApiCommand, max_length: int) -> list[str]:
        doc_lines = self._command_docstring(command, max_length)
        if len(command.arguments) > 0:
            doc_lines.append("")
            doc_lines.append(self._line("Arguments:", level=0))
            doc_lines.extend(self._argument_docstring(command, max_length))
        if len(command.options) > 0:
            doc_lines.append("")
            doc_lines.append(self._line("Options:", level=0))
            doc_lines.extend(self._options_docstring(command, max_length))
        doc_lines = utils.clean_none_or_empty(doc_lines, strip=False)
        doc_lines[-1] = f'{doc_lines[-1]}"'
        return doc_lines

    def _command_call(self, command: ApiCommand) -> str:
        args = self._arguments_names(command)
        return f'({self.lisp_execute_func} "{command.name}" {args})'

    def _lisp_code_descriptions(self) -> list[str]:
        user_name = "Erich Raschle"
        user_and_email = f"{user_name} <erichraschle@gmail.com>"
        repository = "https://github.com/elyo/komorebi.el"
        modified = datetime.now().strftime("%B %d, %Y")
        year = datetime.now().strftime("%Y")
        package_version = "0.0.1"
        emacs_version = "28.1"
        lines = []
        lines.append(self._line(f";;; {self.lisp_module}.el --- Description -*- lexical-binding: t; -*-", level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(f";; Copyright (C) {year} {user_name}", level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(f";; Author: {user_and_email}", level=0))
        lines.append(self._line(f";; Maintainer: {user_and_email}", level=0))
        lines.append(self._line(";; Created: Oktober 07, 2024", level=0))
        lines.append(self._line(f";; Modified: {modified}", level=0))
        lines.append(self._line(f";; Version: {package_version}", level=0))
        lines.append(self._line(";; Keywords: docs emulations extensions help languages lisp local processes", level=0))
        lines.append(self._line(f";; Homepage: {repository}", level=0))
        lines.append(self._line(f';; Package-Requires: ((emacs "{emacs_version}"))', level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(";; This file is not part of GNU Emacs.", level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(";;; Commentary:", level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(";;  Description", level=0))
        lines.append(self._line(";;", level=0))
        lines.append(self._line(";;; Code:", level=0))
        return lines

    @property
    def executable_name(self) -> str:
        return self._function_name("executable", private=False)

    def _lisp_custom_executable(self) -> list[str]:
        lines = []
        lines.append(self._line(f'(defcustom {self.executable_name} ""', level=0))
        lines.append(self._line('"The path to the komorebi executable."', level=1))
        lines.append(self._line(":type 'string", level=1))
        lines.append(self._line(f":group '{self.lisp_module})", level=1))
        return lines

    @property
    def lisp_args_func(self) -> str:
        return self._function_name("args-get", private=True)

    def _lisp_args_function(self) -> list[str]:
        lines = []
        lines.append(self._line(f"(defun {self.lisp_args_func} (args)", level=0))
        lines.append(self._line('"Return string of ARGS."', level=1))
        lines.append(self._line("(string-join", level=1))
        lines.append(self._line("(seq-filter (lambda (arg) (not (or (null arg) (string-empty-p arg)))) args)", level=2))
        lines.append(self._line('" "))', level=2))
        return lines

    @property
    def lisp_execute_func(self) -> str:
        return self._function_name("execute", private=True)

    def _lisp_komorebi_execute(self) -> list[str]:
        func_name = self._function_name("execute", private=True)
        lines = []
        lines.append(self._line(f"(defun {func_name} (command &rest args)", level=0))
        lines.append(self._line('"Execute komorebi COMMAND with ARGS in shell."', level=1))
        lines.append(self._line('(let ((shell-cmd (format "%s %s %s"', level=1))
        lines.append(self._line(f"      (shell-quote-argument {self.executable_name})", level=2))
        lines.append(self._line("      command", level=2))
        lines.append(self._line(f"      ({self.lisp_args_func} args))))", level=2))
        lines.append(self._line("(let ((result (shell-command-to-string shell-cmd)))", level=1))
        lines.append(self._line('(message "Executing: %s\\n%s" shell-cmd result)', level=2))
        lines.append(self._line("result)))", level=1))
        return lines

    def pre_generator(self, code_lines: list[str]) -> list[str]:
        lines = []
        lines.extend(self._lisp_code_descriptions())
        lines.append("")
        lines.append(";; Code generated by pyKomorebi.py")
        lines.append("")
        lines.extend(self._lisp_custom_executable())
        lines.append("")
        lines.extend(self._lisp_args_function())
        lines.append("")
        lines.extend(self._lisp_komorebi_execute())
        lines.append("")
        lines.extend(code_lines)
        return lines

    def generate(self, command: ApiCommand, max_length: int = 80) -> list[str]:
        lines = []
        func_args = self._arguments(command)
        func_name = self._function_name(command.name, self.is_interactive(command))
        if self.is_interactive(command):
            lines.append(self._line(";;;###autoload", level=1))
        lines.append(self._line(f'(cl-defun {func_name} ({func_args})', level=0))
        lines.extend(self._docstring(command, max_length))
        if self.is_interactive(command):
            lines.append(self._line("(interactive)", level=1))
        cmd_line = self._command_call(command) + ")"
        lines.append(self._line(cmd_line, level=1))
        return lines

    def post_generator(self, code_lines: list[str]) -> list[str]:
        code_lines.append(self._line("", level=0))
        code_lines.append(self._line(f"(provide '{self.lisp_module})", level=0))
        code_lines.append(self._line(f";;; {self.lisp_module}.el ends here", level=0))
        return code_lines
