# -*- coding: utf-8  -*-
"""Unit tests for WfdBot."""
from __future__ import unicode_literals

import unittest

from WFDBase import UnmappedValueError
from WFDBase.WfdBot import validate_mapping


class TestValidateMapping(unittest.TestCase):

    """Test the validate_mapping method."""

    def test_validate_mapping_both_empty(self):
        try:
            validate_mapping([], [], 'test')
        except UnmappedValueError:
            self.fail("validate_mapping() raised UnmappedValueError")

    def test_validate_mapping_more_in_dict(self):
        pass

    def test_validate_mapping_less_in_dict(self):
        pass

    def test_validate_mapping_same_in_dict(self):
        pass

    def test_validate_mapping_more_in_dicts(self):
        pass

    def test_validate_mapping_less_in_dicts(self):
        pass

    def test_validate_mapping_same_in_dicts(self):
        pass

    def test_validate_mapping_label(self):
        pass
