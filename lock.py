import getpass
import hashlib
import json
import os.path
import sys

import nacl.exceptions
import nacl.secret

PROGRAM_NAME = 'lock'
ARGC = len(sys.argv)
DATABASE_PATH = os.path.join(os.path.expanduser('~'), f'.{PROGRAM_NAME}')


class PasswordManager:

    def __init__(self, database_path: str, password: str | None = None) -> None:
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
        try:
            plaintext = self.box.decrypt(encrypted)
        except nacl.exceptions.CryptoError:
            print('Decryption failed', file=sys.stderr)
            sys.exit(1)
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
            print(f'Entry {entry_key} already exists in the database', file=sys.stderr)
            sys.exit(1)
        if entry_value is None:
            entry_value = self.read_entry_value()
        self.contents[entry_key] = entry_value
        plaintext = json.dumps(self.contents, separators=(',', ':'), sort_keys=True)
        encrypted = self.box.encrypt(plaintext.encode())
        with open(self.database_path, 'wb') as file:
            file.write(encrypted)

    def read(self, entry_key: str | None = None) -> dict[str, dict[str, str]]:
        if entry_key is None:
            for entry_key, entry_value in self.contents.items():
                print(f'{entry_key}:')
                for name, definition in entry_value.items():
                    print(f'    {name}: "{definition}"')
            return self.contents
        else:
            if self.contents.get(entry_key) is None:
                print(f'Entry {entry_key} does not exist in the database', file=sys.stderr)
                sys.exit(1)
            print(f'{entry_key}:')
            for name, definition in self.contents[entry_key].items():
                print(f'    {name}: "{definition}"')
            return {entry_key: self.contents[entry_key]}

    def update(self, entry_key: str, entry_value: dict[str, str] | None = None) -> None:
        if self.contents.get(entry_key) is None:
            print(f'Entry {entry_key} does not exist in the database', file=sys.stderr)
            sys.exit(1)
        if entry_value is None:
            entry_value = self.read_entry_value()
        self.contents[entry_key] = entry_value
        plaintext = json.dumps(self.contents, separators=(',', ':'), sort_keys=True)
        encrypted = self.box.encrypt(plaintext.encode())
        with open(self.database_path, 'wb') as file:
            file.write(encrypted)

    def delete(self, entry_key: str, interactive: bool = True) -> None:
        if self.contents.get(entry_key) is None:
            print(f'Entry {entry_key} does not exist in the database', file=sys.stderr)
            sys.exit(1)
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


def usage() -> None:
    print('Usage:',
         f'    {PROGRAM_NAME} create <entry>',
         f'    {PROGRAM_NAME} read [entry]',
         f'    {PROGRAM_NAME} update <entry>',
         f'    {PROGRAM_NAME} delete <entry>', file=sys.stderr, sep='\n')


def main() -> None:
    if ARGC == 1:
        usage()
        sys.exit(1)

    pm = PasswordManager(DATABASE_PATH)

    match sys.argv[1]:
        case 'create' if ARGC == 3:
            pm.create(sys.argv[2])
        case 'read' if ARGC == 2 or ARGC == 3:
            if ARGC == 2:
                pm.read()
            else:
                pm.read(sys.argv[2])
        case 'update' if ARGC == 3:
            pm.update(sys.argv[2])
        case 'delete' if ARGC == 3:
            pm.delete(sys.argv[2])
        case _:
            usage()
            sys.exit(1)


if __name__ == '__main__':
    main()
