from pathlib import Path
import os
import secrets
import unittest

from lock import PasswordManager

DATABASE_FILENAME_LENGTH = 4
DATABASE_PASSWORD = '1234'


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.database_path = Path(f'.{secrets.token_hex(DATABASE_FILENAME_LENGTH)}')
        self.pm = PasswordManager(self.database_path, DATABASE_PASSWORD)

    def test_create_one_entry(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        ciphertext = self.pm.read()
        got = self.pm.decrypt(ciphertext)
        expected = '{"Google":{"Password":"1234","Username":"Alice"}}'
        self.assertEqual(got, expected)

    def test_create_two_entries(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        self.pm['Microsoft'] = {'Username': 'Alice', 'Password': '5678'}
        ciphertext = self.pm.read()
        got = self.pm.decrypt(ciphertext)
        expected = '{"Google":{"Password":"1234","Username":"Alice"},"Microsoft":{"Password":"5678","Username":"Alice"}}'
        self.assertEqual(got, expected)

    def tearDown(self):
        os.remove(self.database_path)


class TestRead(unittest.TestCase):

    def setUp(self):
        self.database_path = Path(f'.{secrets.token_hex(DATABASE_FILENAME_LENGTH)}')
        self.pm = PasswordManager(self.database_path, DATABASE_PASSWORD)

    def test_read_one_entry(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        self.pm['Microsoft'] = {'Username': 'Alice', 'Password': '5678'}
        got = self.pm['Google']
        expected = {'Username': 'Alice', 'Password': '1234'}
        self.assertEqual(got, expected)

    def test_read_all_entries(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        self.pm['Microsoft'] = {'Username': 'Alice', 'Password': '5678'}
        got = {entry_name: self.pm[entry_name] for entry_name in self.pm}
        expected = {
            'Google': {'Username': 'Alice', 'Password': '1234'},
            'Microsoft': {'Username': 'Alice', 'Password': '5678'}
        }
        self.assertEqual(got, expected)

    def test_read_nonexistent(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        with self.assertRaises(KeyError):
            self.pm['Microsoft']

    def tearDown(self):
        os.remove(self.database_path)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.database_path = Path(f'.{secrets.token_hex(DATABASE_FILENAME_LENGTH)}')
        self.pm = PasswordManager(self.database_path, DATABASE_PASSWORD)

    def test_delete(self):
        self.pm['Google'] = {'Username': 'Alice', 'Password': '1234'}
        del self.pm['Google']
        ciphertext = self.pm.read()
        got = self.pm.decrypt(ciphertext)
        expected = '{}'
        self.assertEqual(got, expected)

    def test_delete_nonexistent(self):
        with self.assertRaises(KeyError):
            del self.pm['Google']

    def tearDown(self):
        os.remove(self.database_path)
