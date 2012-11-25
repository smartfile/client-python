# -*- coding: utf-8 -*-

import filecmp
import os
import unittest

from smartfile import API
from smartfile.exceptions import SmartFileResponseException


@unittest.skipUnless('SMARTFILE_RUN_TESTS' in os.environ,
                     'Unit tests for development server')
class BaseAPITestCase(unittest.TestCase):
    _test_user = {
        'name': 'Test User',
        'username': 'test_user1',
        'password': 'testpass',
        'email': 'testuser@example.com'
    }
    _test_user2 = {
        'name': 'Test User2',
        'username': 'test_user2',
        'password': 'testpass2',
        'email': 'testuser2@example.com'
    }
    _test_group = {
        'name': 'Test Group'
    }
    _test_group2 = {
        'name': 'Test Group2'
    }
    _test_role = {
        'name': 'Test Role',
        'rights': {
            'self_manage': True
        }
    }
    _test_role2 = {
        'name': 'Test Role2',
        'rights': {
            'self_manage': False
        }
    }
    _test_local_file = '/etc/motd'
    _test_remote_file = '/motd'
    _test_downloaded_file = 'motd.down'
    _test_link = {
        'name': 'Test Link',
        'path': _test_remote_file,
        'read': True,
        'write': True,
        'list': True,
        'remove': True
    }
    _test_link2 = {
        'name': 'Test Link2',
        'path': _test_remote_file,
        'read': True,
        'write': True,
        'list': True,
        'remove': True
    }

    @classmethod
    def setUpClass(cls):
        cls.client = API()


class UserTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(UserTestCase, cls).setUpClass()
        try:
            cls.client.user.delete(cls._test_user['username'])
        except:
            pass
        try:
            cls.client.user.delete(cls._test_user2['username'])
        except:
            pass

    def test_create_user(self):
        response = self.client.user.create(self._test_user2)
        self.assertEqual(response.status_code, 201)
        self.client.user.delete(self._test_user2['username'])

    def test_list_users(self):
        self.client.user.create(self._test_user)
        response = self.client.user.read()
        self.assertEqual(response.status_code, 200)
        self.client.user.delete(self._test_user['username'])

    def test_list_user(self):
        self.client.user.create(self._test_user)
        response = self.client.user.read(self._test_user['username'])
        self.assertEqual(response.status_code, 200)
        self.client.user.delete(self._test_user['username'])

    def test_update_user(self):
        self.client.user.create(self._test_user)
        response = self.client.user.update(self._test_user2,
                                           self._test_user['username'])
        self.assertEqual(response.status_code, 200)
        self.client.user.delete(self._test_user2['username'])

    def test_delete_user(self):
        self.client.user.create(self._test_user)
        response = self.client.user.delete(self._test_user['username'])
        self.assertEqual(response.status_code, 204)


class GroupTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(GroupTestCase, cls).setUpClass()
        try:
            cls.client.group.delete(cls._test_group['name'])
        except:
            pass
        try:
            cls.client.group.delete(cls._test_group2['name'])
        except:
            pass

    def test_create_group(self):
        response = self.client.group.create(self._test_group2)
        self.assertEqual(response.status_code, 201)
        self.client.group.delete(self._test_group2['name'])

    def test_list_groups(self):
        self.client.group.create(self._test_group)
        response = self.client.group.read()
        self.assertEqual(response.status_code, 200)
        self.client.group.delete(self._test_group['name'])

    def test_list_group(self):
        self.client.group.create(self._test_group)
        response = self.client.group.read(self._test_group['name'])
        self.assertEqual(response.status_code, 200)
        self.client.group.delete(self._test_group['name'])

    def test_update_group(self):
        self.client.group.create(self._test_group)
        response = self.client.group.update(self._test_group2,
                                            self._test_group['name'])
        self.assertEqual(response.status_code, 200)
        self.client.group.delete(self._test_group2['name'])

    def test_delete_group(self):
        self.client.group.create(self._test_group)
        response = self.client.group.delete(self._test_group['name'])
        self.assertEqual(response.status_code, 204)


class RoleTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(RoleTestCase, cls).setUpClass()
        try:
            cls.client.user.delete(cls._test_user['username'])
        except:
            pass
        try:
            cls.client.role.delete(cls._test_role['name'])
        except:
            pass
        try:
            cls.client.role.delete(cls._test_role2['name'])
        except:
            pass

    def test_create_role(self):
        response = self.client.role.create(self._test_role)
        self.assertEqual(response.status_code, 201)
        self.client.role.delete(self._test_role['name'])

    def test_list_roles(self):
        self.client.role.create(self._test_role)
        response = self.client.role.read()
        self.assertEqual(response.status_code, 200)
        self.client.role.delete(self._test_role['name'])

    def test_list_role(self):
        self.client.role.create(self._test_role)
        response = self.client.role.read(self._test_role['name'])
        self.assertEqual(response.status_code, 200)
        self.client.role.delete(self._test_role['name'])

    def test_update_role(self):
        self.client.role.create(self._test_role)
        response = self.client.role.update(self._test_role2,
                                           self._test_role['name'])
        self.assertEqual(response.status_code, 200)
        self.client.role.delete(self._test_role2['name'])

    def test_delete_role(self):
        self.client.role.create(self._test_role)
        response = self.client.role.delete(self._test_role['name'])
        self.assertEqual(response.status_code, 204)


class BaseQuotaTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        """ Setup the class based upon the child class. """
        # Test quota and quota update.
        cls._test_quota = {
            cls._test_quota_type: cls._test_entity[cls._test_entity_key],
            'enforcement': 'notify',
            'interval': 'monthly',
            'disk_bytes_limit': 1073741824,
            'xfer_bytes_limit': None
        }
        cls._test_quota_update = {
            'enforcement': 'disable',
            'interval': 'weekly',
            'disk_bytes_limit': None
        }

        super(BaseQuotaTestCase, cls).setUpClass()

        # Set the API of the entity and API of the entity quota.
        cls.entity_api = getattr(cls.client, cls._test_quota_type)
        cls.quota_api = getattr(cls.client.quota, cls._test_quota_type)

        # Create an entity for the quota.
        try:
            cls.entity_api.create(cls._test_entity)
        except:
            pass

    @classmethod
    def tearDownClass(cls):
        # Remove any leftover quota and the entity used for testing.
        super(BaseQuotaTestCase, cls).tearDownClass()
        name = cls._test_quota[cls._test_quota_type]
        try:
            cls.quota_api.delete(name)
        except:
            pass
        try:
            cls.entity_api.delete(name)
        except:
            pass

    def test_create_quota(self):
        response = self.quota_api.create(self._test_quota)
        self.assertEqual(response.status_code, 201)
        self.quota_api.delete(self._test_quota[self._test_quota_type])

    def test_list_quotas(self):
        self.quota_api.create(self._test_quota)
        response = self.quota_api.read()
        self.assertEqual(response.status_code, 200)
        self.quota_api.delete(self._test_quota[self._test_quota_type])

    def test_list_quota(self):
        self.quota_api.create(self._test_quota)
        response = self.quota_api.read(self._test_quota[self._test_quota_type])
        self.assertEqual(response.status_code, 200)
        self.quota_api.delete(self._test_quota[self._test_quota_type])

    def test_update_quota(self):
        self.quota_api.create(self._test_quota)
        response = self.quota_api.update(
            self._test_quota_update, self._test_quota[self._test_quota_type])
        self.assertEqual(response.status_code, 200)
        self.quota_api.delete(self._test_quota[self._test_quota_type])

    def test_delete_quota(self):
        self.quota_api.create(self._test_quota)
        response = self.quota_api.delete(
            self._test_quota[self._test_quota_type])
        self.assertEqual(response.status_code, 204)


class GroupQuotaTestCase(BaseQuotaTestCase):
    _test_quota_type = 'group'
    _test_entity = BaseAPITestCase._test_group
    _test_entity_key = 'name'


class UserQuotaTestCase(BaseQuotaTestCase):
    _test_quota_type = 'user'
    _test_entity = BaseAPITestCase._test_user
    _test_entity_key = 'username'


class BasePathTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(BasePathTestCase, cls).setUpClass()
        try:
            cls.client.path.remove(cls._test_remote_file)
        except:
            pass


