# -*- coding: utf-8 -*-

import unittest
from urlparse import parse_qs, urlparse

from requests.exceptions import HTTPError
from mock import MagicMock, Mock, patch
from dns.resolver import NXDOMAIN
from nose_parameterized import parameterized
from cachetools.func import lru_cache

from spam_lists.service_models import DNSBL, GoogleSafeBrowsing,\
HostCollection, HostList, HpHosts, UrlHostTester
from spam_lists.structures import AddressListItem
from spam_lists.exceptions import UnathorizedAPIKeyError, UnknownCodeError

from .base_test_cases import BaseHostListTest, BaseUrlTesterTest,\
ClientGetExpectedItemsProvider, GeneratedUrlTesterTest, IPv6SupportTest,\
TestFunctionDoesNotHandleProvider

class HostListTest(unittest.TestCase):
    
    def setUp(self):
        self.host_factory_mock = Mock()
        self.tested_instance = HostList(self.host_factory_mock)
        
        self._contains_patcher = patch('spam_lists.service_models.HostList._contains')
        self._contains_mock = self._contains_patcher.start()
        
        self._get_match_and_classification_patcher = patch('spam_lists.service_models.HostList._get_match_and_classification')
        self._get_match_and_classification_mock = self._get_match_and_classification_patcher.start()
        self._get_match_and_classification_mock.return_value = None, None
        
    def tearDown(self):
        self._contains_patcher.stop()
        self._get_match_and_classification_patcher.stop()
        
    @parameterized.expand([
                           ('__contains__', '_contains'),
                           ('lookup', '_get_match_and_classification'),
                           ])
    def test_nonpublic_function_call_for(self, function_name, non_public_function_name):
        
        function = getattr(self.tested_instance, function_name)
        nonpublic_function = getattr(self.tested_instance, non_public_function_name)
        valid_host = 'validhost.com'
        function(valid_host)
        
        expected_argument = self.host_factory_mock(valid_host)
        nonpublic_function.assert_called_once_with(expected_argument)
        
class UrlHostTesterTest(
                        GeneratedUrlTesterTest,
                        BaseUrlTesterTest,
                        ClientGetExpectedItemsProvider,
                        unittest.TestCase):
    
    def setUp(self):
          
        self.tested_instance = UrlHostTester()
          
        self.is_valid_url_patcher = patch('spam_lists.validation.is_valid_url')
        self.is_valid_url_mock = self.is_valid_url_patcher.start()
          
        self.listed_hosts = []
          
        self.contains_patcher = patch('spam_lists.service_models.UrlHostTester.__contains__')
        self.contains_mock = self.contains_patcher.start()
        self.contains_mock.side_effect = lambda h: h in self.listed_hosts
          
        def lookup(h):
            if h in self.listed_hosts:
                return AddressListItem(
                                       h,
                                       self.tested_instance,
                                       self.classification
                                       )
            return None
          
        self.lookup_patcher = patch('spam_lists.service_models.UrlHostTester.lookup')
        self.lookup_mock = self.lookup_patcher.start()
        self.lookup_mock.side_effect = lookup
          
    def tearDown(self):
        self.is_valid_url_patcher.stop()
        self.contains_patcher.stop()
        self.lookup_patcher.stop()
          
    def _set_matching_urls(self, urls):
           
        listed_hosts = [urlparse(u).hostname for u in urls]
        self.listed_hosts = listed_hosts
          
    def _get_expected_items_for_urls(self, urls):
        hosts = [urlparse(u).hostname for u in urls]
        return self._get_expected_items(hosts)
    
@lru_cache()
def dnsbl_host_factory(h):
    host_object = MagicMock()
    host_object.__str__.return_value = h
    return host_object

def create_dns_query_function(expected_query_names):
    def dns_query(query_name):
            if query_name in expected_query_names:
                dns_answer_mock = Mock()
                dns_answer_mock.to_text.return_value = '121.0.0.1'
                return [dns_answer_mock]
            raise NXDOMAIN
    return dns_query
        
