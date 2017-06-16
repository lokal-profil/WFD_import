#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Base class on which to build WFD import bots."""
from __future__ import unicode_literals
from builtins import dict, open
import requests
import xmltodict
import datetime

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS

parameter_help = """\
WfdBot options (may be omitted unless otherwise mentioned):
-in_file           [Required]path to the data file (local .json or online .xml)
-year              year to which the WFD data applies.
-new               if present new items are created on Wikidata, otherwise
                   only updates are processed.
-mappings          path to the mappings file (if not "mappings.json")
-cutoff            number items to process before stopping (if not then all)
-gml_file          path to the gml file (local .json or online .gml)
-preview_file      path to a file where previews should be outputted, sets the
                   run to demo mode

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-dir               directory in which user_config is located
-help              output all available options
"""


class UnmappedValueError(pywikibot.Error):
    """Error when encountering values which need to be manually mapped."""

    message = 'The following values for "{}" were not mapped: {}'

    def __init__(self, mapping, value, message=None):
        """
        Initialise the error.

        :param mapping: the name of the mapping object where the value was
            expected
        :param value: the missing value (or values)
        :param message: message used to override the default message
        """
        message = message or self.message
        super(UnmappedValueError, self).__init__(
            message.format(mapping, value))


class UnexpectedValueError(pywikibot.Error):
    """Error when encountering values which could not be handled."""

    message = 'The following value for "{}" was unexpected: {}'

    def __init__(self, field, value, message=None):
        """
        Initialise the error.

        :param field: the name of the (xml) field where the value was
            encountered
        :param value: the missing value (or values)
        :param message: message used to override the default message
        """
        message = message or self.message
        super(UnexpectedValueError, self).__init__(
            message.format(field, value))


