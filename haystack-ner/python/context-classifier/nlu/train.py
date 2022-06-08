import spacy
from nlu.config.config import load_config
from nlu.handlers import data
from nlu.model import Model
from nlu.classifiers import intent_sklearn


config = load_config()


def train():
    # load load expressions
    filepath = config['TRAIN_FILEPATH']
    expressions = data.load_training_data(filepath)
    # create model
    model = Model()
    # load spaCy
    print('loading spacy model...')
    nlp = spacy.load('en_core_web_sm')
    # train intent classifier
    ic = intent_sklearn.train(nlp, expressions)
    model.set_intent_classifier(ic)
    # save model
    model.dump(config['MODEL_FILEPATH'])


if __name__ == '__main__':
    train()