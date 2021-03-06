# -*- coding: utf-8 -*-
"""Integration tests for supported third party services.

The purpose of the tests is to signal changes in the services that
require changes in the implementation of their clients.
"""
from __future__ import unicode_literals

import os.path

from builtins import object  # pylint: disable=redefined-builtin
import tldextract
from validators import ipv6

from spam_lists.clients import (
    SPAMHAUS_ZEN, SPAMHAUS_ZEN_CLASSIFICATION, SPAMHAUS_DBL,
    SPAMHAUS_DBL_CLASSIFICATION, SURBL_MULTI, SURBL_MULTI_CLASSIFICATION
)
from spam_lists.clients import HpHosts, GoogleSafeBrowsing
from spam_lists.structures import AddressListItem
from test.compat import unittest


def ip_or_registered_domain(host):
    """"Get an IP or a registered domain extracted from the host.

    :param host: a valid IP address or a hostname
    :returns: the host value if it is an IP address or a registered
    domain extracted from it if it is a hostname.
    """
    registered_domain = tldextract.extract(host).registered_domain
    return host if not registered_domain else registered_domain


def url_from_host(host):
    """Get a URL with given host.

    :param host: a host value to be used in the URL
    :returns: a URL to be used during testing
    """
    if ipv6(host):
        host = '['+host+']'
    return 'http://'+host


def get_classification(classification, return_codes):
    """Get expected classification for a host listed by a DNSBL service.

    :param classification: a dictionary with service return codes as
    its keys and classification terms pertaining to them as its values
    :param return_codes: a sequence of return codes expected to be
    returned by the service in response to a query for testing membership
    of a host used during tests
    :returns: a set with classification terms, expected to be identical
    to a set stored in an AddressListItem instance returned by a client
    whose integration with a DNSBL service is being tested
    """
    return set(v for k, v in list(classification.items()) if k in return_codes)


class URLTesterClientTestMixin(object):
    """Integration tests for URL tester clients.

    :cvar tested_client: an instance of client to be tested

    :ivar urls_without_listed: URLs without values listed by the service
    to be queried
    :ivar urls_with_listed: URLs with values listed by the service
    to be queried
    :ivar listed_url: a URL listed (or: with a host listed) by the service
    to be queried
    :ivar listed_item: an instance of AddressListItem representing
    an item listed by the service to be queried
    """

    def test_any_match_for_not_listed(self):
        """Test if False is returned for URLs without a match."""
        actual = self.tested_client.any_match(self.urls_without_listed)
        self.assertFalse(actual)

    def test_any_match_for_listed(self):
        """Test if True is returned for URLs containing a match."""
        actual = self.tested_client.any_match(self.urls_with_listed)
        self.assertTrue(actual)

    def test_filter_matching_not_listed(self):
        """Test if the method detects no matching URLs."""
        generator = self.tested_client.filter_matching(
            self.urls_without_listed
        )
        actual = list(generator)
        self.assertCountEqual([], actual)

    def test_filter_matching_for_listed(self):
        """Test if matching URLs are returned."""
        expected = [self.listed_url]
        filter_matching = self.tested_client.filter_matching
        actual = list(filter_matching(self.urls_with_listed))
        self.assertCountEqual(expected, actual)

    def test_lookup_matching_not_listed(self):
        """Test if no objects are returned."""
        generator = self.tested_client.lookup_matching(
            self.urls_without_listed
        )
        actual = list(generator)
        self.assertCountEqual([], actual)

    def test_lookup_matching_for_listed(self):
        """Test if objects representing  matching URLs are returned."""
        expected = [self.listed_item]
        lookup_matching = self.tested_client.lookup_matching
        actual = list(lookup_matching(self.urls_with_listed))
        self.assertCountEqual(expected, actual)


class HostListClientTestMixin(URLTesterClientTestMixin):
    """Integration tests for clients querying for hosts.

    :cvar listed: an item listed by a service to be queried
    :cvar not_listed: an item not listed by a service to be queried
    :cvar tested_client: an instance of client to be tested
    :cvar urls_without_listed: URLs without values listed by the service
    to be queried
    :cvar urls_with_listed: URLs with values listed by the service
    to be queried
    :cvar listed_url: a URL listed (or: with a host listed) by the service
    to be queried
    :cvar listed_item: an instance of AddressListItem representing
    an item listed by the service to be queried
    :cvar classification: classification of the listed item
    """

    @classmethod
    def setUpClass(cls):
        cls.listed_url = url_from_host(cls.listed)
        cls.not_listed_url = url_from_host(cls.not_listed)
        cls.urls_with_listed = cls.not_listed_url, cls.listed_url
        cls.urls_without_listed = (
            cls.not_listed_url,
            url_from_host(cls.not_listed_2)
        )
        cls.listed_item = AddressListItem(
            ip_or_registered_domain(cls.listed),
            cls.tested_client,
            cls.classification
        )

    def test__contains__for_not_listed(self):
        """Test if False is returned for an unlisted host."""
        actual = self.not_listed in self.tested_client
        self.assertFalse(actual)

    def test_contains_for_listed(self):
        """Test if True is returned for a listed host."""
        actual = self.listed in self.tested_client
        self.assertTrue(actual)

    def test_lookup_for_not_listed(self):
        """Test if None is returned for an unlisted host."""
        actual = self.tested_client.lookup(self.not_listed)
        self.assertIsNone(actual)

    def test_lookup_for_listed(self):
        """Test if a value representing a listed host is returned."""
        actual = self.tested_client.lookup(self.listed)
        self.assertEqual(self.listed_item, actual)


