import argparse
import getpass
import hashlib
import json
import os.path
import sys
import typing

from PySide6 import QtCore, QtWidgets
import nacl.exceptions
import nacl.secret

PROGRAM_NAME = 'lock'
DATABASE_PATH = os.path.join(os.path.expanduser('~'), f'.{PROGRAM_NAME}')
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 0


class EntryDoesNotExistError(Exception):
    pass


class EntryExistsError(Exception):
    pass


class PasswordManager:

    def __init__(self, database_path: str, gui: bool, password: str | None = None) -> None:
        self.gui = gui
        if password is None:
            password = getpass.getpass('Database password: ')
            if len(password) == 0:
                print('Database password can not be empty', file=sys.stderr)
                sys.exit(1)
        key = hashlib.blake2b(password.encode(), digest_size=32).digest()
        self.box = nacl.secret.SecretBox(key)
        self.database_path = database_path
        if not os.path.exists(self.database_path):
            print(f'Creating new database {self.database_path}')
            encrypted = self.box.encrypt('{}'.encode())
            with open(self.database_path, 'wb') as file:
                file.write(encrypted)
        with open(self.database_path, 'rb') as file:
            encrypted = file.read()
        plaintext = self.box.decrypt(encrypted)
        self.contents = json.loads(plaintext.decode())

    def read_entry_value(self) -> dict[str, str]:
        entry_value: dict[str, str] = {}
        password = getpass.getpass()
        entry_value['Password'] = password
        while True:
            entry_value_name = input('Enter name (leave empty to exit): ')
            if not entry_value_name:
                break
            if entry_value_name == 'Password':
                print('Password was already added')
                continue
            entry_value_definition = input('Enter definition (leave empty to exit): ')
            if not entry_value_definition:
                break
            entry_value[entry_value_name] = entry_value_definition
        return entry_value

    def create(self, entry_key: str, entry_value: dict[str, str] | None = None) -> None:
        if self.contents.get(entry_key) is not None:
            raise EntryExistsError(entry_key)
        if entry_value is None:
            entry_value = self.read_entry_value()
        self.contents[entry_key] = entry_value
        plaintext = json.dumps(self.contents, separators=(',', ':'), sort_keys=True)
        encrypted = self.box.encrypt(plaintext.encode())
        with open(self.database_path, 'wb') as file:
            file.write(encrypted)

    def read(self, entry_key: str | None = None) -> dict[str, dict[str, str]]:
        if entry_key is None:
            if not self.gui:
                for entry_key, entry_value in self.contents.items():
                    print(f'{entry_key}:')
                    for name, definition in entry_value.items():
                        print(f'    {name}: "{definition}"')
            return self.contents
        else:
            if self.contents.get(entry_key) is None:
                raise EntryDoesNotExistError(entry_key)
            if not self.gui:
                print(f'{entry_key}:')
                for name, definition in self.contents[entry_key].items():
                    print(f'    {name}: "{definition}"')
            return {entry_key: self.contents[entry_key]}

    def update(self, entry_key: str, entry_value: dict[str, str] | None = None) -> None:
        if self.contents.get(entry_key) is None:
            raise EntryDoesNotExistError(entry_key)
        if entry_value is None:
            entry_value = self.read_entry_value()
        self.contents[entry_key] = entry_value
        plaintext = json.dumps(self.contents, separators=(',', ':'), sort_keys=True)
        encrypted = self.box.encrypt(plaintext.encode())
        with open(self.database_path, 'wb') as file:
            file.write(encrypted)

    def delete(self, entry_key: str, interactive: bool = True) -> None:
        if self.contents.get(entry_key) is None:
            raise EntryDoesNotExistError(entry_key)
        if interactive:
            reply = input(f'Are you sure you want to delete an entry {entry_key}? ')
        else:
            reply = 'y'
        match reply.lower():
            case 'yes' | 'y':
                del self.contents[entry_key]
                plaintext = json.dumps(self.contents, separators=(',', ':'), sort_keys=True)
                encrypted = self.box.encrypt(plaintext.encode())
                with open(self.database_path, 'wb') as file:
                    file.write(encrypted)
            case _:
                pass


