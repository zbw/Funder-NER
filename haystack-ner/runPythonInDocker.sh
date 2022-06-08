#!/bin/bash
#docker-compose run --rm python-haystack conda run --no-capture-output -n funder-ner python "$@"
docker-compose run --rm python-haystack conda run -n funder-ner python "$@"
