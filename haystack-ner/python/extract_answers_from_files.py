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
from unidecode import unidecode
from nlu.prediction import predict
#import strsimpy as strsim


def get_modelname_from_filename(filename: str) -> str:
    """Extract squad model name from filename (e.g. roberta).

    Args:
        filename (str): filename of json file containing answers

    Returns:
        str: the squad model name retrieved from filename (e.g. roberta)
    """

    modelname = ""

    if (filename is not None) and (len(filename) > 5):
        try:
            lindex = filename.rindex('_') + 1
            modelname = filename[lindex:-5]
        except KeyError as k:
            pass

    return modelname


def get_handle_from_filename(filename: str) -> str:
    """Extract item handle from filename.

    Args:
        filename (str): filename of json file containing answers

    Returns:
        str: the EconStor handle retrieved from filename
    """

    prefix_len = len('10419-')
    handle = ""

    if (filename is not None) and (len(filename) > 5):
        try:
            handle = regex.sub('-|_', '/', filename[:filename.find('_', prefix_len)])
        except KeyError as k:
            pass

    return handle


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


def load_funder_from_csv_file(filename: str) -> dict:
    """load funder names from serialized csv file

    Args:
        filename (str): the name of the file containing the serialized rdf crossref funder list

    Returns:
        dict: dictionary of funders
    """

    funder = {'preflabel': {}, 'altlabel': {}}

    try:
        with open(filename, 'r',newline='', encoding='utf-8') as csvinfile:
            csvreader = csv.DictReader(csvinfile, dialect='excel-tab')
            for row in csvreader:
                if row['ispref'] == 'True':
                    funder['preflabel'][row['id']] = row['name']
                else:
                    funder['altlabel'][f"{row['id']}_{row['name']}"] = row['name']

    except Exception as e:
        print(e)
    
    return funder