class DNSBLTest(
                IPv6SupportTest,
                BaseHostListTest, 
                ClientGetExpectedItemsProvider,
                TestFunctionDoesNotHandleProvider,
                unittest.TestCase
                ):
     
    query_domain_str = 'test.query.domain'
     
    def setUp(self):
         
        self.classification_resolver = Mock()
        self.classification_resolver.return_value = self.classification
         
        self.host_factory_mock = Mock()
        self.host_factory_mock.side_effect = dnsbl_host_factory
         
        self.tested_instance = DNSBL('test_service', self.query_domain_str, 
                                   self.classification_resolver, self.host_factory_mock)
         
        self.dns_query_patcher = patch('spam_lists.service_models.query')
        self.dns_query_mock = self.dns_query_patcher.start()
        self.dns_query_mock.side_effect = create_dns_query_function([])
         
    def tearDown(self):
         
        self.dns_query_patcher.stop()
         
    def _set_matching_hosts(self, hosts):
         
        host_objects = [self.host_factory_mock(h) for h in hosts]
        expected_query_names = [h.relative_domain.derelativize() 
                                for h in host_objects]
        self.dns_query_mock.side_effect = create_dns_query_function(expected_query_names)
        
    def _test_function_does_not_handle_unknown_code_error(self, function, *args, **kwargs):
        self._test_function_does_not_handle(
                                            UnknownCodeError,
                                            self.classification_resolver,
                                            function,
                                            *args,
                                            **kwargs
                                            )
        
    def test_lookup_does_not_handle_unknown_code_error(self):
        
        host = 'hostwithunknowncode.com'
        self._set_matching_hosts([host])
        self._test_function_does_not_handle_unknown_code_error(
                                                               self.tested_instance.lookup,
                                                               host
                                                               )
        
    def test_lookup_matching_does_not_handle_unknown_code_error(self):
        
        url = 'http://hostwithunknowncode.com'
        self._set_matching_hosts([urlparse(url).hostname])
        
        self._test_function_does_not_handle_unknown_code_error(
                                                               self.tested_instance.lookup_matching,
                                                               [url]
                                                               )
        
def hp_hosts_host_factory(host_value):
    value = MagicMock()
    value.__str__.return_value = str(host_value)
    return  value

def create_hp_hosts_get(classification, listed_hosts):
    class_str = ','.join(classification)
    def hp_hosts_get(url):
        query_string = urlparse(url).query
        query_data = parse_qs(query_string)
        
        content = 'Not listed'
        host = query_data['s'][0]
        if host in listed_hosts:
            content = 'Listed,{}'.format(class_str)
            
        response = Mock()
        response.content = content
        return response
    return hp_hosts_get

class HpHostsTest(
                  BaseHostListTest,
                  ClientGetExpectedItemsProvider,
                  unittest.TestCase
                  ):
    
    valid_ipv6 = '2001:ddd:ccc:111::33'
    
    @classmethod
    def setUpClass(cls):
         
        cls.tested_instance = HpHosts('spambl_test_suite')
        
    def _set_up_get_mock(self):
        self.get_patcher = patch('spam_lists.service_models.get')
        self.get_mock = self.get_patcher.start()
        self.get_mock.side_effect = create_hp_hosts_get(self.classification, [])
        
    def setUp(self):
         
        self.listed_hosts = []
        
        self._set_up_get_mock()
        
        self.host_factory_mock = Mock()
        
        self.tested_instance = HpHosts('spambl_test_suite')
        self.tested_instance._host_factory = self.host_factory_mock
         
        self.host_factory_mock.side_effect = hp_hosts_host_factory
         
        self.is_valid_url_patcher = patch('spam_lists.validation.is_valid_url')
        self.is_valid_url_mock = self.is_valid_url_patcher.start()
         
    def tearDown(self):
        self.get_patcher.stop()
        self.is_valid_url_patcher.stop()
         
    def _set_matching_hosts(self, hosts):
        self.get_mock.side_effect = create_hp_hosts_get(self.classification, hosts)
    
    def _test_function_raises_value_error_for_valid_ipv6(self, function, ipv6_arg):
        
        self.assertRaises(ValueError, function, ipv6_arg)
        
    def test_contains_raises_value_error_for_valid_ipv6(self):
        
        self._test_function_raises_value_error_for_valid_ipv6(
                                                             self.tested_instance.__contains__,
                                                             self.valid_ipv6
                                                             )
        
    def test_lookup_raises_value_error_for_valid_ipv6(self):
        
        self._test_function_raises_value_error_for_valid_ipv6(
                                                             self.tested_instance.lookup,
                                                             self.valid_ipv6
                                                             )
    def _test_function_raises_value_error_for_valid_ipv6_url(self, function):
        
        url = 'http://[{}]'.format(self.valid_ipv6)
        
        self._test_function_raises_value_error_for_valid_ipv6(
                                                              function,
                                                              [url]
                                                              )
        
    def test_any_match_raises_value_error_for_valid_ipv6_url(self):
        
        self._test_function_raises_value_error_for_valid_ipv6_url(
                                                                  self.tested_instance.any_match
                                                                  )
        
    def test_lookup_matching_raises_value_error_for_valid_ipv6_url(self):
        
        function = lambda u: list(self.tested_instance.lookup_matching(u))
        
        self._test_function_raises_value_error_for_valid_ipv6_url(function)
        
