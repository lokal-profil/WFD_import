#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Shared helper functions for the WFD import.
"""
import requests
import xmltodict
import datetime
import wikidataStuff.helpers as helpers


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


def load_data(in_file, key=None):
    """
    Load the data from the in_file.

    :param in_file: a url to an xml file or the path to a local json dump of
        the same file.
    :param key: optional key used by load_xml_url_data
    :return: the loaded data
    """
    if in_file.partition('://')[0] in ('http', 'https'):
        return load_xml_url_data(in_file, key)
    return helpers.load_json_file(in_file)
