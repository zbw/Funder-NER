import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC


class IntentSklearnClassifier:
    def __init__(self, le, clf):
        self.le = le
        self.clf = clf


def train(nlp, expressions):
    le = LabelEncoder()

    labels = [exp.intent for exp in expressions]
    texts = [exp.text for exp in expressions]
    features = [nlp(text).vector for text in texts]

    X = np.stack(features)
    y = le.fit_transform(labels)

    xtrain, xtest, ytrain, ytest = train_test_split(
        X, y, test_size=0.05, random_state=2503,
        )

    clf = GridSearchCV(SVC(C=1, probability=True, class_weight='balanced'),
                       param_grid=[{'C': [150], 'kernel': ['linear']}],
                       n_jobs=8, cv=2, scoring='f1_weighted', verbose=1)

    print('training intent classifier')
    clf.fit(xtrain, ytrain)

    print('accuracy on val set: {}, ({} samples)'
          .format(clf.score(xtest, ytest), xtest.shape[0]))

    intent_classifier = IntentSklearnClassifier(le, clf)
    return intent_classifier


def predict(nlp, intent_model, text):

    assert isinstance(intent_model, IntentSklearnClassifier), (
        'intent_sklearn-classifier: predict: intent_model is not '
        'of type IntentSklearn'
        )

    le = intent_model.le
    clf = intent_model.clf

    x = nlp(text).vector.reshape(1, -1)
    predictions = clf.predict_proba(x)
    intent_ids = np.fliplr(np.argsort(predictions, axis=1))
    intents = le.inverse_transform(intent_ids[0])
    probabilities = predictions[:, intent_ids]

    intents, probabilities = intents.flatten(), probabilities.flatten()

    intent, confidence = list(zip(intents, probabilities))[0]

    return intent, confidence