class GoogleSafeBrowsingTest(
                             GeneratedUrlTesterTest,
                             BaseUrlTesterTest,
                             ClientGetExpectedItemsProvider,
                             unittest.TestCase
                             ):
    
    def _get_expected_items_for_urls(self, urls):
        return self._get_expected_items(urls)
    
    @classmethod
    def setUpClass(cls):
        cls.tested_instance = GoogleSafeBrowsing('test_client', '0.1', 'test_key')
        
    def _set_up_post_mock(self):
        
        def post(_, body):
            response = Mock()
            if self._expecting_unathorized_api_key_error:
                response.status_code = 401
                response.raise_for_status.side_effect = HTTPError
                
            else:
                urls = body.splitlines()[1:]
                classes = [('ok' if u not in self._spam_urls else 
                       self.classification[0]) for u in urls]
                response.content = '\n'.join(classes)
                code = 200 if self._spam_urls else 204
                response.status_code = code
            
            return response
        
        self.post_patcher = patch('spam_lists.service_models.post')
        self.mocked_post = self.post_patcher.start()
        self.mocked_post.side_effect = post
        
    def setUp(self):
        self._spam_urls = []
        self._expecting_unathorized_api_key_error = False
        
        self._set_up_post_mock()
        
        self.is_valid_url_patcher = patch('spam_lists.validation.is_valid_url')
        self.is_valid_url_mock = self.is_valid_url_patcher.start()
        
    def tearDown(self):
        self.post_patcher.stop()
        self.is_valid_url_patcher.stop()
        
    def _set_matching_urls(self, urls):
        self._spam_urls = urls
        
    def _test_for_unathorized_api_key(self, function):
        
        self._expecting_unathorized_api_key_error = True
        
        self.assertRaises(UnathorizedAPIKeyError, function, self.valid_urls)
        
    def test_any_match_for_unathorized_api_key(self):
        
        self._test_for_unathorized_api_key(self.tested_instance.any_match)
        
    def test_lookup_matching_for_unathorized_api_key(self):
        
        function = lambda u: list(self.tested_instance.lookup_matching(u))
        self._test_for_unathorized_api_key(function)
        
def host_collection_host_factory(h):
            host_object = MagicMock()
            host_object.__str__.return_value = h
            host_object.is_subdomain.return_value = False
            host_object.__eq__.return_value = False
            
            test = lambda h2: str(host_object) == str(h2)
            host_object.__eq__.side_effect = test
            host_object.is_subdomain.side_effect = test
                
            return host_object
        
class HostCollectionTest(
                         IPv6SupportTest,
                         BaseHostListTest,
                         TestFunctionDoesNotHandleProvider,
                         ClientGetExpectedItemsProvider,
                         unittest.TestCase
                         ):
     
    valid_urls = ['http://test.com', 'http://127.33.22.11']
    
    def setUp(self):
         
        self.host_patcher = patch('spam_lists.service_models.host')
        self.host_factory_mock = self.host_patcher.start()
         
        self.host_factory_mock.side_effect = lru_cache()(host_collection_host_factory)
         
        self.classification = ('test_classification',)
        self.tested_instance = HostCollection('test_host_collection',
                                              self.classification)
         
    def tearDown(self):
        self.host_patcher.stop()
        
    def test_add_does_not_handle_value_error(self):
        function = self.tested_instance.add
        
        self._test_function_does_not_handle_invalid_host_error(function, 'invalidhost.com')
         
    @parameterized.expand(BaseHostListTest.valid_host_input)
    def test_add_for_valid(self, _, value):
         
        self.tested_instance.add(value)
         
        in_host_collection = self.host_factory_mock(value) in self.tested_instance.hosts
         
        self.assertTrue(in_host_collection)
         
    def _set_matching_hosts(self, hosts):
        self.tested_instance.hosts = [self.host_factory_mock(h) for h in hosts]
         
    def _set_matching_urls(self, urls):
         
        listed_hosts = [urlparse(u).hostname for u in urls]
        self._set_matching_hosts(listed_hosts)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()