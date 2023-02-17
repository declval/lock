import getpass
import hashlib
import json
import os.path
import sys
import typing

from PySide6 import QtCore, QtGui, QtWidgets
import nacl.exceptions
import nacl.secret

from helpers import error, file_read, file_write, layout_delete, parse_arguments

PROGRAM_NAME = 'lock'

DATABASE_PATH = os.path.join(os.path.expanduser('~'), f'.{PROGRAM_NAME}')
STYLESHEET_PATH = os.path.join(os.path.dirname(__file__), 'stylesheet.css')
FONT_PATH = os.path.join(os.path.dirname(__file__), 'Roboto-Regular.ttf')

JSON_SEPARATORS = (',', ':')
JSON_SORT_KEYS = True


class EntryDoesNotExistError(Exception):
    pass


class EntryExistsError(Exception):
    pass


class PasswordManager:

    def __init__(self, database_path: str, gui: bool, password: str | None = None) -> None:
        self.database_path = database_path
        self.gui = gui
        if password is None:
            password = getpass.getpass('Database password: ')
            if len(password) == 0:
                error('Database password can not be empty')
        key = hashlib.blake2b(password.encode(), digest_size=32).digest()
        self.box = nacl.secret.SecretBox(key)
        if not os.path.exists(self.database_path):
            print(f'Creating new database {self.database_path}')
            ciphertext = self.encrypt('{}')
            file_write(self.database_path, ciphertext)
        ciphertext = file_read(self.database_path)
        plaintext = self.decrypt(ciphertext)
        self.contents = json.loads(plaintext)

    def encrypt(self, plaintext: str) -> bytes:
        return self.box.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        return self.box.decrypt(ciphertext).decode()

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

    def create(self, entry_name: str, entry_value: dict[str, str] | None = None) -> None:
        if self.contents.get(entry_name) is not None:
            raise EntryExistsError(entry_name)
        if entry_value is None:
            entry_value = self.read_entry_value()
        self.contents[entry_name] = entry_value
        plaintext = json.dumps(self.contents, separators=JSON_SEPARATORS, sort_keys=JSON_SORT_KEYS)
        ciphertext = self.encrypt(plaintext)
        file_write(self.database_path, ciphertext)

    def read(self, entry_name: str | None = None) -> dict[str, dict[str, str]]:
        if entry_name is None:
            if not self.gui:
                for entry_name, entry_value in self.contents.items():
                    print(f'{entry_name}:')
                    for name, definition in entry_value.items():
                        print(f'    {name}: "{definition}"')
            return self.contents
        else:
            if self.contents.get(entry_name) is None:
                raise EntryDoesNotExistError(entry_name)
            if not self.gui:
                print(f'{entry_name}:')
                for name, definition in self.contents[entry_name].items():
                    print(f'    {name}: "{definition}"')
            return {entry_name: self.contents[entry_name]}

    def update(self, entry_name: str, entry_value: dict[str, str] | None = None) -> None:
        if self.contents.get(entry_name) is None:
            raise EntryDoesNotExistError(entry_name)
        if entry_value is None:
            if self.gui:
                raise ValueError(entry_value)
            entry_value = self.read_entry_value()
        self.contents[entry_name] = entry_value
        plaintext = json.dumps(self.contents, separators=JSON_SEPARATORS, sort_keys=JSON_SORT_KEYS)
        ciphertext = self.encrypt(plaintext)
        file_write(self.database_path, ciphertext)

    def delete(self, entry_name: str, interactive: bool = True) -> None:
        if self.contents.get(entry_name) is None:
            raise EntryDoesNotExistError(entry_name)
        if interactive:
            reply = input(f'Are you sure you want to delete an entry {entry_name}? ')
        else:
            reply = 'y'
        match reply.lower():
            case 'yes' | 'y':
                del self.contents[entry_name]
                plaintext = json.dumps(self.contents, separators=JSON_SEPARATORS, sort_keys=JSON_SORT_KEYS)
                ciphertext = self.encrypt(plaintext)
                file_write(self.database_path, ciphertext)
            case _:
                pass


