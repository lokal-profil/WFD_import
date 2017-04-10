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
import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS

from WFDBase import WfdBot

parameter_help = u"""\
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
EDIT_SUMMARY = u'importing #SWB using data from #WFD'


class LakeBot(WfdBot):
    """Bot to enrich/create info on Wikidata for lake objects."""

    def __init__(self, mappings, year='2016', new=False, cutoff=None):
        """
        Initialise the LakeBot.

        :param mappings: dict holding data for any offline mappings
        :param year: year of the report (used to date certain statements.
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        """
        super(LakeBot, self).__init__(mappings, new, cutoff, EDIT_SUMMARY)
        self.year = year
        self.dataset_q = 'Q27074294'

        self.swb_q = None  # @todo: figure out/create the appropriate item
        self.eu_swb_p = 'P2856'  # eu_cd
        self.eu_swb_cat_p = None  # @todo surfaceWaterBodyCategory (qualifier or prop)
        self.eu_rbd_p = 'P2965'  # euRBDCode

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
        country_q = self.mappings('countryCode').get(country).get('qId')
        rbd_q = self.rbd_items.get(data.get('euRBDCode'))

        self.country = self.wd.QtoItemPage(country_q)
        self.rbd = self.wd.QtoItemPage(rbd_q)
        self.ref = self.make_ref(data)

    def validate_indata(self, data):
        """
        Validate that all encountered values needing to be mapped are.

        :param data: the source data from the xml
        """
        # validate @language
        # @todo: DO we use this?
        assert data.get('@language') in self.mappings('languageCode')
        # @todo: check descriptions?

        # validate <countryCode>
        assert data.get('countryCode') in self.mappings('countryCode')

        # validate <euRBDCode>
        assert data.get('euRBDCode') in self.rbd_items

        # validate each <surfaceWaterBodyCategory> and
        # <swSignificantImpactType>
        swb_cats = set()
        impacts = set()
        for swb in data.get('SurfaceWaterBody'):
            swb_cats.add(swb.get('surfaceWaterBodyCategory'))
            impacts |= set(swb.get('swSignificantImpactType'))
        impacts = [impact.split(' - ')[0] for impact in impacts]

        assert all(swb_cat in self.mappings('surfaceWaterBodyCategory')
                   for swb_cat in swb_cats)
        assert all(impact in self.mappings('swSignificantImpactType')
                   for impact in impacts)

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
        Process (whether item exists or not)

        :param data: dict of data for a single swb
        :param item: Wikidata item asssociated with a swb, or None if one
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
        protoclaims = {}

        # P31: self.swb_q with surfaceWaterBodyCategory qualifier
        # @todo: Is P794 the appropriate qualifier
        swb_cat = self.mappings('surfaceWaterBodyCategory').get(
            data.get(u'surfaceWaterBodyCategory'))
        protoclaims[u'P31'] = WdS.Statement(
            self.wd.QtoItemPage(self.swb_q)).addQualifier(
                WdS.Qualifier(self.eu_swb_cat_p,
                              self.wd.QtoItemPage(swb_cat)))

        # self.eu_swb_p: euSurfaceWaterBodyCode
        protoclaims[self.eu_swb_p] = WdS.Statement(
            data.get(u'euSurfaceWaterBodyCode'))

        # P17: country (via self.countries)
        protoclaims[u'P17'] = WdS.Statement(self.country)

        # P361: parent RBD
        protoclaims[u'P361'] = WdS.Statement(self.rbd)

        # P3643: swSignificantImpactType with year as timePoint
        # @todo: Needs knowledge of existing claims to handle adding endtimes
        # and not adding timepoints for ongoing claims (but change these to
        # start time?)
        protoclaims[u'P3643'] = []
        for impact in data.get('swSignificantImpactType'):
            impact = impact.split(' - ')[0]
            impact_q = self.mappings('swSignificantImpactType').get(impact)
            protoclaims[u'P3643'].append(
                WdS.Statement(self.wd.QtoItemPage(impact_q)).addQualifier(
                    WdS.Qualifier('P585', self.year)))
        if not protoclaims[u'P3643']:
            # none were added for this year
            protoclaims[u'P3643'].append(
                WdS.Statement('novalue', special=True).addQualifier(
                    WdS.Qualifier('P585', self.year)))

        return protoclaims

    @staticmethod
    def main(*args):
        """Command line entry point."""
        mappings = 'mappings.json'
        force_path = __file__
        in_file = None
        new = False
        cutoff = None
        year = None

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

        # load mappings and initialise LakeBot object
        mappings = helpers.load_json_file(mappings, force_path)
        data = WfdBot.load_data(in_file, key='SWB')
        bot = LakeBot(mappings, year, new=new, cutoff=cutoff)
        bot.validate_indata(data)
        bot.set_common_values(data)

        bot.process_all_swb(data)


if __name__ == "__main__":
    LakeBot.main()
