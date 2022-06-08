#!/bin/env python
import argparse
import functools
import logging
import os
import json
import yaml
import sys
from haystack.reader.farm import FARMReader
from haystack.reader.transformers import TransformersReader
from haystack.utils import print_answers
from haystack.retriever.sparse import ElasticsearchRetriever
from haystack.retriever.dense import DensePassageRetriever
from haystack.pipeline import ExtractiveQAPipeline
from haystack.document_store.elasticsearch import ElasticsearchDocumentStore


def extract_relevant_data_from_answer(prediction_answer: dict) -> dict:
    """[summary]

    Args:
        prediction_answer (dict): [description]

    Returns:
        dict: [description]
    """    

    result = {}
    
    try:
        result['answer'] = prediction_answer['answer']
        result['score'] = prediction_answer['score']
        result['probability'] = prediction_answer['probability']
        result['context'] = prediction_answer['context']
        result['lang'] = prediction_answer['meta']['lang']
    except KeyError as k:
        print('KeyError for answer: ', k)
    
    return result

sprint = functools.partial(print, end="")

# store haystack log output in logfile
logging.basicConfig(filename='extract_top_hits.log', format='%(asctime)s %(message)s', level=logging.INFO)

def main():

    parser = argparse.ArgumentParser(description="extract_top_hits.py\n" +
                                    "Extract top 2 Answers for all supported moddels and questions for all PDF files.\n" +
                                    "Iterate over PDF filenames in doc_dir_pdf to extract item handles for retrieval.\n"+
                                    "You can also use a DensePassageRetriever if you have done the preprocessing in load_docs_into_elasticsearch_split_pdf_lang.py.\n")
    parser.add_argument('-d', '--DPR',
                        help='use DensePassageRetriever for retrieval.',
                        dest='d',
                        action="store_true")
    parser.add_argument('-?', help='print this help message', dest='h', action="store_true")
    args = parser.parse_args()
 
    if args.h:
        parser.print_help()
        sys.exit(0)

    if args.d:
        print('Use DensePassageRetriever!')

    with open('config.yaml', 'r') as cfgin:
            config = yaml.safe_load(cfgin)

    use_gpu = config['use_gpu']
    es = config['elastic']

    if args.d:
        document_store = ElasticsearchDocumentStore(host=es['host'], port=es['port'], username=es['username'], password=es['password'], index=es['dprindex'])
    else:
        document_store = ElasticsearchDocumentStore(host=es['host'], port=es['port'], username=es['username'], password=es['password'], index=es['index'])


    # Path of the directory where the extracted source TXT files are stored in
    #doc_dir_txt = config['doc_dir_txt']

    # Path of the directory where the source PDF files are stored in
    doc_dir_pdf = config['doc_dir_pdf']

    # Path of the directory where the DSpace json files with the metadata of the source PDF/TXT files are stored in
    #doc_dir_json = config['doc_dir_json']

    if args.d:
        print('use DensePsssageRetriever')
        el_retriever = DensePassageRetriever(document_store=document_store,
                                    query_embedding_model="facebook/dpr-question_encoder-single-nq-base",
                                    passage_embedding_model="facebook/dpr-ctx_encoder-single-nq-base",
                                    max_seq_len_query=64,
                                    max_seq_len_passage=256,
                                    batch_size=16,
                                    use_gpu=use_gpu,
                                    embed_title=True,
                                    use_fast_tokenizers=True)
        # Path of the directory where to store json files with extracted answers in
        doc_dir_answers = config['doc_dir_answers_dpr']
    else:
        print('use default BM25 Retriever')
        el_retriever = ElasticsearchRetriever(document_store=document_store)
        # Path of the directory where to store json files with extracted answers in
        doc_dir_answers = config['doc_dir_answers']


    models = [('roberta', 'deepset/roberta-base-squad2'),
                ('xlm-roberta', 'deepset/xlm-roberta-large-squad2'),
                ('electra', 'deepset/electra-base-squad2'),
                ('mfeb-albert-xxl-v2', 'mfeb/albert-xxlarge-v2-squad2'),
                ('minilm-uncased', 'deepset/minilm-uncased-squad2')]

    questions = ['Who funded the article?', 'Who funded the work?', 'Who gives financial support?',
                    'By whom was the study funded?', 'Whose financial support do you acknowledge?',
                    'Who provided funding?', 'Who provided financial support?',
                    'By which grant was this research supported?']

    for model_name, model in models:
        print(f'Load model: {model_name}, {model}')
        reader = FARMReader(model_name_or_path=model, use_gpu=use_gpu, no_ans_boost=1, return_no_answer=True)
        pipe = ExtractiveQAPipeline(reader, el_retriever)
        pdf_files = os.listdir(doc_dir_pdf)
        for pdf_file in pdf_files:
            try:
                if pdf_file.lower().endswith(".pdf"):
                    text_name=pdf_file[:-4]
                    print(f'Predict answers for text: {text_name}')
                    results = {}
                    for question in questions:
                        print(f'Predict answers for question: {question}')
                        prediction = pipe.run(query=question, filters={'name': [text_name]}, top_k_retriever=10, top_k_reader=2)
                        results[question] = []
                        results[question] = list(map(extract_relevant_data_from_answer, prediction['answers']))
                    try:
                        with open(doc_dir_answers +'/'+text_name+'_'+model_name+'.json', 'w', encoding="utf-8") as json_file:
                            json.dump(results, json_file, ensure_ascii=False, indent=4)
                    except Exception as e:
                        print("\nException writing file!", e)
            except Exception as e:
                print("\nException ", e)

if __name__ == "__main__":
    main()