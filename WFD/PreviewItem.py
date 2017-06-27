#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Generate a preview of a single updated/created WFD item."""
# Based on PreviewTable by Alicia Fagerving
from __future__ import unicode_literals

from collections import OrderedDict

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WdS
# @todo: T167661 Generalise and move to WikidataStuff


class PreviewItem(object):
    """A visualization of a single created/updated WFD item."""

    def __init__(self, labels, descriptions, protoclaims, item, ref=None):
        """
        Initialise the PreviewItem.

        :param labels: dict holding the label/aliases per language code
        :param descriptions: dict holding the descriptions per language code
        :param protoclaims: dict of Statements per (P-prefixed) property-id
        :param item: the pywikibot.ItemPage to which the data should be added
            (None for a new item)
        :param ref: a Reference which is attached to every single protoclaim,
            unless overridden on a per statement basis.
        """
        # sort dicts by key to ensure consistent behaviour
        self.labels_dict = OrderedDict(
            sorted(labels.items(), key=lambda t: t[0]))
        self.desc_dict = OrderedDict(
            sorted(descriptions.items(), key=lambda t: t[0]))
        self.item = item

        # sort by the numeric part of the property id
        self.protoclaims = OrderedDict(
            sorted(protoclaims.items(), key=lambda t: int(t[0][1:])))

        self.ref = ref

    def make_preview_page(self):
        """Create a preview of the entire PreviewItem."""
        txt = ''
        txt += '{key}:\n{data}\n\n'.format(
            key=PreviewItem.make_text_bold('Labels | Aliases'),
            data=self.format_labels())
        txt += '{key}:\n{data}\n\n'.format(
            key=PreviewItem.make_text_bold('Descriptions'),
            data=self.format_descriptions())
        txt += '{key}: {data}\n\n'.format(
            key=PreviewItem.make_text_bold('Matching item'),
            data=self.format_item())

        if self.ref:
            txt += '{key}:\n{data}\n\n'.format(
                key=PreviewItem.make_text_bold(
                    'Default reference (same for all claims)'),
                data=PreviewItem.format_reference(self.ref))
        txt += '{key}:\n{data}\n\n'.format(
            key=PreviewItem.make_text_bold('Claims'),
            data=self.format_protoclaims())
        return txt

    def format_protoclaims(self):
        """Create a preview table for the protoclaims."""
        table_head = (
            "{| class='wikitable'\n"
            "|-\n"
            "! Property\n"
            "! Value\n"
            "! Qualifiers\n"
        )
        table_end = '|}'
        table_row = (
            '|-\n'
            '| {prop} \n'
            '| {value} \n'
            '| {quals} \n'
        )

        # format each table row
        rows = []
        for prop, statements in self.protoclaims.items():
            if not statements:
                continue
            prop = PreviewItem.make_wikidata_template(prop)
            for statement in helpers.listify(statements):
                quals = ''
                if statement.quals:
                    if len(statement.quals) > 1:
                        quals = ['* {}'.format(PreviewItem.format_qual(qual))
                                 for qual in statement.quals]
                    else:
                        quals = [PreviewItem.format_qual(statement.quals[0])]

                ref = ''
                if statement.ref:
                    ref = PreviewItem.format_reference(statement.ref)

                rows.append(
                    {
                        'prop': prop,
                        'value': PreviewItem.format_itis(statement),
                        'quals': ' \n'.join(quals),
                        'references': ref
                    }
                )

        # if any statement has a reference then add the reference column
        if any(row.get('references') for row in rows):
            default_ref = PreviewItem.make_text_italics('default reference')
            table_head += '! References\n'
            table_row += '| {references} \n'
            if self.ref:
                for row in rows:
                    row['references'] = row['references'] or default_ref

        # start table construction
        table = table_head
        for row in rows:
            table += table_row.format(**row)
        table += table_end

        return table

    @staticmethod
    def format_qual(qual):
        """Create a preview for a single Qualifier."""
        prop = PreviewItem.make_wikidata_template(qual.prop)
        itis = PreviewItem.format_itis(qual.itis)
        return '{0}: {1}'.format(prop, itis)

    @staticmethod
    def format_reference(ref):
        """Create a preview for a single Reference."""
        txt = ''
        if ref.source_test:
            txt += ':{}:\n'.format(PreviewItem.make_text_italics('tested'))
            for claim in ref.source_test:
                txt += ':*{}\n'.format(PreviewItem.format_claim(claim))
        if ref.source_notest:
            txt += ':{}:\n'.format(PreviewItem.make_text_italics('not tested'))
            for claim in ref.source_notest:
                txt += ':*{}\n'.format(PreviewItem.format_claim(claim))

        return txt

    @staticmethod
    def format_claim(claim):
        """Create a preview for a single pywikibot.Claim."""
        special = False
        itis = claim.getTarget()
        if claim.getSnakType() != 'value':
            special = True
            itis = claim.getSnakType()

        return '{prop}: {itis}'.format(
            prop=PreviewItem.make_wikidata_template(claim.id),
            itis=PreviewItem.format_itis(itis, special)
        )

    @staticmethod
    def format_itis(itis, special=False):
        """
        Create a preview for the itis component of a Statement.

        :param itis: a Statement or the itis component of a Statement or
            Qualifier.
        :param special: if it is a special type of value (i.e. novalue,
            somevalue). Is set automatically if a Statement is passed to itis.
        """
        # handle the case where a Statement was passed
        if isinstance(itis, WdS.Statement):
            special = itis.special
            itis = itis.itis

        if isinstance(itis, pywikibot.ItemPage):
            return PreviewItem.make_wikidata_template(itis)
        elif special:
            return PreviewItem.make_wikidata_template(itis, special=True)
        elif isinstance(itis, pywikibot.WbQuantity):
            unit = itis.get_unit_item() or ''
            amount = itis.amount
            if unit:
                unit = PreviewItem.make_wikidata_template(unit)
            return '{} {}'.format(amount, unit).strip()
        elif isinstance(itis, pywikibot.WbTime):
            return itis.toTimestr()
        else:
            return str(itis)

    # @todo: T167791
    def format_labels(self):
        """
        Create a label(s) preview.

        The first label is italicised (to indicate it is the preferred label
        whereas the rest are aliases).

        :return: string
        """
        preview = ''
        for lang, labels in self.labels_dict.items():
            if labels:
                labels = [PreviewItem.make_text_italics(labels[0])] + \
                    labels[1:]
                preview += '* {}: {}\n'.format(
                    PreviewItem.make_text_bold(lang), ' | '.join(labels))
        return preview

    def format_descriptions(self):
        """
        Create a descriptions(s) preview.

        :return: string
        """
        preview = ''
        for lang, description in self.desc_dict.items():
            preview += '* {}: {}\n'.format(
                PreviewItem.make_text_bold(lang), description)
        return preview

    def format_item(self):
        """
        Create an item preview.

        :return: string
        """
        if self.item:
            return PreviewItem.make_wikidata_template(self.item)
        else:
            return '–'  # New item created

    @staticmethod
    def make_text_bold(text):
        """Wikitext format the text as bold."""
        return "'''{}'''".format(text)

    @staticmethod
    def make_text_italics(text):
        """Wikitext format the text as italics."""
        return "''{}''".format(text)

    @staticmethod
    def make_wikidata_template(wd_entry, special=False):
        """
        Make a wikidata template for items and properties.

        :param wd_entry: a Q/P prefixed item/property id or an
            ItemPage/PropertyPage
        :param special: if it is a special type of value
            (i.e. novalue, somevalue)
        :return: string
        """
        if isinstance(wd_entry, (pywikibot.ItemPage, pywikibot.PropertyPage)):
            wd_id = wd_entry.id
        else:
            wd_id = wd_entry

        typ = None
        if helpers.is_str(wd_id) and (
                wd_id.startswith('Q') or wd_id.startswith('P')):
            typ = wd_id[0]
        elif special:
            typ = "Q'"
            # convert to format used by the template
            if wd_id == 'somevalue':
                wd_id = 'some value'
            elif wd_id == 'novalue':
                wd_id = 'no value'
            else:
                raise ValueError(
                    'Sorry but "{}" is not a recognized special '
                    'value/snaktype.'.format(wd_id))
        else:
            raise ValueError(
                'Sorry only items and properties are supported, not whatever '
                '"{}" is.'.format(wd_id))

        return '{{%s|%s}}' % (typ, wd_id)
