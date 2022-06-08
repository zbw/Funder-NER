#!/bin/env python
import argparse
import functools
import os
import pycld2 as cld2
import json
import yaml
import sys
from haystack.preprocessor.cleaning import clean_wiki_text
from haystack.preprocessor.utils import convert_files_to_dicts, fetch_archive_from_http, PDFToTextConverter, TextConverter
from haystack.reader.farm import FARMReader
from haystack.reader.transformers import TransformersReader
from haystack.retriever.dense import DensePassageRetriever
from haystack.utils import print_answers
from haystack.preprocessor.preprocessor import PreProcessor

from haystack.document_store.elasticsearch import ElasticsearchDocumentStore


def extract_metadata_from_json(json_obj: dict, doc_meta: dict) -> dict:
    """Extract item metadata from JSON as returned by DSpace 5.x rest api.
       Append metadata from JSON to metadata returned by Haystack Converter.

    Args:
        json_obj (dict): item metadata in JSON returned by DSpace 5.x rest api
        doc_meta (dict): document metadata as returned by Converter

    Returns:
        dict: doc_metadata + metadata retrieved from json_obj
    """

    for key, value in map(lambda x: (x['key'], x['value']), json_obj['metadata']):
        if key in ['dc.title', 'dc.language.iso', 'dc.type', 'dc.rights.license']:
            doc_meta[key] = value

        if key in ['dc.subject.keyword', 'dc.subject.ddc', 'dc.identifier.ppn', 'dc.identifier.pi', 
                'dc.identifier.uri', 'dc.contributor.author']:
            if key in doc_meta:
                doc_meta[key].append(value)
            else:
                doc_meta[key] = [value]
    return doc_meta


def read_docs_from_PDFs(doc_dir_pdf: str, doc_dir_json: str) -> list:
    """Prepare ingest of text content from PDFs stored in doc_dir_pdf
       by using Haystack PDFToTextConverter.

    Args:
        doc_dir_pdf (str): The directory containing the PDFs to ingest
        doc_dir_json (str): The directory containing the item metadata from DSpace

    Returns:
        list: The converted documents
    """    
    
    preprocessor_pdf = PreProcessor(
        clean_empty_lines=True,
        clean_whitespace=True,
        clean_header_footer=True,
        split_by="word",
        split_length=100,
        split_respect_sentence_boundary=True
    )

    converter = PDFToTextConverter(remove_numeric_tables=True) # , valid_languages=["en", "de"])

    all_docs = []
    count = 0
    pdf_files = os.listdir(doc_dir_pdf)
    for pdf_file in pdf_files:
        try:
            if pdf_file.lower().endswith(".pdf"):
                lang = 'en'
                sprint(f"{count:4} Convert doc: {pdf_file}" )
                doc = converter.convert(file_path= doc_dir_pdf + '/' + pdf_file, meta={"name": pdf_file[:-4], "lang" : ""}, encoding="UTF-8")
                # cld2 chokes on some utf-8 encondings need to use Latin1
                doc_lang_detection = converter.convert(file_path= doc_dir_pdf + '/' + pdf_file, meta={"name": pdf_file[:-4], "lang" : ""}, encoding="Latin1")
                try:
                    sReliable, textBytesFound, details = cld2.detect(doc_lang_detection['text'])
                    try:
                        lang = details[0][1]
                        sprint(f" - {details[0]}")
                    except KeyError:
                        # if detect failed - default to en
                        sprint(" - language detection failed - set 'en'")
                        lang = 'en'
                except cld2.error as e:
                    # if encoding error - default to en
                    sprint(" - language detection failed error - set 'en'")
                    lang = 'en'
                #try:
                #    json_fn = doc_dir_json + '/' + pdf_file[:-4] + '.json'
                #    sprint(f" - {json_fn}")
                #    with open(json_fn, "r", encoding="utf-8") as fp:
                #        my_json_obj = json.load(fp)
                #    doc['meta'] = extract_metadata_from_json(my_json_obj, doc['meta'])
                #except Exception as e:
                #    sprint(" - Exception", e)
                doc['meta']['lang'] = lang
                print(f" - {lang}")
                doc_parts = preprocessor_pdf.process(doc)
                all_docs.extend(doc_parts)
                count = count + 1
        except Exception as e:
            print("\nException ", e)

    return all_docs


