import os
import secrets
import unittest

from helpers import file_read
import lock


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.database_path = f'.{secrets.token_hex(4)}'
        self.pm = lock.PasswordManager(self.database_path, False, '1234')

    def test_create(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        encrypted = file_read(self.database_path)
        plaintext = self.pm.box.decrypt(encrypted)
        got = plaintext.decode()
        expected = '{"Google":{"Password":"1234","Username":"Alice"}}'
        self.assertEqual(got, expected)

    def test_create_existing(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        with self.assertRaises(lock.EntryExistsError):
            self.pm.create('Google', {'Username': 'Alice', 'Password': '5678'})
        encrypted = file_read(self.database_path)
        plaintext = self.pm.box.decrypt(encrypted)
        got = plaintext.decode()
        expected = '{"Google":{"Password":"1234","Username":"Alice"}}'
        self.assertEqual(got, expected)

    def tearDown(self):
        os.remove(self.database_path)


class TestRead(unittest.TestCase):

    def setUp(self):
        self.database_path = f'.{secrets.token_hex(4)}'
        self.pm = lock.PasswordManager(self.database_path, False, '1234')

    def test_read_one_entry(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        self.pm.create('Microsoft', {'Username': 'Alice', 'Password': '1234'})
        got = self.pm.read('Google')
        expected = {'Google': {'Username': 'Alice', 'Password': '1234'}}
        self.assertEqual(got, expected)

    def test_read_every_entry(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        self.pm.create('Microsoft', {'Username': 'Alice', 'Password': '1234'})
        got = self.pm.read()
        expected = {
            'Google': {'Username': 'Alice', 'Password': '1234'},
            'Microsoft': {'Username': 'Alice', 'Password': '1234'}
        }
        self.assertEqual(got, expected)

    def test_read_nonexistent(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        with self.assertRaises(lock.EntryDoesNotExistError):
            self.pm.read('Microsoft')

    def tearDown(self):
        os.remove(self.database_path)


class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.database_path = f'.{secrets.token_hex(4)}'
        self.pm = lock.PasswordManager(self.database_path, False, '1234')

    def test_update(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        self.pm.update('Google', {'Username': 'Alice', 'Password': '5678'})
        encrypted = file_read(self.database_path)
        plaintext = self.pm.box.decrypt(encrypted)
        got = plaintext.decode()
        expected = '{"Google":{"Password":"5678","Username":"Alice"}}'
        self.assertEqual(got, expected)

    def test_update_nonexistent(self):
        with self.assertRaises(lock.EntryDoesNotExistError):
            self.pm.update('Google', {'Username': 'Alice', 'Password': '1234'})

    def tearDown(self):
        os.remove(self.database_path)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.database_path = f'.{secrets.token_hex(4)}'
        self.pm = lock.PasswordManager(self.database_path, False, '1234')

    def test_delete(self):
        self.pm.create('Google', {'Username': 'Alice', 'Password': '1234'})
        self.pm.delete('Google', interactive=False)
        encrypted = file_read(self.database_path)
        plaintext = self.pm.box.decrypt(encrypted)
        got = plaintext.decode()
        expected = '{}'
        self.assertEqual(got, expected)

    def test_delete_nonexistent(self):
        with self.assertRaises(lock.EntryDoesNotExistError):
            self.pm.delete('Google')

    def tearDown(self):
        os.remove(self.database_path)
