# Funder-NER
Extracting funder information from scientific papers - with a question answering approach to named entity recognition

## haystack-ner
The folder haystack-ner contains a docker-compose file for running two docker container.
One with elastic search for data storage and one with a python 3 environment for running the scripts utilizing haystack.
For further information see README.md in folder haystack-ner.

## jupyter-nbs/ACKNER-comparison
The folder jupyter-nbs/ACKNER-comparison contains a jupiter notebook with results achieved with code from the AckNER project https://github.com/informagi/AckNER and our testset data compared to results with haystack.