class WfdBot(object):
    """Base bot to enrich Wikidata with info from WFD."""

    def __init__(self, mappings, year, new, cutoff, edit_summary,
                 gml_data=None, preview_file=None):
        """
        Initialise the WfdBot.

        :param mappings: dict holding data for any offline mappings
        :param year: year of the report (used to date certain statements).
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        :param edit_summary: string to append to all automatically generated
            edit summaries
        :param gml_data: dict holding data from a gml file, if provided
        :param preview_file: run in demo mode (create previews rather than
            live edits) and output the result to this file.
        """
        self.repo = pywikibot.Site().data_repository()
        self.wd = WdS(self.repo, edit_summary)
        self.new = new
        self.cutoff = cutoff
        self.mappings = mappings
        self.year = year
        self.wbtime_year = helpers.iso_to_WbTime(year)
        self.gml_data = gml_data
        self.preview_file = preview_file
        if preview_file:
            self.demo = True
        else:
            self.demo = False
        self.preview_data = []

        # known (lower case) non-names
        self.bad_names = ('not applicable', )

        # Languages in which we require translations of descriptions and
        # country names.
        self.langs = ('en', 'sv', 'fi')

        # the following must be overridden
        self.dataset_q = None
        self.ref = None
        self.language = None
        self.descriptions = None

    def set_common_values(self, data):
        """
        Set and validate values shared by every instance of the batch.

        :param data: dict of all the data for the batch
        """
        country = data.get('countryCode')
        try:
            self.country_dict = self.mappings.get('countryCode')[country]
            self.country = self.wd.QtoItemPage(self.country_dict['qId'])
        except KeyError:
            raise UnmappedValueError('countryCode', country)
        WfdBot.validate_mapping(self.country_dict, self.langs, 'countryCode')

        try:
            wfd_year_datasets = self.mappings.get('dataset')[self.year]
            self.dataset_q = wfd_year_datasets[country]
        except KeyError:
            raise UnmappedValueError('dataset', (self.year, country))

        # per schema "Code of the language of the file" but it isn't
        try:
            language = data.get('@language')
            self.language = self.mappings.get('languageCode')[language]
        except KeyError:
            raise UnmappedValueError('languageCode', language)

        self.ref = self.make_ref(data)

        if self.gml_data:
            self.set_common_gml_values()

    def set_common_gml_values(self):
        """Validate the gml values and set a gml reference."""
        # validate that language and units are mapped
        langs = set()
        units = set()
        for key, feature in self.gml_data.get('features').items():
            langs.add(feature.get('lang'))
            units.add(feature.get('area_unit'))
        # area_units are not guaranteed
        if None in units:
            units.remove(None)

        WfdBot.validate_mapping(
            self.mappings.get('languageCode'), langs, 'gml language codes')
        WfdBot.validate_mapping(
            self.mappings.get('units'), units, 'gml units')

        self.gml_ref = self.make_ref(self.gml_data)

    def commit_labels(self, labels, item):
        """
        Add labels and aliases to item.

        :param labels: label object
        :param item: item to add labels to
        """
        if labels:
            self.wd.add_multiple_label_or_alias(
                labels, item, case_sensitive=False)

    def commit_descriptions(self, descriptions, item):
        """
        Add descriptions to item.

        :param descriptions: description object
        :param item: item to add descriptions to
        """
        if descriptions:
            self.wd.add_multiple_descriptions(descriptions, item)

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

        for pc_prop, pc_value in protoclaims.items():
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

    def make_descriptions(self, description_dict):
        """
        Make a description object in the required languages.

        The provided description strings can support taking the country name
        as a formatting variable.

        :param description_dict: dict with language codes as keys and
            description string as value.
        :return: description object
        """
        descriptions = dict()
        for lang in self.langs:
            desc = description_dict.get(lang).format(
                country=self.country_dict.get(lang))
            descriptions[lang] = desc
        return descriptions

    def add_local_name(self, labels, code):
        """
        Add local names from gml data to label dict if gml is provided.

        :param labels: dict of language-name pairs to which local name is added
        :param code: the SWB or RBD identifier code
        """
        if self.gml_data:
            feature_data = self.gml_data['features'].get(code)
            lang_code = feature_data.get('lang')
            lang = self.mappings.get('languageCode').get(lang_code)
            names = feature_data.get('name')
            if names:
                names_list = [name.strip() for name in names.split(' / ')]
                labels[lang] = labels.get(lang) or []
                labels[lang].extend(names_list)

    def create_new_item(self, labels, desc, id_claim, summary):
        """
        Create a new item with some basic info and return it.

        The new item is created with labels, descriptions and an id claim.
        This allows the item to be found in a second pass should the script
        crash before adding further claims.

        The id claim need not contain a reference (this can be handled
        during the later stages).

        :param labels: a label dictionary
        :param desc: a description dictionary
        :param id_claim: a pywikibot.Claim adding the unique id to the item
        :param summary: to use for the edit
        :return: pywikibot.ItemPage
        """
        labels = WfdBot.convert_language_dict_to_json(labels, typ='labels')
        desc = WfdBot.convert_language_dict_to_json(desc, typ='descriptions')

        item_data = {
            "labels": labels,
            "descriptions": desc,
            "claims": [id_claim.toJSON(), ]
        }

        try:
            return self.wd.make_new_item(item_data, summary)
        except pywikibot.data.api.APIError as e:
            raise pywikibot.Error('Error during item creation: {:s}'.format(e))

    def output_previews(self):
        """Output any PreviewItems to the preview_file."""
        with open(self.preview_file, 'w', encoding='utf-8') as f:
            for preview in self.preview_data:
                f.write(preview.make_preview_page())
                f.write('--------------\n\n')
        pywikibot.output('Created "{}" for previews'.format(self.preview_file))

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

    @staticmethod
    def load_gml_data(in_file, feature_key):
        """
        Load data from a gml file.

        This also repackages the features to ensure the structure is the same
        for both RBDs and SWBs.

        As there is no creation date in the data one needs to be extract
        from the filename instead.

        Ensures that the outputted data is compatible with make_ref().

        :param in_file: a url to an .gml file or the path to a local .json
            dump of the same file.
        :param feature_key: key for the type of feature we are looking for.
        :return: dict of the loaded data
        """
        raw_data = WfdBot.load_data(in_file, key='wfdgml:FeatureCollection')

        # repackage features
        gml_features = {}
        for feature in raw_data['wfdgml:featureMember']:
            feature_data = {}
            entry_data = feature[feature_key]
            feature_data['name'] = entry_data['wfdgml:nameText']
            feature_data['lang'] = entry_data['wfdgml:nameLanguage']
            feature_data['area'] = entry_data.get('wfdgml:sizeValue')
            feature_data['area_unit'] = entry_data.get('wfdgml:sizeUom')
            feature_data['int_name'] = entry_data.get(
                'wfdgml:nameTextInternational')
            eu_cd = entry_data['wfdgml:thematicIdIdentifier']
            gml_features[eu_cd] = feature_data

        # extract creation date from filename
        date = raw_data['source_url'].rpartition('_')[2].rpartition('.')[0]
        iso_date = '{yyyy}-{mm}-{dd}'.format(
            yyyy=date[:4], mm=date[4:6], dd=date[6:])

        data = {
            'features': gml_features,
            'source_url': raw_data['source_url'],
            'retrieval_date': raw_data['retrieval_date'],
            '@creationDate': iso_date
        }
        return data

    @staticmethod
    def validate_mapping(found, expected, label):
        """
        Validate that all of the expected key are found in a given mapping.

        :param found: the found mapping. Can either be a dict of values or a
            dict of dicts with values.
        :param expected: the expected keys in the dict or each containing dict
        :param label: a label describing the mapping
        """
        expected = set(expected)
        is_dict = False
        for k, v in found.items():
            if isinstance(v, dict):
                is_dict = True

        if is_dict:
            for k, v in found.items():
                diff = expected - set(v.keys())
                if diff:
                    value = '({}, [{}])'.format(k, ', '.join(sorted(diff)))
                    raise UnmappedValueError(label, value)
        else:
            diff = expected - set(found.keys())
            if diff:
                value = '[{}]'.format(', '.join(sorted(diff)))
                raise UnmappedValueError(label, value)

    @staticmethod
    def handle_args(args):
        """
        Parse and load all of the basic arguments.

        Also passes any needed arguments on to pywikibot and sets any defaults.

        :param args: list of arguments to be handled
        :return: dict of options
        """
        options = {
            'mappings': 'mappings.json',
            'force_path': __file__,
            'in_file': None,
            'new': False,
            'cutoff': None,
            'preview_file': None,
            'year': '2016',
            'gml_file': None
        }

        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-in_file':
                options['in_file'] = value
            elif option == '-mappings':
                options['mappings'] = value
                options['force_path'] = None
            elif option == '-new':
                options['new'] = True
            elif option == '-year':
                options['year'] = value
            elif option == '-cutoff':
                options['cutoff'] = int(value)
            elif option == '-preview_file':
                options['preview_file'] = value
            elif option == '-gml_file':
                options['gml_file'] = value

        # require in_file
        if not options.get('in_file'):
            raise pywikibot.Error('An in_file must be specified')

        return options

    # @todo: T167661 Move to WikidataStuff.helpers?
    @staticmethod
    def convert_language_dict_to_json(data, typ):
        """
        Convert a description/label/alias dictionary to input formatted json.

        The json format is needed during e.g. item creation.

        :param data: a language-value dictionary where value is either a string
            or list of strings.
        :param typ: the type of output. Must be one of descriptions, labels or
            aliases
        :return: dict
        """
        if typ not in ('descriptions', 'labels', 'aliases'):
            raise ValueError('"{0}" is not a valid type for '
                             'convert_language_dict_to_json().'.format(typ))
        allow_list = (typ == 'aliases')

        json_data = dict()
        for lang, val in data.items():
            if not allow_list and isinstance(val, list):
                if len(val) == 1:
                    val = val[0]
                else:
                    raise ValueError('{0} must not have a list of values for '
                                     'a single language.'.format(typ))
            json_data[lang] = {'language': lang, 'value': val}
        return json_data
