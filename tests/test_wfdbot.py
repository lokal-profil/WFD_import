# -*- coding: utf-8  -*-
"""Unit tests for WfdBot."""
from __future__ import unicode_literals

import unittest

from wikidataStuff.WikidataStuff import WikidataStuff as WdS

from WFD.WFDBase import WfdBot, UnmappedValueError, UnexpectedValueError


class CustomAsserts(object):

    """Custom assertion methods to make life easier."""

    def assert_not_raised(self, func, error):
        """
        Assert that a given error was not raised.

        :param func: function call to test
        :param error: error to listen for
        """
        try:
            func
        except error as e:
            self.fail(e)


class TestValidateMapping(unittest.TestCase, CustomAsserts):

    """Test the validate_mapping method."""

    def setUp(self):
        self.label = 'test'
        self.expected = ['a', 'b', 'c']

    def test_validate_mapping_both_empty(self):
        self.assert_not_raised(
            WfdBot.validate_mapping({}, [], self.label),
            UnmappedValueError)

    def test_validate_mapping_more_in_dict(self):
        found = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.assert_not_raised(
            WfdBot.validate_mapping(found, self.expected, self.label),
            UnmappedValueError)

    def test_validate_mapping_less_in_dict(self):
        found = {'a': 1, 'b': 2, 'd': 4}
        with self.assertRaises(UnmappedValueError) as cm:
            WfdBot.validate_mapping(found, self.expected, self.label)
        self.assertEqual(
            str(cm.exception),
            'The following values for "test" were not mapped: [c]')

    def test_validate_mapping_many_less_in_dict(self):
        found = {'a': 1, 'd': 4}
        with self.assertRaises(UnmappedValueError) as cm:
            WfdBot.validate_mapping(found, self.expected, self.label)
        self.assertEqual(
            str(cm.exception),
            'The following values for "test" were not mapped: [b, c]')

    def test_validate_mapping_same_in_dict(self):
        found = {'a': 1, 'b': 2, 'c': 3}
        self.assert_not_raised(
            WfdBot.validate_mapping(found, self.expected, self.label),
            UnmappedValueError)

    def test_validate_mapping_more_in_dicts(self):
        found = {
            'first': {'a': 1, 'b': 2, 'c': 3, 'd': 4},
            'second': {'a': 5, 'b': 6, 'c': 7, 'd': 8}
        }
        self.assert_not_raised(
            WfdBot.validate_mapping(found, self.expected, self.label),
            UnmappedValueError)

    def test_validate_mapping_less_in_all_dicts(self):
        found = {
            'first': {'a': 1, 'b': 2, 'd': 4},
            'second': {'a': 5, 'b': 6, 'd': 8}
        }
        with self.assertRaises(UnmappedValueError):
            WfdBot.validate_mapping(found, self.expected, self.label)
        # don't check message since order is not guaranteed

    def test_validate_mapping_less_in_some_dicts(self):
        found = {
            'first': {'a': 1, 'b': 2, 'c': 3},
            'second': {'a': 5, 'b': 6, 'd': 8}
        }
        with self.assertRaises(UnmappedValueError) as cm:
            WfdBot.validate_mapping(found, self.expected, self.label)
        self.assertEqual(
            str(cm.exception),
            'The following values for "test" were not mapped: (second, [c])')

    def test_validate_mapping_same_in_dicts(self):
        found = {
            'first': {'a': 1, 'b': 2, 'c': 3},
            'second': {'a': 5, 'b': 6, 'c': 7}
        }
        self.assert_not_raised(
            WfdBot.validate_mapping(found, self.expected, self.label),
            UnmappedValueError)

    def test_validate_mapping_label(self):
        found = {'a': 1, 'b': 2, 'd': 4}
        with self.assertRaises(UnmappedValueError) as cm:
            WfdBot.validate_mapping(found, self.expected, 'test2')
        self.assertEqual(
            str(cm.exception),
            'The following values for "test2" were not mapped: [c]')


class TestYearsAsQualifiers(unittest.TestCase, CustomAsserts):

    """Test the years_as_qualifiers method."""

    def setUp(self):
        self.statement = WdS.Statement('dummy')
        self.expected = WdS.Statement('dummy')
        self.source = 'a_field'

    def test_years_as_qualifiers_empty(self):
        expected_quals = []
        self.assert_not_raised(
            WfdBot.years_as_qualifiers('', self.statement, self.source),
            UnexpectedValueError)
        self.assertEqual(expected_quals, self.statement.quals)

    def test_years_as_qualifiers_single(self):
        self.expected._quals.add(WdS.Qualifier('P585', '1983'))
        WfdBot.years_as_qualifiers('1983', self.statement, self.source)
        self.assertEqual(self.expected, self.statement)

    def test_years_as_qualifiers_range(self):
        self.expected._quals.add(WdS.Qualifier('P580', '1983'))
        self.expected._quals.add(WdS.Qualifier('P582', '2014'))
        WfdBot.years_as_qualifiers('1983--2014', self.statement, self.source)
        self.assertEqual(self.expected, self.statement)

    def test_years_as_qualifiers_nonsense(self):
        expected_quals = []
        with self.assertRaises(UnexpectedValueError) as cm:
            WfdBot.years_as_qualifiers(
                'Hi', self.statement, self.source)
        self.assertEqual(
            str(cm.exception),
            'The following value for "a_field" was unexpected: Hi')
        self.assertEqual(expected_quals, self.statement.quals)
