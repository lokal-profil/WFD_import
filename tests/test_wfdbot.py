# -*- coding: utf-8  -*-
"""Unit tests for WfdBot."""
from __future__ import unicode_literals

import unittest

from WFD.WFDBase import WfdBot, UnmappedValueError


class TestValidateMapping(unittest.TestCase):

    """Test the validate_mapping method."""

    def setUp(self):
        self.label = 'test'
        self.expected = ['a', 'b', 'c']

    def assert_not_raised(self, func, error):
        try:
            func
        except error as e:
            self.fail(e)

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
