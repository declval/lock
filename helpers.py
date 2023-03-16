from pathlib import Path
import argparse
import sys

from PySide6.QtWidgets import QLayout


def layout_delete(layout: QLayout) -> None:
    for i in reversed(range(layout.count())):
        item = layout.takeAt(i)
        widget = item.widget()
        widget.deleteLater()
    layout.deleteLater()


def error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def file_read(file_path: Path) -> bytes:
    with open(file_path, 'rb') as file:
        return file.read()


def file_write(file_path: Path, buffer: bytes) -> None:
    with open(file_path, 'wb') as file:
        file.write(buffer)


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