REASON_TO_SKIP = (
    'These tests are expected to fail frequently for users of public'
    ' DNS resolvers:'
    ' https://www.spamhaus.org/faq/section/DNSBL%20Usage#261'
)


# @unittest.skip(REASON_TO_SKIP)
class SpamhausZenTest(HostListClientTestMixin, unittest.TestCase):
    """Tests for the client of Spamhaus ZEN service."""

    # pylint: disable=too-many-public-methods
    tested_client = SPAMHAUS_ZEN
    listed = '127.0.0.2'
    not_listed = '127.0.0.1'
    not_listed_2 = '8.8.8.8'
    classification = get_classification(
        SPAMHAUS_ZEN_CLASSIFICATION,
        [2, 4, 10]
    )


# @unittest.skip(REASON_TO_SKIP)
class SpamhausDBLTest(HostListClientTestMixin, unittest.TestCase):
    """Tests for the client of Spamhaus DBL service."""

    # pylint: disable=too-many-public-methods
    tested_client = SPAMHAUS_DBL
    listed = 'dbltest.com'
    not_listed = 'example.com'
    not_listed_2 = 'google.com'
    classification = get_classification(
        SPAMHAUS_DBL_CLASSIFICATION,
        [2]
    )


class SURBLTest(HostListClientTestMixin):
    """Tests for the client of SURBL MULTI service."""

    tested_client = SURBL_MULTI
    classification = get_classification(
        SURBL_MULTI_CLASSIFICATION,
        [2, 4, 8, 16, 32, 64]
    )


class SURBLMultiIPTest(SURBLTest, unittest.TestCase):
    """Tests for the client of SURBL MULTI service.

    These tests involve querying for an IP address value.
    """

    # pylint: disable=too-many-public-methods
    listed = '127.0.0.2'
    not_listed = '127.0.0.1'
    not_listed_2 = '8.8.8.8'


class SURBLMultiDomainTest(SURBLTest, unittest.TestCase):
    """Tests for the client of SURBL MULTI service.

    These tests involve querying for a hostname value.
    """

    # pylint: disable=too-many-public-methods
    listed = 'surbl-org-permanent-test-point.com'
    not_listed = 'test.com'
    not_listed_2 = 'google.com'


HP_HOSTS = HpHosts('spam-lists-test-suite')


class HpHostsIPTest(HostListClientTestMixin, unittest.TestCase):
    """Tests for the hpHosts service client.

    These tests involve querying for an IP address value.
    """

    # pylint: disable=too-many-public-methods
    listed = '174.36.207.146'
    not_listed = '64.233.160.0'
    not_listed_2 = '2001:ddd:ccc:123::55'
    tested_client = HP_HOSTS
    classification = set()


class HpHostsDomainTest(HostListClientTestMixin, unittest.TestCase):
    """Tests for the hpHosts service client.

    These tests involve querying for a hostname value.
    """

    # pylint: disable=too-many-public-methods
    listed = 'ecardmountain.com'
    not_listed = 'google.com'
    not_listed_2 = 'microsoft.com'
    tested_client = HP_HOSTS
    classification = set(['EMD'])


GSB_API_KEY_FILE = os.path.join(
    os.path.dirname(__file__),
    'google_safe_browsing_api_key.txt'
)
try:
    with open(GSB_API_KEY_FILE, 'r') as key_file:
        SAFE_BROWSING_API_KEY = key_file.readline().rstrip()
except IOError:
    SAFE_BROWSING_API_KEY = None


REASON_TO_SKIP_GSB_TEST = (
    'No API key provided. Provide the key in file: {}'.format(GSB_API_KEY_FILE)
)


@unittest.skipIf(not SAFE_BROWSING_API_KEY, REASON_TO_SKIP_GSB_TEST)
class GoogleSafeBrowsingTest(URLTesterClientTestMixin, unittest.TestCase):
    """Tests for the Google Safe Browsing Lookup API client."""

    # pylint: disable=too-many-public-methods
    listed_url = 'http://www.gumblar.cn/'
    not_listed_url = 'http://www.google.com/'
    not_listed_url_2 = 'https://github.com/'
    urls_with_listed = not_listed_url, listed_url
    urls_without_listed = not_listed_url, not_listed_url_2

    @classmethod
    def setUpClass(cls):
        cls.tested_client = GoogleSafeBrowsing(
            'spam-lists-test-suite',
            '0.5',
            SAFE_BROWSING_API_KEY
        )
        cls.listed_item = AddressListItem(
            cls.listed_url,
            cls.tested_client,
            set(['malware'])
        )


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
