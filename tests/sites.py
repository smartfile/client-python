# -*- coding: utf-8 -*-

from tests import BaseAPITestCase
from tests import BaseQuotaTestCase


class SiteTestCase(BaseAPITestCase):
    """ Test CRUD for sites.

    A successful run is dependent upon the order of tests.
    """
    _test_site1 = {
        'name': 'site1',
        'industry': 'Other',
        'contact': BaseAPITestCase._test_user['name'],
        'email': BaseAPITestCase._test_user['email'],
        'username': BaseAPITestCase._test_user['username'],
        'password': BaseAPITestCase._test_user['password']
    }
    _test_site2 = {
        'name': 'site2',
        'industry': 'Personal Use'
    }

    @classmethod
    def setUpClass(cls):
        super(SiteTestCase, cls).setUpClass()
        for name in (cls._test_site1['name'], cls._test_site2['name']):
            try:
                cls.client.site.delete(name)
            except:
                pass

    @classmethod
    def tearDownClass(cls):
        super(SiteTestCase, cls).tearDownClass()
        for name in (cls._test_site1['name'], cls._test_site2['name']):
            try:
                cls.client.site.delete(name)
            except:
                pass

    def test_1_create_site(self):
        response = self.client.site.create(self._test_site1)
        self.assertEqual(response.status_code, 201)

    def test_2_read_site(self):
        response = self.client.site.read(self._test_site1['name'])
        self.assertEqual(response.status_code, 200)

    def test_3_read_sites(self):
        response = self.client.site.read()
        self.assertEqual(response.status_code, 200)

    def test_4_update_site(self):
        response = self.client.site.update(self._test_site2,
                                           self._test_site1['name'])
        self.assertEqual(response.status_code, 200)

    def test_5_delete_site(self):
        response = self.client.site.delete(self._test_site2['name'])
        self.assertEqual(response.status_code, 204)


class SiteQuotaTestCase(BaseQuotaTestCase):
    _test_quota_type = 'site'
    _test_entity = SiteTestCase._test_site1
    _test_entity_key = 'name'
