import filecmp
import os
import unittest

from smartfile import API


class BaseAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = API()


class UserTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(UserTestCase, cls).setUpClass()
        cls._test_user = {
            'name': 'Test User',
            'username': 'testuser',
            'password': 'testpass',
            'email': 'testuser@example.com'
        }
        cls._test_user2 = {
            'name': 'Test User2',
            'username': 'testuser2',
            'password': 'testpass2',
            'email': 'testuser2@example.com'
        }
        cls.client.user.delete(cls._test_user['username'])
        cls.client.user.delete(cls._test_user2['username'])

    def test_create_user(self):
        response = self.client.user.create(self._test_user2)
        self.assertEqual(response.status_code, 201)
        self.client.user.delete(self._test_user2['username'])

    def test_list_users(self):
        self.client.user.create(self._test_user)
        response = self.client.user.list()
        self.assertEqual(response.status_code, 200)
        self.client.user.delete(self._test_user['username'])

    def test_list_user(self):
        self.client.user.create(self._test_user)
        response = self.client.user.list(self._test_user['username'])
        self.assertEqual(response.status_code, 200)
        self.client.user.delete(self._test_user['username'])

    def test_delete_user(self):
        self.client.user.create(self._test_user)
        response = self.client.user.delete(self._test_user['username'])
        self.assertEqual(response.status_code, 204)


class BasePathTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(BasePathTestCase, cls).setUpClass()
        cls.local_file = '/etc/motd'
        cls.remote_file = '/motd'
        cls.downloaded_file = 'motd.down'
        cls.client.path.remove(cls.remote_file)


class PathTestCase(BasePathTestCase):
    def test_file_upload(self):
        response = self.client.path.upload(self.remote_file, self.local_file)
        self.assertEqual(response.status_code, 200)
        self.client.path.remove(self.remote_file)

    def test_file_download(self):
        self.client.path.upload(self.remote_file, self.local_file)
        response = self.client.path.download(self.downloaded_file,
                                             self.remote_file)
        cmp_result = filecmp.cmp(self.local_file, self.downloaded_file)
        try:
            os.unlink(self.downloaded_file)
        except:
            pass
        self.assertEqual(response.status_code, 200)
        self.assertTrue(cmp_result)
        self.client.path.remove(self.remote_file)

    def test_file_remove(self):
        """ Delete file using shortcut within Path API. """
        self.client.path.upload(self.remote_file, self.local_file)
        response = self.client.path.remove(self.remote_file)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['result']['status'], 'SUCCESS')


class PathOperTestCase(BasePathTestCase):
    def test_file_remove(self):
        # Create task to delete file.
        self.client.path.upload(self.remote_file, self.local_file)
        response = self.client.path_oper.remove(self.remote_file)
        self.assertEqual(response.status_code, 200)

        # Check that the task completed.
        response = self.client.path_oper.poll(response.json['url'])
        status = response.json['result']['status']
        self.assertEqual(status, 'SUCCESS')


class PathTreeTestCase(BasePathTestCase):
    @classmethod
    def setUpClass(cls):
        super(PathTreeTestCase, cls).setUpClass()
        cls.local_file = '/etc/motd'
        cls.remote_file = '/motd'
        cls.downloaded_file = 'motd.down'
        cls.client.path.remove(cls.remote_file)

    def test_file_list(self):
        self.client.path.upload(self.remote_file, self.local_file)
        response = self.client.path_tree.list(self.remote_file)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['path'], self.remote_file)

    def test_directory_list(self):
        response = self.client.path_tree.list('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['path'], '/')

    def test_directory_and_children_list(self):
        response = self.client.path_tree.list('/', children=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('children', response.json)
        self.assertGreater(len(response.json['children']), 0)
