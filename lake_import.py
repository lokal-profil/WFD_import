#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about River Basin Districts.

Author: Lokal_Profil
License: MIT

usage:
    python WFD/lake_import.py [OPTIONS]

&params;
"""
import pywikibot
import wikidataStuff.helpers as helpers
import wikidataStuff.wdqsLookup as wdqsLookup
from wikidataStuff.WikidataStuff import WikidataStuff as WD
import wfd_helpers

parameter_help = u"""\
Lakebot options (may be omitted):
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
EDIT_SUMMARY = u'import using #WFDdata'


class LakeBot():
    """Bot to enrich/create info on Wikidata for lake objects."""

    def __init__(self, mappings, new=False, cutoff=None):
        self.repo = pywikibot.Site().data_repository()
        self.wd = WD(self.repo, EDIT_SUMMARY)
        self.new = new
        self.cutoff = cutoff

    @staticmethod
    def main(*args):
        """Command line entry point."""
        mappings = 'mappings.json'
        force_path = __file__
        in_file = None
        new = False
        cutoff = None

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
            elif option == '-cutoff':
                cutoff = int(value)

        # require in_file
        if not in_file:
            raise pywikibot.Error('An in_file must be specified')

        # load mappings and initialise RBD object
        mappings = helpers.load_json_file(mappings, force_path)
        data = wfd_helpers.load_data(in_file, key='SWB')
        rbd = LakeBot(mappings, new=new, cutoff=cutoff)

        rbd.process_all_rbd(data)

if __name__ == "__main__":
    LakeBot.main()
