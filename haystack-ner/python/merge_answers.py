#!/bin/env python
import argparse
import csv
import datetime as dt
import functools
import json
import logging
import os
import regex
import yaml
import sys
import rapidfuzz as fuzz


def load_testset_answers_from_csv_file(filename: str) -> dict:
    """[summary]

    Args:
        filename (str): [description]

    Returns:
        dict: [description]
    """    

    rows = {}
    try:
        with open(filename, 'r',newline='', encoding='utf-8') as csvinfile:
            csvreader = csv.DictReader(csvinfile, dialect='excel-tab')
            for row in csvreader:
                rows[row['Handle']] = row
    except Exception as e:
        print(e)
    
    return rows


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


def extract_questions(keys: list, known_questions = None) -> list:
    questions = set()
    if known_questions is not None:
        questions = known_questions
    
    for key in keys:
        if key.find(detect_question) > 0:
            parts = key.split(detect_question)
            questions.add(parts[0])

    return questions


def check_similarity_of_answers(given_answer: str, expected_answer: str) -> bool:
    fuzz_conf = fuzz.fuzz.partial_ratio(fuzz.utils.default_process(given_answer), fuzz.utils.default_process(expected_answer))
    logging.debug(f"\nfuzz.fuzz.partial_ratio('{fuzz.utils.default_process(given_answer)}', '{fuzz.utils.default_process(expected_answer)}') -> {fuzz_conf}")
    if  fuzz_conf >= 90.0:
        return True
    else:
        return False


def not_yet_included(test_for: str, in_values: list) -> bool:
    
    for value in in_values:
        if ( test_for.lower() in value.lower() ) or ( value.lower() in test_for.lower() ):
            return False
        elif check_similarity_of_answers(test_for, value):
            return False

    return True


def extract_doi_from_funder(funder_with_doi: str) -> str:
    fpos2 = funder_with_doi.rfind(';')
    if fpos2 > 0:
        fpos1 = funder_with_doi.rfind(';',0,fpos2)
        if fpos1 > 0:
            return funder_with_doi[(fpos1+2):fpos2]
    else:
        return ''


def merge_answers(merge_into: dict, merge: dict, min_score: float, multiply_with_probability: bool = False, min_prob_score: float = 5.0) -> dict:
    """[summary]

    Args:
        merge_into (dict): Dictionary to merge the answers to.
        merge (dict): Dictionary of answers that should be merged into the Dictionary merge_into
        min_score (float): minimum score an answers needs to be accepted

    Returns:
        dict: [description]
    """

    questions = None
    for item, answers in merge.items():
        if questions is None:
            questions = extract_questions(answers.keys())
        if item not in merge_into.keys():
            merge_into[item] = {'answers': [], 'found_funder_ids': [], 'funder_dois': [], 'min_score': 0.0, 'max_score': 0.0, 'distinct_matches': 0, 'match': 0, 'false_positive': 0, 'no_funder': 0, 'funder_ids': 0}
            for header in common_rowheaders:
                merge_into[item][header] = answers[header]
        
        for question in questions:
            if question not in exclude_questions:
                if answers[f'{question}?_1_score'] != '-':
                    current_score = float(answers[f'{question}?_1_score'])
                else:
                    current_score = 0.0
                if answers[f'{question}?_1_probability'] != '-':
                    current_probability = float(answers[f'{question}?_1_probability'])
                else:
                    current_probability = 0.0
                if merge_into[item]['max_score'] < current_score:
                    merge_into[item]['max_score'] = float(answers[f'{question}?_1_score'])
                elif merge_into[item]['min_score'] > current_score:
                    merge_into[item]['min_score'] = float(answers[f'{question}?_1_score'])
                if ( current_score >= min_score ) or ( multiply_with_probability and current_score * current_probability >= min_prob_score ):
                    current_answer = answers[f'{question}?_1_answer'].strip()
                    if ( len(current_answer) > 0 ) and ( current_answer != '-' ):
                        if not_yet_included(current_answer, merge_into[item]['answers']):
                            merge_into[item]['answers'].append(current_answer)
                            if answers[f'{question}?_1_check'] == 'match':
                                merge_into[item]['distinct_matches'] = merge_into[item]['distinct_matches'] + 1
                    if answers[f'{question}?_1_check'] == 'match':
                        merge_into[item]['match'] = merge_into[item]['match'] + 1
                    elif answers[f'{question}?_1_check'] == 'false positive':
                        merge_into[item]['false_positive'] = merge_into[item]['false_positive'] + 1
                    if len(answers[f'{question}?_1_found_funder_id']) > 0 :
                        doi = extract_doi_from_funder(answers[f'{question}?_1_found_funder_id'])
                        #if answers[f'{question}?_1_found_funder_id'] not in merge_into[item]['found_funder_ids']:
                        if doi not in merge_into[item]['funder_dois']:
                            merge_into[item]['funder_dois'].append(doi)
                            merge_into[item]['found_funder_ids'].append(answers[f'{question}?_1_found_funder_id'])
                            merge_into[item]['funder_ids'] = merge_into[item]['funder_ids'] + 1
                if answers[f'{question}?_1_check'] == 'no funder':
                    merge_into[item]['no_funder'] = merge_into[item]['no_funder'] + 1
    
    return merge_into