class CentralWidget(QtWidgets.QWidget):

    def __init__(self, pm: PasswordManager) -> None:
        super().__init__()
        self.pm = pm
        self.contents = self.pm.read()
        self.plus_icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'plus-solid.svg'))
        self.minus_icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'minus-solid.svg'))
        layout = QtWidgets.QVBoxLayout()
        create_layout = QtWidgets.QHBoxLayout()
        create_name = QtWidgets.QLineEdit()
        create_name.setPlaceholderText('New entry name')
        def wrapper_create_new_entry(create_name: QtWidgets.QLineEdit) -> typing.Callable[[], None]:
            return lambda: self.create_new_entry(create_name)
        create_name.returnPressed.connect(wrapper_create_new_entry(create_name))
        create_layout.addWidget(create_name)
        create_button = QtWidgets.QPushButton('Create')
        create_button.setProperty('class', 'button-alt')
        create_button.clicked.connect(wrapper_create_new_entry(create_name))
        create_layout.addWidget(create_button)
        layout.addLayout(create_layout)
        for entry_name, entry_value in self.contents.items():
            entry = self.create_entry(entry_name, entry_value)
            layout.addWidget(entry)
        self.setLayout(layout)

    def create_entry(self, entry_name: str, entry_value: dict[str, str]) -> QtWidgets.QGroupBox:
        entry = QtWidgets.QGroupBox(entry_name)
        entry_layout = QtWidgets.QVBoxLayout()
        field_pairs_layout = QtWidgets.QVBoxLayout()
        for entry_value_name, entry_value_definition in entry_value.items():
            field_pair_layout = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLineEdit(entry_value_name)
            field_pair_layout.addWidget(name)
            definition = QtWidgets.QLineEdit(entry_value_definition)
            buttons_layout = None
            if entry_value_name == 'Password':
                name.setReadOnly(True)
                definition.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
                buttons_layout = QtWidgets.QHBoxLayout()
                buttons_layout.addStretch()
                copy = QtWidgets.QPushButton('Copy')
                def wrapper_copy_password_to_clipboard(password: QtWidgets.QLineEdit) -> typing.Callable[[], None]:
                    return lambda: self.copy_password_to_clipboard(password)
                copy.clicked.connect(wrapper_copy_password_to_clipboard(definition))
                buttons_layout.addWidget(copy)
                show = QtWidgets.QPushButton('Show')
                def wrapper_show_hide_password(password: QtWidgets.QLineEdit) -> typing.Callable[[], None]:
                    return lambda: self.show_hide_password(password)
                show.clicked.connect(wrapper_show_hide_password(definition))
                buttons_layout.addWidget(show)
                buttons_layout.addSpacing(38)
            field_pair_layout.addWidget(definition)
            if entry_value_name == 'Password':
                field_pair_layout.addSpacing(38)
            else:
                minus = QtWidgets.QPushButton()
                minus.setIcon(self.minus_icon)
                minus.setIconSize(QtCore.QSize(12, 12))
                minus.setProperty('class', 'button-icon-only')
                def wrapper_minus(field_pair_layout: QtWidgets.QHBoxLayout) -> typing.Callable[[], None]:
                    return lambda: self.minus(field_pair_layout)
                minus.clicked.connect(wrapper_minus(field_pair_layout))
                field_pair_layout.addWidget(minus)
            field_pairs_layout.addLayout(field_pair_layout)
            if buttons_layout is not None:
                field_pairs_layout.addLayout(buttons_layout)
        entry_layout.addLayout(field_pairs_layout)
        plus = QtWidgets.QPushButton()
        plus.setIcon(self.plus_icon)
        plus.setIconSize(QtCore.QSize(12, 12))
        plus.setProperty('class', 'button-icon-only')
        def wrapper_plus(field_pairs_layout: QtWidgets.QVBoxLayout) -> typing.Callable[[], None]:
            return lambda: self.plus(field_pairs_layout)
        plus.clicked.connect(wrapper_plus(field_pairs_layout))
        entry_layout.addWidget(plus, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        save = QtWidgets.QPushButton('Save')
        def wrapper_save(entry: QtWidgets.QGroupBox) -> typing.Callable[[], None]:
            return lambda: self.save(entry)
        save.clicked.connect(wrapper_save(entry))
        entry_layout.addWidget(save)
        delete = QtWidgets.QPushButton('Delete')
        delete.setProperty('class', 'button-warn')
        def wrapper_delete(entry: QtWidgets.QGroupBox) -> typing.Callable[[], None]:
            return lambda: self.delete(entry)
        delete.clicked.connect(wrapper_delete(entry))
        entry_layout.addWidget(delete)
        # Necessary to get rid of UI flicker when fields are removed with the minus button
        entry_layout.addStretch()
        entry.setLayout(entry_layout)
        return entry

    @QtCore.Slot()
    def copy_password_to_clipboard(self, password: QtWidgets.QLineEdit) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(password.text())

    @QtCore.Slot()
    def create_new_entry(self, create_name: QtWidgets.QLineEdit) -> None:
        entry_name = create_name.text()
        if not entry_name or entry_name in self.contents:
            create_name.setStyleSheet('background-color: #d61c54;')
            return
        create_name.setStyleSheet('background-color: #ffffff;')
        self.contents[entry_name] = {'Password': ''}
        group_box = self.create_entry(entry_name, self.contents[entry_name])
        self.layout().addWidget(group_box)

    @QtCore.Slot()
    def delete(self, group_box: QtWidgets.QGroupBox) -> None:
        self.pm.delete(group_box.title(), interactive=False)
        group_box.deleteLater()

    @QtCore.Slot()
    def minus(self, field_pair_layout: QtWidgets.QHBoxLayout) -> None:
        layout_delete(field_pair_layout)

    @QtCore.Slot()
    def plus(self, field_pairs_layout: QtWidgets.QVBoxLayout) -> None:
        field_pair_layout = QtWidgets.QHBoxLayout()
        name = QtWidgets.QLineEdit()
        name.setPlaceholderText('Name')
        field_pair_layout.addWidget(name)
        definition = QtWidgets.QLineEdit()
        definition.setPlaceholderText('Definition')
        field_pair_layout.addWidget(definition)
        minus = QtWidgets.QPushButton()
        minus.setIcon(self.minus_icon)
        minus.setIconSize(QtCore.QSize(12, 12))
        minus.setProperty('class', 'button-icon-only')
        def wrapper_minus(field_pair_layout: QtWidgets.QHBoxLayout) -> typing.Callable[[], None]:
            return lambda: self.minus(field_pair_layout)
        minus.clicked.connect(wrapper_minus(field_pair_layout))
        field_pair_layout.addWidget(minus)
        field_pairs_layout.addLayout(field_pair_layout)

    @QtCore.Slot()
    def save(self, group_box: QtWidgets.QGroupBox) -> None:
        line_edits = group_box.findChildren(QtWidgets.QLineEdit)
        result = {}
        for i in range(0, len(line_edits), 2):
            name = line_edits[i]
            definition = line_edits[i+1]
            if len(name.text()) == 0:
                name.setStyleSheet('background-color: #d61c54;')
            if len(definition.text()) == 0:
                definition.setStyleSheet('background-color: #d61c54;')
            if name.text() and definition.text():
                result[name.text()] = definition.text()
        if 'Password' not in result:
            return
        try:
            self.pm.update(group_box.title(), result)
        except EntryDoesNotExistError:
            self.pm.create(group_box.title(), result)

    @QtCore.Slot()
    def show_hide_password(self, password: QtWidgets.QLineEdit) -> None:
        if password.echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
        else:
            password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)


