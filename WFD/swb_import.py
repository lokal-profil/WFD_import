#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Surface Water Bodies.

Author: Lokal_Profil
License: MIT

usage:
    python swb_import.py [OPTIONS]

&params;
"""
from __future__ import unicode_literals
from builtins import dict

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS

from WFD.WFDBase import WfdBot, UnmappedValueError, UnexpectedValueError

parameter_help = """\
SwbBot options (may be omitted):
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


class SwbBot(WfdBot):
    """Bot to enrich/create info on Wikidata for SWB objects."""

    def __init__(self, mappings, year, new=False, cutoff=None):
        """
        Initialise the SwbBot.

        :param mappings: dict holding data for any offline mappings
        :param year: year of the report (used to date certain statements).
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        """
        super(SwbBot, self).__init__(mappings, year, new, cutoff,
                                     EDIT_SUMMARY)

        self.eu_swb_p = 'P2856'  # eu_cd
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
        """
        Set and validate values shared by every SWB in the dataset.

        :param data: dict of all the SWB:s in the RBD
        """
        super(SwbBot, self).set_common_values(data)
        try:
            rbd_q = self.rbd_items.get[data.get('euRBDCode')]
            self.rbd = self.wd.QtoItemPage(rbd_q)
        except KeyError:
            raise UnmappedValueError('online rbd objects',
                                     data.get('euRBDCode'))

        self.descriptions = self.mappings.get('descriptions').get('SWB')
        WfdBot.validate_mapping(self.descriptions, self.langs, 'descriptions')

    def process_all_swb(self, data):
        """
        Handle all the surface water bodies in a single RBD.

        Only increments counter when an swb is updated.

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
        item.exists()  # load the item contents

        # Determine claims
        labels = self.make_labels(data)
        descriptions = self.make_descriptions(self.descriptions)
        protoclaims = self.make_protoclaims(data)

        # Upload claims
        self.commit_labels(labels, item)
        self.commit_descriptions(descriptions, item)
        self.commit_claims(protoclaims, item)

    def make_labels(self, data):
        """
        Make a label object from the available info.

        surfaceWaterBodyName always gives the English name but may also be
        set to 'not applicable' (per p.33 of the WFD specifications).

        :param data: dict of data for a single swb
        :return: label dict
        """
        labels = {}
        name = data.get('surfaceWaterBodyName')
        if name and name.lower() not in self.bad_names:
            labels['en'] = name
        return labels

    def create_new_swb_item(self, data):
        """
        Create a new swb item with some basic info and return it.

        :param data: dict of data for a single swb
        :return: pywikibot.ItemPage
        """
        labels = self.make_labels(data)
        desc = self.make_descriptions(self.descriptions)
        id_claim = self.wd.make_simple_claim(
            self.eu_swb_p, data.get('euSurfaceWaterBodyCode'))

        self.create_new_item(labels, desc, id_claim, EDIT_SUMMARY)

    def make_protoclaims(self, data):
        """
        Construct potential claims for an entry.

        :param data: dict of data for a single swb
        """
        protoclaims = dict()

        # P31: surfaceWaterBodyCategory
        swb_cat = self.swb_cats.get(data.get('surfaceWaterBodyCategory'))
        protoclaims['P31'] = WdS.Statement(self.wd.QtoItemPage(swb_cat))

        # self.eu_swb_p: euSurfaceWaterBodyCode
        protoclaims[self.eu_swb_p] = WdS.Statement(
            data.get('euSurfaceWaterBodyCode'))

        # P17: country
        protoclaims['P17'] = WdS.Statement(self.country)

        # P361: parent RBD
        protoclaims['P361'] = WdS.Statement(self.rbd)

        # P3643: swSignificantImpactType
        protoclaims['P3643'] = self.make_significant_impact_type(data)

        # P4002: swEcologicalStatusOrPotentialValue
        protoclaims['P4002'] = self.make_general_ecological_status(data)

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
        :return: [Statement]
        """
        # @todo: Support for UNKN, OTHE (somevalue) + NOTA, NOSI (novalue)
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

    def make_general_ecological_status(self, data):
        """
        Construct statements for swEcologicalStatusOrPotentialValue data.

        Uses self.year as timepoint (for the year the status was decided).

        swEcologicalAssessmentYear gives the year, or range for which the
        data was collected/assesments made.

        Sets the 'somevalue' statement if the status is "Unknown".
        Skips if the value is "Not applicable".

        :param data: dict of data for a single swb
        :return: Statement
        """
        claim = None
        mapping = self.mappings.get('swEcologicalStatusOrPotentialValue')
        raw_val = data.get('swEcologicalStatusOrPotentialValue')
        mapped_val = mapping.get(raw_val)
        if mapped_val:
            claim = WdS.Statement(self.wd.QtoItemPage(mapped_val))
        elif raw_val == 'Unknown':
            claim = WdS.Statement('somevalue', special=True)
        elif raw_val == 'Not applicable':
            return
        else:
            raise UnexpectedValueError(
                'swEcologicalStatusOrPotentialValue', raw_val)

        if claim:
            claim.addQualifier(WdS.Qualifier('P585', self.year))
            # @todo: handle measurement years https://www.wikidata.org/wiki/Wikidata:Project_chat#Date_qualifiers  # noqa E501

        return claim

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
        validate_indata(data, mappings)

        # initialise SwbBot object
        bot = SwbBot(mappings, year, new=new, cutoff=cutoff)
        bot.set_common_values(data)

        bot.process_all_swb(data)


def validate_indata(data, mappings):
    """
    Validate that all encountered values needing to be mapped are.

    :param data: the source data from the xml
    :param mappings: dict holding data for any offline mappings
    """
    # validate mapping of each <surfaceWaterBodyCategory> and
    # <swSignificantImpactType>
    swb_cats = set()
    impacts = set()
    for swb in data.get('SurfaceWaterBody'):
        swb_cats.add(swb.get('surfaceWaterBodyCategory'))
        impacts |= set(helpers.listify(swb.get('swSignificantImpactType')))
    impacts = [impact.split(' - ')[0] for impact in impacts]

    WfdBot.validate_mapping(
        mappings.get('surfaceWaterBodyCategory'), swb_cats,
        'surfaceWaterBodyCategory')
    WfdBot.validate_mapping(
        mappings.get('swSignificantImpactType'), impacts,
        'swSignificantImpactType')


if __name__ == "__main__":
    SwbBot.main()