def load_testset_from_csv_file(filename: str) -> dict:
    """load testset data from csv file

    Args:
        filename (str): the filename of the csv file

    Returns:
        dict: the testset data
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


def find_funder_from_list(possible_funder: str, list_of_funders: dict) -> str:
    """search for funder name in crossref authority records

    Args:
        possible_funder (str): fundername to look up in authority records
        list_of_funders (dict): crossref funder authority records

    Returns:
        str: containing a list of possible authority records -> 
            'funder name; crossref id; similarity ratio between possible_funder and funder name in record' 
    """
    
    results = fuzz.process.extract(possible_funder, list_of_funders['preflabel'], scorer=fuzz.fuzz.WRatio)
    result_str = ""
    max_sim_res = ""
    maxsim = 0.0
    for funder, similarity, funder_identifier in results:
        if similarity > maxsim:
            maxsim = similarity
            max_sim_res = f"{funder}; {funder_identifier}; {similarity:.2f}"
        result_str = result_str + f", ({funder}; {funder_identifier}; {similarity:.2f})"
    result_str = result_str[2:]
    if maxsim >= 90.0:
        logging.debug(f"\nmatch preflabel search: '{possible_funder}' -> {result_str}'")
        return max_sim_res
    else:
        logging.debug(f"\nno match preflabel search: '{possible_funder}' -> {result_str}'")
        results = fuzz.process.extract(possible_funder, list_of_funders['altlabel'], scorer=fuzz.fuzz.WRatio)
        result_str = ""
        max_sim_res = ""
        max_sim_res_id = ""
        maxsim = 0.0
        for funder, similarity, funder_identifier in results:
            id = (funder_identifier.split("_"))[0]
            if similarity > maxsim:
                maxsim = similarity
                max_sim_res = f" ({funder}); {id}; {similarity:.2f}"
                max_sim_res_id = id
            result_str = result_str + f", ({funder}; {id}; {similarity:.2f})"
        result_str = result_str[2:]
        if maxsim >= 90.0:
            funderpref = list_of_funders['preflabel'].get(max_sim_res_id)
            max_sim_res = funderpref + max_sim_res
            logging.debug(f"\nmatch altlabel search: '{possible_funder}' -> {result_str}'")
            return max_sim_res
        else:
            logging.debug(f"\nno match altlabel search: '{possible_funder}' ->  {result_str}'")
            return ""


def check_similarity_of_answers(given_answer: str, expected_answer: str, try_unidecode: bool = True) -> bool:
    """Compare a given answer to an expected answer. Use fuzz.partial_ratio to compare.

    Args:
        given_answer (str): the given answer
        expected_answer (str): the expected answer
        try_unidecode (bool, optional): if no similarity detected try unidecoded strings. Defaults to True.

    Returns:
        bool: returns True if the given answer is simmilar to the expected answer (fuzz.partial_ratio >= 90%), returns False otherwise.
    """

    fuzz_conf = fuzz.fuzz.partial_ratio(fuzz.utils.default_process(given_answer), fuzz.utils.default_process(expected_answer))
    logging.debug(f"\nfuzz.fuzz.partial_ratio('{fuzz.utils.default_process(given_answer)}', '{fuzz.utils.default_process(expected_answer)}') -> {fuzz_conf}")
    if fuzz_conf >= 90.0:
        return True
    elif try_unidecode:
        return check_similarity_of_answers(unidecode(given_answer), unidecode(expected_answer), False)
    else:
        return False


def update_testset_answer(question: str, valid_score: bool, valid_score_probability: bool, min_no_funder_confidence: float,
                            answer: dict, answerno: int, testsetitem: dict, funder: dict, add_context: bool) -> dict:
    """Create dictionary with result data
    
        testset_answer[f"{question}_{answerno}_COLUMN]"]\n
        where COLUMN is on of:\n
            score_ge_12\n
            score_x_probability_ge_5\n
            answer\n
            score\n
            probability\n
            context_prediction\n
            context_confidence \n
            check\n
            found_funder_id\n
        
        testset_answer[f"{question}_{answerno}_check"] can contain one the following values:
            "match" -> item has funder and a matching funder was found by haystack\n
            "no funder" -> item has no funder and no funder was found by haystack\n
            "false positive" -> item has no funder, but a funder was found by haystack
                                                or the reported funder could not be verified\n
            "false negative" -> item has a funder, but no funder was found by haystack

    Args:
        question (str): the question asked
        valid_score (bool): answer has a score greater or equal to 12.0
        valid_score_probability (bool): the score multiplied with the probabilty of the answer is greater or equal to 5.0
        answer (dict): the answer with information from haystack for an item
        answerno (int): the number of the answer to the question (first: 1 or second: 2)
        testsetitem (dict): the testset data of an item

    Returns:
        dict: [description]
    """

    testset_answer = {}
    prefix = f"{question}_{answerno}"
    testset_answer[f"{prefix}_score_ge_12"] = valid_score
    testset_answer[f"{prefix}_score_x_probability_ge_5"] = valid_score_probability
    if (answer['answer'] is not None) and (valid_score or valid_score_probability):
        testset_answer[f"{prefix}_answer"] = answer['answer']
        testset_answer[f"{prefix}_score"] = answer['score']
        testset_answer[f"{prefix}_probability"] = answer['probability']
        testset_answer[f"{prefix}_context_prediction"] = ''
        testset_answer[f"{prefix}_context_confidence"] = 0.0
        if not(is_open_access_funding(answer['answer'], answer['context'])):
            if testsetitem["keine Funder-Angabe im PDF"] is not None and testsetitem["keine Funder-Angabe im PDF"] != '':
                testset_answer = check_testset_false_positive(testset_answer, prefix, answer, testsetitem, add_context, min_no_funder_confidence)
            elif testsetitem["Funder-Phrase lt. PDF"] is not None and (
                    unidecode(testsetitem["Funder-Phrase lt. PDF"]).lower() in unidecode(answer['answer']).lower() or
                    unidecode(answer['answer']).lower() in unidecode(testsetitem["Funder-Phrase lt. PDF"]).lower() or
                    check_similarity_of_answers(answer['answer'], testsetitem["Funder-Phrase lt. PDF"])
                    ):
                prediction = predict(answer['context'])
                testset_answer[f"{prefix}_context_prediction"] = prediction['intent']['value']
                testset_answer[f"{prefix}_context_confidence"] = prediction['intent']['confidence']
                if((prediction['intent']['value'] == 'no_funder') and (prediction['intent']['confidence'] > min_no_funder_confidence)):
                    testset_answer = check_testet_false_negative(testset_answer, prefix, testsetitem, add_context)
                else:
                    testset_answer[f"{prefix}_check"] = 'match'
                    testset_answer[f"{prefix}_found_funder_id"] = find_funder_from_list(answer['answer'], funder)
            else:
                testset_answer = check_testset_false_positive(testset_answer, prefix, answer, testsetitem, add_context, min_no_funder_confidence)
            if add_context:
                testset_answer[f"{prefix}_context"] = answer['context']
    else:
        testset_answer[f"{prefix}_answer"] = '-'
        testset_answer[f"{prefix}_score"] = '-'
        testset_answer[f"{prefix}_probability"] = '-'
        testset_answer[f"{prefix}_context_prediction"] = ''
        testset_answer[f"{prefix}_context_confidence"] = 0.0
        testset_answer = check_testet_false_negative(testset_answer, prefix, testsetitem, add_context)
    
    return testset_answer


def check_testset_false_positive(testset_answer: dict, prefix: str, answer: dict, testsetitem: dict, add_context: bool, min_no_funder_confidence: float) -> dict:
    prediction = predict(answer['context'])
    testset_answer[f"{prefix}_context_prediction"] = prediction['intent']['value']
    testset_answer[f"{prefix}_context_confidence"] = prediction['intent']['confidence']
    if((prediction['intent']['value'] == 'no_funder') and (prediction['intent']['confidence'] > min_no_funder_confidence)):
        testset_answer = check_testet_false_negative(testset_answer, prefix, testsetitem, add_context)
    else:
        testset_answer[f"{prefix}_check"] = 'false positive'
        testset_answer[f"{prefix}_found_funder_id"] = ''
    
    return testset_answer


def check_testet_false_negative(testset_answer: dict, prefix: str, testsetitem: dict, add_context: bool) -> dict:
    if testsetitem["keine Funder-Angabe im PDF"] is None or testsetitem["keine Funder-Angabe im PDF"] == '':
        testset_answer[f"{prefix}_check"] = 'false negative'
        testset_answer[f"{prefix}_found_funder_id"] = ''
    else:
        testset_answer[f"{prefix}_check"] = 'no funder'
        testset_answer[f"{prefix}_found_funder_id"] = ''
    if add_context:
        testset_answer[f"{prefix}_context"] = ''

    return testset_answer


def is_open_access_funding(given_answer: str , given_answer_context: str) -> bool:
    if "open access" in given_answer.lower():
        return True
    elif "open access" in given_answer_context.lower():
        return True
    else:
        return False


sprint = functools.partial(print, end="")
subpattern = regex.compile(r"\s+")


def main():
    logging.basicConfig(filename=f'./logs/extract_answers_from_files_{dt.datetime.now():%Y-%m-%d}.log',
                    format='%(asctime)s %(message)s', level=logging.DEBUG)

    with open('config.yaml', 'r') as cfgin:
        config = yaml.safe_load(cfgin)

    logging.getLogger().setLevel(config['logging_level'])

    # min score for an answer to be accepted as valid
    min_score = 12.0
    
    # min of (probabiltiy * score) for an answer to be accepted as valid
    min_prob_score = 5.0

    # min confidence of "no_funder" prediction to invalidate answer
    min_no_funder_confidence = 0.75

    # Path of the directory where the excel tab csv-files with the valid answers are stored
    out_dir_csv = config['doc_dir_csv']
    
    # Path of the directory where the extracted answers in json files are stored
    doc_dir_answers = config['doc_dir_answers']

    # Path of the excel tab csv-file with the human checked test data sets
    test_csv_file = config['test_csv_file']

    # Path of the excel tab csv-file with the complete crossref funderlist
    funder_csv_file = config['funder_csv_file']

    # blacklist to remove questions and their answers
    filter_questions = ['Has there been a grant by a funding agency?', 'Was some funding granted?']
    
    valid_model_answers = {}
    testset_model_answers = {}
    all_valid_answers = []

    parser = argparse.ArgumentParser(description="extract_answers_from_files.py\n" +
                                    "Extracts the most likeliest answers from the json files for each model (roberta, electra, ...).\n" +
                                    "The questions and answers along with their score and probability are saved.\n")
    parser.add_argument('-f', '--fulllist',
                        help='create one excel-tab-csv-file (all_answers_YYYY-mm-dd.csv) with all answers deemed valid',
                        dest='f',
                        action="store_true")
    parser.add_argument('-p', '--permodel',
                        help='create one excel-tab-csv-file per model ({modelname}_answers_YYYY-mm-dd.csv) with all answers deemed valid from the model',
                        dest='p',
                        action="store_true")
    parser.add_argument('-t', '--testset',
                        help='create one excel-tab-csv-file per model (testset_YYYY-mm-dd.csv) with all answers deemed valid for the items from the testset.',
                        dest='t',
                        action="store_true")
    parser.add_argument('-c', '--add-context',
                        help='add context data per answer.',
                        dest='c',
                        action="store_true")
    parser.add_argument('-d', '--DPR',
                        help='use answers from DensePassageRetriever.',
                        dest='d',
                        action="store_true")
    parser.add_argument('-?', help='print this help message', dest='h', action="store_true")
    args = parser.parse_args()
 
    if args.h or not (args.f or args.p or args.t):
        parser.print_help()
        sys.exit(0)
    if args.f:
        print('create fulllist file.')
    if args.p:
        print('create per model files.')
    if args.t:
        print('create per model testset file.')
    if args.c:
        print('add context info to answers.')
    if args.d:
        print('use DensePsssageRetriever answers')
        # Path of the directory where the excel tab csv-files with the valid answers are stored
        out_dir_csv = config['doc_dir_csv_dpr']
        # Path of the directory where the extracted answers in json files are stored
        doc_dir_answers = config['doc_dir_answers_dpr']

    testset = load_testset_from_csv_file(test_csv_file)
    funder = load_funder_from_csv_file(funder_csv_file)

    print(f"start extraction: {dt.datetime.now():%Y-%m-%d %H:%M:%S}")

    answer_files_json = os.listdir(doc_dir_answers)
    for answer_file_json in answer_files_json:
        try:
            if answer_file_json.lower().endswith(f".json"):
                with open(f"{doc_dir_answers}/{answer_file_json}", "r", encoding="utf-8") as answer_file:
                    answers_from_file = json.load(answer_file)
                modelname = get_modelname_from_filename(answer_file_json)
                item_handle = get_handle_from_filename(answer_file_json)
                if modelname not in valid_model_answers:
                    valid_model_answers[modelname] = []
                if modelname not in testset_model_answers:
                    testset_model_answers[modelname] = {}
                if item_handle in testset and item_handle not in testset_model_answers[modelname]:
                    testset_model_answers[modelname][item_handle] = {}
                    if testset[item_handle]["Funder-Phrase lt. PDF"] is not None:
                        testset[item_handle]["Funder-Phrase lt. PDF"] = regex.sub(subpattern, " ", testset[item_handle]["Funder-Phrase lt. PDF"])
                    testset_model_answers[modelname][item_handle].update(testset[item_handle])
                    testset_model_answers[modelname][item_handle]['model'] = modelname
                for question, answers in answers_from_file.items():
                    answerno = 0
                    for answer in answers:
                        if question not in filter_questions:
                            answerno = answerno + 1
                            valid_score = (answer['score'] >= min_score)
                            valid_score_probability = (answer['score']*answer['probability'] >= min_prob_score)
                            if answer['answer'] is not None:
                                answer['answer'] = regex.sub(subpattern, " ", answer['answer'])
                            if answer['context'] is not None:
                                answer['context'] = regex.sub(subpattern, " ", answer['context'])
                            if args.t and item_handle in testset:
                                testset_model_answers[modelname][item_handle].update(update_testset_answer(question, valid_score,
                                                                            valid_score_probability, min_no_funder_confidence,
                                                                            answer, answerno, testset[item_handle], funder, args.c))
                            if (answer['answer'] is not None) and (args.p or args.f) and (valid_score or valid_score_probability):
                                if not(is_open_access_funding(answer['answer'], answer['context'])):
                                    prediction = predict(answer['context'])
                                    if ((prediction['intent']['value'] == 'funder') or (prediction['intent']['confidence'] <= min_no_funder_confidence)):
                                        valid_answer = {}
                                        valid_answer['handle'] = item_handle
                                        valid_answer['question'] = question
                                        valid_answer['score_ge_12'] = valid_score
                                        valid_answer['score_x_probability_ge_5'] = valid_score_probability
                                        valid_answer["context_prediction"] = prediction['intent']['value']
                                        valid_answer["context_confidence"] = prediction['intent']['confidence']
                                        valid_answer['model'] = modelname
                                        valid_answer.update(answer)
                                        valid_answer[f"found_funder_id"] = find_funder_from_list(answer['answer'], funder)
                                        valid_model_answers[modelname].append(valid_answer)
                                        all_valid_answers.append(valid_answer)
        except Exception as e:
            print("\nException :", e)

    if args.p:
        for modelname in valid_model_answers:
            if len(valid_model_answers[modelname]) > 0:
                fieldnames = valid_model_answers[modelname][0].keys()
                write_excel_tab_csv_file(filename=f"{out_dir_csv}/{modelname}_answers_{dt.datetime.now():%Y-%m-%d}.csv",
                                            fieldnames=fieldnames, records=valid_model_answers[modelname])

    if args.f and len(all_valid_answers) > 0:
        fieldnames = all_valid_answers[0].keys()
        write_excel_tab_csv_file(filename=f"{out_dir_csv}/all_answers_{dt.datetime.now():%Y-%m-%d}.csv",
                                    fieldnames=fieldnames, records=all_valid_answers)

    if args.t:
        for modelname in testset_model_answers:
            if len(testset_model_answers[modelname]) > 0:
                model_items = testset_model_answers[modelname]
                model_answers = list(model_items.values())
                fieldnames = model_answers[0].keys()
                print(f"Writing testset answers for model:'{modelname}' no. if items: {len(model_items)}")
                write_excel_tab_csv_file(filename=f"{out_dir_csv}/{modelname}_testset_answers_{dt.datetime.now():%Y-%m-%d}.csv",
                                            fieldnames=fieldnames, records=model_answers)

    print(f"finished extraction: {dt.datetime.now():%Y-%m-%d %H:%M:%S}")

if __name__ == "__main__":
    main()
