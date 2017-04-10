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

        self.swb_q = None  #@todo: figure out/create the appropriate item
        self.eu_swb_p = 'P2856'  # eu_cd
        self.eu_swb_cat_p = None  #@todo surfaceWaterBodyCategory (qualifier or prop)
        self.eu_rbd_p = 'P2965'  # euRBDCode

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