class PasswordWindow(QtWidgets.QWidget):

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('Database password')
        self.password.returnPressed.connect(self.run)
        layout.addWidget(self.password)
        button = QtWidgets.QPushButton('Continue')
        button.setProperty('class', 'button-alt')
        button.clicked.connect(self.run)
        layout.addWidget(button)
        self.setLayout(layout)

    @QtCore.Slot()
    def run(self) -> None:
        try:
            pm = PasswordManager(DATABASE_PATH, True, self.password.text())
        except nacl.exceptions.CryptoError:
            self.password.setStyleSheet('background-color: #d61c54;')
            return
        self.hide()
        open_main_window(pm)


def open_password_window() -> None:
    global password_window
    password_window = PasswordWindow()
    password_window.setWindowTitle(PROGRAM_NAME)
    password_window.show()


def open_main_window(pm: PasswordManager) -> None:
    global main_window
    main_window = QtWidgets.QMainWindow()
    main_window.layout().setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
    central_widget = CentralWidget(pm)
    main_window.setCentralWidget(central_widget)
    main_window.setWindowTitle(PROGRAM_NAME)
    main_window.show()


def main() -> None:
    args = parse_arguments()

    if len(sys.argv) == 1:
        app = QtWidgets.QApplication()
        QtGui.QFontDatabase.addApplicationFont(FONT_PATH)
        stylesheet = file_read(STYLESHEET_PATH).decode()
        app.setStyleSheet(stylesheet)
        open_password_window()
        sys.exit(app.exec())

    try:
        pm = PasswordManager(DATABASE_PATH, False)
    except nacl.exceptions.CryptoError:
        error('Decryption failed')

    match args.subcommand:
        case 'create':
            try:
                pm.create(args.entry)
            except EntryExistsError as e:
                error(f'Entry {e} already exists in the database')
        case 'read':
            try:
                pm.read(args.entry)
            except EntryDoesNotExistError as e:
                error(f'Entry {e} does not exist in the database')
        case 'update':
            try:
                pm.update(args.entry)
            except EntryDoesNotExistError as e:
                error(f'Entry {e} does not exist in the database')
        case 'delete':
            try:
                pm.delete(args.entry)
            except EntryDoesNotExistError as e:
                error(f'Entry {e} does not exist in the database')
        case _:
            pass


if __name__ == '__main__':
    main()
