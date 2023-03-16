from pathlib import Path
from typing import Callable
import argparse
import secrets
import string
import sys

from PySide6.QtWidgets import QApplication, QLayout, QLineEdit, QWidget


def error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def file_read(file_path: Path) -> bytes:
    with open(file_path, 'rb') as file:
        return file.read()


def file_write(file_path: Path, buffer: bytes) -> None:
    with open(file_path, 'wb') as file:
        file.write(buffer)


def layout_delete(layout: QLayout) -> None:
    for i in reversed(range(layout.count())):
        item = layout.takeAt(i)
        widget = item.widget()
        widget.deleteLater()
    layout.deleteLater()


def line_edit_reset_color(line_edit: QLineEdit) -> Callable[[], None]:
    return lambda: line_edit.setStyleSheet('color: #535353;')


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='lock is a very simple password manager written in Python.')
    subparsers = parser.add_subparsers(dest='subcommand', title='subcommands')
    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('entry')
    parser_read = subparsers.add_parser('read')
    parser_read.add_argument('entry', nargs='?')
    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('entry')
    parser_delete = subparsers.add_parser('delete')
    parser_delete.add_argument('entry')
    return parser.parse_args()


def password_generate(length: int) -> str:
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))


# This function needs to be called after the show() method on a widget. Otherwise
# widget size is reported incorrectly
def widget_center(widget: QWidget) -> None:
    screens = QApplication.screens()
    if len(screens) == 1:
        screen_width = screens[0].availableGeometry().width()
        screen_height = screens[0].availableGeometry().height()

        window_width = widget.frameGeometry().width()
        window_height = widget.frameGeometry().height()

        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        widget.move(x, y)
