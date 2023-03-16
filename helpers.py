import argparse
import secrets
import string
import sys

from PySide6.QtWidgets import QApplication, QWidget


def error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


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


def password_generate(length: int, *, lowercase: bool = False,
                      uppercase: bool = False, digits: bool = False,
                      punctuation: bool = False) -> str:
    characters = ''
    password = [''] * length
    password_indices = list(range(length))

    if lowercase:
        characters += string.ascii_lowercase

        password_index = secrets.choice(password_indices)
        password_indices.pop(password_indices.index(password_index))
        password[password_index] = secrets.choice(string.ascii_lowercase)

    if uppercase:
        characters += string.ascii_uppercase

        password_index = secrets.choice(password_indices)
        password_indices.pop(password_indices.index(password_index))
        password[password_index] = secrets.choice(string.ascii_uppercase)

    if digits:
        characters += string.digits

        password_index = secrets.choice(password_indices)
        password_indices.pop(password_indices.index(password_index))
        password[password_index] = secrets.choice(string.digits)

    if punctuation:
        characters += string.punctuation

        password_index = secrets.choice(password_indices)
        password_indices.pop(password_indices.index(password_index))
        password[password_index] = secrets.choice(string.punctuation)

    if not characters:
        characters = (string.ascii_lowercase
            + string.ascii_uppercase
            + string.digits
            + string.punctuation)

    return ''.join(secrets.choice(characters) if not c else c for c in password)


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
