from pathlib import Path
import getpass
import hashlib
import json
import sys

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from nacl.exceptions import CryptoError
from nacl.secret import SecretBox

from helpers import error, file_read, file_write, parse_arguments

PROGRAM_NAME = 'lock'

PROGRAM_DIR_PATH = Path(__file__).parent
PROGRAM_ICON_PATH = PROGRAM_DIR_PATH / 'icon.png'
DATABASE_PATH = Path.home() / f'.{PROGRAM_NAME}'
STYLESHEET_PATH = PROGRAM_DIR_PATH / 'stylesheet.css'
FONT_PATH = PROGRAM_DIR_PATH / 'Roboto-Regular.ttf'

JSON_SEPARATORS = (',', ':')
JSON_SORT_KEYS = True

STATUSBAR_TIMEOUT = 4000

WINDOW_WIDTH = 450
WINDOW_HEIGHT = 450


class EntryDoesNotExistError(Exception):
    pass


class EntryExistsError(Exception):
    pass


class PasswordManager:

    def __init__(self, database_path: Path, gui: bool, password: str | None = None) -> None:
        self.database_path = database_path
        self.gui = gui
        if password is None:
            password = getpass.getpass('Database password: ')
            if len(password) == 0:
                error('Database password can not be empty')
        key = hashlib.blake2b(password.encode(), digest_size=32).digest()
        self.box = SecretBox(key)
        if not self.database_path.exists():
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


def main() -> None:
    args = parse_arguments()

    if len(sys.argv) == 1:
        # Importing module widgets here to avoid circular dependencies when running tests
        import widgets

        app = QApplication()
        QFontDatabase.addApplicationFont(str(FONT_PATH))
        stylesheet = file_read(STYLESHEET_PATH).decode()
        app.setStyleSheet(stylesheet)
        password_widget = widgets.PasswordWidget()
        password_widget.show()
        sys.exit(app.exec())

    pm: PasswordManager | None = None

    try:
        pm = PasswordManager(DATABASE_PATH, False)
    except CryptoError:
        error('Decryption failed')

    assert pm is not None

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
