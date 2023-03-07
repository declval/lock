from getpass import getpass
from pathlib import Path
import hashlib
import json
import sys

from PySide6.QtCore import QFile, QIODevice, QTextStream
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from nacl.exceptions import CryptoError
from nacl.secret import SecretBox

from helpers import error, parse_arguments, widget_center
import resources_rc as _

PROGRAM_NAME = 'lock'

PROGRAM_DIR_PATH = Path(__file__).parent
DATABASE_PATH = Path.home() / f'.{PROGRAM_NAME}'
STYLESHEET_PATH = PROGRAM_DIR_PATH / 'stylesheet.qss'

JSON_SEPARATORS = (',', ':')
JSON_SORT_KEYS = True


class PasswordManager:

    def __init__(self, database_path: Path, password: str) -> None:
        self.database_path = database_path
        key = hashlib.blake2b(password.encode(), digest_size=32).digest()
        self.box = SecretBox(key)
        if not self.database_path.exists():
            ciphertext = self.encrypt('{}')
            self.write(ciphertext)
        ciphertext = self.read()
        plaintext = self.decrypt(ciphertext)
        self.contents = json.loads(plaintext)

    def __getitem__(self, key: str) -> dict[str, str]:
        return self.contents[key]

    def __setitem__(self, key: str, value: dict[str, str]) -> None:
        self.contents[key] = value
        plaintext = json.dumps(self.contents, separators=JSON_SEPARATORS, sort_keys=JSON_SORT_KEYS)
        ciphertext = self.encrypt(plaintext)
        self.write(ciphertext)

    def __delitem__(self, key):
        del self.contents[key]
        plaintext = json.dumps(self.contents, separators=JSON_SEPARATORS, sort_keys=JSON_SORT_KEYS)
        ciphertext = self.encrypt(plaintext)
        self.write(ciphertext)

    def __iter__(self):
        for entry_name in self.contents:
            yield entry_name

    def encrypt(self, plaintext: str) -> bytes:
        return self.box.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        return self.box.decrypt(ciphertext).decode()

    def read(self) -> bytes:
        with open(self.database_path, 'rb') as file:
            return file.read()

    def write(self, buffer) -> None:
        with open(self.database_path, 'wb') as file:
            file.write(buffer)

    @staticmethod
    def get_entry_value() -> dict[str, str]:
        entry_value = {'Password': getpass()}
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


def main() -> None:
    args = parse_arguments()

    if len(sys.argv) == 1:
        # Importing module widgets here to avoid circular dependencies when running tests
        import widgets

        app = QApplication([])
        QFontDatabase.addApplicationFont(':/roboto.ttf')
        file = QFile(':/stylesheet.qss')
        if not file.open(QIODevice.OpenModeFlag.ReadOnly):
            error('Failed to open :/stylesheet.qss resource')
        stylesheet = QTextStream(file).readAll()
        app.setStyleSheet(stylesheet)
        password_widget = widgets.PasswordWidget(app)
        password_widget.show()
        widget_center(password_widget)
        sys.exit(app.exec())

    pm: PasswordManager | None = None

    password = getpass.getpass('Database password: ')
    if not password:
        error('Database password can not be empty')

    try:
        pm = PasswordManager(DATABASE_PATH, password)
    except CryptoError:
        error('Decryption failed')

    assert pm is not None

    match args.subcommand:
        case 'create':
            if args.entry in pm:
                error(f'Entry {args.entry} already exists in the database')
            pm[args.entry] = PasswordManager.get_entry_value()
        case 'read':
            if args.entry:
                if args.entry not in pm:
                    error(f'Entry {args.entry} does not exist in the database')
                print(f'{args.entry}:')
                for name, definition in pm[args.entry].items():
                    print(f'    {name}: "{definition}"')
            else:
                for entry_name in pm:
                    print(f'{entry_name}:')
                    for name, definition in pm[entry_name].items():
                        print(f'    {name}: "{definition}"')
        case 'update':
            if args.entry not in pm:
                error(f'Entry {args.entry} does not exist in the database')
            pm[args.entry] = PasswordManager.get_entry_value()
        case 'delete':
            if args.entry not in pm:
                error(f'Entry {args.entry} does not exist in the database')
            reply = input(f'Are you sure you want to delete entry {args.entry}? ')
            match reply.lower():
                case 'yes' | 'y':
                    del pm[args.entry]
                case _:
                    pass
        case _:
            pass


if __name__ == '__main__':
    main()
