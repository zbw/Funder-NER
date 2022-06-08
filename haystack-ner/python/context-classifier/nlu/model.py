import pickle


class Model:

    def __init__(self, filepath=None):
        if filepath is not None:
            print('loading model from {}'.format(filepath))
            with open(filepath, 'rb') as fs:
                model = pickle.load(fs)
                self.intent_classifier = model.intent_classifier
        else:
            self.intent_classifier = None

    def dump(self, filepath):
        print('saving model to {}'.format(filepath))
        with open(filepath, 'wb') as fs:
            return pickle.dump(self, fs)

    def set_intent_classifier(self, intent_classifier):
        self.intent_classifier = intent_classifier