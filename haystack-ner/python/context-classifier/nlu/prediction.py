from nlu.handlers.prediction import make_prediction
from nlu.model import Model
from nlu.config.config import load_config
import spacy

config = load_config()
print('loading model')
model = Model(config['MODEL_FILEPATH'])
print('loading spaCy')
nlp = spacy.load('en_core_web_sm')


def predict(text):
    return make_prediction(nlp, model, text)