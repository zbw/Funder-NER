from nlu.classifiers import intent_sklearn
import numpy as np


def make_prediction(nlp, model, text):

    # predict intent
    prediction = {}
    ic = model.intent_classifier

    intent, confidence = intent_sklearn.predict(nlp, ic, text)

    prediction['intent'] = {
        'value': intent,
        'confidence': round(np.float64(confidence), 4),
        }

    return prediction