def read_docs_from_TXTs(doc_dir_txt: str, doc_dir_json: str) -> list:
    """Prepare ingest of plain text files stored in doc_dir_txt
       by using Haystack TextConverter.

    Args:
        doc_dir_txt (str): The directory containing the plain text files to ingest
        doc_dir_json (str): The directory containing the item metadata from DSpace

    Returns:
        list: The converted documents
    """    
    
    preprocessor_txt = PreProcessor(
        clean_empty_lines=True,
        clean_whitespace=True,
        clean_header_footer=False,
        split_by="word",
        split_length=100,
        split_respect_sentence_boundary=True
    )

    converter = TextConverter(remove_numeric_tables=True) # , valid_languages=["en", "de"])

    all_docs = []
    count = 0
    txt_files = os.listdir(doc_dir_txt)
    for txt_file in txt_files:
        try:
            if txt_file.lower().endswith(".txt"):
                lang = "en"
                sprint(f"{count:4} Convert doc: {txt_file}" )
                doc = converter.convert(file_path= doc_dir_txt + '/' + txt_file, meta={"name": txt_file[:-4], "lang" : ""}, encoding="UTF-8")
                try:
                    sReliable, textBytesFound, details = cld2.detect(doc['text'])
                    try:
                        lang = details[0][1]
                        sprint(f" - {details[0]}")
                    except KeyError:
                        # if detect failed - default to en
                        sprint(" - language detection failed - set 'en'")
                        lang = 'en'
                except cld2.error as e:
                    # if encoding error - default to en
                    sprint(" - language detection failed error - set 'en'")
                    lang = 'en'
                #try:
                #    json_fn = doc_dir_json + '/' + txt_file[:-4] + '.json'
                #    sprint(f" - {json_fn}")
                #    with open(json_fn, "r", encoding="utf-8") as fp:
                #        my_json_obj = json.load(fp)
                #    doc['meta'] = extract_metadata_from_json(my_json_obj, doc['meta'])
                #except Exception as e:
                #    sprint(" - Exception", e)
                doc['meta']['lang'] = lang
                print(f" - {lang}")
                doc_parts = preprocessor_txt.process(doc)
                all_docs.extend(doc_parts)
                count = count + 1
        except Exception as e:
            print("\nException ", e)

    return all_docs


sprint = functools.partial(print, end="")

def main():

    parser = argparse.ArgumentParser(description="load_docs_into_elasticsearch_split_pdf_lang.py\n" +
                                    "Ingest documents into Elasticsearch for NLP QA with Haystack.\n" +
                                    "The document sources can be PDFs or textfiles.\n" +
    #                                "Additional meta-data will be read from JSON files.\n"+
                                    "You can also have the data in Elasticsearch postprocessed for use with a DensePassageRetriever.\n")
    parser.add_argument('-p', '--pdf',
                        help='ingest from PDF files.',
                        dest='p',
                        action="store_true")
    parser.add_argument('-t', '--text',
                        help='ingest from text files.',
                        dest='t',
                        action="store_true")
    parser.add_argument('-d', '--DPR',
                        help='do post processing for DensePassageRetriever.',
                        dest='d',
                        action="store_true")
    parser.add_argument('-?', help='print this help message', dest='h', action="store_true")
    args = parser.parse_args()
 
    if args.h or not (args.p or args.t):
        parser.print_help()
        sys.exit(0)

    if args.p:
        print('Ingest from PDF files.')
    if args.t:
        print('Ingest from text files')
    if args.d:
        print('Do post prosessing for DPR')

    with open('config.yaml', 'r') as cfgin:
            config = yaml.safe_load(cfgin)

    es = config['elastic']
    use_gpu = config['use_gpu']

    if args.d:
        document_store = ElasticsearchDocumentStore(host=es['host'], port=es['port'], username=es['username'], password=es['password'], index=es['dprindex'])
    else:
        document_store = ElasticsearchDocumentStore(host=es['host'], port=es['port'], username=es['username'], password=es['password'], index=es['index'])
    

    # Path of the directory where the source PDF files are stored in
    doc_dir_pdf = config['doc_dir_pdf']

    # Path of the directory where the extracted source TXT files are stored in
    doc_dir_txt = config['doc_dir_txt']

    # Path of the directory where the DSpace json files with the metadata of the source PDF/TXT files are stored in
    doc_dir_json = config['doc_dir_json']

    all_docs = []

    if args.p:
        all_docs = read_docs_from_PDFs(doc_dir_pdf=doc_dir_pdf, doc_dir_json=doc_dir_json)
    elif args.t:
        all_docs = read_docs_from_TXTs(doc_dir_txt=doc_dir_txt, doc_dir_json=doc_dir_json)

    if len(all_docs) > 0:
        print(f"write all {len(all_docs)} docs to elasticsearch")
        document_store.write_documents(all_docs)
        if args.d:
            print('init DensePsssageRetriever')
            retriever = DensePassageRetriever(document_store=document_store,
                                        query_embedding_model="facebook/dpr-question_encoder-single-nq-base",
                                        passage_embedding_model="facebook/dpr-ctx_encoder-single-nq-base",
                                        max_seq_len_query=64,
                                        max_seq_len_passage=256,
                                        batch_size=16,
                                        use_gpu=use_gpu,
                                        embed_title=True,
                                        use_fast_tokenizers=True)
            print('update elasticsearch with DPR')
            document_store.update_embeddings(retriever)

if __name__ == "__main__":
    main()