class PathTestCase(BasePathTestCase):
    def test_file_upload(self):
        response = self.client.path.upload(self._test_remote_file,
                                           self._test_local_file)
        self.assertEqual(response.status_code, 200)
        self.client.path.remove(self._test_remote_file)

    def test_file_download(self):
        self.client.path.upload(self._test_remote_file, self._test_local_file)
        response = self.client.path.download(self._test_downloaded_file,
                                             self._test_remote_file)
        cmp_result = filecmp.cmp(self._test_local_file,
                                 self._test_downloaded_file)
        try:
            os.unlink(self._test_downloaded_file)
        except:
            pass
        self.assertEqual(response.status_code, 200)
        self.client.path.remove(self._test_remote_file)
        self.assertTrue(cmp_result)

    def test_file_remove(self):
        """ Delete file using shortcut within Path API. """
        self.client.path.upload(self._test_remote_file, self._test_local_file)
        response = self.client.path.remove(self._test_remote_file)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['result']['status'], 'SUCCESS')


class PathOperTestCase(BasePathTestCase):
    def test_file_remove(self):
        # Create task to delete file.
        self.client.path.upload(self._test_remote_file, self._test_local_file)
        response = self.client.path_oper.remove(self._test_remote_file)
        self.assertEqual(response.status_code, 200)

        # Check that the task completed.
        response = self.client.path_oper.poll(response.json['url'])
        status = response.json['result']['status']
        self.assertEqual(status, 'SUCCESS')


class PathTreeTestCase(BasePathTestCase):
    def test_file_list(self):
        self.client.path.upload(self._test_remote_file, self._test_local_file)
        response = self.client.path_tree.read(self._test_remote_file)
        self.assertEqual(response.status_code, 200)
        self.client.path.remove(self._test_remote_file)
        self.assertEqual(response.json['path'], self._test_remote_file)

    def test_file_non_existent_list(self):
        with self.assertRaises(SmartFileResponseException) as cm:
            self.client.path_tree.read(self._test_remote_file)
        self.assertEqual(cm.exception.status_code, 404)

    def test_directory_list(self):
        response = self.client.path_tree.read('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['path'], '/')

    def test_directory_and_children_list(self):
        response = self.client.path_tree.read('/', children=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('children', response.json)
        self.assertGreater(len(response.json['children']), 0)


class LinkTestCase(BaseAPITestCase):
    @classmethod
    def setUpClass(cls):
        super(LinkTestCase, cls).setUpClass()
        cls.client.path.upload(cls._test_remote_file, cls._test_local_file)
        try:
            cls.client.link.delete(cls._test_link['name'])
        except:
            pass
        try:
            cls.client.link.delete(cls._test_link2['name'])
        except:
            pass

    @classmethod
    def tearDownClass(cls):
        super(LinkTestCase, cls).tearDownClass()
        cls.client.path.remove(cls._test_remote_file)

    def test_create_link(self):
        response = self.client.link.create(self._test_link)
        self.assertEqual(response.status_code, 201)
        self.client.link.delete(response.json['uid'])

    def test_list_links(self):
        response = self.client.link.create(self._test_link)
        uid = response.json['uid']
        response = self.client.link.read()
        self.assertEqual(response.status_code, 200)
        self.client.link.delete(uid)

    def test_list_link(self):
        response = self.client.link.create(self._test_link)
        uid = response.json['uid']
        response = self.client.link.read(uid)
        self.assertEqual(response.status_code, 200)
        self.client.link.delete(uid)

    def test_update_link(self):
        response = self.client.link.create(self._test_link)
        response = self.client.link.update(self._test_link2,
                                           response.json['uid'])
        self.assertEqual(response.status_code, 200)
        self.client.link.delete(response.json['uid'])

    def test_delete_link(self):
        response = self.client.link.create(self._test_link)
        uid = response.json['uid']
        response = self.client.link.delete(uid)
        self.assertEqual(response.status_code, 204)


class PingTestCase(BaseAPITestCase):
    def test_ping(self):
        response = self.client.ping.read()
        self.assertEqual(response.status_code, 200)
        self.assertIn('ping', response.json)
        self.assertEqual(response.json['ping'], 'pong')
