#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from spambl import DNSBL, UnknownCodeError


class DNSBLTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        code_item_class = {1: 'Class #1', 2: 'Class #2'}
        query_suffix = 'query.suffix'
        
        cls.dnsbl = DNSBL('test.dnsbl', query_suffix, code_item_class, True, True)
        
    def testGetClassification(self):
        ''' Test get_classification method of DNSBL instance '''
        
        msg = 'The expected value {} is not equal to received value {}'
        
        for key, value in self.dnsbl._code_item_class.iteritems():
            actual = self.dnsbl.get_classification(key)
            self.assertEqual(actual, value, msg.format(value, actual))
        
        self.assertRaises(UnknownCodeError, self.dnsbl.get_classification, 4)
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()