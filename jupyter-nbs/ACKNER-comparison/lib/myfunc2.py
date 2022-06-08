import rapidfuzz as fuzz
from unidecode import unidecode
import pandas as pd
import csv

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
    #logging.debug(f"\nfuzz.fuzz.partial_ratio('{fuzz.utils.default_process(given_answer)}', '{fuzz.utils.default_process(expected_answer)}') -> {fuzz_conf}")
    if fuzz_conf >= 90.0:
        return True
    elif try_unidecode:
        return check_similarity_of_answers(unidecode(given_answer), unidecode(expected_answer), False)
    else:
        return False
    
def compare_answers(answer1: str, answer2: str) -> bool:
    if (unidecode(answer1).lower() in unidecode(answer2).lower() or
        unidecode(answer2).lower() in unidecode(answer1).lower() or
        check_similarity_of_answers(answer1, answer2)):
        return True
    else:
        return False


def deduplicate_row_by_value(src_dataframe: pd.DataFrame, column_name: str) -> list:
    chosenrows = []
    equalrows = []
    no_of_rows = len(src_dataframe.index)
    if no_of_rows > 1:
        for i in range(no_of_rows):
            row = src_dataframe.iloc[i]
            answer1 = src_dataframe.iloc[i][column_name]
            if i not in equalrows:
                for j in range(i+1,no_of_rows):
                    answer2 = src_dataframe.iloc[j][column_name]
                    chosenanswer = None
                    if compare_answers(answer1, answer2):
                        if(len(answer1) >= len(answer2)):
                            chosenanswer = i
                        else:
                            chosenanswer = j
                        equalrows.append(i)
                        equalrows.append(j)
                        chosenrows.append(src_dataframe.iloc[chosenanswer])
                if i not in equalrows:
                    chosenrows.append(src_dataframe.iloc[i])
    return chosenrows


def load_funder_from_csv_file(filename: str) -> dict:
    """[summary]
 
    Args:
        filename (str): [description]
 
    Returns:
        dict: [description]
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


def find_funder_from_list(possible_funder: str, list_of_funders: dict) -> str:
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
        #logging.debug(f"\nmatch preflabel search: '{possible_funder}' -> {result_str}'")
        return max_sim_res
    else:
        #logging.debug(f"\nno match preflabel search: '{possible_funder}' -> {result_str}'")
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
            #logging.debug(f"\nmatch altlabel search: '{possible_funder}' -> {result_str}'")
            return max_sim_res
        else:
            #logging.debug(f"\nno match altlabel search: '{possible_funder}' ->  {result_str}'")
            return ""