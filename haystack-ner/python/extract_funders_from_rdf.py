#!/bin/env python
import csv
import datetime as dt
import os
import pycountry
import logging
from typing import List
import rdflib
from rdflib import Graph, Literal, RDF, URIRef, plugins
from rdflib.namespace import FOAF , XSD
from rdflib.namespace import SKOS
from rdflib.namespace import Namespace
from rdflib.plugins import sparql
import yaml


def search_for_label(graph: Graph, label: str, language: str = None) -> List[rdflib.query.ResultRow]:
    """Search for label in graph. Returns a list of tuples related to the label.

    Args:
        graph (Graph, label, optional) ->list(tuple).

    Returns:
        [Rows]: Rows are Tuples containing the Concept and a (pref|alt)Lable
    """

    q = rdflib.plugins.sparql.prepareQuery(
    """SELECT ?a ?blabel WHERE {
            ?a (skosxl:prefLabel | skosxl:altLabel)/skosxl:literalForm ?s .
            ?a (skosxl:prefLabel | skosxl:altLabel)/skosxl:literalForm ?blabel .
        }""", initNs = {"rdf": RDF, "skos": SKOS, "skosxl": SKOSXL} )

    if (language is not None) and (len(language) == 2):
        searchfor = rdflib.term.Literal(label, lang=language)
    else:
        searchfor = rdflib.term.Literal(label)
    
    results = graph.query(q, initBindings={'s': searchfor})

    return results


def return_all_pref_label(graph: Graph) -> List[rdflib.query.ResultRow]:
    """[summary]

    Args:
        graph (Graph): [description]

    Returns:
        [type]: [description]
    """

    respref = graph.query(
    """SELECT ?a ?label ?region ?country ?clink WHERE {
            ?a skosxl:prefLabel/skosxl:literalForm ?label .
            ?a svf:region ?region .
            ?a schema:address/ schema:addressCountry ?country .
            ?a svf:country ?clink .
        }""")

    return respref


def return_all_alt_label(graph: Graph) -> List[rdflib.query.ResultRow]:
    """[summary]

    Args:
        graph (Graph): [description]

    Returns:
        [type]: [description]
    """

    respref = graph.query(
    """SELECT ?a ?label ?region ?country ?clink WHERE {
            ?a skosxl:altLabel/skosxl:literalForm ?label .
            ?a svf:region ?region .
            ?a schema:address/ schema:addressCountry ?country .
            ?a svf:country ?clink .
        }""")

    return respref


def write_excel_tab_csv_file(filename: str, fieldnames: list, records: list) -> None:
    """Writes an exel csv file that uses TABs as separators.

    Args:
        filename (str): The filename of the csv file
        fieldnames (list): The fieldnames in the first row
        records (list): The rows of data to save in the file
    """

    with open(filename, 'w', newline='', encoding='utf-8') as csvoutfile:
        csvwriter = csv.DictWriter(csvoutfile, fieldnames=fieldnames, dialect='excel-tab')
        csvwriter.writeheader()
        for record in records:
            csvwriter.writerow(record)


def canonical_funder_id(doi: str) -> str:
    """[summary]

    Args:
        doi (str): [description]

    Returns:
        str: [description]
    """

    if not(doi.startswith('doi:10.13039')):
        try:
            start = doi.index('10.13039')
            doi = f"doi:{doi[start:]}"
        except ValueError as v:
            print(v)
            doi = ''
    return doi


def map_row(is_pref: bool, row: list) -> dict:
    """[summary]

    Args:
        is_pref (bool): [description]
        row (list): [description]

    Returns:
        dict: [description]
    """

    country = pycountry.countries.get(alpha_3=row[3].upper())
    funder = {}
    funder['ispref'] = is_pref
    funder['id'] = canonical_funder_id(row[0])
    if country:
        logging.debug(f"{row[3]}: {country.name}")
        #funder['name'] = f"{row[1]} ({row[2]}, {country.name})" # Funder Name (Region, Country)
        funder['name'] = f"{row[1]} ({country.name})" # Name (Country)
    else:
        logging.warning(f"No country in ISO 3166-1 alpha-3 for code: {row[3]}")
        #funder['name'] = f"{row[1]} ({row[2]}, {row[3]})" # Name (Region, Country Code)
        if row[3].upper() == "EUE":
            funder['name'] = f"{row[1]} ({row[2]})" # Funder Name (Region)
        else:
            funder['name'] = f"{row[1]} ({row[3]})" # Funder Name (Country Code)
    
    return funder


SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
SVF = Namespace("http://data.crossref.org/fundingdata/xml/schema/grant/grant-1.2/")
SCHEMA = Namespace("http://schema.org/")


def main():
    logging.basicConfig(filename=f'./logs/extract_funders_from_rdf_{dt.datetime.now():%Y-%m-%d}.log',
                    format='%(asctime)s %(message)s', level=logging.DEBUG)

    with open('config.yaml', 'r') as cfgin:
        config = yaml.safe_load(cfgin)

    logging.getLogger().setLevel(config['logging_level'])

    # filename and path of crossref funder registry rdf-file (v1.32)
    # https://gitlab.com/crossref/open_funder_registry
    rdf_funder_registry = './rdf-funder/registry.rdf'    

    g = Graph()
    g.parse(rdf_funder_registry)

    respref = return_all_pref_label(g)

    resalt = return_all_alt_label(g)

    record_labels = ['ispref', 'id', 'name']
    complete_funder_label_list = []

    complete_funder_label_list = list(map(lambda row: map_row(True, row), respref))

    complete_funder_label_list.extend(list(map(lambda row: map_row(False, row), resalt)))

    write_excel_tab_csv_file("complete_funder_list.csv", fieldnames=record_labels, records=complete_funder_label_list)

if __name__ == "__main__":
    main()