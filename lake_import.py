#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Surface Water Bodies.

Author: Lokal_Profil
License: MIT

usage:
    python WFD/lake_import.py [OPTIONS]

&params;
"""
from __future__ import unicode_literals
from builtins import dict

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS

from WFDBase import WfdBot

parameter_help = """\
Lakebot options (may be omitted):
-year              Year to which the WFD data applies.
-new               if present new items are created on Wikidata, otherwise
                   only updates are processed.
-in_file           path to the data file
-mappings          path to the mappings file (if not "mappings.json")
-cutoff            number items to process before stopping (if not then all)

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-dir               directory in which user_config is located
-help              output all available options
"""
docuReplacements = {'&params;': parameter_help}
EDIT_SUMMARY = 'importing #SWB using data from #WFD'


class LakeBot(WfdBot):
    """Bot to enrich/create info on Wikidata for lake objects."""

    def __init__(self, mappings, year, new=False, cutoff=None):
        """
        Initialise the LakeBot.

        :param mappings: dict holding data for any offline mappings
        :param year: year of the report (used to date certain statements.
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        """
        super(LakeBot, self).__init__(mappings, year, new, cutoff, EDIT_SUMMARY)

        self.swb_q = None  # @todo: figure out/create the appropriate item
        self.eu_swb_p = 'P2856'  # eu_cd
        self.eu_swb_cat_p = None  # @todo surfaceWaterBodyCategory (qualifier or prop)
        self.eu_rbd_p = 'P2965'  # euRBDCode

        self.swb_cats = mappings.get('surfaceWaterBodyCategory')
        self.impact_types = mappings.get('swSignificantImpactType')

        self.load_known_items()

    def load_known_items(self):
        """
        Load existing eu_swb and eu_rbd items.

        The loaded values are Qids (without q-prefixes)
        """
        self.swb_items = helpers.fill_cache_wdqs(self.eu_swb_p)
        self.rbd_items = helpers.fill_cache_wdqs(self.eu_rbd_p)

    def set_common_values(self, data):
        """Set values shared by every lake in the dataset."""
        country = data.get('countryCode')
        country_q = self.mappings.get('countryCode').get(country).get('qId')

        rbd_q = self.rbd_items.get[data.get('euRBDCode')]

        wfd_year_datasets = self.mappings.get('dataset').get(self.year)

        self.country = self.wd.QtoItemPage(country_q)
        self.rbd = self.wd.QtoItemPage(rbd_q)
        self.dataset_q = wfd_year_datasets.get(country)
        self.ref = self.make_ref(data)

    def process_all_swb(self, data):
        """
        Handle all the surface water bodies in a single RBD.

        Only increments counter when updating an swb.

        :param data: dict of all the swb:s in the RBD
        """
        count = 0
        for entry_data in data:
            if self.cutoff and count >= self.cutoff:
                break
            eu_swb_code = entry_data.get('euSurfaceWaterBodyCode')
            item = None
            if eu_swb_code in self.swb_items:
                item = self.wd.QtoItemPage(self.swb_items[eu_swb_code])

            if item or self.new:
                self.process_single_swb(entry_data, item)
                count += 1

    def process_single_swb(self, data, item):
        """
        Process a swb (whether item exists or not).

        :param data: dict of data for a single swb
        :param item: Wikidata item associated with a swb, or None if one
            should be created.
        """
        item = item or self.create_new_swb_item(data)
        item.exists()

        # Determine claims
        name = data.get('surfaceWaterBodyName')  # in English per page 33
        protoclaims = self.make_protoclaims(data)

        # Upload claims
        self.wd.addLabelOrAlias('en', name, item)
        self.commit_claims(protoclaims, item)

    def create_new_swb_item(self, data):
        """Create a new swb item with some basic info and return."""
        # Add at lest label, description and
        # eu_swb_code (references can be added later)
        raise NotImplementedError

    def make_protoclaims(self, data):
        """Construct potential claims for an entry.

        @todo: More logic for ImpactType
        @todo: Qualifier property for SWB category
        @todo: Mapping of SWB categories

        :param data: dict of data for a single swb
        """
        protoclaims = dict()

        # P31: self.swb_q with surfaceWaterBodyCategory qualifier
        # @todo: Is P794 the appropriate qualifier (and should it be a
        #        qualifier or separate claim).
        swb_cat = self.swb_cats.get(data.get('surfaceWaterBodyCategory'))
        protoclaims['P31'] = WdS.Statement(
            self.wd.QtoItemPage(self.swb_q)).addQualifier(
                WdS.Qualifier(self.eu_swb_cat_p,
                              self.wd.QtoItemPage(swb_cat)))

        # self.eu_swb_p: euSurfaceWaterBodyCode
        protoclaims[self.eu_swb_p] = WdS.Statement(
            data.get('euSurfaceWaterBodyCode'))

        # P17: country
        protoclaims['P17'] = WdS.Statement(self.country)

        # P361: parent RBD
        protoclaims['P361'] = WdS.Statement(self.rbd)

        # P3643: swSignificantImpactType
        protoclaims['P3643'] = self.make_significant_impact_type(data)

        return protoclaims

    def make_significant_impact_type(self, data):
        """
        Construct statements for swSignificantImpactType data.

        Uses self.year as timepoint.

        Sets the 'novalue' statement if there are no impact types in the data.

        @todo: This needs to be made aware of pre-existing claim to be able to
               update the data. Specifically:
               * If a claim was previously present but is not any more:
                 add an end time as qualifier to that value.
               * If a claim was previously present and still is:
                 no change needed (but we should possibly us start time instead
                 of time point?
               * In both cases the reference can still be added.

        :param data: dict of data for a single swb
        """
        claims = []
        for impact in data.get('swSignificantImpactType'):
            impact = impact.split(' - ')[0]
            impact_q = self.impact_types.get(impact)
            claims.append(
                WdS.Statement(self.wd.QtoItemPage(impact_q)).addQualifier(
                    WdS.Qualifier('P585', self.year)))
        if not claims:
            # none were added for this year
            claims.append(
                WdS.Statement('novalue', special=True).addQualifier(
                    WdS.Qualifier('P585', self.year)))
        return claims

    @staticmethod
    def main(*args):
        """Command line entry point."""
        mappings = 'mappings.json'
        force_path = __file__
        in_file = None
        new = False
        cutoff = None
        year = '2016'

        # Load pywikibot args and handle local args
        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-in_file':
                in_file = value
            elif option == '-mappings':
                mappings = value
                force_path = None
            elif option == '-new':
                new = True
            elif option == '-year':
                year = value
            elif option == '-cutoff':
                cutoff = int(value)

        # require in_file
        if not in_file:
            raise pywikibot.Error('An in_file must be specified')

        # load and validate data and mappings
        mappings = helpers.load_json_file(mappings, force_path)
        data = WfdBot.load_data(in_file, key='SWB')
        validate_indata(data, mappings, year)

        # initialise LakeBot object
        bot = LakeBot(mappings, year, new=new, cutoff=cutoff)
        bot.set_common_values(data)

        bot.process_all_swb(data)


def validate_indata(data, mappings, year):
    """
    Validate that all encountered values needing to be mapped are.

    :param data: the source data from the xml
    """
    # validate @language
    # @todo: DO we use this?
    assert data.get('@language') in mappings.get('languageCode')
    # @todo: check descriptions?

    # validate <countryCode>
    assert data.get('countryCode') in mappings.get('countryCode')

    # ensure matching dataset exists
    assert mappings.get('dataset').get(year).get(data.get('countryCode'))

    # validate each <surfaceWaterBodyCategory> and
    # <swSignificantImpactType>
    swb_cats = set()
    impacts = set()
    for swb in data.get('SurfaceWaterBody'):
        swb_cats.add(swb.get('surfaceWaterBodyCategory'))
        impacts |= set(swb.get('swSignificantImpactType'))
    impacts = [impact.split(' - ')[0] for impact in impacts]

    assert all(swb_cat in mappings.get('surfaceWaterBodyCategory')
               for swb_cat in swb_cats)
    assert all(impact in mappings.get('swSignificantImpactType')
               for impact in impacts)


if __name__ == "__main__":
    LakeBot.main()
