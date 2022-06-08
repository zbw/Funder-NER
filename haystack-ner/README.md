EconStor ML-Q&A Haystack eval
=============================

Docker container and Python3 scripts to evaluate ML-Q&A with [haystack framework](https://haystack.deepset.ai/).


Requirements
------------

Latest version of:

- EconStor items:
    + PDF: https://www.econstor.eu/ki-hackathon/econstor-cc-by-4.0-pdf.zip
    + or TXT: https://www.econstor.eu/ki-hackathon/econstor-cc-by-4.0-txt.tgz
- EconStor item meta-data:
    + https://www.econstor.eu/ki-hackathon/econstor-cc-by-4.0-json.tgz


### Docker:

* docker
* docker-compose


### Without Docker:

* Elasticsearch
* poppler-utils / pdftools
* git
* PostgreSQL client libraries
* Python 3
    - git+https://github.com/deepset-ai/haystack.git
    - pyyaml
    - pycld2
    - rdflib


Python 3 files
-------------

* `load_docs_into_elasticsearch_split_pdf_lang.py` - Ingest PDF or TXT files into Elastisearch (optional create DPR info)
* `extract_top_hits.py` - Extract the 2 top answers per ai language model per question per item -> store in json files
* `extract_answers_from_files.py` - Build excel tab CSV file / files per model / files per model for analyzed test set.
* `extract_funders_from_rdf.py` - Build flat excel tab CSV file from crossref RDF file of funders (https://gitlab.com/crossref/open_funder_registry)
* `config.yaml` - Configuration file containing: file paths, elasticsearch configuration and use_gpu flag to enable/disable nvidia gpu acceleration

Usage
-----

Check and update `Dockerfile` and `docker-compose.yml`, if neccessary.
Update paths and gpu setting in `python/config.yaml`.

### Docker

1. Switch to folder with docker-compose file.
2. Create subfolders `./textdocuments` and `./results`, if they don't exist.
3. Place documents for ingest either in `./textdocuments/pdf` or in `./textdocuments/text`  
    https://www.econstor.eu/ki-hackathon/econstor-cc-by-4.0-pdf.zip  
    https://www.econstor.eu/ki-hackathon/econstor-cc-by-4.0-txt.tgz
4. Start elasticsearch container via docker-compose `docker-compose up -d haystack-elastic-n0`
5. Import data into Elasticsearch `runPythonInDocker.sh load_docs_into_elasticsearch_split_pdf_lang.py -p|t [-d]`
    * `-p` import pdf files
    * `-t` import txt files
    * `-d` use DensePassageRetriever
6. Extract top answers from Elasticsearch into json files `runPythonInDocker.sh extract_top_hits.py [-d]`
    * `-d` use DensePassageRetriever requires step 3 to also use `-d`
7. Aggregate answers in csv files `runPythonInDocker.sh extract_answers_from_files.py -f -p -t [-d]`
    * `-f` generate one csv with all answers from all modells
    * `-p` generate one csv per modell
    * `-t` generate one csv per modell for testset
    * `-d` use DensePassageRetriever results requires previous steps to also use `-d`
8. Optional Aggregate 1st answer of different questions into a single result per testset item
    `runPythonInDocker.sh merge_answers.py [-i MIN_SCORE -m MIN_SCORE_x_PROB -p -d -o OUTFIILE] INPUTFILE1.csv INPUTFILE2.csv ...`
    * `-i MIN_SCORE` set minimum score for answer to be accepted (default 12.0)
    * `-m MIN_SCORE_x_PROB` set minimum score * probability for answer to be accepted (default 5.0)
    * `-p` use MIN_SCORE_x_PROB instead of MIN_SCORE as check (MIN_SCORE is default)
    * `-d` use DensePassageRetriever results requires previous steps to also use `-d`
    * `-o OUTFILE` defaults to: `./results/answers_csv/merged_answers_%Y-%m-%d.csv`
    * `INPUTFILEx.csv` file created in step 7