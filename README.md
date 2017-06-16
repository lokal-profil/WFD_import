## WFD_import
*WFD import* are a collection of scripts and tools for batch importing of
European water data, reported under the Water Framework Directive, to Wikidata.

It currently supports harvesting data on River Basin Districts (RBDs) and
Surface Water Bodies (SWBs).

### How to run
To do a basic run simply call either `RBD.py` or `swb_import.py` from the
commandline together with the `-in_file:<path>` argument. The `-in_file` <path>
value should be the url to an RBDSUCA .xml file for a RBD import or an SWB
file(there is one per RBD) for an SWB import.

The xml files only include the names of the RBD/SWB in English (if any), to
load the names in a local language use the `-gml_file:<path>` argument together
with the path to a .gml file belonging to the RBD or SWB dataset.

You can also use the `WfdBot.load_data()` to create a json dump of either of
the .xml or .gml files. The local json dumps can then be used together with the
`-in_file` or `gml_file` argument.

To create new items, rather than just enriching pre-existing ones, use the
`-new` flag. A new item is one where the unique RBD/SWB code is not yet
associated with an item on Wikidata.

To ensure no data is written to Wikidata you may use the `-simulate` flag. The
`-preview_file:<path>` also prevents data from being written to Wikidata,
instead outputting a preview of the data, in wikitext, to the file at the
specified path. This can be combined with the `-cutoff:<num>` argument which
limits the number of items being processed.

### Where to find the data files
*Sweden is used as an example in all links below:*

The data can be found on the [Central Data Repository](https://cdr.eionet.europa.eu/)
(CDR) under [*European Union (EU) obligations/Water Framework Directive: River Basin Management Plans - 2016 Reporting*](https://cdr.eionet.europa.eu/se/eu/wfd2016/).

* The [RBDSUCA file](https://cdr.eionet.europa.eu/se/eu/wfd2016/rbdsuca/envwnulfg/RBDSUCA_SE_20170329.xml/manage_document)
  (for Competent Authorities and RBDs) is found under *National RBDSUCA*.
* The [SWB files](https://cdr.eionet.europa.eu/se/eu/wfd2016/districts/se1/envwntvaw/SWB_SE_20170411.xml/manage_document)
  can be found in their respective RBD directories under *River Basin Districts*.
* Both .gml files (one for RBDs and one for SWBs) are located under
  [*National spatial data*](https://cdr.eionet.europa.eu/se/eu/wfd2016/spatial/envwdqi7a/).

It is worth nothing that there may be multiple releases of data (separate
directories), always chose the most recent. For the .gml files it varies from
country to country whether either of them are made accessible to the public.

### How to add a new country
Before investing energy into adding support for a new country you should ensure
that the license of the data is compatible with Wikidata (CC0). The default
license on CDR is CC BY which is not free enough. You therefore need a
source indicating that the member country released their data under a more
permissive CC0 license.

* Create an item for the Report, and add to the "dataset" entry in
  `mappings.json`. See [the 2016 Sweden report](https://www.wikidata.org/wiki/Q29563137)
  for an example item.
* Add the country to the "countryCode" entry in `mappings.json`.
* Add a mapping of the three-letter language code to the two-letter code used
  on Wikidata to the "languageCode" entry in `mappings.json`.
* Create items for each of the Competent Authorities listed in the RBDSUCA
  file, then and add these to the "CompetentAuthority" entry in `mappings.json`.
  Instructions for the claims to use on a Competent Authorities item can be
  found [on this page](https://se.wikimedia.org/wiki/Projekt:WFD-data_till_Wikidata_2016/Mappings#CompetentAuthority).
* If you wish to add support for a new language add it to `self.langs` in
  `WfdBot.__init__` and ensure all the required entries in `mappings.json` have
  been translated.

During the run the above additions are validated to ensure all the required
mappings are present. Feel free to add any new mappings as a pull request to
this repository.

To import the data first run the RBD importer (with `-new` if needed) before
running the SWB importer.

### Known issues and limitations
The results are of curse limited by the data quality. If a country has not
followed the guidelines on e.g. language labeling then imported data will also
be wrong.

The full logic of Significant Impact has not been implemented. Specifically it
does not adapt its output based on pre-existing values for other years. See
[see the porperty proposal](https://www.wikidata.org/wiki/Wikidata:Property_proposal/Significant_environmental_impact_types)
for the full logic.

RBD does not make use of `internationalRBDName` (nor does either SWB or RBD make
use of `nameTextInternational`). Although this is supposed to be an international
(English) label the field was found to hold a variety of content.

### Issues
Issues and bugs are tracked on [Phabricator](https://phabricator.wikimedia.org/tag/wmse-wfd-data-to-wikidata-2016/).

### Installation
if `pip -r requirements.txt` does not work correctly you might have to add
the `--process-dependency-links` flag to ensure you get the right version
of pywikibot and [lokal-profil/wikidata-stuff](https://github.com/lokal-profil/wikidata-stuff).

### Note
This repository was split off from 
[lokal-profil/wikidata_batches](https://github.com/lokal-profil/wikidata_batches)
so the history might be a bit mixed up.
