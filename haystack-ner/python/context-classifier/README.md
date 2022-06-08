# Context Classifier

Context classifier to predict if a part of a scientific paper is relevant for funder extraction

## how to setup:

- configure application via config-files in classifier/config directory
- install conda-environment: `conda env create -f environment.yaml`
- activate conda-environment: `source activate context-classifier`
- download spacy model: `python -m spacy download en_core_web_sm`

## how to run

### training

    - activate conda-environment: `source activate context-classifier`
    - copy your csv file to training-data folder and set correct path to file in the config
    - **run**: `PYTHON_ENV=staging python -m nlu.train`

### prediction

- activate conda-environment: `source activate context-classifier`
- import nlu into your code and run prediction (also see `example.py` for more information)

```
from nlu.predict import predict

prediction = predict("your context")
print(prediction)

# returns dict with intent ('funder', 'none') and confidence, e.g.
# {
#   'value': 'valid',
#   'confidence': 0.9876,
# }
```

## how to contribute

- recreate environment.yaml after environment changes
- `conda env export | grep -v "^prefix: " > environment.yaml`