class CentralWidget(QtWidgets.QWidget):

    def __init__(self, pm: PasswordManager) -> None:
        super().__init__()
        self.pm = pm
        contents = self.pm.read()
        layout = QtWidgets.QVBoxLayout(self)
        for entry_key, entry_value in contents.items():
            group_box = QtWidgets.QGroupBox(entry_key)
            entries_and_buttons = QtWidgets.QVBoxLayout()
            entries = QtWidgets.QVBoxLayout()
            for entry_value_name, entry_value_description in entry_value.items():
                entry = QtWidgets.QHBoxLayout()

                name = QtWidgets.QLineEdit(entry_value_name)
                entry.addWidget(name)

                description = QtWidgets.QLineEdit(entry_value_description)
                buttons = None
                if entry_value_name == 'Password':
                    description.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
                    buttons = QtWidgets.QHBoxLayout()
                    buttons.addStretch()
                    copy = QtWidgets.QPushButton('Copy')
                    def wrapper_copy_password_to_clipboard(password: QtWidgets.QLineEdit) -> typing.Callable[[], None]:
                        return lambda: self.copy_password_to_clipboard(password)
                    copy.clicked.connect(wrapper_copy_password_to_clipboard(description))
                    buttons.addWidget(copy)
                    show = QtWidgets.QPushButton('Show')
                    def wrapper_show_hide_password(password: QtWidgets.QLineEdit) -> typing.Callable[[], None]:
                        return lambda: self.show_hide_password(password)
                    show.clicked.connect(wrapper_show_hide_password(description))
                    buttons.addWidget(show)
                entry.addWidget(description)

                entries.addLayout(entry)
                if buttons is not None:
                    entries.addLayout(buttons)
            entries_and_buttons.addLayout(entries)
            add = QtWidgets.QPushButton('Add')
            def wrapper_add(entries: QtWidgets.QVBoxLayout) -> typing.Callable[[], None]:
                return lambda: self.add(entries)
            add.clicked.connect(wrapper_add(entries))
            entries_and_buttons.addWidget(add, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
            save = QtWidgets.QPushButton('Save')
            def wrapper_save(group_box: QtWidgets.QGroupBox) -> typing.Callable[[], None]:
                return lambda: self.save(group_box)
            save.clicked.connect(wrapper_save(group_box))
            entries_and_buttons.addWidget(save)
            delete = QtWidgets.QPushButton('Delete')
            def wrapper_delete(group_box: QtWidgets.QGroupBox) -> typing.Callable[[], None]:
                return lambda: self.delete(group_box)
            delete.clicked.connect(wrapper_delete(group_box))
            entries_and_buttons.addWidget(delete)
            group_box.setLayout(entries_and_buttons)
            layout.addWidget(group_box)
        self.setLayout(layout)

    @QtCore.Slot()
    def copy_password_to_clipboard(self, password: QtWidgets.QLineEdit) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(password.text())

    @QtCore.Slot()
    def show_hide_password(self, password: QtWidgets.QLineEdit) -> None:
        if password.echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
        else:
            password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

    @QtCore.Slot()
    def add(self, entries: QtWidgets.QVBoxLayout) -> None:
        entry = QtWidgets.QHBoxLayout()
        name = QtWidgets.QLineEdit()
        entry.addWidget(name)
        description = QtWidgets.QLineEdit()
        entry.addWidget(description)
        entries.addLayout(entry)

    @QtCore.Slot()
    def save(self, group_box: QtWidgets.QGroupBox) -> None:
        line_edits = group_box.findChildren(QtWidgets.QLineEdit)
        result = {}
        for i in range(0, len(line_edits), 2):
            result[line_edits[i].text()] = line_edits[i+1].text()
        self.pm.update(group_box.title(), result)

    @QtCore.Slot()
    def delete(self, group_box: QtWidgets.QGroupBox) -> None:
        self.pm.delete(group_box.title(), interactive=False)
        group_box.hide()


class PasswordWindow(QtWidgets.QWidget):

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('Database password')
        self.password.returnPressed.connect(self.run)
        layout.addWidget(self.password)
        self.button = QtWidgets.QPushButton('Continue')
        self.button.clicked.connect(self.run)
        layout.addWidget(self.button)
        self.setLayout(layout)

    @QtCore.Slot()
    def run(self) -> None:
        try:
            pm = PasswordManager(DATABASE_PATH, True, self.password.text())
        except nacl.exceptions.CryptoError:
            self.password.setStyleSheet('background-color: red;')
            return
        self.hide()
        open_main_window(pm)


def open_password_window() -> None:
    global password_window
    password_window = PasswordWindow()
    password_window.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    password_window.setWindowTitle(PROGRAM_NAME)
    password_window.show()


def open_main_window(pm: PasswordManager) -> None:
    global main_window
    main_window = QtWidgets.QMainWindow()
    central_widget = CentralWidget(pm)
    main_window.setCentralWidget(central_widget)
    main_window.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    main_window.setWindowTitle(PROGRAM_NAME)
    main_window.show()


def main() -> None:
    parser = argparse.ArgumentParser(description='lock is a very simple password manager written in Python.')
    parser.add_argument('-g', action='store_true', help='start GUI version of the program')

    subparsers = parser.add_subparsers(dest='subcommand', title='subcommands')

    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('entry')

    parser_read = subparsers.add_parser('read')
    parser_read.add_argument('entry', nargs='?')

    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('entry')

    parser_delete = subparsers.add_parser('delete')
    parser_delete.add_argument('entry')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.g:
        app = QtWidgets.QApplication()
        open_password_window()
        sys.exit(app.exec())

    try:
        pm = PasswordManager(DATABASE_PATH, False)
    except nacl.exceptions.CryptoError:
        print('Decryption failed', file=sys.stderr)
        sys.exit(1)

    match args.subcommand:
        case 'create':
            try:
                pm.create(args.entry)
            except EntryExistsError as e:
                print(f'Entry {e} already exists in the database', file=sys.stderr)
                sys.exit(1)
        case 'read':
            try:
                pm.read(args.entry)
            except EntryDoesNotExistError as e:
                print(f'Entry {e} does not exist in the database', file=sys.stderr)
                sys.exit(1)
        case 'update':
            try:
                pm.update(args.entry)
            except EntryDoesNotExistError as e:
                print(f'Entry {e} does not exist in the database', file=sys.stderr)
                sys.exit(1)
        case 'delete':
            try:
                pm.delete(args.entry)
            except EntryDoesNotExistError as e:
                print(f'Entry {e} does not exist in the database', file=sys.stderr)
                sys.exit(1)
        case _:
            pass


if __name__ == '__main__':
    main()
