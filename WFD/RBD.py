#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about River Basin Districts.

Author: Lokal_Profil
License: MIT

@todo: Follow up creation by ensuring that each CA has the corresponding RBD
    as it's P2541

usage:
    python RBD.py [OPTIONS]

&params;
"""
from __future__ import unicode_literals
import pywikibot

import wikidataStuff.helpers as helpers
import wikidataStuff.WdqToWdqs as WdqToWdqs
from wikidataStuff.WikidataStuff import WikidataStuff as WdS

from WFD.WFDBase import WfdBot
from WFD.PreviewItem import PreviewItem

parameter_help = """\
RBDbot options (may be omitted):
-year              Year to which the WFD data applies.
-new               if present new items are created on Wikidata, otherwise
                   only updates are processed.
-in_file           path to the data file
-mappings          path to the mappings file (if not "mappings.json")
-cutoff            number items to process before stopping (if not then all)
-preview_file      path to a file where previews should be outputted, sets the
                   run to demo mode

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-dir               directory in which user_config is located
-help              output all available options
"""
docuReplacements = {'&params;': parameter_help}
EDIT_SUMMARY = 'importing #RBD using data from #WFD'


class RbdBot(WfdBot):
    """Bot to enrich/create info on Wikidata for RBD objects."""

    def __init__(self, mappings, year, new=False, cutoff=None,
                 preview_file=None):
        """Initialise the RbdBot."""
        super(RbdBot, self).__init__(mappings, year, new, cutoff,
                                     EDIT_SUMMARY, preview_file=preview_file)

        self.rbd_q = 'Q132017'
        self.eu_rbd_p = 'P2965'
        self.area_unit = pywikibot.ItemPage(self.repo,
                                            helpers.get_unit_q('km²'))

        self.countries = mappings['countryCode']
        self.competent_authorities = mappings['CompetentAuthority']
        self.descriptions = mappings['descriptions']['RBD']
        self.rbd_id_items = self.load_existing_rbd()

    def load_existing_rbd(self):
        """Load existing RBD items and check all have unique ids."""
        item_ids = WdqToWdqs.make_claim_wdqs_search(
            'P31', q_value=self.rbd_q, optional_props=[self.eu_rbd_p, ])

        # invert and check existence and uniqueness
        rbd_id_items = {}
        for q_id, values in item_ids.iteritems():
            eu_rbd_code = values.get(self.eu_rbd_p)
            if not eu_rbd_code:
                raise pywikibot.Error(
                    'Found an RBD without euRBDCode: {}'.format(q_id))
            elif eu_rbd_code in rbd_id_items.keys():
                raise pywikibot.Error(
                    'Found an two RBDs with same euRBDCode: {} & {}'.format(
                        q_id, rbd_id_items[eu_rbd_code]))
            rbd_id_items[eu_rbd_code] = q_id
        return rbd_id_items

    def check_all_descriptions(self):
        """Check that the description are available for all languages."""
        WfdBot.validate_mapping(self.descriptions, self.langs, 'descriptions')

    def check_all_competent_authorities(self, data, country):
        """Check that all competent authorities are mapped.

        :param data: dict of all the rbds in the country with euRBDCode as keys
        :param country: name of the country
        """
        found_ca = []
        for d in data:
            found_ca.append(d['primeCompetentAuthority'])

        WfdBot.validate_mapping(self.competent_authorities, found_ca,
                                'CompetentAuthority')

    def check_country(self, country):
        """Check that the country is mapped and that languages are available.

        :param country: name of the country
        """
        country_data = self.countries.get(country)
        if not country_data:
            raise pywikibot.Error(
                "The country code \"{}\" was not mapped.".format(country))
        if not country_data.get('qId'):
            raise pywikibot.Error(
                "The country code \"{}\" was not mapped to Wikidata.".format(
                    country))

        diff = set(self.langs) - set(country_data.keys())
        if diff:
            raise pywikibot.Error(
                'The following languages should be mapped for country {} '
                'before continuing: {}'.format(country, ', '.join(diff)))

    def process_country_rbd(self, country, data):
        """Handle the RBDs of a single country.

        :param country: the country code as a string
        :param data: dict of all the rbds in the country with euRBDCode as keys
        """
        # check if CA in self.competent_authorities else raise error
        self.check_country(country)
        self.check_all_competent_authorities(data, country)

        # identify euRBDCode and check if it is in self.rbd_id_items
        count = 0
        for entry_data in data:
            if self.cutoff and count >= self.cutoff:
                break
            rbd_code = entry_data.get('euRBDCode')
            item = None
            if rbd_code in self.rbd_id_items.keys():
                item = self.wd.QtoItemPage(self.rbd_id_items[rbd_code])

            if item or self.new:
                self.process_single_rbd(entry_data, item, country)
                count += 1

    def process_single_rbd(self, data, item, country):
        """
        Process a rbd (whether item exists or not).

        :param data: dict of data for a single rbd
        :param item: Wikidata item associated with a rbd, or None if one
            should be created.
        :param country: the country code as a string
        """
        if not self.demo:
            item = item or self.create_new_rbd_item(data, country)
            item.exists()  # load the item contents

        # Determine claims
        labels = self.make_labels(data, with_alias=True)
        descriptions = self.make_descriptions(data)
        protoclaims = self.make_protoclaims(
            data, self.countries.get(country).get('qId'))

        # Upload claims
        if self.demo:
            self.preview_data.append(
                PreviewItem(labels, descriptions, protoclaims, item, self.ref))
        else:
            self.commit_labels(labels, item)
            self.commit_descriptions(descriptions, item)
            self.commit_claims(protoclaims, item)

    def create_new_rbd_item(self, entry_data, country):
        """
        Create a new rbd item with some basic info and return it.

        :param entry_data: dict of data for a single rbd
        :return: pywikibot.ItemPage
        """
        labels = self.make_labels(entry_data)
        desc = self.make_descriptions(entry_data)
        id_claim = self.wd.make_simple_claim(
            self.eu_rbd_p, entry_data.get('euRBDCode'))

        self.create_new_item(labels, desc, id_claim, EDIT_SUMMARY)

    def make_labels(self, entry_data, with_alias=False):
        """
        Make a label object from the available info.

        rbdName always gives the English names.
        internationalRBDName is sometimes in English, sometimes NULL and
        sometimes a comment.

        The output is a dict with lang as key and a list of names as value.

        @todo Figure out how to handle internationalRBDName (which can be in
              other languages, or a duplicate, or different English).

        :param entry_data: dict with the data for the rbd
        :param with_alias: add RBDcode to list of names
        """
        labels = {}

        name = entry_data.get('rbdName')
        if name and name.lower() not in self.bad_names:
            labels['en'] = [name, ]

        if with_alias:
            labels['en'] = labels.get('en') or []
            labels['en'].append(entry_data.get('euRBDCode'))
        return labels

    def make_descriptions(self, entry_data):
        """Make a description object from the available info.

        :param entry_data: dict with the data for the rbd
        :return: dict
        """
        description_type = self.descriptions.get('national')
        if entry_data.get('internationalRBD') == 'Yes':
            description_type = self.descriptions.get('international')

        return super(RbdBot, self).make_descriptions(description_type)

    def make_protoclaims(self, entry_data, country_q):
        """
        Construct potential claims for an entry.

        Expects that entry_data is a dict like:
        {
            "euRBDCode": "SE5101",
            "internationalRBD": "Yes",
            "internationalRBDName": "<long name>",
            "primeCompetentAuthority": "SE5",
            "otherCompetentAuthority": "SEHAV",
            "rbdArea": "990",
            "rbdAreaExclCW": "Data is missing",
            "rbdName": "<long name>",
            "subUnitsDefined": "No"
        }

        :param entry_data: dict with the data for the rbd per above
        :param country_q: q_id for the coutnry
        """
        protoclaims = {}
        #   P31: self.rbd_q
        protoclaims['P31'] = WdS.Statement(
            self.wd.QtoItemPage(self.rbd_q))
        #   self.eu_rbd_p: euRBDCode
        protoclaims[self.eu_rbd_p] = WdS.Statement(
            entry_data['euRBDCode'])
        #   P17: country (via self.countries)
        protoclaims['P17'] = WdS.Statement(
            self.wd.QtoItemPage(country_q))
        #   P137: primeCompetentAuthority (via self.competent_authorities)
        protoclaims['P137'] = WdS.Statement(
            self.wd.QtoItemPage(
                self.competent_authorities[
                    entry_data['primeCompetentAuthority']]))
        #   P2046: rbdArea + self.area_unit (can I set unknown accuracy)
        protoclaims['P2046'] = WdS.Statement(
            pywikibot.WbQuantity(entry_data['rbdArea'],
                                 unit=self.area_unit, site=self.wd.repo))
        return protoclaims

    # @todo: merge this with process_country_rbd and remove duplication
    #        with WfdBot.set_common_values()
    def process_all_rbd(self, data):
        """Handle every single RBD in a datafile."""
        wfd_year_datasets = self.mappings.get('dataset').get(self.year)

        # Check that all descriptions are present
        self.check_all_descriptions()

        # Find the country code in mappings (skip if not found)
        country = data.get('countryCode')
        # per schema "Code of the language of the file" but it isn't
        # language = data.get('@language')

        # Make a Reference (or possibly one per country)
        self.dataset_q = wfd_year_datasets[country]
        self.ref = self.make_ref(data)

        # Send rbd data for the country onwards
        self.process_country_rbd(
            country, helpers.listify(data.get('RBD')))

    @staticmethod
    def main(*args):
        """Command line entry point."""
        mappings = 'mappings.json'
        force_path = __file__
        in_file = None
        new = False
        cutoff = None
        preview_file = None
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
            elif option == '-preview_file':
                preview_file = value

        # require in_file
        if not in_file:
            raise pywikibot.Error('An in_file must be specified')

        # load mappings and initialise RBD object
        mappings = helpers.load_json_file(mappings, force_path)
        data = WfdBot.load_data(in_file, key='RBDSUCA')
        rbd = RbdBot(mappings, year, new=new, cutoff=cutoff,
                     preview_file=preview_file)
        rbd.set_common_values(data)

        rbd.process_all_rbd(data)

        if rbd.demo:
            rbd.output_previews()


if __name__ == "__main__":
    RbdBot.main()