common_rowheaders = ['Handle', 'Funder Identifier lt. CrossRef', 'Funder-Info lt. CrossRef', 'Funder-Phrase lt. PDF', 'keine Funder-Angabe im PDF', 'model']
header_per_question = ['?_1_score_ge_12', '?_1_score_x_probability_ge_5', '?_1_answer', '?_1_score', '?_1_probability', '?_1_check', '?_1_found_funder_id']
detect_question = '?_1_'
csv_rows = ['Handle', 'Funder Identifier lt. CrossRef', 'Funder-Info lt. CrossRef', 'Funder-Phrase lt. PDF', 'keine Funder-Angabe im PDF', 'model',
            'answers', 'found_funder_ids', 'funder_dois', 'min_score', 'max_score', 'distinct_matches', 'match', 'false_positive', 'no_funder', 'funder_ids']

exclude_questions = []

all_questions = ['Who funded the article', 'Who funded the work', 'Who gives financial support',
                    'By whom was the study funded', 'Whose financial support do you acknowledge',
                    'Who provided funding', 'Who provided financial support',
                    'By which grant was this research supported']

def main():
    logging.basicConfig(filename=f'./logs/merge_answers_from_files_{dt.datetime.now():%Y-%m-%d}.log',
                    format='%(asctime)s %(message)s', level=logging.DEBUG)

    with open('config.yaml', 'r') as cfgin:
        config = yaml.safe_load(cfgin)

    logging.getLogger().setLevel(config['logging_level'])

    # Path of the directory where the excel tab csv-files with the valid answers are stored
    out_dir_csv = config['doc_dir_csv']
    
    # Path of the directory where to store json files with extracted answers in
    doc_dir_answers = config['doc_dir_answers']

    # Path of the excel tab csv-file with the human checked test data sets
    test_csv_file = config['test_csv_file']

    # Path of the excel tab csv-file with the complete crossref funderlist
    funder_csv_file = config['funder_csv_file']

    # min score for an answer to be accepted as valid
    min_score = 12.0

    # min of (probabiltiy * score) for an answer to be accepted as valid
    min_prob_score = 5.0

    parser = argparse.ArgumentParser(description="merge_answers.py\n" +
                                    "Merge answers of different questions for a document from a single model (roberta, electra, ...).\n" +
                                    "The merged answers are saved as a new csv file in the folder specified in config['doc_dir_csv'] \n")
    parser.add_argument('csvfilenames', metavar='csv-filename', type=str, nargs='+',
                    help='a csv-filename with results for the testset')
    parser.add_argument('-o', '--outfile',
                        help='The name of the file to write the output csv into (fullpath).\n'
                                f'Default: {out_dir_csv}/merged_answers_%%Y-%%m-%%d.csv',
                        metavar='Outputfile',
                        dest='o', default=f"{out_dir_csv}/merged_answers_{dt.datetime.now():%Y-%m-%d}.csv")
    parser.add_argument('-i', '--minscore',
                        help='The minimum score of a result.'
                             '\nDefault: 12.0.',
                        metavar='Float',
                        dest='i', type=float, default=12.0)
    parser.add_argument('-m', '--minscoreprobability',
                        help='The minimum score * probability value of a result.'
                             '\nDefault: 5.0.',
                        metavar='Float',
                        dest='m', type=float, default=5.0)
    parser.add_argument('-p', '--useprobablity',
                        help='if set multiply score with probability for minimum result score.',
                        dest='p', action="store_true")
    parser.add_argument('-d', '--DPR',
                        help='use answers from DensePassageRetriever.',
                        dest='d',
                        action="store_true")
        
    args = parser.parse_args()

    outfilename = args.o
    min_score = args.i
    min_prob_score = args.m

    if args.p:
        multiply_with_probability = True
    else:
        multiply_with_probability = False

    if args.d:
        print('use DensePsssageRetriever answers')
        # Path of the directory where the excel tab csv-files with the valid answers are stored
        out_dir_csv = config['doc_dir_csv_dpr']
        # Path of the directory where the extracted answers in json files are stored
        doc_dir_answers = config['doc_dir_answers_dpr']

    merged_answers = {}

    print('Merging results from the following files:', args.csvfilenames)
    for csvfilename in args.csvfilenames:
        print("load file: " + out_dir_csv + '/' + csvfilename)
        answers = load_testset_answers_from_csv_file(out_dir_csv + '/' + csvfilename)
        merged_answers = merge_answers(merged_answers, answers, min_score, multiply_with_probability, min_prob_score)
    
    write_excel_tab_csv_file(filename=f"{outfilename}",
                                fieldnames=csv_rows, records=merged_answers.values())


if __name__ == "__main__":
    main()
