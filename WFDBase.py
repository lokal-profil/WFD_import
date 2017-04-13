#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Base class on which to build WFD import bots."""
from __future__ import unicode_literals
import requests
import xmltodict
import datetime

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS


class WfdBot(object):
    """Base bot to enrich Wikidata with info from WFD."""

    def __init__(self, mappings, year, new, cutoff, edit_summary):
        """
        Initialise the WfdBot.

        :param mappings: dict holding data for any offline mappings
        :param year: year of the report (used to date certain statements.
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        :param edit_summary: string to append to all automatically generated
            edit summaries
        """
        self.repo = pywikibot.Site().data_repository()
        self.wd = WdS(self.repo, edit_summary)
        self.new = new
        self.cutoff = cutoff
        self.mappings = mappings
        self.year = year

        # the following must be overridden
        self.dataset_q = None
        self.ref = None

    def commit_labels(self, labels, item):
        """Add labels and aliases to item."""
        if not labels:
            return
        for lang, data in labels.iteritems():
            values = helpers.listify(data['value'])
            for value in values:
                self.wd.addLabelOrAlias(lang, value, item,
                                        caseSensitive=False)

    def commit_claims(self, protoclaims, item):
        """
        Add each claim (if new) and source it.

        :param protoclaims: a dict of claims with
            key: Prop number
            val: Statement|list of Statements
        :param item: the target entity
        """
        if not self.ref:
            raise NotImplementedError(
                'self.ref must be set by the class inheriting WfdBot')

        for pc_prop, pc_value in protoclaims.iteritems():
            if pc_value:
                if isinstance(pc_value, list):
                    pc_value = set(pc_value)  # eliminate potential duplicates
                    for val in pc_value:
                        # check if None or a Statement(None)
                        if (val is not None) and (not val.isNone()):
                            self.wd.addNewClaim(
                                pc_prop, val, item, self.ref)
                            # reload item so that next call is aware of changes
                            item = self.wd.QtoItemPage(item.title())
                            item.exists()
                elif not pc_value.isNone():
                    self.wd.addNewClaim(
                        pc_prop, pc_value, item, self.ref)

    def make_ref(self, data):
        """Make a Reference object for the dataset.

        Contains 4 parts:
        * P248: Stated in <the WFD2016 dataset> (per year and country)
        * P577: Publication date <from creation date of the document>
        * P854: Reference url <using the input url>
        * P813: Retrieval date <current date>

        :param data: the source data from the xml
        :return: WdS.Reference
        """
        if not self.dataset_q:
            raise NotImplementedError(
                'self.dataset_q must be set by the class inheriting WfdBot')

        creation_date = helpers.iso_to_WbTime(data['@creationDate'])
        retrieval_date = helpers.iso_to_WbTime(data['retrieval_date'])

        ref = WdS.Reference(
            source_test=[
                self.wd.make_simple_claim(
                    'P248',
                    self.wd.QtoItemPage(self.dataset_q)),
                self.wd.make_simple_claim(
                    'P854',
                    data['source_url'])],
            source_notest=[
                self.wd.make_simple_claim(
                    'P577',
                    creation_date),
                self.wd.make_simple_claim(
                    'P813',
                    retrieval_date)
            ]
        )
        return ref

    @staticmethod
    def load_xml_url_data(url, key=None):
        """
        Load the data from an url of a xml file.

        Also add source_url and retrieval_date to the data.

        :param url: url to xml file
        :param key: key in the data to filter on. If None then all the data is
            returned.
        :return: the loaded data
        """
        r = requests.get(url)
        data = xmltodict.parse(
            r.text.encode(r.encoding),
            encoding='utf-8')
        if key:
            data = data.get(key)
        data['source_url'] = url
        data['retrieval_date'] = datetime.date.today().isoformat()
        return data

    @staticmethod
    def load_data(in_file, key=None):
        """
        Load the data from the in_file.

        :param in_file: a url to an xml file or the path to a local json dump
            of the same file.
        :param key: optional key used by load_xml_url_data
        :return: the loaded data
        """
        if in_file.partition('://')[0] in ('http', 'https'):
            return WfdBot.load_xml_url_data(in_file, key)
        return helpers.load_json_file(in_file)
